
from pathlib import Path

from fabric import Connection
from fabric.config import Config
import pytz

from .servers import PHP, Python2, Python3, Python310


# Settings
GIT_SERVER = 'git'
TIMEZONE = pytz.timezone('Pacific/Auckland')
USER_REMOTE = 'ubuntu'
USER_WEBSERVER_REMOTE = 'www-data'


# Folders
FOLDER_GIT_SERVER = Path('/srv/git/websites')
FOLDER_PROJECT_BASE = Path('~/DigitalAdvisor').expanduser()
FOLDER_PROJECT_REMOTE = Path('/srv/websites/')
APPS_DEFAULT = (
    'admin',
    'animal3',
    'common',
    'contact',
    'dashboard',
    'lib',
    'pages',
    'users',
)
APPS_FOLDERS = ('source', 'static', 'templates')
FOLDER_STATIC = 's'
FOLDERS_DATA = ('data', 'media')
SKELETON_FOLDER = 'skeleton.example.com'


# Server types
staging1 = Config()
staging1['server_type'] = Python2('50.112.114.3')

staging2 = Config()
staging2['server_type'] = Python3('35.167.37.253')

staging4 = Config()
staging4['server_type'] = Python310('13.54.91.243')

web2 = Config()
web2['server_type'] = Python2('50.112.114.7')

web3 = Config()
web3['server_type'] = Python3('52.39.131.4')


# Server hoststrings
SERVERS = {
    'git': Connection(
        'user@git.example.com',
        config=staging4,
        connect_kwargs={'disabled_algorithms': {'disabled_keys': {'pubkeys':['rsa-sha2-512','rsa-sha2-256']}}},
    ),
    'staging1': Connection('user@staging1.example.com', config=staging1),
    'staging2': Connection('user@staging2.example.com', config=staging2),
    'staging4': Connection('user@staging4.example.com', config=staging4),
    'web2': Connection('user@web2.example.com', config=web2),
    'web3': Connection('user@web3.example.com', config=web3),
}


def get_connection(hostname):
    """
    Convert between alias and full server string.

    Acts as the 'type' in a call to `argparse.add_argument()`.
    """
    # Grab first part of hostname
    key = hostname.split('.')[0]
    try:
        connection = SERVERS[key]
    except KeyError:
        valid_keys = ', '.join(SERVERS.keys())
        message = f"Hostname must be one of: {valid_keys}"
        raise KeyError(message) from None
    return connection


def servers_ip_to_host():
    """
    Produce mapping of server IP addresses to hostnames.

    Return:
        Dictionary.
    """
    ips = {}
    for hostname, server in SERVERS.items():
        server = server.config.get('server_type')
        if server is None:
            continue
        ips[server.ip] = hostname
    return ips


def server_summary(indent='', show_domain=False):
    """
    Return a multi-line string containing server details.
    """
    domain = 'example.com'
    lines = []
    for key in SERVERS:
        hostname = f"{f'{key}.{domain}':<24}" if show_domain else f"{key:<12}"
        line = f"{indent}{hostname}"
        config = SERVERS[key].config.get('server_type')
        if config:
            line += f"{config.ip:<15} ({config.distribution} + {config.language})"
        lines.append(line)
    return '\n'.join(lines)
