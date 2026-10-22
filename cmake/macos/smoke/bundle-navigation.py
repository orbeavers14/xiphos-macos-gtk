#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise the bundled launcher, private X11 and D-Bus, and verse navigation."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from navigation import require, stop


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--sandbox-profile', type=Path, required=True)
    parser.add_argument('--imp2vs', type=Path, default=Path('/opt/local/bin/imp2vs'))
    args = parser.parse_args()
    app = args.app.resolve(strict=True)
    resources = app / 'Contents/Resources'
    profile = args.profile.resolve()
    marker = profile / '.xiphos-navigation-fixture'
    require(not profile.exists() or not any(profile.iterdir()) or marker.is_file(),
            'refusing an existing non-test profile')
    profile.mkdir(parents=True, exist_ok=True)
    marker.write_text('Disposable bundled Xiphos test profile\n')
    for name in ['.config', '.cache', '.local/share', '.sword/mods.d',
                 '.sword/modules/texts/rawtext/buildfixture']:
        (profile / name).mkdir(parents=True, exist_ok=True)
    fixtures = Path(__file__).resolve().parent / 'fixtures'
    shutil.copyfile(fixtures / 'buildfixture.conf', profile / '.sword/mods.d/buildfixture.conf')
    subprocess.run([str(args.imp2vs), str(fixtures / 'buildfixture.imp'), '-o',
                    str(profile / '.sword/modules/texts/rawtext/buildfixture')],
                   check=True, capture_output=True, timeout=30)
    env = os.environ.copy()
    env.update(HOME=str(profile), SWORD_PATH=str(profile / '.sword'),
               XDG_CONFIG_HOME=str(profile / '.config'), XDG_CACHE_HOME=str(profile / '.cache'),
               XDG_DATA_HOME=str(profile / '.local/share'), G_DEBUG='fatal-criticals',
               LANG='en_US.UTF-8', LC_ALL='en_US.UTF-8')
    sandbox = ['/usr/bin/sandbox-exec', '-f', str(args.sandbox_profile.resolve(strict=True))]
    log_path = profile / 'bundle-app.log'
    app_process = None
    try:
        with log_path.open('w') as log:
            app_process = subprocess.Popen(sandbox + [str(app / 'Contents/MacOS/Xiphos'),
                'sword://BuildFixture/Genesis1:1'], env=env, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + 40
            address = None
            while time.monotonic() < deadline:
                require(app_process.poll() is None, f'launcher exited; see {log_path}')
                match = re.search(r'Xiphos: private bus (unix:[^\n]+)', log_path.read_text())
                if match:
                    address = match[1]
                    break
                time.sleep(.2)
            require(address, f'private bus was not announced; see {log_path}')
            base = sandbox + [str(resources / 'runtime/bin/gdbus'), 'call', '--address', address,
                '--dest', 'org.xiphos.remote', '--object-path', '/org/xiphos/remote/ipc', '--method']

            def call(method, *values):
                require(app_process.poll() is None, f'launcher exited; see {log_path}')
                return subprocess.run(base + ['org.xiphos.remote.' + method, *values],
                                      env=env, cwd=resources, capture_output=True, text=True, timeout=5)

            def wait_for(expected):
                deadline = time.monotonic() + 30
                last = ''
                while time.monotonic() < deadline:
                    reply = call('getCurrentReference')
                    last = reply.stderr or reply.stdout
                    if reply.returncode == 0:
                        actual = ast.literal_eval(reply.stdout)[0]
                        if actual.replace(' ', '').lower() == expected:
                            return actual
                    time.sleep(.2)
                raise RuntimeError('reference did not become ' + expected + ': ' + last)

            result = {'private_x11_and_bus_started': True,
                      'startup_with_fatal_criticals': wait_for('gen1:1'), 'navigation': []}
            for uri, expected in [('Genesis1:2', 'gen1:2'), ('John1:1', 'john1:1'),
                                  ('Genesis1:1', 'gen1:1')]:
                reply = call('setCurrentReference', 'sword://BuildFixture/' + uri)
                require(reply.returncode == 0, reply.stderr)
                result['navigation'].append(wait_for(expected))
            # Allow asynchronous WebKit startup errors time to surface.
            time.sleep(3)
            require(app_process.poll() is None, f'launcher exited; see {log_path}')
            require('Unable to spawn' not in log_path.read_text(), 'WebKit helper startup failed')
            print(json.dumps(result, indent=2))
    finally:
        # The launcher shuts down the app, window manager, and server in turn.
        stop(app_process, timeout=25)
        match = re.search(r'Xiphos: private display :(\d+) ready', log_path.read_text())
        if match:
            socket = Path('/private/tmp/.X11-unix/X' + match[1])
            require(not socket.exists(), f'private display socket was left behind: {socket}')


if __name__ == '__main__':
    main()
