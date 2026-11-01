#!/usr/bin/env python3
"""Create a local configuration without overwriting a concurrent creator."""
import os
from pathlib import Path
import sys
import tempfile


def main():
    source, destination = map(Path, sys.argv[1:])
    data = source.read_bytes()
    fd, temporary = tempfile.mkstemp(prefix='.config-local-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
        try:
            os.link(temporary, destination)
        except FileExistsError:
            pass
    finally:
        os.unlink(temporary)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        print(f'Cannot initialize local configuration: {error}', file=sys.stderr)
        sys.exit(1)
