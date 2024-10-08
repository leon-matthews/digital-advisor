"""
Implements the 'stage' and 'launch' commands.
"""

import datetime
import sys

from ... import config
from ...servers import Python2, Python3

from ..utils import line_random, Print, temp_directory

from .base import ProjectCommand


class Deploy(ProjectCommand):
    """
    Deploy project to specified server.
    """
    def main(self):
        # Heading
        Print.heading(f"Deploy to {self.role.upper()}")
        print()

        # Pre-flight checks
        verbose = self.options.verbose
        self.connection = self.get_connection()
        self.ensure_active_venv()
        self.ensure_git_committed()

        # Tests
        if self.options.no_tests:
            Print.warning("Skipping tests")
        else:
            self.run_tests()

        # Confirmation
        self.confirmation()

        # Upload code
        self.upload_code()
        self.clear_remote_bytecode()

        # Set up environment
        self.delete_venv_remote()
        self.create_venv_remote()
        self.install_requirements_remote(verbose)

        # Set up project
        self.sub_folders_setup()
        self.collect_static(verbose)

        # Update database
        if self.options.no_migrate:
            Print.warning("Skipping database migration")
        else:
            self.run_database_migration()

        if self.options.syncdb:
            self.run_database_syncdb()

        # Apache setup
        self.activate_apache()
        self.restart_application()

        # Tag git
        self.tag_deployment()

    def activate_apache(self):
        Print.progress("Activate project's apache configuration")
        commands = []

        # Create symlink to project's config
        name = self.get_project_name()
        source = (
            self.get_project_path_remote() /
            'deploy' / 'apache' / f"{self.role}.conf")
        destination = f"/etc/apache2/sites-available/{name}.conf"
        commands.append(f"sudo ln --force --symbolic {source} {destination}")

        # Activate site
        commands.append(f"sudo a2ensite {name}")
        commands.append(f"sudo apache2ctl configtest")
        if isinstance(self.connection.server_type, Python2):
            commands.append(f"sudo apache2ctl graceful")
        else:
            commands.append(f"sudo systemctl reload apache2")
        self.run_many_remote(commands)
        print()

    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        # No migrate
        parser.add_argument(
            '-m', '--no-migrate', action='store_true',
            help="do not run 'migrate' on database")

        # Run 'syncdb'
        parser.add_argument(
            '-s', '--syncdb', action='store_true',
            help="run 'syncdb' on database (Django < 1.9 only)")

        # No Tests
        parser.add_argument(
            '-t', '--no-tests', action='store_true',
            help="do not run project's unit tests")

    def clear_remote_bytecode(self):
        Print.progress("Clear Python bytecode caches")
        source = self.get_project_path_remote() / 'source'
        commands = []
        commands.append(f"cd {source}")
        commands.append(
            "sudo find . -type f -name '*.py[co]' -delete "
            "-or -type d -name '__pycache__' -delete")
        self.run_many_remote(commands)
        print()

    def collect_static(self, verbose=False):
        Print.progress("Collect and preprocess static assets")
        verbosity = '2' if verbose else '0'
        command = f"collectstatic --link --clear --noinput --verbosity={verbosity}"
        self.run_manage_remote(command)
        print()

    def confirmation(self):
        pass

    def create_venv_remote(self):
        type_ = self.connection.server_type
        folder = self.get_venv_path_remote()
        if isinstance(type_, Python2):
            Print.progress("Create Python 2 virtual environment")
            self.run_remote(f"virtualenv -q -p python2 {folder}")
        elif isinstance(type_, Python3):
            Print.progress("Create new Python 3 virtual environment")
            self.run_remote(f"virtualenv -q -p python3 {folder}")
        else:
            Print.error(f"Unknown Python version for server: {type_!r}")
            sys.exit(1)
        print()

    def delete_venv_remote(self):
        Print.progress("Delete existing virtual environment")
        folder = self.get_venv_path_remote()
        self.run_remote(f"rm -fr {folder}")
        print()

    def ensure_git_committed(self):
        """
        Make sure that we do not forget any code.

        We use `git archive` to ensure that the code tree that we upload
        confirms to the settings in our '.gitignore' file - and that we get an
        accurate reflection of the of the current state of git's HEAD.

        However, doing so means that uncommited code would fail to be copied, hence
        the need for this check.
        """
        Print.progress("Check that we've committed all of our changes.")
        result = self.run('git status --porcelain', hide=True)
        print()

        if result.stdout:
            Print.error("Uncommited changes detected. Aborting.")
            Print.help("Only files that have been committed to git can be uploaded.")
            sys.exit(1)

    def get_connection(self):
        raise NotImplementedError()

    def install_requirements_remote(self, verbose=False):
        Print.progress("Install third-party packages")
        venv_bin = self.get_venv_path_remote() / 'bin'
        requirements = self.get_project_path_remote() / 'deploy' / 'requirements.txt'
        pip = f"{venv_bin}/pip install"
        if not verbose:
            pip += ' --quiet'
        cmds = []
        cmds.append(f"source {venv_bin}/activate")
        # ~ cmds.append(f"{pip} --no-cache-dir --upgrade pip setuptools wheel")
        cmds.append(f"{pip} --requirement {requirements}")
        self.run_many_remote(cmds)
        print()

    def run_database_migration(self):
        """
        Run 'migrate' management command (Django > 1.6 only).
        """
        Print.progress("Run database migrations")
        self.run_manage_remote('migrate')
        print()

    def run_database_syncdb(self):
        """
        Run 'syncdb' management command (Django < 1.9 only).
        """
        Print.progress("Run database synchronisation")
        self.run_manage_remote('syncdb')
        print()

    def restart_application(self):
        Print.progress("Restart WSGI application")
        wsgi = self.get_project_path_remote() / 'deploy' / 'wsgi.py'
        self.run_remote(f"touch -c {wsgi}")
        print()

    def run_tests(self):
        Print.progress("Run project's unit tests.")
        result = self.run_manage(
            'test --failfast --settings common.settings.testing',
            warn=True)
        print()

        # Tests failed?
        if result.exited != 0:
            Print.progress("Please fix the failing tests and try again.")
            Print.help("If this is not possible, try the '--no-tests' argument.")
            sys.exit(1)

    def sub_folders_setup(self):
        Print.progress("Create sub-folders, ensure correct permissions")
        cmds = []
        root = self.get_project_path_remote()
        cmds.append(f"cd {root}")

        # Ensure output folder for static assets
        cmds.append(f"mkdir -p {config.FOLDER_STATIC}")

        # Default permissions are strict
        user_group = f"{config.USER_REMOTE}:{config.USER_REMOTE}"
        cmds.append(f"sudo chown {user_group} -R .")

        # Relax permissions for the data folders only
        user_group = f"{config.USER_REMOTE}:{config.USER_WEBSERVER_REMOTE}"
        for folder in config.FOLDERS_DATA:
            folder += '/'
            cmds.append(f"mkdir -p {folder}")
            cmds.append(f"sudo chown {user_group} -R {folder}")
            cmds.append(f"sudo chmod -R g+w {folder}")
        self.run_many_remote(cmds)
        print()

    def tag_deployment(self):
        Print.progress("Git tag deployment")

        # Tag name
        now = datetime.datetime.now(datetime.timezone.utc)
        iso8601 = now.strftime('%Y-%m-%dT%H%MZ')

        # Friendly message
        now = now.astimezone(config.TIMEZONE)
        date = now.strftime('%A %d %B %Y')
        time = now.strftime('%I:%M%p %Z')
        name = "{}-{}".format(iso8601, self.role)
        host = self.connection.host.split('.')[0]
        message = "Deployed to {} on {} at {}".format(host, date, time)
        self.run(f"git tag --annotate {name} --message '{message}'")

    def upload_code(self):
        """
        Checks out git HEAD into a temp folder, then rsyncs *that* to
        the server.
        """
        name = self.ensure_project_name()
        prefix = 'da_deploy_{}_'.format(name.replace('.', '_'))
        with temp_directory(prefix) as temp_folder:
            # Checkout git HEAD
            Print.progress("Check out a copy of the code from git HEAD")
            self.run(f"chmod 775 {temp_folder}")
            with self.cd(self.get_project_path()):
                command = f"git archive --format=tar HEAD | tar xf - -C {temp_folder}"
                self.run(command)
                print()

            # Upload files
            Print.progress("Upload project code and files to remote server.")
            exclude = [
                '/data/',
                '/env/',
                '/media/',
                '/s/',
                '*.pyc',
                '*.pyo',
                '__pycache__/',
            ]
            destination = self.get_project_path_remote()
            self.upload_folder(temp_folder, destination, exclude=exclude)
            print()


class Stage(Deploy):
    """
    Deploy to staging (see 'launch')
    """
    role = 'staging'

    def confirmation(self):
        Print.heading(f"Deploy to {self.role.upper()}")
        print()

    def get_connection(self):
        connection = self.get_server_staging()
        return connection


class Launch(Deploy):
    """
    Deploy to production (see 'stage')
    """
    role = 'production'

    def confirmation(self):
        self.warning()
        message = f"Deploy to {self.role.upper()}"
        self.confirm(f"{message} [y/N]?")
        print()

    def get_connection(self):
        return self.get_server_production()

    def warning(self):
        """
        Print silly warning to remind user that we're deploying to production.
        """
        warnings = self.get_files_path() / 'warnings.txt'
        Print.warning(line_random(warnings))
