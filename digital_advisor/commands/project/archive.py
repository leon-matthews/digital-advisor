
import os
from pathlib import Path
import textwrap

from ...config import FOLDERS_DATA

from ..utils import file_size, Print

from .base import ProjectCommand


class Archive(ProjectCommand):
    """
    Archive entire project: code, media, and data together.
    """
    def main(self):
        # Preflight
        self.project_folder = self.ensure_project_path()
        Print.heading(f"Export {self.project_folder.name}")
        self.archive_path = self.calculate_archive_path(self.project_folder)
        message = f"Create export {self.format_path(self.archive_path)}"

        # Confirm
        no_prompt = self.options.no_prompt
        if no_prompt:
            Print.yellow(message)
        else:
            print(textwrap.dedent("""
                The media and data folders will be saved as-is.

                Be sure to run 'da data --production' first if you wish to export
                the currently live data and media files.
            """))
            self.confirm(f"{message} [y/N]?")

        # Create archive
        self.delete_existing()
        if self.options.zip:
            self.create_zip()
        elif self.options.tar:
            self.create_tar()
        else:
            raise RuntimeError("Unknown output file type")
        print()

        # Check output
        if self.archive_path.exists():
            size = file_size(self.archive_path.stat().st_size)
            Print.green(f"{size} archive created")
        else:
            Print.error("No archive created")

    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        # Archive type
        archive_type = parser.add_mutually_exclusive_group(required=True)
        archive_type.add_argument(
            '--zip', action='store_true', help='Create compressed ZIP archive')
        archive_type.add_argument(
            '--tar', action='store_true', help='Create uncompressed TAR archive')

        # Skip confirmation
        parser.add_argument(
            '-y', '--no-prompt', action='store_true',
           help='do not show warning before starting export')

    def create_tar(self):
        # Export website code
        name = self.project_folder.name
        command = (
            f"git archive --format=tar --prefix={name}/ "
            f"--output {self.archive_path} HEAD"
        )
        self.run(command)

        # Add data folders
        with self.cd(self.archive_path.parent):
            for folder_name in FOLDERS_DATA:
                command = f"tar -rf {self.archive_path} {name}/{folder_name}/"
                self.run(command)

    def create_zip(self):
        # Export website code
        name = self.project_folder.name
        command = (
            f"git archive --format=zip -9 --prefix={name}/ "
            f"--output {self.archive_path} HEAD"
        )
        self.run(command)

        # Add data folders
        with self.cd(self.archive_path.parent):
            for folder_name in FOLDERS_DATA:
                command = f"zip -9rq {self.archive_path} {name}/{folder_name}/"
                self.run(command)

    def calculate_archive_path(self, project_folder):
        """
        Calculate the full path to the archive file we are creating.
        """
        # Suffix
        if self.options.zip:
            suffix = '.zip'
        elif self.options.tar:
            suffix = '.tar'
        else:
            raise RuntimeError("Unknown output file type")

        # Generate file name. Use hyphens instead of dots.
        name = project_folder.name
        try:
            name = name.replace('.', '-')
        except ValueError:
            pass
        name = f"{name}{suffix}"

        # Build path
        path = project_folder.parent / name
        return path

    def delete_existing(self):
        """
        Delete existing archive, if present.
        """
        if self.archive_path.exists():
            message = f"Delete existing archive"
            Print.warning(message)
            self.archive_path.unlink()

    def format_path(self, path):
        """
        Produce a plain string version of a path, replacing home with '~'

        Returns: str
        """
        return str(path).replace(str(Path.home()), '~')
