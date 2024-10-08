
import argparse
import os
import shlex
import subprocess

from ...servers import Python2, Python3

from ..utils import Print

from .base import ProjectCommand


class Test(ProjectCommand):
    """
    Execute automated tests
    """
    def main(self):
        self.ensure_active_venv()
        connection = self.get_server_staging()
        self.server_type = connection.server_type
        return self.run_tests()

    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        # Tags
        tags_group = parser.add_mutually_exclusive_group()
        tags_group.add_argument(
            '--all',
            action='store_true',
            help="run all tests, even those marked 'slow'"
        )
        tags_group.add_argument(
            '--slow',
            action='store_true',
            help="only run tests tagged 'slow'"
        )

        # Labels (optional)
        parser.add_argument(
            'test_label',
            metavar="LABEL",
            nargs='*',
            type=str,
            help="dotted path to tests, eg. 'package.module.Class.method'"
        )

        # Parallel execution
        parser.add_argument(
            '-j',
            metavar='N',
            default=argparse.SUPPRESS,
            dest='parallel',
            nargs='?',
            type=int,
            help="Run tests using either N processes, or number of CPUs",
        )

    def build_command(self):
        command = [
            self._get_python_version(),
            './manage.py',
            'test',
            '--failfast',
            '--settings', 'common.settings.testing',
        ]

        # Verbosity
        verbosity = self._get_verbosity()
        if verbosity:
            command.append(verbosity)

        # Parallel
        # ~ '--parallel', '4',
        if hasattr(self.options, 'parallel'):
            command.append('--parallel')
            num_processes = getattr(self.options, 'parallel', None)
            if num_processes is None:
                num_processes = os.cpu_count() // 2
            command.append(str(num_processes))

        # Tags
        if isinstance(self.server_type, Python3):
            tags = self._get_tags()
            if tags:
                command.append(tags)

        # Labels
        if self.options.test_label:
            command.append(' '.join(self.options.test_label))

        return ' '.join(command)

    def run_tests(self):
        command = self.build_command()
        source = self.get_project_path() / 'source'
        with self.cd(source):
            Print.command(command)
            arguments = shlex.split(command)
            result = subprocess.run(arguments)
        return result.returncode

    def _get_python_version(self):
        if isinstance(self.server_type, Python2):
            return 'python2'
        elif isinstance(self.server_type, Python3):
            if self.options.quiet:
                return 'python3'
            else:
                return 'python3 -X dev'
        else:
            Print.error(f"Unknown Python version for server: {type_!r}")
            sys.exit(1)

    def _get_tags(self):
        """
        Build options string to select tests by tag.

        Returns:
            Option string
        """
        if self.options.all:
            option = ''
        elif self.options.slow:
            option = '--tag="slow"'
        else:
            option = '--exclude-tag="slow"'

        return option

    def _get_verbosity(self):
        # Most quiet
        if self.options.quiet:
            return '-v0'

        # Default output
        if not self.options.verbose:
            return ''

        # Increase verbosity with each repeat
        if self.options.verbose == 1:
            return '-v2'
        else:
            return '-v3'
