"""
Details of the various server types we use and their configuration.
"""

from pathlib import Path


class ServerTypeBase:
    apache_disable_conf = []
    apache_enable_mods = []
    distribution = 'unknown'
    ip = 'unknown'
    language = 'unknown'
    packages_to_install = []
    packages_to_remove = []

    def __init__(self, ip):
        self.ip = ip

    def __str__(self):
        type_ = self.__class__.__name__
        return f"{type_}: {self.ip:<15} {self.distribution} + {self.language}"

    def __repr__(self):
        return f"<{self!s}>"

    def get_conf_folder(self):
        path = Path(__file__).parent.parent / 'conf'
        type_name = self.__class__.__name__.lower()
        path = path / type_name
        path.resolve()
        if not path.is_dir():
            print(f"Configuration files directory not found: {path}")
            raise SystemExit(1)
        return path


class PHP(ServerTypeBase):
    distribution = 'Ubuntu 14.04'
    language = 'PHP 5.5'


class Python2(ServerTypeBase):
    distribution = 'Ubuntu 16.04'
    language = 'Python 2.7'


class Python3(ServerTypeBase):
    apache_disable_conf = [
        'charset',
        'localized-error-pages',
        'other-vhosts-access-log',
        'serve-cgi-bin',
    ]

    apache_enable_mods = [
        'expires',
        'headers',
        'socache_shmcb',
        'ssl'
    ]

    distribution = 'Ubuntu 20.04'
    language = 'Python 3.8'

    packages_to_install = [
        'apache2',
        'build-essential',
        'certbot',
        'dstat',
        'fail2ban',
        'ffmpeg',
        'ffmpegthumbnailer',
        'htop',
        'graphicsmagick',
        'imagemagick',
        'libapache2-mod-wsgi-py3',
        'lynx',
        'neofetch',
        'postgresql',
        #'postfix', #Have to install manually. Setup dialog not working as of June 2019
        'python3-cffi',
        'python3-dev',
        'python3-pil',
        'python3-lxml',
        'python3-venv',
        'redis-server',
        'rst2pdf',
        'rsync',
        'shared-mime-info',
        'silversearcher-ag',
        'sqlite3',
        'smemstat',
        'sysstat',
        'trash-cli',
        'tree',
        'virtualenv',
        'xtail',
        'yui-compressor',
        'zstd',
        'zip',
    ]

    packages_to_remove = [
        'snapd',
    ]


class Python310(Python3):
    distribution = 'Ubuntu 22.04'
    language = 'Python 3.10'
