
import shutil

from ... import config

from .. import utils
from ..utils import Print

from .base import ProjectCommand


class Add(ProjectCommand):
    """
    Add an app to the current project.
    """
    def main(self):
        self.ensure_project_name()
        self.project_path = self.get_project_path()
        self.adder = Adder(self.project_path, verbose=self.options.verbose)
        application = self.options.application
        if application:
            self.add(application)
        else:
            self.list()

    def add(self, application):
        """
        Copy files from application's skeleton folders.
        """
        self.adder.check_application(application)
        Print.heading(f"Add {application!r} to {self.project_path.name}")
        self.adder.add(application)
        # TODO: Create initial migration after creating app, if relevant.
        # ~ self.migrate(application)
        # TODO: Add hint
        # ~ Print.help("...")

    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        parser.add_argument(
            'application', metavar='APPLICATION', nargs='?', type=str,
            help='leave empty to list available applications')

    def list(self):
        Print.heading(f"List Available Applications")
        applications = self.adder.list_available()
        applications = self._add_tick_marks(applications)
        print(utils.columnise(applications, width=80))
        print()
        Print.help("To add application, run 'da add APPLICATION'")

    def _add_tick_marks(self, available):
        """
        Add a 'tick' mark to the name of applications already installed.
        """
        installed = set(self.adder.list_installed())
        prefixed = []
        for name in available:
            prefix = '[x]' if name in installed else '[ ]'
            prefixed.append(f"{prefix} {name}")
        return prefixed


class Adder:
    """
    Actually do the application adding.

    Broken off into its own class so that it can be used by other commands.
    """
    def __init__(self, project_root, verbose=False):
        self.project = project_root
        if not self.project.is_dir():
            Print.error(f"Project root folder not found: {self.project!r}")
            raise SystemExit(1)

        self.skeleton = config.FOLDER_PROJECT_BASE / config.SKELETON_FOLDER
        if not self.skeleton.is_dir():
            Print.error(f"Skeleton root folder not found: {self.skeleton!r}")
            raise SystemExit(1)

        self.verbose = verbose

    def add(self, application):
        """
        Recursively copy all the application folders and files into project.

        application
            Name of application to add, eg. 'news'
        """
        self.check_application(application)
        self.copy_folders(application)
        self.delete_migrations(application)

    def delete_migrations(self, application):
        """
        Do not use migrations from skeleton.
        """
        # Remove existing 'migrations' folder
        migrations_folder = self.project / 'source' / application / 'migrations'
        if migrations_folder.exists():
            Print.progress(f"Delete existing migrations for {application}")
            shutil.rmtree(migrations_folder)

            # Create empty migrations folder
            migrations_folder.mkdir()
            init_py = migrations_folder / '__init__.py'
            init_py.touch()

            # Print equivilant commands
            if self.verbose:
                printable = utils.ensure_slash(
                    utils.shortest_path(migrations_folder))
                Print.command(f"rm -fr {printable}")
                Print.command(f"mkdir {printable}")
                Print.command(f"touch {printable}__init__.py")

    def check_application(self, application):
        """
        Abort if application is not available or already installed.
        """
        error = None

        if application not in self.list_available():
            error = f"Application {application!r} not found. Aborting."

        if application in self.list_installed():
            error = f"Application {application!r} already installed. Aborting."

        if error:
            Print.error(error)
            Print.help("To list applications, run 'da add'")
            raise SystemExit(1)

    def copy_folders(self, application):
        """
        Copy all application folders, call forth any skeletons that exist.
        """
        if self.verbose:
            Print.progress(f"Install {application}")
        for app_folder in config.APPS_FOLDERS:
            skeleton = self.skeleton / app_folder / application
            # Not all applications use all app. folders
            if not skeleton.is_dir():
                continue

            # Copy folders
            project = self.project / app_folder / application
            utils.copytree(skeleton, project, verbose=self.verbose)

            # Call forth skeletons!
            utils.call_forth_skeletons(project, verbose=self.verbose)

    def list_available(self):
        """
        Return set of app names from the given project name.
        """
        return self._list(self.skeleton)

    def list_installed(self):
        return self._list(self.project)

    def _list(self, root):
        """
        Find all application names under the given project root.

        Returns:
            Sorted list of project names.
        """
        apps = set()
        for name in config.APPS_FOLDERS:
            app_folder = root / name
            for path in app_folder.iterdir():
                if path.is_dir() and not path.name.startswith('.'):
                    apps.add(path.name)
        return sorted(apps)
