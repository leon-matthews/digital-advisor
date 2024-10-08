
from ..utils import Print

from .base import ProjectCommand


class Run(ProjectCommand):
    """
    Start local server for development.
    """
    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        parser.add_argument('port', type=int, default=8000, nargs='?',
                            help='optional port number')

    def main(self):
        self.ensure_active_venv()
        project = self.ensure_project_name()
        port = self.options.port
        Print.help(f"Visit webserver for {project}: http://localhost:{port}/")
        try:
            self.run_manage(f"runserver {port}")
        except KeyboardInterrupt:
            pass
