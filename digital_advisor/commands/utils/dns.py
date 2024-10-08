
import logging
import os
import socket
import time

from .threading import threadpool_generator


logger = logging.getLogger(__name__)


class DNSClient:
    """
    Multi-threaded DNS and reverse-DNS lookups.

    Designed specifically to consume large generators effiently. To keep
    resource usage to a minimum, only enough records are consumed at a time
    to keep the desired number of threads busy.
    """

    def __init__(self, num_threads=None):
        """
        Initialiser.

        Args:
            num_threads (int):
                How many threads to run. If not given, defaults to the number of
                cores times four.
        """
        self.num_threads = num_threads
        if self.num_threads is None:
            self.num_threads = os.cpu_count() * 4

    def lookup(self, hostnames):
        """
        DNS lookup: hostnames to IP addresses.

        Args:
            hostnames:
                Iterable of hostname strings.

        Yields:
            2-tuple of (hostname, address), where address is either an
            IP address string, or None if the lookup failed.
        """
        start = time.perf_counter()
        num_failed = 0
        num_resolved = 0
        generator = threadpool_generator(
            self.num_threads, self._gethostbyname, hostnames
        )

        for hostname, address in generator:
            if address is None:
                num_failed += 1
            else:
                num_resolved += 1
            yield (hostname, address)

        elapsed = time.perf_counter() - start
        logger.info(
            f"{num_resolved:,} hostnames resolved in {elapsed:.2f} seconds. "
            f"{num_failed:,} failed."
        )

    def reverse_lookup(self, addresses):
        """
        Reverse DNS lookup: IP addresses to hostnames.

        Args:
            addresses:
                Iterable of IP address strings.

        Yields:
            2-tuple of (address, hostname), where hostname is either an
            string, or None if the lookup failed.
        """
        start = time.perf_counter()
        num_failed = 0
        num_resolved = 0
        generator = threadpool_generator(
            self.num_threads, self._gethostbyaddr, addresses)

        for address, hostname in generator:
            logger.debug("%s: %s", address, hostname)
            if hostname is None:
                num_failed += 1
            else:
                num_resolved += 1
            yield (address, hostname)

        elapsed = time.perf_counter() - start
        logger.info(
            f"{num_resolved:,} IP addresses resolved in {elapsed:.2f} seconds. "
            f"{num_failed:,} failed."
        )

    def _gethostbyname(self, hostname):
        """
        Attempt to resolve single hostname to a IPv4 address.

        Args:
            hostname (str):
                Hostname to lookup.

        Returns:
            2-tuple of (hostname, address).
            Address is either a string, or None if lookup failed.
        """
        try:
            address = socket.gethostbyname(hostname)
            logger.debug("Hostname %s resolved to %s", hostname, address)
        except OSError as e:
            logger.debug("Hostname lookup failed: %s: %s", hostname, e)
            address = None
        return (hostname, address)

    def _gethostbyaddr(self, address):
        """
        Attempt to do a reverse lookup for the given IP address.

        Args:
            ip (str):
                IP address to lookup.

        Returns:
            2-tuple of (ip, hostname)
        """
        try:
            hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(address)
            hostname = socket.getfqdn(hostname)
            logger.debug("IP %s resolved to %s", address, hostname)
        except (OSError, UnicodeError) as e:
            logger.debug("Address lookup failed: %s: %s", address, e)
            hostname = None
        return (address, hostname)
