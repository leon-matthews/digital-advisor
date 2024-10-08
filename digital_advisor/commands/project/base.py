
import configparser
import os
from pathlib import Path
from string import Template
import sys
from typing import List

from ... import config
from ..utils import Print

from ..base import CommandBase


class ProjectCommand(CommandBase):
    FILES_FOLDER = 'project'

    def __init__(self):
        super().__init__()
        self._settings_ini = None

    def create_geany_project(self, project_folder: Path) -> None:
        """
        Create project definition file for Geany (https://geany.org/).
        """
        # Build context
        context = {
            'NAME': project_folder.name,
            'BASE_PATH': project_folder,
        }

        # Build project definition from templatef
        template_path = self.get_files_path('template.geany')
        with open(template_path, 'rt') as fp:
            template = Template(fp.read())
        body = template.substitute(context)

        # Write it
        geany = project_folder.name.split('.')[0] + '.geany'
        path = project_folder / geany
        Print.progress(f"Write project file to {path}")
        with open(path, 'wt', encoding='utf-8') as fp:
            fp.write(body)

    def ensure_active_venv(self):
        """
        Abort if active venv does not match the current project.

        Also abort, of course, if there is no current venv or project.
        """
        project = self.ensure_project_name()
        venv = self.get_active_venv()
        if not venv:
            Print.error("No venv active. Aborting.")
            Print.help(f"To activate, run 'workon {project}'")
            sys.exit(1)
        if project != venv:
            Print.error("Project and venv do not match. Aborting.")
            Print.help(f"Run 'workon {project}', or 'cd ../{venv}'")
            sys.exit(1)
        return venv

    def ensure_project_name(self):
        """
        Like `get_project_name()`, but aborts if not in project folder.
        """
        name = self.get_project_name()
        if not name:
            Print.red('Not in a project folder. Aborting.')
            sys.exit(1)
        return name

    def ensure_project_path(self):
        path = self.get_project_path()
        if not path:
            Print.red('Not in a project folder. Aborting.')
            sys.exit(1)
        return path

    def get_active_venv(self):
        """
        Return name of current virtualenv.

        Returns: Path to virtualenv, None if no virtualenv active.
        """
        path = os.environ.get('VIRTUAL_ENV')
        if path is None:
            return None
        vpath = Path(path)
        return vpath.name if vpath else None

    def get_project_name(self):
        """
        Return name of current project.

        Being 'in' a project is having your `cwd` being somewhere under
        the local projects folder.  The *name* of the project is the top-level
        directory under FOLDER_PROJECT_BASE.
        """
        # Calculate project folder
        folder = config.FOLDER_PROJECT_BASE
        cwd = Path.cwd()
        try:
            relative = cwd.relative_to(folder)
            name = relative.parts[0]
        except (IndexError, ValueError):
            name = None
        return name

    def get_project_path(self):
        """
        Return path to project folder.
        """
        name = self.get_project_name()
        if name is None:
            return None
        return config.FOLDER_PROJECT_BASE / name

    def get_project_path_remote(self):
        """
        Return path to project folder.
        """
        name = self.get_project_name()
        if name is None:
            return None
        return config.FOLDER_PROJECT_REMOTE / name

    def get_server_by_role(self, role):
        """
        Return the connection object for the given role.

        Args:
            role (str): Server role. Either 'staging' or 'production'

        Returns: Connection object.
        """
        try:
            hostname = self.settings_ini['servers'][role]
        except KeyError:
            Print.error(f"Could not find {role} server in 'settings.ini'")
            sys.exit(1)

        try:
            return config.get_connection(hostname)
        except KeyError:
            Print.error(f"Unknown {role} server in 'settings.ini': {hostname}")
            print("Valid servers are: ")
            print(config.server_summary(indent='    ', show_domain=True))
            sys.exit(1)

    def get_server_production(self):
        return self.get_server_by_role('production')

    def get_server_staging(self):
        return self.get_server_by_role('staging')

    def get_venv_path(self):
        project = self.ensure_project_name()
        base = os.environ.get('WORKON_HOME')
        if not base:
            Print.error("WORKON_HOME not found. Is 'virtualenvwrapper' installed?")
            sys.exit(1)
        return Path(base) / project

    def get_venv_path_remote(self):
        name = self.ensure_project_name()
        folder = config.FOLDER_PROJECT_REMOTE
        return Path(folder) / name / 'env'

    def list_projects_local(self) -> List[Path]:
        """
        List projects checked-out locally.
        """
        base = config.FOLDER_PROJECT_BASE
        subfolders = [Path(f.path) for f in os.scandir(base) if f.is_dir()]
        return subfolders

    def list_projects_remote(self):
        """
        Fetch a sorted list of every project on git server.
        """
        Print.progress("List projects on git server")
        connection = config.get_connection(config.GIT_SERVER)
        result = self.run_remote(
            f"ls {config.FOLDER_GIT_SERVER}",
            connection=connection,
            hide=True)
        folders = result.stdout.split()
        folders = [f.replace('.git', '') for f in folders]
        folders.sort()
        return folders

    def run_manage(self, command='', pty=True, **kwargs):
        """
        Run a Django 'manage.py' command from the projects 'source' directory.

        Args:
            command (str):
                Command to run, including its arguments.
            kwargs (dict):
                Keyword arguments to pass down to `CommandBase.run()` method.

        """
        self.ensure_active_venv()
        command = f"./manage.py {command}"
        source = self.get_project_path() / 'source'
        with self.cd(source):
            return self.run(command, pty=pty, **kwargs)

    def run_manage_remote(self, command, pty=True):
        commands = []
        folder = self.get_project_path_remote()
        python = self.get_venv_path_remote() / 'bin' / 'python'
        commands.append(f"cd {folder}")
        settings = ' --settings=common.settings.production' if command else ''
        commands.append("export DJANGO_SETTINGS_MODULE=common.settings.production")
        commands.append(f"{python} ./source/manage.py {command}{settings}")
        commands.append("sudo chown -R ubuntu:www-data data/ media/")
        commands.append("sudo chmod -R g+w data/ media/")
        self.run_many_remote(commands, pty=pty)

    @property
    def settings_ini(self) -> configparser.ConfigParser:
        """
        Current project's settings.ini as a cached mapping.

        cached property, so you can use it directly::

            >>> self.settings_ini['keys']['google_api_key']
            'UA-555-4933'

        """
        if self._settings_ini is None:
            base = self.ensure_project_path()
            self._settings_ini = self.settings_ini_parse(base)
        return self._settings_ini

    def settings_ini_parse(self, project_folder) -> configparser.ConfigParser:
        """
        Find and parse 'settings.ini' under given project folder.

        Raises:
            FileNotFoundError:
                No 'settings.ini' found under given folder.
        """
        config = configparser.ConfigParser()
        path = project_folder / 'settings.ini'
        if path.is_file():
            config.read(path)
            return config
        else:
            message = f"Project settings file not found: {path}"
            Print.error(message)
            Print.help(
                "Copy an example 'settings.ini' from the root "
                "folder of the skeleton project."
            )
            raise FileNotFoundError(message)
