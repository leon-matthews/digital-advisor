
from . import add
from . import archive
from . import clone
from . import create
from . import data
from . import dns
from . import deploy
from . import dumpdata
from . import manage
from . import run
from . import setup
from . import test


# List of command objects to use
COMMANDS = [
    add.Add(),
    archive.Archive(),
    clone.Clone(),
    create.Create(),
    data.Data(),
    deploy.Launch(),
    dns.DNS(),
    dumpdata.Dumpdata(),
    manage.Manage(),
    run.Run(),
    setup.Setup(),
    deploy.Stage(),
    test.Test(),
]
