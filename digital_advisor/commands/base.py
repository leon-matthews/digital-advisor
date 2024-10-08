"""
Common base class for all sub-commands.

Commands are further specialised into commands that operate on
servers or those that operate on projects themselves. These
correspond to the 'da' and 'da-servers' commands.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import sys

import invoke

from . import utils
from .utils import path_to_string, path_to_string_remote, Print


class CommandBase:
    FILES_FOLDER = None

    def __init__(self):
        """
        Initialiser.

        TODO: Rename `self.connection` to `self.default_connection`
        TODO: Use keyword argument for connections, as per `self.run_remote()`
        """
        self.connection = None
        self.name = self.__class__.__name__.lower()

    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        pass

    @contextmanager
    def cd(self, folder):
        """
        Context manager to change local directory.

        For remote connections use `run_many_remote()`, with a 'cd' command
        at the front.
        """
        previous = Path.cwd()
        target = utils.relative_path(previous, folder)

        # Do nothing?
        if target == Path('.'):
            yield
            return

        # Change and print
        os.chdir(target)
        Print.command(f"cd {target}")
        yield
        os.chdir(previous)

    def confirm(self, message):
        """
        Prompt user for confirmation.
        """
        Print.confirm(message)
        response = input().lower().strip()
        if not (response == 'y' or response == 'yes'):
            sys.exit(1)

    def get_files_path(self, relpath='.'):
        """
        Return full path to relpath under the command's 'files' folder.
        """
        # Check folder
        folder = Path(__file__).resolve().parent.parent / 'files' / self.FILES_FOLDER
        if not folder.is_dir():
            raise FileNotFoundError(f"Folder  for 'files' not found: {folder}")

        # Check path
        path = folder / relpath
        if not path.exists():
            raise FileNotFoundError(f"Relative path '{relpath}' under 'files' not found: {path}")
        return path

    def main(self):
        message = "Command class {!r} requires a 'main()' method"
        raise NotImplementedError(message.format(self.__class__.__name__))

    def download_file(self, source, destination, **kwargs):
        """
        Download a single file from remove server.
        """
        source = path_to_string_remote(source, self.connection, is_dir=False)
        destination = path_to_string(destination)
        self._rsync_file(source, destination, **kwargs)

    def download_folder(self, source, destination, **kwargs):
        """
        Download files from remote server to local folder.

        WARNING: Local files not present remotely will be DELETED.
        """
        if not destination.is_dir():
            Print.error(f"Rsync destination must be an existing folder: {destination}")
            sys.exit(1)

        source = path_to_string_remote(source, self.connection)
        destination = path_to_string(destination)
        self._rsync_folders(source, destination, **kwargs)

    def upload_folder(self, source, destination, **kwargs):
        """
        Upload files from local folder server to remote server.

        WARNING: Remote files not present locally will be DELETED.

        See the docs for `_rsync()` for the available keyword-arguments.
        """
        if not source.is_dir():
            Print.error(f"Rsync source must be an existing folder: {source}")
            sys.exit(1)
        source = path_to_string(source)
        destination = path_to_string_remote(destination, self.connection, is_dir=True)
        self._rsync_folders(source, destination, **kwargs)

    def run(self, command, hide=False, warn=False, pty=False):
        """
        Run external command.

        Args:
            command (str):
                Command to run.
            hide (bool):
                Hide stdout if `True`.
            warn (bool):
                Warn only, do not abort on command failure.
            pty (bool):
                Connect to process through a pseudoterminal (pty),
                rather than directly.
        """
        hide = 'stdout' if hide else False
        Print.command(command)
        try:
            result = invoke.run(command, hide=hide, warn=warn, pty=pty)
        except invoke.UnexpectedExit:
            Print.error(f"Command failed: {command}")
            sys.exit(1)

        # If warn is True, print error anyway.
        if result.exited:
            Print.error(f"Command failed: {command}")
        return result

    def run_many_remote(self, commands, pty=False):
        """
        Run multiple commands in a single command chain.
        """
        commands = [f"{{ {command}; }}" for command in commands]
        command = ' && '.join(commands)
        self.run_remote(command, pty=pty)

    def run_remote(self, command, *, connection=None, hide=False, pty=False):
        Print.command(command)
        if connection is None:
            connection = self.connection
        hide = 'stdout' if hide else False
        result = connection.run(command, hide=hide, pty=pty)
        return result

    def set_options(self, options):
        """
        Set the command's options, as parsed by the main program.
        """
        self.options = options
        if hasattr(options, 'connection'):
            self.connection = options.connection

    def sudo(self, command, hide=False):
        hide = 'stdout' if hide else False
        result = invoke.sudo(command, hide=hide)
        return result

    def sudo_remote(self, command, hide=False):
        Print.command('sudo ' + command)
        hide = 'stdout' if hide else False
        result = self.connection.sudo(command, hide=hide)
        return result

    def _create_subparser(self, subparsers, global_parser):
        docs = self.__doc__
        if not docs:
            message = "Missing docstring in command class: {!r}"
            raise TypeError(message.format(self.__class__.__name__))
        short = utils.first_sentence(docs)
        if short.endswith('.'):
            short = short[:-1]
        parser = subparsers.add_parser(self.name, help=short, parents=[global_parser])
        return parser

    def _rsync_file(self, source: str, destination: str, *, dry_run: bool = False):
        """
        Rsync a single file between local and remote.

        Args:
            source:
                Path to master file
            destination:
                Path to copy to
            dry_run:
                Set to true to run test.
        """
        # Prepare arguments for rsync
        args = [
            '--checksum',
            '--human-readable',
            '--stats',
            '--info=all1,flist0,progress1',
        ]
        if dry_run:
            args.append('--dry-run')
        arguments = ' '.join(args)
        command = f"rsync {source} {destination} {arguments}"
        return self.run(command)

    def _rsync_folders(self, source, destination, *, exclude=None, dry_run=False):
        """
        Rsync between local and remote folders.

        The public API is broken into various public methods, as this is a very
        dangerous operation. We must do our upmost to make the API as
        idiot-proof as possible - especially as future-me is the idiot in
        question!

        Args:
            source (str):
                Path to master copy of data.
            destination (str):
                Path to data to be updated.
            exclude (list):
                List of glob patterns to exclude. See the section
                'INCLUDE/EXCLUDE PATTERN RULES' in the rsync man page
                for details.
            dry_run (bool):
                Show actions to be taken, but perform none. Defaults to False.

        See: https://linux.die.net/man/1/rsync
        """
        # Ensure trailing slashes on folder names
        message = "Rsync folder paths must end with trailing slash"
        assert source.endswith('/'), message
        assert destination.endswith('/'), message

        # Prepare arguments for rsync
        args = [
            '--checksum',
            '--delete-delay',
            '--human-readable',
            '--no-inc-recursive',
            '--recursive',
            '--stats',
            '--progress',
        ]
        for pattern in exclude:
            args.append(f"--exclude '{pattern}'")
        if dry_run:
            args.append('--dry-run')
        arguments = ' '.join(args)
        command = f"rsync {source} {destination} {arguments}"
        return self.run(command)
