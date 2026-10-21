# Experimental Apple Silicon macOS build of the GTK application

This path keeps the upstream GTK3 application, SWORD engine, WebKitGTK renderer,
BibleSync, translations and D-Bus code. It is independent of any native UI or
SwordReader rewrite. It is a developer build path, not a finished macOS port.

## Dependencies

Use one arm64 dependency prefix with matching GTK and WebKitGTK backends.
CMake, Apple Clang, pkg-config, GLib tools, GTK3, WebKitGTK 4.1 (or 4.0),
libsoup matching WebKitGTK, ICU, SWORD >= 1.8.1, BibleSync >= 1.2.0, minizip,
zlib, libxml2, gettext/libintl and pthreads are needed. The macOS SDK supplies
UUID through libSystem. AVFoundation/Foundation supply read-aloud.

Homebrew's `webkitgtk` formula explicitly requires Linux, so installing the
remaining Homebrew dependencies does not give a complete build environment.
MacPorts' `webkit2-gtk` port has Darwin patches and `+quartz` / `+x11` variants.
Its GTK3 dependency must use the same variant. This is a prospective route;
a full MacPorts installation/build has not been validated here. Do not mix
Homebrew GTK with MacPorts WebKitGTK, or x86_64 libraries with arm64 libraries.
Apple's WebKit.framework does not implement the WebKitGTK C API.

SWORD discovery on macOS uses its headers and library, because Homebrew's
SWORD 1.9.0 package does not ship `sword.pc`. Pass the intended prefix first
in `CMAKE_PREFIX_PATH`; explicit `Sword_INCLUDE_DIR` / `Sword_LIBRARY` overrides
are available. Prefer a shared SWORD library; static builds may need additional
compression/network dependencies. Avoid stale `/usr/local` package metadata.

## BibleSync

The wrapper builds an unmodified external checkout, supplies Darwin's UUID
library and links gettext explicitly. It downloads nothing and patches no
external source. Example commands, run from the Xiphos source root:

```sh
git clone https://github.com/karlkleinpaste/biblesync.git ../biblesync
# Revision used in the local build:
git -C ../biblesync checkout e1d35362351e4eef9da71fe49caf709efd05c179
cmake -S cmake/macos/BibleSync -B build/biblesync \
  -DBIBLESYNC_SOURCE_DIR="$PWD/../biblesync" \
  -DCMAKE_PREFIX_PATH=/opt/local \
  -DCMAKE_INSTALL_PREFIX="$PWD/build/prefix"
cmake --build build/biblesync
cmake --install build/biblesync
```

Replace `/opt/local` with the coherent prefix you actually use. For the tested
Homebrew subset, the gettext prefix was `/opt/homebrew/opt/gettext`.
The wrapper requires CMake >= 3.18.

## Configure and build

Once the complete dependency stack is available, from the source root:

```sh
export PATH="/opt/local/bin:$PATH"
export PKG_CONFIG_LIBDIR="/opt/local/lib/pkgconfig:/opt/local/share/pkgconfig"
cmake -S . -B build/macos \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_PREFIX_PATH="$PWD/build/prefix;/opt/local" \
  -DCMAKE_INSTALL_PREFIX="$PWD/build/install" \
  -DGTKTVEDITOR=ON -DHELP=OFF -DEPUB=OFF -DI18N=OFF
cmake --build build/macos --parallel
cmake --install build/macos
./build/install/bin/xiphos
```

These commands remain unverified beyond dependency discovery on this machine.
`GTKTVEDITOR=ON` selects the existing upstream GtkTextView notes/journal editor.
Upstream's default WebKit2 editor is a disabled stub; this patch does not change
that default or claim GtkTextView has complete rich-text editor parity.
`I18N=OFF` and `HELP=OFF` reduce build-time documentation/translation tools for
the initial attempt. They do not remove the source. Enable I18N and HELP once
itstool and the requested help generators are installed, then validate them.
D-Bus stays enabled by default and requires a working session bus at runtime.
TGZ packaging is a prefix archive, not a relocatable `.app` or installer.

## Independently runnable compatibility checks

These checks compile and link real dependencies and the actual speech adapter;
they do not need WebKitGTK or open the GTK UI:

```sh
cmake -S cmake/macos/smoke -B build/macos-smoke \
  -DCMAKE_PREFIX_PATH="$PWD/build/prefix;/opt/local"
cmake --build build/macos-smoke
ctest --test-dir build/macos-smoke --output-on-failure
```

The dependency test exercises UUID generation, gettext lookup, SWORD string
handling and BibleSync construction in disabled mode (no multicast). The speech
test covers null/invalid input and safe shutdown only; it does not play audio.
Neither is a UI, scripture-rendering, module-installation or feature-parity test.

## Local results: 2026-10-20

Environment: arm64 macOS 27.0.1 (26A434), Apple Clang 21.0.0,
CMake 4.4.0. Upstream base: `52302cb051d17e2bbe6846be52a942fb2490f75a`.

* Pristine upstream configure first failed on missing GLib tools, then on
  `desktop-file-validate` after the available dependencies were installed.
* Pristine BibleSync configure failed: `Could not find UUID`.
* Wrapped BibleSync 2.2.0: configured, compiled, linked and installed as arm64.
  Upstream emits an assignment-in-condition warning and duplicate `-lSystem`
  warning; neither prevents the build.
* Patched Xiphos discovers real GTK3 3.24.52, SWORD 1.9.0, BibleSync 2.2.0,
  GLib 2.90.1, ICU 78.3, libsoup 3.8.0 and the other non-renderer dependencies.
  Both default-editor and GtkTextView configurations fail because neither
  `webkit2gtk-4.1` nor `webkit2gtk-4.0` is installed.
* A build invocation after failed configuration cannot run: no Makefile exists.
  No Xiphos executable, app bundle or distributable installer was produced.
* Both independent tests pass on arm64. An additional compiled comparison
  confirms all 61 shortcut key values changed to GDK match the original X11
  values. No Linux/Windows regression build was run.

Next: provision a coherent arm64 MacPorts GTK3/WebKitGTK stack, reconfigure,
compile all app sources and fix any further compiler errors. Then launch the
GTK UI and exercise rendering/navigation, search, notes/save, module management,
BibleSync multicast, D-Bus, image opening, read-aloud/cancel, translations and
help. No feature-parity conclusion is justified before those checks. Application
bundling, resource relocation, dylib bundling, signing and notarization remain.

Sources inspected:

* https://github.com/crosswire/xiphos/issues/760
* https://github.com/Homebrew/homebrew-core/blob/main/Formula/w/webkitgtk.rb
* https://github.com/macports/macports-ports/blob/master/www/webkit2-gtk/Portfile
* https://github.com/karlkleinpaste/biblesync
