#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reject escaping or unresolved non-system Mach-O dependencies in a bundle."""
import argparse
import json
from pathlib import Path
import subprocess

MAGICS = {bytes.fromhex(value) for value in
          ('feedface', 'cefaedfe', 'feedfacf', 'cffaedfe', 'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca')}


def output(*args):
    return subprocess.check_output(args, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app', type=Path)
    args = parser.parse_args()
    app = args.app.resolve(strict=True)
    errors, images = [], []
    for path in sorted(app.rglob('*')):
        if path.is_symlink():
            if not path.resolve().is_relative_to(app):
                errors.append(f'escaping symlink: {path.relative_to(app)}')
            continue
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            if stream.read(4) not in MAGICS:
                continue
        description = output('/usr/bin/file', '-b', str(path))
        if 'Mach-O' not in description:
            continue
        name = str(path.relative_to(app))
        if 'arm64' not in description:
            errors.append(f'missing arm64 code: {name}')
        for line in output('/usr/bin/otool', '-L', str(path)).splitlines()[1:]:
            dependency = line.strip().split(' (compatibility version')[0]
            if dependency.startswith(('/usr/lib/', '/System/Library/')):
                continue
            if dependency.startswith('@loader_path/'):
                target = (path.parent / dependency.removeprefix('@loader_path/')).resolve()
                if not target.is_relative_to(app) or not target.is_file():
                    errors.append(f'{name}: dependency escapes bundle or is missing: {dependency}')
            else:
                errors.append(f'{name}: unresolved external dependency: {dependency}')
        if 'cmd LC_RPATH' in output('/usr/bin/otool', '-l', str(path)):
            errors.append(f'{name}: retained runtime search path')
        images.append(name)
    if not images:
        errors.append('no Mach-O images found')
    print(json.dumps({'mach_o_images': len(images), 'errors': errors,
                      'scope': 'load commands, architecture and symlinks; runtime testing still required'}, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
