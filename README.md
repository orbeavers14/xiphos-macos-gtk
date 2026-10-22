# Xiphos macOS GTK

Apple Silicon compatibility work for the existing [CrossWire Xiphos](https://github.com/crosswire/xiphos) application, starting from [issue #760](https://github.com/crosswire/xiphos/issues/760).

**Status:** builds as arm64 with MacPorts. An experimental ad-hoc signed macOS 27 application now bundles the GTK/WebKit runtime and a private X11 server. Startup and verse navigation passed after moving the app, with host package-manager and build paths blocked. It is not notarized or fully validated on a clean Mac.

- [Build instructions and resolved issues](doc/macos.md)
- [Validation evidence and remaining limitations](doc/macos-validation.md)
- [Standalone preview packaging, tests and limitations](doc/macos-packaging.md)

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
