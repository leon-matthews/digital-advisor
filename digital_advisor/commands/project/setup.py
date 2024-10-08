
from pathlib import Path
import sys

from ...servers import Python2, Python3

from ..utils import Print

from .base import ProjectCommand


class Setup(ProjectCommand):
    """
    Set up environment for current project
    """
    def main(self):
        # Options
        self.verbose = self.options.verbose

        # Checks
        project_folder = self.ensure_project_path()
        active = self.get_active_venv()
        if active:
            Print.error('Virtual environment still active. Aborting.')
            Print.help("To continue, run 'deactivate'")
            sys.exit(1)

        # IDE
        Print.heading("Create IDE project")
        self.create_geany_project(project_folder)

        # Create new venv
        Print.heading("Create Python environment")
        self.delete_venv()
        virtualenv_folder = self.create_venv()
        print()

        # Install dependencies
        Print.heading("Install 3rd-Party Packages")
        self.install_requirements()
        self.set_virtualenv_project(virtualenv_folder, project_folder)
        print()

        # Complete
        print()
        Print.help(f"Completed. To begin, run 'workon {project_folder.name}'")

    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        # No migrate
        parser.add_argument(
            '-m', '--no-migrate', action='store_true',
            help="do not run 'migrate' on database")

    def create_venv(self):
        """
        Create either a Python2 or a Python3 environment.

        We use the 'virtualenv' command, rather than 'python3 -m venv', as that
        is what the author of the Apache mod_wsgi recomends:

        https://modwsgi.readthedocs.io/en/develop/user-guides/virtual-environments.html

        Returns:
            Path to virtualev folder.
        """
        connection = self.get_server_staging()
        type_ = connection.server_type
        folder = self.get_venv_path()

        # Create virtualenv, Python2 or Python3
        Print.progress(f"Create Python environment")
        verbosity = '-v' if self.verbose else '-q'

        if isinstance(type_, Python2):
            self.run(f"virtualenv {verbosity} -p python2 {folder}")
            get_pip = self.get_files_path('python2-get-pip.py')
            python2 = self.get_venv_path() / 'bin' / 'python2'
            self.run(f"{python2} {get_pip}")
        elif isinstance(type_, Python3):
            self.run(f"virtualenv {verbosity} -p python3 {folder}")
        else:
            Print.error(f"Unknown Python version for server: {type_!r}")
            sys.exit(1)

        return folder

    def delete_venv(self):
        folder = self.get_venv_path()
        if folder.exists():
            Print.progress("Delete existing Python environment")
            assert folder.is_dir(), 'venv should be a folder'
            self.run(f"rm -fr {folder}")

    def install_requirements(self):
        """
        Install required packages locally.

        Start with packages from 'deploy/requirements.txt'.  If it exists
        install packages from 'deploy/development.txt'.
        """
        venv_bin = self.get_venv_path() / 'bin'
        path = self.ensure_project_path() / 'deploy' / 'requirements.txt'
        path_development = path.parent / 'development.txt'
        with self.cd(venv_bin):
            quiet = '' if self.verbose else '--quiet'
            pip = f"./pip install {quiet}"

            # Packaging tools
            self.run(f"{pip} --upgrade pip setuptools wheel")

            # Requirements
            self.run(f"{pip} --requirement {path}")

            # Development environment
            if path_development.is_file():
                self.run(f"{pip} --requirement {path_development}")

    def set_virtualenv_project(self, virtualenv: Path, project: Path) -> None:
        """
        Associate virtualenv with project folder for virtualenvwrapper.

        We can't run the BASH function directly, so we duplicate its effect
        instead; we write the project's path as a single line into the
        file ``.project`` in the virtualenv's root folder.

        Once done, typing ``workon project`` will warp us into the correct
        folder.

        Args:
            virtualenv:
                Path to virtualenv's root folder.
            project:
                Path to project's root folder.

        Returns:
            None
        """
        path = virtualenv / '.project'
        with open(path, 'wt', encoding='utf-8') as fp:
            fp.write(str(project))
