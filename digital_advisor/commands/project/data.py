
from ..utils import Print

from .base import ProjectCommand


class Data(ProjectCommand):
    """
    Replace local data with that from webserver.

    TODO:

    * Change rsync options:
        - Exclude thumbnails
        - Show progress

    """
    def main(self):
        # Load options
        no_prompt = self.options.no_prompt
        dry_run = self.options.dry_run

        if self.options.production:
            role = 'production'
            self.connection = self.get_server_production()
        elif self.options.staging:
            role = 'staging'
            self.connection = self.get_server_staging()
        else:
            Print.error("Unknown server specified")
            raise SystemExit(1)

        message = f"Download data from {role.upper()}"
        if dry_run:
            message += " (DRY RUN)"

        # Pre-flight
        Print.heading(message)
        self.ensure_project_name()

        # Confirm overwrite
        if not dry_run:
            Print.error("This will DELETE your local media and database files!")
        if no_prompt:
            Print.progress(message)
        else:
            self.confirm(f"{message} [y/N]?")
        print()

        # Downloads
        self.download_database(role, dry_run)
        self.download_media_files(role, dry_run)

        # Finished
        Print.help("Run './manage.py migrate' if database schema has changed")

    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        # Dry run
        parser.add_argument(
            '-n', '--dry-run', action='store_true',
            help='only show which files would be transfered')

        # No prompt
        parser.add_argument(
            '-y', '--no-prompt', action='store_true',
            help='do not ask for confirmation before deleting data')

        # Select server
        server = parser.add_mutually_exclusive_group(required=True)
        server.add_argument(
            '-P',
            '--production',
            action='store_true',
            help="Download from production server",
        )
        server.add_argument(
            '-S',
            '--staging',
            action='store_true',
            help="Download from staging server",
        )

    def download_database(self, role, dry_run):
        Print.progress(f"Downloading database from {role.upper()}...")
        source = self.get_project_path_remote() / 'data'
        destination = self.get_project_path() / 'data'
        exclude = ('.gitignore',)
        self.download_folder(source, destination, dry_run=dry_run, exclude=exclude)
        print()

    def download_media_files(self, role, dry_run):
        Print.progress(f"Downloading media files from {role.upper()}...")
        source = self.get_project_path_remote() / 'media'
        destination = self.get_project_path() / 'media'
        exclude = ('.gitignore',)
        self.download_folder(source, destination, dry_run=dry_run, exclude=exclude)
        print()
