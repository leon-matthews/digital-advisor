
import collections
import itertools
import random
import re
import shutil
import textwrap
from typing import Iterable, Optional

from colorama import Fore, Style

from .math import round_significant


TERMINAL_WIDTH, _ = shutil.get_terminal_size()


def columnise(
        strings: Iterable[str],
        width: int=TERMINAL_WIDTH,
        longest: Optional[int]=None) -> str:
    """
    Return multi-line string containing given strings formatted in columns.

    Args:
        strings:
            Short strings to columnise.
        width:
            Max width of lines to produce
        longest:
            Optionally override the length of the longest string.  Misuse may
            result in too-long lines. Useful when multiple groups of strings
            need to be aligned.

    Returns:
        A single, multi-line string.

    """
    if not strings:
        return ''

    if longest is None:
        longest = len(max(strings, key=len))
    max_columns = int(width / (longest + 1))
    max_columns = max(max_columns, 1)                       # Avoid division by zero
    num_rows = int(len(strings) / max_columns) + 1
    padded = ["{0:<{1}}".format(s, longest) for s in strings]
    lines = []
    step = num_rows
    for i in range(num_rows):
        parts = padded[i::step]
        line = " ".join(parts)
        lines.append(line)
    return '\n'.join(lines)


def create_secret_key(length=50):
    alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$^&*(-_=+)'
    parts = [random.choice(alphabet) for i in range(50)]
    return ''.join(parts)


# Useful measures of time.
# Being careful to use the *exact* length of the mean Gregorian calendar year
# may seem excessive, but it does make a difference of 54 seconds per month!
# (So.. yes. Probably excessive.)
DURATIONS = collections.OrderedDict([
    ('year', int(60 * 60 * 24 * 365.2425)),                 # Mean Gregorian year
    ('month', int((60 * 60 * 24 * 365.2425) / 12)),         # Mean Gregorian month
    ('week', (60 * 60 * 24 * 7)),
    ('day', (60 * 60 * 24)),
    ('hour', (60 * 60)),
    ('minute', 60),
    ('second', 1),
])


def duration(seconds, suffix=None):
    """
    Return 'human' description of number of seconds given. eg.

        >>> duration(1e6)
        '11 days'
    """
    # Validate input
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        raise ValueError("Number of seconds expected, given: {seconds!r}")

    if seconds < 0:
        raise ValueError("Positive number expected, given: {seconds!r}")

    # Special cases
    if seconds == 0:
        return '0 seconds'
    if seconds < 2:
        return '1 second'

    # Use two or more units of whatever time unit we have
    for key in DURATIONS:
        length = DURATIONS[key]
        count = seconds // length
        if count > 1:
            return f"{count:,} {key}s"

    # Won't happen if we have a unary second and a singular special-case.
    raise ValueError(f"Unexpected error using: {seconds!r}")


def ensure_slash(string):
    """
    Ensure that given string ends with a forward-slash.
    """
    if not string.endswith('/'):
        string += '/'
    return string


def file_size(size: int, traditional: bool = False) -> str:
    """
    Produce human-friendly string from given file size.

    Raises:
        ValueError:
            If given size has an error in its... ah... value.

    Args:
        size
            file size in bytes
        traditional
            Use traditional base-2 units, otherwise default to using
            'proper' SI multiples of 1000.

    Returns:
        Human-friendly file size.
    """
    try:
        size = int(size)
    except (ValueError, TypeError):
        raise ValueError("Given file size '{}' not numeric.".format(size))

    if size < 0:
        raise ValueError("Given file size '{}' not positive".format(size))

    if size < 1000:
        return '{}B'.format(size)

    suffixes = {
        1000: ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
        1024: ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    }

    multiple = 1024.0 if traditional else 1000.0
    for suffix in suffixes[multiple]:
        size /= multiple
        if size < multiple:
            size = round_significant(size, 2)
            size = int(size) if size >= 10 else size
            return '{:,}{}'.format(size, suffix)

    # Greater than 1000 Yottabytes!? That is a pile of 64GB MicroSD cards
    # as large as the Great Pyramid of Giza!  You're dreaming, but in the
    # interests of completeness...
    # http://en.wikipedia.org/wiki/Yottabyte
    return '{:,}{}'.format(int(round(size)), suffix)


def first_sentence(string):
    """
    Returns first sentence from given string.

    The end of a sentence is defined as being one or more full-stops, question, or
    exclamation marks.
    """
    parts = first_sentence.regex.split(string, maxsplit=1)
    return "".join(parts[:2]).strip()
first_sentence.regex = re.compile(r"([\.\?\!]+)")         # noqa


def join_and(parts: Iterable[str], *, oxford_comma: bool = True) -> str:
    """
    Join mulitple strings together as an human don would.

        >>> join_and(['Mary', 'Suzy', 'Jane'])
        'Mary, Suzy, and Jane'

    Args:
        parts:
            The strings to join together.
        oxford_comma:
            Add a comma before the 'and', which is of course the best way.

    Returns:
        The joined string.
    """
    # Empty
    if not parts:
        return ''

    # Just one
    parts = list(parts)
    last = parts.pop()
    if not parts:
        return last

    # More
    string = ", ".join(parts)
    if oxford_comma and len(parts) >= 2:
        string += ','
    string += f" and {last}"
    return string


def line_random(path, encoding='utf-8'):
    """
    Return random line from given text file.
    Blank lines and lines begining with '#' are skipped.
    """
    lines = []
    with open(path, 'rt', encoding=encoding) as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            if not line.startswith('#'):
                lines.append(line)
    return random.choice(lines)


def wrap_command(command, *, indent='    ', suffix=' \\', width=TERMINAL_WIDTH):
    """
    Wrap long command onto multiple lines.

    Args:
        command: String to wrap
        indent: Prepend this to every line *after* the first. Defaults to
            four spaces.
        suffix: Add this to the end of every line *except* the last.
            Defaults to a space then backslash.
        width: The maximum allowable width allowed. If not given, the
            current terminal width will be used.
    """
    # Adjust width
    width -= (len(indent) + len(suffix))

    # Easy?
    if len(command) < width:
        return command

    # Break on chained commands
    parts = re.split(r"(\s&&\s)", command)
    if len(parts) == 1:
        groups = parts
    else:
        groups = []
        for line, separator in itertools.zip_longest(parts[::2], parts[1::2]):
            groups.append(line + (separator if separator else ''))

    # Break lines within parts
    lines = []
    for group in groups:
        if len(group) < width:
            lines.append(group)
        else:
            lines.extend(textwrap.wrap(
                group,
                break_on_hyphens=False,
                replace_whitespace=False,
                width=width))

    # Add suffixes and indents
    num_lines = len(lines)
    is_first = True
    is_last = False
    output = []
    for num, line in enumerate(lines, 1):
        if num == num_lines:
            is_last = True
        if not is_first:
            line = indent + line
        if not is_last:
            line = line + suffix
        is_first = False
        output.append(line)

    return '\n'.join(output)


class Print:
    @staticmethod
    def it(string, *styles, **kwargs):
        """
        Print string using colorama styles in single operation.

        Many styles can be passed at once. The terminal colours are reset
        after each print operation.

        https://pypi.org/project/colorama/
        """
        parts = [*styles, str(string), Style.RESET_ALL]
        print(''.join(parts), **kwargs)

    # Styles ###########################
    @staticmethod
    def command(string, prefix='$'):
        string = wrap_command(string)
        Print.cyan(f"{prefix} {string}")

    @staticmethod
    def confirm(string):
        Print.yellow(string, end=' ')

    @staticmethod
    def heading(string=None, padding='.', width=80):
        if string is None:
            string = padding * width
        else:
            string = f"{f' {string} ':{padding}^{width}}"
        Print.green(string)

    @staticmethod
    def help(string):
        Print.yellow(string)

    @staticmethod
    def progress(string):
        Print.grey(f"# {string}")

    @staticmethod
    def warning(string):
        Print.magenta(string)

    @staticmethod
    def error(string):
        Print.red(string)

    # Colours ##########################
    @staticmethod
    def cyan(string, **kwargs):
        Print.it(string, Fore.CYAN, Style.NORMAL)

    @staticmethod
    def green(string, **kwargs):
        Print.it(string, Fore.GREEN, Style.BRIGHT)

    @staticmethod
    def grey(string, **kwargs):
        Print.it(string, Fore.WHITE, Style.DIM, **kwargs)

    @staticmethod
    def magenta(string, **kwargs):
        Print.it(string, Fore.MAGENTA, Style.BRIGHT)

    @staticmethod
    def red(string, **kwargs):
        Print.it(string, Fore.RED, Style.BRIGHT)

    @staticmethod
    def yellow(string, **kwargs):
        Print.it(string, Fore.YELLOW, Style.BRIGHT, **kwargs)

    @staticmethod
    def white(string, **kwargs):
        Print.it(string, Fore.WHITE, Style.BRIGHT, **kwargs)
