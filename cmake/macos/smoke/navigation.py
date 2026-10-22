#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Test the real app's D-Bus navigation on an already running test X display."""
import argparse
import ast
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import time


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def stop(process, timeout=5):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', required=True, type=Path)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--display', default=':99')
    parser.add_argument('--session-config', type=Path,
                        default=Path('/opt/local/share/dbus-1/session.conf'))
    args = parser.parse_args()
    app_path, profile = args.app.resolve(), args.profile.resolve()
    marker = profile / '.xiphos-navigation-fixture'
    require(app_path.is_file(), 'app executable does not exist')
    require(not profile.exists() or not any(profile.iterdir()) or marker.is_file(),
            'refusing to overwrite an existing non-test profile')
    profile.mkdir(parents=True, exist_ok=True)
    marker.write_text('Disposable Xiphos navigation test profile\n')
    for name in ['.config', '.cache', '.local/share', '.sword/mods.d',
                 '.sword/modules/texts/rawtext/buildfixture']:
        (profile / name).mkdir(parents=True, exist_ok=True)
    fixtures = Path(__file__).resolve().parent / 'fixtures'
    shutil.copyfile(fixtures / 'buildfixture.conf',
                    profile / '.sword/mods.d/buildfixture.conf')
    env = os.environ.copy()
    # Scope profile overrides to test children; never change the calling shell.
    env.update({'HOME': str(profile), 'SWORD_PATH': str(profile / '.sword'),
                'XDG_CONFIG_HOME': str(profile / '.config'),
                'XDG_CACHE_HOME': str(profile / '.cache'),
                'XDG_DATA_HOME': str(profile / '.local/share'),
                'DISPLAY': args.display, 'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8',
                'G_DEBUG': 'fatal-criticals', 'WEBKIT_DISABLE_COMPOSITING_MODE': '1',
                'LIBGL_ALWAYS_SOFTWARE': '1'})
    subprocess.run(['imp2vs', str(fixtures / 'buildfixture.imp'), '-o',
                    str(profile / '.sword/modules/texts/rawtext/buildfixture')],
                   env=env, check=True, capture_output=True, timeout=30)
    config = args.session_config.read_text()
    original = '<listen>launchd:env=DBUS_LAUNCHD_SESSION_BUS_SOCKET</listen>'
    require(original in config, 'unexpected MacPorts D-Bus session configuration')
    config = config.replace(original, '<listen>unix:tmpdir=/private/tmp</listen>')
    config_path = profile / 'session.conf'
    config_path.write_text(config)
    bus = app = None
    with (profile / 'app.log').open('w') as log:
        try:
            bus = subprocess.Popen(['dbus-daemon', '--nofork', '--print-address=1',
                                    '--config-file=' + str(config_path)],
                                   env=env, stdout=subprocess.PIPE, stderr=log, text=True)
            require(select.select([bus.stdout], [], [], 10)[0], 'private bus did not start')
            address = bus.stdout.readline().strip()
            require(address.startswith('unix:'), 'private bus returned no Unix address')
            env['DBUS_SESSION_BUS_ADDRESS'] = address
            app = subprocess.Popen([str(app_path), 'sword://BuildFixture/Genesis1:1'],
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
            base = ['gdbus', 'call', '--session', '--dest', 'org.xiphos.remote',
                    '--object-path', '/org/xiphos/remote/ipc', '--method']

            def call(method, *values):
                require(app.poll() is None, f'app exited: {app.returncode}; see app.log')
                return subprocess.run(base + ['org.xiphos.remote.' + method, *values],
                                      env=env, capture_output=True, text=True, timeout=5)

            def wait_for(expected):
                deadline = time.monotonic() + 30
                last = ''
                while time.monotonic() < deadline:
                    reply = call('getCurrentReference')
                    last = reply.stderr or reply.stdout
                    if reply.returncode == 0:
                        actual = ast.literal_eval(reply.stdout)[0].replace(' ', '').lower()
                        if actual == expected:
                            return ast.literal_eval(reply.stdout)[0]
                    time.sleep(.2)
                raise RuntimeError('reference did not become ' + expected + ': ' + last)

            result = {'startup_with_fatal_criticals': wait_for('gen1:1'), 'navigation': []}
            for uri, expected in [('Genesis1:2', 'gen1:2'), ('John1:1', 'john1:1'),
                                  ('Genesis1:1', 'gen1:1')]:
                reply = call('setCurrentReference', 'sword://BuildFixture/' + uri)
                require(reply.returncode == 0, reply.stderr)
                result['navigation'].append(wait_for(expected))
            print(json.dumps(result, indent=2))
        finally:
            stop(app)
            stop(bus)


if __name__ == '__main__':
    main()
