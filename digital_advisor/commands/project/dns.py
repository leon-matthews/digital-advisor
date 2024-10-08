
import collections

from ... import config

from ..utils import columnise, DNSClient, Print

from .base import ProjectCommand


class DNS(ProjectCommand):
    """
    Check status of DNS for our projects.
    """
    def add_arguments(self, parser):
        """
        Hook to add arguments to this command's `argparse` parser.
        """
        # All or Local
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '-a',
            '--all',
            action='store_true',
            help="Quick check for projects on git server")
        group.add_argument(
            '-l',
            '--local',
            action='store_true',
            help="Examine checked-out projects (default)")
        group.add_argument(
            '-s',
            '--server',
            choices=config.SERVERS.keys(),
            metavar='NAME',
            help="Check projects running on this server")

    def check_all(self, num_threads=32):
        """
        Check basic DNS of all projects found on git server.

        Assumes that the project's folder name is also its canonical hostname.

        Used when called with the '--all' argument.
        """
        Print.heading("Quick Check for Projects on Git Server")
        Print.help(
            "Look-up IP addresses for project folder names on git server and compare \n"
            "against our servers' addresses.  Unmatched or unresovlable IP addresses \n"
            "are shown in detail. Aliases and prefixes are not checked."
        )
        Print.heading()

        # Fetch list of project names from git server
        projects = self.list_projects_remote()

        groups = collections.defaultdict(list)

        # Resolve IP addresses of folder names, add to groups
        Print.progress("Look-up DNS for all hostnames")
        ips = config.servers_ip_to_host()
        dns = DNSClient(num_threads)
        longest = 0
        other = []
        for (hostname, address) in dns.lookup(projects):
            try:
                server = ips[address]
                groups[server].append(hostname)
                longest = max(longest, len(hostname))
            except KeyError:
                other.append((hostname, address))

        # Map IP address against our severs and display
        for hostname in sorted(groups):
            hostnames = sorted(groups[hostname])
            Print.heading(f"{hostname}.example.com ({len(hostnames)} sites)")
            print(columnise(hostnames, longest=longest))
            print()

        # Show problematic hostnames
        Print.heading(f"{len(other)} DNS Errors")
        addresses = [x[1] for x in other if x[1]]
        longest = len(max([x[0] for x in other], key=len))
        other = sorted(other, key=lambda x: x[0].lower())
        reversed_mapping = {
            address: hostname for (address, hostname) in dns.reverse_lookup(addresses)
        }
        for hostname, address in other:
            if address is None:
                address = '  None'
            line = f"{hostname:<{longest}} -> {address:<15}"
            reverse = reversed_mapping.get(address)
            if reverse:
                line += f" -> {reverse}"
            print(line)

    def check_local(self):
        """
        Examine DNS entries for checked-out projects.

        Used when called with no arguments.
        """
        Print.heading("DNS for Checked-Out Projects")

        # Read project's 'settings.ini' for staging and production IP addresses
        folders = self.list_projects_local()
        for base in folders:
            try:
                settings =  self.settings_ini_parse(base)
            except FileNotFoundError:
                Print.warning(f"No settings.ini found for {base.name}")
                continue

            servers = settings['servers']
            print(base.name)
            print('   ', servers['production'])
            print('   ', servers['staging'])
            print()

        # TODO: Parse Apache configurations and read hostnames for production and staging
        #       from 'ServerName' and 'ServerAlias' entries

        # TODO: Check DNS mapping and display
        raise NotImplementedError()

    def check_server(self, server):
        """
        Check DNS of projects on a specific server.
        """
        message = f"DNS for Projects on {server}"
        Print.heading(message)
        # TODO: How deep togo? Folder names only? Or examine Apache config.,
        #       as per `check_local()` and 'da servers ages'

        # TODO: Move to 'da-servers' command instead?

        # TODO: Generalise 'website-ages.py' script to handle other types of
        #       metadata? Could be used for server status metrics too.
        raise NotImplementedError()

    def main(self):
        self.check_all()
        return

        if self.options.all:
            self.check_all()
        elif self.options.server:
            self.check_server(self.options.server)
        else:
            self.check_local()
