# Apple Silicon macOS build with MacPorts

The existing GTK3 application builds and installs on arm64 macOS. This keeps the
SWORD engine, WebKitGTK renderer, BibleSync and D-Bus support. A standalone `.app`, signing and notarization are not implemented.

## Install dependencies

Install the official [MacPorts package](https://www.macports.org/install.php)
for your macOS version and Apple developer tools. MacPorts 2.12.7 with Xcode 27
was used for the recorded build on macOS 27.0.1. Administrator authorization is
needed for MacPorts installation and package management.

If rsync synchronization fails, use the official signed HTTPS snapshot in
`/opt/local/etc/macports/sources.conf`, keeping a backup of that file:

```text
https://distfiles.macports.org/ports.tar.gz [default]
```

Then run:

```sh
sudo port sync
sudo port install webkit2-gtk sword minizip pkgconfig gettext xorg-server +x11
```

The tested GTK/WebKit combination is **X11**, with GTK3 3.24.52 and WebKitGTK
2.52.4. Do not mix Homebrew GTK, MacPorts WebKit, or different architectures.
The Quartz variant has not been tested. Homebrew's WebKitGTK formula requires
Linux; Apple's WebKit.framework cannot replace the WebKitGTK C API.

### SWORD 1.9.0 and ICU 78 build correction

On the tested ports snapshot, SWORD's binary archive was unavailable, and its
source recipe forced C++11 even though ICU 78 headers need C++17. If the same
failure occurs, back up the recipe, then apply
[`sword-icu78.patch`](../cmake/macos/sword-icu78.patch) to your ports tree.
Locate the recipe with `port file sword`. In that file change:

```text
compiler.cxx_standard     2011  ->  compiler.cxx_standard     2017
-std=c++11                    ->  -std=c++17
```

Then run `sudo port clean sword` and repeat the install. This changes the
local dependency recipe only; a later ports-tree refresh may replace it.
Do not apply it if the current recipe already fixes the standard. The actual
SWORD source build succeeded after this correction.

## Build BibleSync and Xiphos

From this repository's source root:

```sh
export PATH="/opt/local/bin:$PATH"
export PKG_CONFIG_LIBDIR="/opt/local/lib/pkgconfig:/opt/local/share/pkgconfig"
unset PKG_CONFIG_PATH

git clone https://github.com/karlkleinpaste/biblesync.git ../biblesync
git -C ../biblesync checkout e1d35362351e4eef9da71fe49caf709efd05c179

cmake -S cmake/macos/BibleSync -B build/biblesync \
  -DBIBLESYNC_SOURCE_DIR="$PWD/../biblesync" \
  -DCMAKE_PREFIX_PATH=/opt/local \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_INSTALL_PREFIX="$PWD/build/prefix"
cmake --build build/biblesync --parallel 2
cmake --install build/biblesync

cmake -S . -B build/macos \
  -DCMAKE_PREFIX_PATH="$PWD/build/prefix;/opt/local" \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_INSTALL_PREFIX="$PWD/build/install" \
  -DGTKTVEDITOR=ON -DHELP=OFF -DEPUB=OFF -DI18N=OFF
cmake --build build/macos --parallel 2
cmake --install build/macos
```

Use an installed CMake >= 3.18; the tested CMake executable came from Homebrew,
while all application libraries came from MacPorts or the local BibleSync prefix.
The macOS app build requires C++17 for the current ICU stack. The wrapper builds
unmodified BibleSync source and supplies libSystem UUID and explicit libintl
linkage. Both flat and qualified BibleSync includes are supported. The installed
executable retains external-prefix runtime search paths; keep the dependency
prefix in place. This is not a relocatable distribution.

`GTKTVEDITOR=ON` selects the existing upstream GtkTextView notes editor. Upstream's
default WebKit2 editor is already a disabled stub; rich-text editor parity is not
claimed. HELP/EPUB/I18N build options were disabled for the initial build; complete
help and localization validation remains. Existing defaults and source are retained.

## Launch

For a normal graphical session, MacPorts' xinit instructions require logging out
and back in after installing X11. Start `/Applications/MacPorts/X11.app` and
ensure a working `DISPLAY`. D-Bus must also have a working session; see
`port notes dbus`. Then launch:

```sh
./build/install/bin/xiphos
```

The recorded validation used `Xvfb :99`, software compositing, a private D-Bus
session, an isolated child-process profile and an original-prose SWORD module.
It did not require a logout or alter existing user modules. The default MacPorts
D-Bus configuration uses launchd and fails before a new login environment exists.
For an isolated test session, copy `/opt/local/share/dbus-1/session.conf` and replace
its launchd `<listen>` entry with `<listen>unix:tmpdir=/private/tmp</listen>`, then
use `dbus-run-session --config-file=PATH_TO_COPY -- PROGRAM`. Authentication and
policy entries remain unchanged; no global D-Bus configuration change is needed.

## Compatibility tests

```sh
cmake -S cmake/macos/smoke -B build/macos-smoke \
  -DCMAKE_PREFIX_PATH="$PWD/build/prefix;/opt/local"
cmake --build build/macos-smoke
ctest --test-dir build/macos-smoke --output-on-failure
```

The three default tests exercise real UUID/gettext/SWORD/BibleSync dependencies,
AVFoundation invalid-input handling, SWORD verse lookup and phrase search, and
UTF-8 RawFiles note persistence. They require `imp2vs` from the SWORD package.
The storage check does not operate the GTK editor.

For the optional full-app navigation regression, choose an unused virtual display
(the following uses `:99`) and keep it running while CTest executes:

```sh
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &
xiphos_test_display_pid=$!
cmake -S cmake/macos/smoke -B build/macos-smoke \
  -DCMAKE_PREFIX_PATH="$PWD/build/prefix;/opt/local" \
  -DXIPHOS_TEST_APP="$PWD/build/install/bin/xiphos" \
  -DXIPHOS_TEST_DISPLAY=:99
cmake --build build/macos-smoke
ctest --test-dir build/macos-smoke --output-on-failure
kill "$xiphos_test_display_pid"
```

Four tests passed with the optional integration test enabled. Python 3, `gdbus`,
`dbus-daemon`, and MacPorts' session configuration are required for that test.
It runs the app with `G_DEBUG=fatal-criticals` using a disposable profile and
private D-Bus bus, then checks navigation to Genesis 1:2, John 1:1 and Genesis 1:1.
It does not interact with the user's running app. These tests do not establish
full application parity. See [validation](macos-validation.md).
