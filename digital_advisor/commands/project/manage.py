
import argparse

from ..utils import Print

from .base import ProjectCommand


class Manage(ProjectCommand):
    """
    Run a Django management command.
    """
    def main(self):
        self.ensure_active_venv()

        # Heading
        Print.heading(f"Run Django management command")
        print()

        # Build command
        command = ' '.join(self.options.command)

        # Run
        if self.options.production:
            self.confirm("Run command on PRODUCTION server [y/N]?")
            self.connection = self.get_server_production()
            self.run_manage_remote(command)
        elif self.options.staging:
            self.confirm("Run command on STAGING server [y/N]?")
            self.connection = self.get_server_staging()
            self.run_manage_remote(command)
        else:
            Print.help("Run ./manage.py locally")
            self.run_manage(command)

    def add_arguments(self, parser):
        # Optionally select remote server instead of running locally
        server = parser.add_mutually_exclusive_group()
        server.add_argument(
            '--production', action='store_true', help="Run on production server")
        server.add_argument(
            '--staging', action='store_true', help="Run on staging server")

        # Pass remaining arguments to management command
        parser.add_argument('command', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
