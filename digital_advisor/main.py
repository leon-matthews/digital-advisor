
import argparse
import builtins
from pprint import pprint
import sys

from colorama import init as init_colorama


class MainBase:
    def __init__(self):
        self.commands = None
        self.options = None
        init_colorama()
        # For easy debugging, make `pprint` available as `pp` everywhere.
        builtins.pp = pprint

    def add_global_arguments(self, parser):
        """
        Hook for sub-classes to add extra arguments.
        """
        return

    def parse(self, commands, arguments, **kwargs):
        parser = self._make_parser(commands, **kwargs)

        # Print 'long help' by default
        if not arguments:
            parser.print_help(sys.stderr)
            sys.exit(1)

        self.options = parser.parse_args(arguments)

    def main(self):
        """
        Run the chosen command object.
        """
        command_name = self.options.command_name
        del self.options.command_name
        command = self.commands[command_name]
        command.set_options(self.options)
        return command.main()

    def _make_parser(self, commands, *, program, description, epilog=None):
        # Global arguments
        global_parser = argparse.ArgumentParser(add_help=False)
        verbosity = global_parser.add_mutually_exclusive_group()
        verbosity.add_argument(
            '-v', '--verbose', action="count",
            help='increase output verbosity, repeat for more')
        verbosity.add_argument('-q', '--quiet', action='store_true',
            help='minimal output only')

        # ...from subclasses
        self.add_global_arguments(global_parser)

        main = argparse.ArgumentParser(
            prog=program,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=description,
            epilog=epilog)

        # Sub-parsers
        subparsers = main.add_subparsers(metavar='COMMAND', dest='command_name', required=True)
        self.commands = {}
        for command in commands:
            subparser = command._create_subparser(subparsers, global_parser)
            command.add_arguments(subparser)
            self.commands[command.name] = command
        return main
