# Xiphos macOS GTK

Apple Silicon compatibility work for the existing [CrossWire Xiphos](https://github.com/crosswire/xiphos) application, starting from [issue #760](https://github.com/crosswire/xiphos/issues/760).

## Download for macOS

[Download the Apple Silicon preview (240.9 MB)](https://github.com/orbeavers14/xiphos-macos-gtk/releases/tag/macos-gtk-audit-candidate-2026-11-26). It requires macOS 27 or later. Unzip the download and open **Xiphos GTK Preview.app**. The preview bundles GTK 3, WebKitGTK, and a private X11 server. It is ad-hoc signed and remains an experimental build.

## Build from source

1. Install the Apple developer tools, [MacPorts](https://www.macports.org/install.php), and CMake 3.18 or later on an Apple Silicon Mac.
2. Clone this repository, enter the checkout, and install the runtime and build dependencies:

   ```sh
   sudo port sync
   sudo port install webkit2-gtk sword minizip pkgconfig gettext xorg-server +x11
   ```

3. Follow the [BibleSync and Xiphos build commands](doc/macos.md#build-biblesync-and-xiphos). The install step places the executable at `build/install/bin/xiphos`. Follow the [launch steps](doc/macos.md#launch) to start it in a working X11 and D-Bus session.

See the [standalone packaging guide](doc/macos-packaging.md) to build a distributable `.app`, and the [validation notes](doc/macos-validation.md) for the tested configurations.

This repository preserves upstream history, GTK3 UI, SWORD functionality and license notices. It is separate from SwordReader and any native UI rewrite. It is an independently hosted derivative, rather than a second GitHub fork-network entry under the same account. Upstream documentation follows below.

---

[![Build Status](https://travis-ci.org/crosswire/xiphos.svg?branch=master)](https://travis-ci.org/crosswire/xiphos)

# Xiphos

Xiphos is a Bible study application for Linux, UNIX, and Windows operating
systems. It uses Sword to display Bibles, commentaries, dictionary, and other
texts and images. Xiphos includes features such as, searching, biblesync,
bookmarks, parallel study, and original language study.

To install Xiphos, search in your package manager for xiphos and install the
package. If you are using Windows, please download the exe from here:

http://xiphos.org/download/

## Building Xiphos

Please see the `INSTALL.md` file.

## Translating Xiphos

Please see files in the `doc` directory.

## History and Acknowledgements

Xiphos started life as the Sword Project's Cheatah program.

Over the course of Xiphos development many ideas and some pieces of code have
come from the Bibletime program and the Sword Project's BibleCS program.

We wish to thank the folks who have put so much time and work into the Sword
Project and then giving it to the world! God Bless you!


## Developing Xiphos


If you want to help develop Xiphos your help will be very appreciated!

The first steps would be to make yourself familiar with the Xiphos build
process, so go read the INSTALL file.

If you are looking for things to do, the best place to find out is to jump into
the #xiphos channel of irc.libera.chat

If you make changes to C or C++ files, please make sure they are cleaned up to
follow our style of coding. The best way to make sure of it is to run this:

	$ clang-format -i -style=file /path/to/edited.c

Where /path/to/edited.c, the C or C++ file you edited. The option '-style=file'
uses a predefined style file called .clang-format in the source tree.


## Thank you!


We hope that your Bible study will be enhanced by Xiphos!

The Xiphos Development Team
