
import os
from pathlib import Path
import textwrap
from typing import List, Optional

from invoke import UnexpectedExit

from ... import config

from ..utils import file_size, join_and, Print

from .base import ProjectCommand


class Dumpdata(ProjectCommand):
    """
    Create or update a dumpdata export archive.

    Most apps have an 'import_dumpdata' command that take as their
    input the output of this command.

    A zip file is created containing a full database dump in JSON format and
    optionally a copy of its media folder, sans thumbnails (as they are handled
    by another app).

    Zip archives are a little awkward to create on Linux systems, but are used
    here as reading the contents of a zip file in Python is very convenient.
    """
    def main(self):
        # Preflight
        app_names = self.options.apps
        if self.options.server is None:
            self.options.server = self.settings_ini['servers']['production']

        message = f"Dumpdata from {self.options.server} for {join_and(app_names)}"
        Print.heading(message)
        self.connection = self.get_connection(self.options.server)
        self.project_folder = config.FOLDER_PROJECT_REMOTE / self.options.project
        self.check_remote(self.options.project, self.options.apps)

        for app in app_names:
            path = self.dumpdata_create(app)
            try:
                self.dumpdata_download(path)
            finally:
                self.delete_remote(path)

    def delete_remote(self, path: str) -> None:
        """
        Delete file from remote server.

        Args:
            Path to remote file.

        Returns:
            None
        """
        Print.progress(f"Delete {path}")
        self.run_remote(f"rm {path}")

    def dumpdata_create(self, app: str) -> str:
        """
        Create dumpdata archive on remote server.

        Args:
            app:
                Name of app, eg. 'news'

        Returns:
            Full path of dumpdata archive, eg. '/srv/websites/test.com/news.zip'
        """
        # Dump JSON data
        Print.progress(f"Export database tables for {app}")
        json_name = f"{app}.json"
        json_path = self.project_folder / json_name
        zip_name = f"{app}.zip"
        zip_path = self.project_folder / zip_name
        command = f"dumpdata --indent=4 {app} --output {json_path}"
        self.run_manage_remote(command)

        # Zip dumpdata
        Print.progress(f"Create zip archive for {app}")
        Print.progress(f"Add dumpdata file for {app} to {zip_name}")
        commands = [
            f"cd {self.project_folder}",
            f"zip -9 -q {zip_name} {json_name}",
            f"rm {json_path}",
        ]
        try:
            self.run_many_remote(commands)
        except UnexpectedExit:
            self.run_remote(f"rm -f {json_path} {zip_path}")
            raise

        # Zip media
        Print.progress(f"Add media folder for {app} to {zip_name}")
        commands = [
            f"cd {self.project_folder}",
            f"cd media/",
            f"zip -r -q {zip_path} {app}/",
        ]
        try:
            self.run_many_remote(commands)
        except UnexpectedExit:
            Print.warning(f"No media folder found for {app}")

        return zip_path

    def dumpdata_download(self, path: str):
        """
        Download dumpdata archive onto local machine.
        """
        Print.progress(f"Download {path}")
        self.download_file(path, Path.cwd())

    def check_remote(self, project: str, app_names: List[str]) -> None:
        """
        Ensure that remote project exists and that given app names are valid.

        Raises:
            SystemExit:
                If any problems encountered.

        Returns:
            None
        """
        Print.progress(f"Check that apps {join_and(app_names)} exist remotely")
        source = self.project_folder / 'source'
        try:
            result = self.run_remote(f"ls {source}", hide=True)
        except UnexpectedExit:
            Print.error(f"Project {project!r} not found on {self.connection.host}")
            raise SystemExit(1)

        folders = [line.strip() for line in result.stdout.split() if '.' not in line]
        for app_name in app_names:
            if app_name not in folders:
                Print.error(f"App {app_name!r} not found in {source}")
                raise SystemExit(1)

    def get_connection(self, hostname: str):
        try:
            return config.get_connection(hostname)
        except KeyError:
            Print.error(f"Unknown server name given: {hostname}")
            print("Valid servers are: ")
            print(config.server_summary(indent='    ', show_domain=True))
            raise SystemExit(1)

    def add_arguments(self, parser):
        # List of apps
        parser.add_argument(
            'apps',
            metavar='APP',
            nargs='+',
            help="One or more app names",
        )

        # Override project name?
        parser.add_argument(
            '-p',
            '--project',
            default=self.get_project_name(),
            help="Overide project name (current by default)",
        )

        # Server
        parser.add_argument(
            '-s',
            '--server',
            default=None,
            help="Override server (production by default)",
        )
