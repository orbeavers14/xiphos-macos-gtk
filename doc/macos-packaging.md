# Experimental standalone Apple Silicon application

The macOS 27 preview packages Xiphos 4.5.0, its GTK/WebKit runtime, and a private
XQuartz server in one ad-hoc signed `.app`. The recipient does not need MacPorts,
Homebrew, or a separate X11 installation for the tested startup/navigation path.
This is an experimental build, not a notarized release or a claim that every
feature has been tested on a clean Mac.

## How it works

`bundle-runtime.py` copies the installed app/resources, runtime plugins, fonts,
schemas, certificates and dependency libraries. It follows Mach-O load commands,
rewrites non-system links relative to the loading binary, removes build RPATHs,
generates image/GIO caches, and signs code from the inside out. A manifest records
file origins and hashes without embedding the builder's home-directory path.

Vendor binaries and data also contain compiled `/opt/local` paths. This preview
uses a fixed-width replacement with `./runtime/`, preserving binary offsets. The
launcher keeps `Contents/Resources` as its working directory. Xiphos' bundle path
lookup uses its executable location; the SWORD backend retains the bundle's
working directory, and macOS note-module renames use absolute paths. Prefix
installs retain their resource-path fallback and backend working-directory
behavior. This approach needs revalidation whenever vendor dependencies change.

The launcher starts its own X11 display, Xauthority cookie, window manager, and
private session bus. TCP X11 listening and indirect GLX are disabled. It owns and
stops its child processes, leaving an existing desktop X11 session alone. The
nested server uses `org.xiphos.gtk.X11`, rather than MacPorts' application ID.
Accessibility bus/registry services are bundled. Font caches go in the user's
cache directory; the application bundle is not used as a writable cache.

## Reproduce the server build

Start with the successful [MacPorts Xiphos build](macos.md). The following example
uses directories alongside the checkout; adapt the paths to your workspace.
The exact server source matches MacPorts xorg-server 21.1.24_1.

```sh
taskroot="$PWD"
python3 -m venv packaging-tools
packaging-tools/bin/pip install meson==1.12.1 ninja==1.13.2
git clone https://github.com/XQuartz/xorg-server.git xquartz-source
git -C xquartz-source checkout c0fb33e194c9430352c8c8eec7cd5609721103e9
git -C xquartz-source apply "$taskroot/xiphos-macos/cmake/macos/xquartz-standalone.patch"

curl -fL https://www.x.org/releases/individual/lib/xtrans-1.5.2.tar.xz -o xtrans-1.5.2.tar.xz
echo '5c5cbfe34764a9131d048f03c31c19e57fb4c682d67713eab6a65541b4dff86c  xtrans-1.5.2.tar.xz' | shasum -a 256 -c -
tar -xf xtrans-1.5.2.tar.xz
(cd xtrans-1.5.2 && ./configure --prefix="$taskroot/x11-build-prefix" --disable-docs && make install)

export PATH="$taskroot/packaging-tools/bin:/opt/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PKG_CONFIG_LIBDIR="$taskroot/x11-build-prefix/share/pkgconfig:/opt/local/lib/pkgconfig:/opt/local/share/pkgconfig"
unset PKG_CONFIG_PATH
meson setup xquartz-build xquartz-source --prefix=/opt/local \
  -Dapple-applications-dir=/Applications -Dbundle-id-prefix=org.xiphos.gtk \
  -Dsha1=CommonCrypto -Ddtrace=false -Dsecure-rpc=false \
  -Dxquartz=true -Dxvfb=true -Dxnest=false -Dxorg=false -Dxephyr=false \
  -Dxwin=false -Dglamor=false -Ddri1=false -Ddri2=false -Ddri3=false \
  -Ddocs=false -Ddevel-docs=false \
  -Ddefault_font_path=/opt/local/share/fonts/misc \
  -Dxkb_dir=/opt/local/share/X11/xkb -Dxkb_bin_dir=/opt/local/bin
meson compile -C xquartz-build -j 2
DESTDIR="$taskroot/xquartz-staged" meson install -C xquartz-build
```

The Xtrans checksum was verified against the MacPorts recipe. The patch provides
an opt-in `XIPHOS_BUNDLE_ROOT` entry point that starts the server directly and
keeps diagnostic output available. Without that variable, normal XQuartz startup
is retained. The install ownership script is omitted to allow staging without root.

## Assemble and check

Use a fresh destination. The Xiphos install must be rebuilt from the current
sources so that resource discovery and working-directory handling are included.
The BibleSync source directory is the one used for the existing dependency build.

```sh
python3 xiphos-macos/cmake/macos/bundle-runtime.py \
  --install macports-xiphos-install \
  --x11-app xquartz-staged/Applications/X11.app \
  --xquartz-source xquartz-source --biblesync-source biblesync \
  --app 'staged/Xiphos GTK Preview.app'
python3 xiphos-macos/cmake/macos/audit-bundle.py 'staged/Xiphos GTK Preview.app'
codesign --verify --deep --strict 'staged/Xiphos GTK Preview.app'
```

The packager currently requires the `/opt/local` prefix and an arm64 macOS 27
build environment. It includes installed dependency documentation and the
Xiphos, BibleSync and X11 license texts. Before publishing a binary release,
finish the dependency license/corresponding-source distribution inventory.

For a runtime check, create a child-only `sandbox-exec` profile allowing normal
operations but denying reads under `/opt/local`, `/opt/homebrew`,
`/Applications/MacPorts`, and the original build/source/install directories.
Then run the automated test with a fresh disposable profile:

```sh
python3 xiphos-macos/cmake/macos/smoke/bundle-navigation.py \
  --app 'staged/Xiphos GTK Preview.app' --profile bundle-test-profile \
  --sandbox-profile deny-host-runtime.sb
```

The fixture importer runs outside that child sandbox; the app, its server/bus
and runtime helpers, and the test's bundled D-Bus client run inside it. Repeat
after moving the signed `.app` to a different folder. Tests assert startup and
verse-navigation responses, not visual correctness or all application features.

## Verified outcomes and limits (2026-10-21)

- Full Xiphos and the private XQuartz server compiled on Apple Silicon macOS 27.0.1.
- The dependency audit checked 467 Mach-O images: all contain arm64 code, with no
  escaping/missing non-system library links or retained runtime search paths.
- Strict ad-hoc signature verification passed before and after relocation.
- After moving the app to a path containing spaces, startup with fatal GTK
  criticals enabled and Genesis 1:1 → Genesis 1:2 → John 1:1 → Genesis 1:1 passed
  with all host package-manager/build paths above blocked.
- The private accessibility bus and registry activated successfully.
- Test cleanup allows the launcher to stop all child groups; the launcher removes
  a leftover private display socket only if its inode still matches the socket
  observed while its own server was running.
- All four existing prefix-build regression tests passed as well.
- A test-only incorrect X11 library path caused a launch crash during development;
  it was corrected, and the dependency audit now rejects escaping paths.
- XQuartz's native-keymap fallback warning also occurs in the working MacPorts
  session. Keyboard/input-method coverage still requires manual testing.

The preview's compiled minimum OS is **macOS 27.0**. Intel Macs and older macOS
versions are not supported by this artifact. A separate machine, Finder launch,
download quarantine, module downloads/TLS, media/audio, printing, rich notes,
screen-reader interaction and full UI workflows have not been validated here.
Help/EPUB build options remain disabled as in the validated MacPorts build.
Ad-hoc signing is not notarization; macOS may require manual approval of a
downloaded app. Do not describe this preview as a fully validated public release.
