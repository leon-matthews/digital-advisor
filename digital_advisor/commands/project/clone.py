
from pathlib import Path
import sys

from ... import config
from ..utils import columnise, Print

from .base import ProjectCommand


class Clone(ProjectCommand):
    """
    Clone project from git server
    """
    def main(self):
        """
        TODO
            * Move steps out of clone() into here.
            * Add user help at end of command.
            * Run migrate at end
            * Create local user at end
        """
        self.connection = config.get_connection(config.GIT_SERVER)
        project_name = self.options.project
        if project_name:
            Print.heading(f"Clone {project_name}")
            self.clone(project_name)
        else:
            Print.heading(f"List Active Projects")
            self.list()

    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        parser.add_argument('project', metavar='PROJECT', nargs='?', type=str,
                            help='leave empty for a list of projects')

    def clone(self, name):
        """
        Fetch code from server
        """
        # Check paths
        projects = Path(config.FOLDER_PROJECT_BASE)
        destination = Path(projects, name)
        if destination.exists():
            Print.error("Already cloned: {}".format(destination))
            sys.exit(1)

        # Fetch code from server
        Print.progress("Fetching project code from server")
        with self.cd(projects):
            path = config.FOLDER_GIT_SERVER / name
            command = f"git clone --progress ubuntu@git.example.com:{path}.git"
            print(command)
            self.run(command)

    def list(self):
        """
        Print list of available projects.
        """
        projects = self.list_projects_remote()
        projects = self._add_tick_marks(projects)
        print(columnise(projects))
        Print.help("To begin, run eg. 'da clone example.com'")

    def _add_tick_marks(self, projects):
        """
        Add a 'tick' mark to the name of projects that we already have a copy of.
        """
        folder = Path(config.FOLDER_PROJECT_BASE)
        prefixed = []
        for name in projects:
            local = folder / name
            prefix = '[x]' if local.exists() else '[ ]'
            prefixed.append(f"{prefix} {name}")
        return prefixed
