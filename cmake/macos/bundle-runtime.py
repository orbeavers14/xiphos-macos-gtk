#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Stage an experimental Xiphos runtime. Does not certify standalone operation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys

MAGICS = {bytes.fromhex(value) for value in
          ('feedface', 'cefaedfe', 'feedfacf', 'cffaedfe', 'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca')}


def macho(path):
    if path.is_symlink() or not path.is_file():
        return False
    with path.open('rb') as stream:
        candidate = stream.read(4) in MAGICS
    # Java class files share CAFEBABE with universal Mach-O containers.
    return candidate and 'Mach-O' in output('/usr/bin/file', '-b', str(path))


def output(*args):
    return subprocess.check_output(args, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, default=Path('/opt/local'))
    parser.add_argument('--install', type=Path, required=True)
    parser.add_argument('--x11-app', type=Path, required=True)
    parser.add_argument('--xquartz-source', type=Path, required=True)
    parser.add_argument('--biblesync-source', type=Path, required=True)
    parser.add_argument('--app', type=Path, required=True)
    args = parser.parse_args()
    prefix, install, x11 = (path.resolve(strict=True) for path in
                            (args.prefix, args.install, args.x11_app))
    # Binary string relocation keeps Mach-O offsets intact. The launcher must
    # keep Resources as cwd, including in the patched private X11 entry point.
    old_prefix = os.fsencode(prefix)
    new_prefix = b'./runtime/'
    if len(old_prefix) != len(new_prefix):
        parser.error('experimental fixed-width relocation requires /opt/local')
    app = args.app.absolute()
    if app.exists():
        parser.error('destination already exists; use a fresh staging directory')
    resources = app / 'Contents/Resources'
    runtime = resources / 'runtime'
    macos = app / 'Contents/MacOS'
    macos.mkdir(parents=True)
    runtime.mkdir(parents=True)
    origins = {}

    def copy_file(source, destination):
        source = source.resolve(strict=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        origins[destination] = source

    def copy_tree(source, destination):
        if not source.exists():
            return
        # Dereference links: no staging links can escape to the build machine.
        shutil.copytree(source, destination, symlinks=False, dirs_exist_ok=True)
        for path in destination.rglob('*'):
            if path.is_file():
                origins[path] = (source / path.relative_to(destination)).resolve()

    copy_file(install / 'bin/xiphos', macos / 'xiphos-bin')
    copy_tree(install / 'share', resources / 'share')
    copy_tree(x11, resources / 'X11.app')
    x11_info = resources / 'X11.app/Contents/Info.plist'
    x11_metadata = plistlib.loads(x11_info.read_bytes())
    x11_metadata['CFBundleExecutable'] = 'X11.bin'
    x11_info.write_bytes(plistlib.dumps(x11_metadata))
    for name in ('X11', 'X11.sh'):
        unused = resources / 'X11.app/Contents/MacOS' / name
        unused.unlink()
        origins.pop(unused, None)
    for relative in ('share/fonts', 'share/X11', 'share/icons', 'share/mime',
                     'share/locale', 'share/glib-2.0/schemas', 'share/iso-codes',
                     'share/fontconfig', 'share/gtk-3.0', 'share/doc', 'share/sword',
                     'share/curl', 'share/xml', 'share/defaults/at-spi2',
                     'share/dbus-1/accessibility-services',
                     'etc/fonts', 'lib/gdk-pixbuf-2.0', 'lib/gio/modules',
                     'lib/gtk-3.0', 'lib/gstreamer-1.0', 'lib/webkit2gtk-4.1',
                     'lib/dri', 'lib/enchant-2'):
        copy_tree(prefix / relative, runtime / relative)
    for relative in ('bin/dbus-daemon', 'bin/dbus-run-session', 'bin/gdbus',
                     'bin/xauth', 'bin/xkbcomp', 'bin/quartz-wm',
                     'bin/gdk-pixbuf-query-loaders', 'bin/gio-querymodules',
                     'share/dbus-1/services/org.a11y.Bus.service',
                     'libexec/at-spi-bus-launcher', 'libexec/at-spi2-registryd',
                     'libexec/webkit2gtk-4.1/WebKitWebProcess',
                     'libexec/webkit2gtk-4.1/WebKitNetworkProcess',
                     'libexec/gstreamer-1.0/gst-plugin-scanner'):
        copy_file(prefix / relative, runtime / relative)

    def dependencies(source):
        lines = output('/usr/bin/otool', '-L', str(source)).splitlines()[1:]
        names = [line.strip().split(' (compatibility version')[0] for line in lines]
        identifiers = output('/usr/bin/otool', '-D', str(source)).splitlines()[1:]
        return [name for name in names if name not in identifiers]

    def resolve_dependency(name, source):
        def expand(value):
            return value.replace('@loader_path', str(source.parent)).replace(
                '@executable_path', str(install / 'bin'))
        if name.startswith('@rpath/'):
            lines = output('/usr/bin/otool', '-l', str(source)).splitlines()
            for index, line in enumerate(lines):
                if line.strip() == 'cmd LC_RPATH':
                    root = lines[index + 2].strip().removeprefix('path ').split(' (offset ')[0]
                    candidate = Path(expand(root)) / name.removeprefix('@rpath/')
                    if candidate.is_file():
                        return candidate
            raise RuntimeError(f'unresolved dependency {name} in {source}')
        return Path(expand(name))

    def destination_for(source):
        if source.is_relative_to(prefix):
            return runtime / source.relative_to(prefix)
        # The separately built BibleSync dependency lives outside MacPorts.
        if source.name.startswith('libbiblesync.'):
            return runtime / 'lib' / source.name
        raise RuntimeError(f'unsupported external dependency: {source}')

    queue = [path for path in origins if macho(path)]
    links = {}
    for path in queue:
        source = origins[path]
        links[path] = []
        for name in dependencies(source):
            if name.startswith(('/System/Library/', '/usr/lib/')):
                continue
            dependency = resolve_dependency(name, source)
            destination = destination_for(dependency)
            links[path].append((name, destination))
            if destination not in origins:
                copy_file(dependency, destination)
                queue.append(destination)

    relocations = []
    for path, source in list(origins.items()):
        data = path.read_bytes()
        count = data.count(old_prefix)
        if count:
            data = data.replace(old_prefix, new_prefix)
            path.write_bytes(data)
            relocations.append({'file': str(path.relative_to(app)), 'replacements': count})
        if path in links:
            changes = []
            for name, destination in links[path]:
                # Prefix strings have already been replaced in load commands.
                name = name.replace(str(prefix), new_prefix.decode())
                target = '@loader_path/' + os.path.relpath(destination, path.parent)
                changes += ['-change', name, target]
            if path.suffix == '.dylib' or '.dylib' in path.name:
                changes += ['-id', '@loader_path/' + path.name]
            commands = output('/usr/bin/otool', '-l', str(path)).splitlines()
            for index, line in enumerate(commands):
                if line.strip() == 'cmd LC_RPATH':
                    value = commands[index + 2].strip().removeprefix('path ').split(' (offset ')[0]
                    changes += ['-delete_rpath', value]
            if changes:
                subprocess.run(['/usr/bin/install_name_tool', *changes, str(path)],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    fonts = runtime / 'etc/fonts/fonts.conf'
    font_config = fonts.read_text()
    font_config = re.sub(r'<dir>(\./runtime/[^<]+)</dir>',
                         r'<dir prefix="cwd">\1</dir>', font_config)
    font_config = re.sub(r'<cachedir>\./runtime/[^<]+</cachedir>', '', font_config)
    fonts.write_text(font_config)
    accessibility = runtime / 'share/defaults/at-spi2/accessibility.conf'
    accessibility.write_text(re.sub(r'<servicedir>[^<]+</servicedir>',
        '<servicedir>../../dbus-1/accessibility-services</servicedir>', accessibility.read_text()))
    source_dir = Path(__file__).resolve().parents[2]
    version = (source_dir / 'cmake/source_version.txt').read_text().strip()
    match = re.match(r'\d+(?:\.\d+){0,2}', version)
    if not match:
        raise RuntimeError(f'invalid source version: {version}')
    plist = {'CFBundleIdentifier': 'org.xiphos.gtk', 'CFBundleName': 'Xiphos',
             'CFBundleDisplayName': 'Xiphos GTK', 'CFBundleExecutable': 'Xiphos',
             'CFBundlePackageType': 'APPL', 'CFBundleVersion': '1',
             'CFBundleShortVersionString': match[0], 'NSHighResolutionCapable': True,
             'LSMinimumSystemVersion': '27.0'}
    (app / 'Contents/Info.plist').write_bytes(plistlib.dumps(plist))
    # Use a small private bus, without host launchd or service activation paths.
    (resources / 'session.conf').write_text('''<!DOCTYPE busconfig PUBLIC
 "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig><type>session</type><listen>unix:tmpdir=/private/tmp</listen>
<servicedir>runtime/share/dbus-1/services</servicedir>
<auth>EXTERNAL</auth><policy context="default"><allow send_destination="*"/>
<allow eavesdrop="true"/><allow own="*"/></policy></busconfig>
''')
    copy_file(source_dir / 'COPYING', resources / 'COPYING-Xiphos')
    copy_file(args.xquartz_source / 'COPYING', resources / 'COPYING-X11')
    copy_file(args.biblesync_source / 'COPYING', resources / 'COPYING-BibleSync')
    copy_file(args.biblesync_source / 'LICENSE', resources / 'LICENSE-BibleSync')
    launcher = macos / 'Xiphos'
    subprocess.run(['/usr/bin/clang', '-Wall', '-Wextra', '-Werror', '-arch', 'arm64',
                    str(Path(__file__).with_name('bundle-launcher.c')), '-o', str(launcher)], check=True)
    sign = [sys.executable, str(Path(__file__).with_name('adhoc-sign.py')), str(app)]
    subprocess.run(sign, check=True)
    loaders = runtime / 'lib/gdk-pixbuf-2.0/2.10.0/loaders'
    cache = subprocess.check_output([str(runtime / 'bin/gdk-pixbuf-query-loaders'),
                                     *map(str, sorted(loaders.glob('*.so')))],
                                    cwd=resources, text=True)
    (loaders.parent / 'loaders.cache').write_text(cache.replace(str(resources) + '/', './'))
    subprocess.run([str(runtime / 'bin/gio-querymodules'), str(runtime / 'lib/gio/modules')],
                   cwd=resources, check=True)

    def provenance(source):
        for label, directory in [('macports', prefix), ('xiphos-install', install), ('xquartz-install', x11)]:
            if source.is_relative_to(directory):
                return label + ':' + str(source.relative_to(directory))
        return 'external-library:' + source.name

    manifest = {'status': 'experimental; standalone launch requires validation',
                'fixed_width_prefix': {'from': str(prefix), 'to': new_prefix.decode()},
                'files': [{'path': str(path.relative_to(app)), 'source': provenance(source),
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                          for path, source in sorted(origins.items())],
                'binary_and_data_relocations': relocations}
    (resources / 'runtime-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none', str(app)], check=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    print(f'Staged {len(origins)} files, {len(links)} Mach-O images in {app}')
    print('Runtime caches generated and ad-hoc signatures verified. Validate standalone operation before release.')


if __name__ == '__main__':
    main()
