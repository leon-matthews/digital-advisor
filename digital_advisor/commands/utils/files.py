
from contextlib import contextmanager
import fnmatch
import os
from pathlib import Path
import shutil
import sys

import tempfile

from .text import ensure_slash, Print


def call_forth_skeletons(folder, verbose=False):
    """
    Recursively activate any skeleton files found.

    A skeleton file is a simplified file that should replace its homonym
    in a new project. This is best explained by example.

    Given a folder containing the two files:

        example.py
        example.skeleton.py

    This function will replace `example.py` with the contents of
    `example.skeleton.py` then delete the latter. The folder will end
    up containing a single `example.py` file.
    """
    for root, dirnames, filenames in os.walk(folder):
        root = Path(root)
        for skeleton in fnmatch.filter(filenames, '*.skeleton.*'):
            expected = skeleton.replace('.skeleton.', '.')
            expected_path = root / expected
            if not expected_path.is_file():
                Print.error(f"No skeleton file destination found: {root}/{expected}")
                sys.exit(1)

            skeleton_path = root / skeleton
            shutil.copy(skeleton_path, expected_path)
            skeleton_path.unlink()

            if verbose:
                s = shortest_path(skeleton_path, root)
                d = shortest_path(expected_path, root)
                Print.command(f"cp {s} {d} && rm {s}")


def copy(source, destination, verbose=False):
    """
    Wrapper around `shutil.copy()`.

    Prints progress and ignores Python cache files.
    """
    if not source.is_file():
        Print.error(f"File not found: {source}")
        raise SystemExit(1)

    if destination.is_file():
        Print.error(f"File already exists: {destination}")
        raise SystemExit(1)

    if verbose:
        source2 = shortest_path(source)
        destination2 = ensure_slash(shortest_path(destination))
        Print.command(f"cp {source2} {destination2}")
    shutil.copy(source, destination)


def copytree(source, destination, verbose=False):
    """
    Wrapper around `shutil.copytree()`

    Prints progress and ignores Python cache files.
    """
    if not source.is_dir():
        Print.error(f"Folder not found: {source}")
        raise SystemExit(1)

    if verbose:
        source2 = shortest_path(source)
        destination2 = shortest_path(destination)
        Print.command(f"cp -a {source2} {destination2}")

    ignore = shutil.ignore_patterns('*.pyc', '*.pyo', '__pycache__')
    shutil.copytree(source, destination, dirs_exist_ok=True, ignore=ignore)


def path_to_string(path):
    """
    Convert path object to plain string.

    We use rsync a lot, so we are as fussy as it is about adding
    trailing slashes on paths to folders.

    Args:
        path (pathlib.Path): File-system path.

    Returns:
        Plain string, with trailing slash if path points to folder.
    """
    string = str(path)
    if path.is_dir() and not string.endswith('/'):
        string += '/'
    return string


def path_to_string_remote(path, connection, is_dir=True):
    """
    As per `path_to_string()`, but with a SSH-style connection string appended.

    Args:
        path (pathlib.Path): Path on remote
        is_dir (bool): Should we append a slash to the path?

    eg. 'user@db1.example.com:/some/path/here'
    """
    string = str(path)
    if is_dir and not string.endswith('/'):
        string += '/'
    string = f"{connection.user}@{connection.host}:{string}"
    return string


def shortest_path(target, cwd=None):
    """
    Attempt to produce a short path string for printing purposes.

    Args:
        current (Path):
            Path to current folder
        target (Path):
            Path to target file or folder.

    Returns (str):
        Shortest sensible string.
    """
    if cwd is None:
        cwd = Path.cwd()

    # Absolutely always
    paths = [str(target.resolve())]

    # Directly down?
    try:
        relative = target.relative_to(cwd)
        paths.append(str(relative))
    except ValueError:
        pass

    # Directly up?
    try:
        depth = cwd.relative_to(target)
    except ValueError:
        pass
    else:
        # Limit to three 'updots' in a row
        if len(depth.parts) > 3:
            return str(target.resolve())

        updots = Path('.')
        for _ in depth.parts:
            updots /= '..'
        paths.append(str(updots))

    # Up to common ancestor, then down again
    try:
        ancestor = os.path.commonpath((cwd, target))
        ancestor = Path(ancestor)
        up = cwd.relative_to(ancestor)
        updots = Path('.')
        for _ in up.parts:
            updots /= '..'
        down = target.relative_to(ancestor)
        paths.append(str(updots/down))
    except ValueError:
        pass

    # Pick best path
    shortest = min(paths, key=len)
    return shortest


def relative_path(old, new):
    """
    Attempt to produce a short relative path for printing purposes.

    Returns an absolute path if the relative path becomes too
    unwieldy, ie. '../../../../..'
    """
    # Changing down the tree?
    try:
        target = new.relative_to(old)
        return target
    except ValueError:
        pass

    # Going up?
    try:
        depth = old.relative_to(new)
        if len(depth.parts) > 3:
            return new.resolve()
        target = Path('.')
        for _ in depth.parts:
            target /= '..'
        return target
    except ValueError:
        return new.resolve()


def search_and_replace(path, search, replace):
    """
    Perform in-place search-and-replace on given text-file path.
    """
    with open(path, 'rt') as fin:
        contents = fin.read()
    contents = contents.replace(search, replace)
    with open(path, 'wt') as fout:
        fout.write(contents)


@contextmanager
def temp_directory(prefix='_da_'):
    """
    Context manager creates and returns local temporary directory.

    The temporary directory is automatically cleaned-up up once context
    manager exits.
    """
    path = tempfile.mkdtemp(prefix=prefix)
    try:
        yield Path(path)
    finally:
        shutil.rmtree(path)
