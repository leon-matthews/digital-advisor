
from pathlib import Path
import re
import sys

from ... import config
from .. import utils
from ..utils import Print

from .add import Adder
from .base import ProjectCommand


class Create(ProjectCommand):
    """
    Create new project based on skeleton project.
    """
    dotfiles = ('.gitignore', 'settings.ini')

    def main(self):
        # Config
        self.connection = config.get_connection('git')
        self.domain = self.options.domain.lower()
        self.folder = config.FOLDER_PROJECT_BASE / self.domain
        self.git_folder_name = f"{self.domain}.git"
        self.skeleton = config.FOLDER_PROJECT_BASE / config.SKELETON_FOLDER
        self.verbose = self.options.verbose

        # Checks
        self.check_domain_format()
        Print.heading(f"Create {self.domain}")
        self.check_project_is_new()
        self.check_skeleton_exists()
        message = f"Create new project: '{self.domain}'?"
        self.confirm(f"{message} [y/N]?")
        print()

        # Create empty repo
        self.create_bare_remote()
        self.clone_remote()

        # Copy from skeleton
        self.create_application_folders()
        self.create_data_folders()
        self.copy_dotfiles()
        self.copy_deployment()

        # Copy apps from skeleton
        print()
        Print.heading("Add default applications")
        adder = Adder(self.folder, verbose=self.verbose)
        for name in config.APPS_DEFAULT:
            adder.add(name)

        # Settings
        self.install_secret_key()

        # Commit to git and push to remote
        print()
        Print.heading("Initial git commit")
        self.git_initial_commit()
        print()
        Print.heading("Push project to git server")
        self.git_push()

    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        parser.add_argument(
            'domain',
            metavar='DOMAIN',
            help="domain name for project, eg. 'example.com'")

    def check_domain_format(self):
        """
        Project name must be valid domain name, eg. 'example.com'
        """
        if not re.match(r'^[\w\-]+\.[\w\-\.]+$', self.domain):
            Print.red(f"Domain name format error: '{self.domain}'")
            sys.exit(1)

    def check_project_is_new(self):
        """
        Project cannot overwrite existing code.
        """
        Print.progress("Check that project does not already exist")
        # Local
        if self.folder.exists():
            Print.red(f"Project already exists locally: {self.folder}")
            sys.exit(1)

        # Remote
        existing = self.list_projects_remote()
        if self.domain in existing:
            Print.red(f"Project already exists on Git server")
            sys.exit(1)

    def check_skeleton_exists(self):
        """
        Check that the skeleton project exists
        """
        if not self.skeleton.is_dir():
            Print.red(f"Project skeleton not found: {self.skeleton}")
            sys.exit(1)

    def clone_remote(self):
        """
        Download (bare) repo from remote server.
        """
        Print.progress("Clone remote git repository locally")
        with self.cd(config.FOLDER_PROJECT_BASE):
            remote_path = config.FOLDER_GIT_SERVER / self.git_folder_name
            host_string = f"{self.connection.user}@{self.connection.host}"
            command = f"git clone --quiet {host_string}:{remote_path}"
            self.run(command)

    def copy_deployment(self):
        """
        Copy and customise deployment configuration.
        """
        Print.progress("Copy and customise deployment files")

        # Copy full tree
        source = self.skeleton / 'deploy'
        destination = self.folder / 'deploy'
        utils.copytree(source, destination, verbose=self.verbose)

        # Customise Apache config.
        Print.progress("Customise Apache configuration")
        apache = self.folder / 'deploy' / 'apache'
        for path in apache.iterdir():
            utils.search_and_replace(path, config.SKELETON_FOLDER, self.domain)

        # Skeletons!
        utils.call_forth_skeletons(self.folder / 'deploy')

    def copy_dotfiles(self):
        """
        Copy root-level configuration files
        """
        Print.progress("Copy configuration files from skeleton")
        for name in self.dotfiles:
            source = self.skeleton / name
            utils.copy(source, self.folder, verbose=self.verbose)

    def create_application_folders(self):
        """
        Create root folders for apps to live in, copy root files from skeleton.
        """
        Print.progress("Create application folders")
        for name in config.APPS_FOLDERS:
            folder = self.folder / name

            # Create empty folder
            if not folder.is_dir():
                folder.mkdir()
                if self.verbose:
                    Print.command(f"mkdir {utils.shortest_path(folder)}")

            # Copy root files from skeleton ('manage.py', etc..)
            skeleton = self.skeleton / name
            for path in skeleton.iterdir():
                if path.is_file():
                    utils.copy(path, folder, verbose=self.verbose)

    def create_bare_remote(self):
        """
        Create empty (and bare) git repo on remote server.
        """
        Print.progress("Create empty remote git repository")
        folder = Path(config.FOLDER_GIT_SERVER) / self.git_folder_name
        commands = [
            f"mkdir {folder}",
            f"cd {folder}",
            "git init --bare",
        ]
        self.run_many_remote(commands)

    def create_data_folders(self):
        """
        Create data folders and copy '.gitignore' files from skeleton.
        """
        Print.progress("Create media and data folders")
        for name in config.FOLDERS_DATA:
            folder = self.folder / name
            # Make folder
            if not folder.is_dir():
                folder.mkdir()
                if self.verbose:
                    Print.command(f"mkdir {utils.shortest_path(folder)}")

            # Create placeholder for git
            source = self.skeleton / name / '.gitignore'
            utils.copy(source, folder, verbose=self.verbose)

    def git_initial_commit(self):
        """
        Update local Git repository
        """
        with self.cd(self.folder):
            self.run("git add .")
            self.run("git add -f media/.gitignore")
            self.run("git add -f data/.gitignore")
            self.run("git commit -q -m'Project created'")
            self.run("git gc --aggressive --quiet")

    def git_push(self):
        with self.cd(self.folder):
            self.run("git push --progress origin master")

    def install_secret_key(self):
        Print.progress("Create and install unique SECRET_KEY value")
        # Create random secret key
        secret_key = utils.create_secret_key()
        base_py = self.folder / 'source' / 'common' / 'settings' / 'settings.py'
        needle = '{{ SECRET_KEY }}'
        if needle not in base_py.read_text():
            Print.error(f"{needle!r} not found in {base_py}")
            raise SystemExit(1)
        utils.search_and_replace(base_py, needle, secret_key)
