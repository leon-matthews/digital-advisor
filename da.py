""""
Digital Advisor Project Automation.

A slightly awkward layer-cake is used here to load each of the available
commands and check for problems importing required library modules. If found,
the bash script can rebuild the Python venv to allow for automatic updating
on staff machines.

https://digitaladvisor.nz/
"""

import sys
import warnings


# Do not show warnings for 3rd-party library code
SUPRESS_WARNINGS = (
    'paramiko',
    'pipeline',
    'redis',
)
warnings.filterwarnings('ignore', module='|'.join(SUPRESS_WARNINGS))


# Problem with venv? Exit with return code 100.
try:
    from digital_advisor.commands.project import COMMANDS
    from digital_advisor.main import MainBase
except ModuleNotFoundError as e:
    print(f"{e.__class__.__name__}: {e!s}", file=sys.stderr)
    sys.exit(100)


class Main(MainBase):
    pass


if __name__ == '__main__':
    main = Main()
    arguments = sys.argv[1:]
    kwargs = {
        'program': 'da',
        'description': 'Digital Advisor Project Automation',
    }
    main.parse(COMMANDS, arguments, **kwargs)
    sys.exit(main.main())
