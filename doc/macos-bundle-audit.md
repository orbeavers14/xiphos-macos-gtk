# Xiphos macOS bundle audit

The Apple Silicon preview dropped from **256.67 MB to 240.91 MB as a download** and from **693.98 MB to 636.69 MB unpacked**. The GitHub branch is `macos/bundle-size-audit`, based on the published preview commit `162ece2e7613b5406b2d2ca8bb3e9d185d7ac1e9`.

## Size comparison

Numbers use decimal MB. Unpacked values sum regular-file contents. Symlinks are excluded from the byte count. The Windows figure is the NSIS payload extracted with 7-Zip, including installer support files and bundled fonts. It represents the unpacked distribution payload. A Windows installation's final on-disk footprint can vary.

| Distribution | Download | Unpacked payload |
| --- | ---: | ---: |
| macOS Apple Silicon preview | 256,667,176 B (244.78 MiB) | 693,982,045 B (661.83 MiB) |
| macOS audit candidate | 240,914,692 B (229.75 MiB) | 636,687,696 B (607.19 MiB) |
| Savings | **15,752,484 B (6.14%)** | **57,294,349 B (8.26%)** |
| Windows 4.5.0.2 x64 | 84,009,192 B (80.12 MiB) | 257,707,956 B (245.77 MiB) |

The reported 50–80 MB Windows range is consistent with compressed installers. Windows 4.4.0 x64 is 62.79 MB. The 4.5.0 macOS preview download is 3.06× the 4.5.0.2 Windows download before the change and 2.87× after it. Unpacked payload ratios are 2.69× and 2.47×. The published macOS preview's SHA-256 matched GitHub's checksum. Repacking the baseline and candidate with the same `ditto` options produced the same byte count as the published baseline ZIP.

The Windows build ships DLLs named WebKitGTK 3.0 and JavaScriptCoreGTK 3.0 totaling 44.59 MB. The macOS WebKitGTK 4.1 and JavaScriptCoreGTK 4.1 dylibs total 146.13 MB. The Windows payload also includes Festival, bundled fonts and help. The macOS preview packages private XQuartz, GTK 3, and a separate set of runtime plugins. These are different runtime builds and archive formats. [macOS preview](https://github.com/orbeavers14/xiphos-macos-gtk/releases/tag/macos-gtk-preview-2026-10-21), [Windows 4.5.0](https://github.com/crosswire/xiphos/releases/tag/4.5.0), [Windows 4.4.0](https://github.com/crosswire/xiphos/releases/tag/4.4.0)

## What changed

- Restored **532 same-directory aliases** flattened by the packager. Each alias had the same resolved source provenance and identical staged bytes as its target. This saved 20,939,584 bytes of icon data and 19,072,586 bytes of locale data. Both filenames remain available.
- Excluded **114 build-tool catalogs** for Bash, GNU Coreutils and GNU M4, saving 17,137,710 bytes. None of those tools is bundled or invoked by the launcher. The app's own catalogs and runtime dependency catalogs remain available.
- Updated the runtime manifest and signing seal. The re-extracted candidate had all 20,842 expected readable file paths. Comparing retained paths by SHA-256 found differences only in the manifest, signing seal, and re-signed launcher. All previously included documentation, license materials, and runtime libraries were preserved.

## What still accounts for the size

| Baseline bundle area | Logical bytes | Evidence and disposition |
| --- | ---: | --- |
| Top-level runtime libraries | 289,390,448 | WebKitGTK 112.42 MB and JavaScriptCoreGTK 33.71 MB are direct Xiphos loads. ICU data adds 33.18 MB via ICU i18n. |
| Dependency documentation | 116,649,944 | Berkeley DB's documentation accounts for 60.72 MB. A release inventory needs to identify the applicable license, notices, and source obligations before filtering this tree. |
| Dependency locale data | 125,178,329 | Reduced to 88,968,033 bytes. Remaining catalogs cover runtime messages and supported languages. |
| Fonts | 43,256,681 | Retained for private X11 and font rendering. Input and language coverage matter for any future reduction. |
| Icons | 34,752,632 | Reduced to 13,813,048 bytes by restoring the verified aliases. |
| GStreamer plugin files | 28,666,000 | 214 plugin Mach-O images. Their linked closure adds 305 images and 71.40 MB beyond the main executable's static closure, including the plugin images. Other helpers can share parts of that closure. This is a measurement of its reach, not a removal estimate. |

The audit inspected arm64 load commands for all **467 Mach-O images**. They total 335.20 MB. Graphify built a directed graph from 2,628 observed load commands and found 28 system-library endpoints. Starting at `xiphos-bin`, 108 other bundled images are reachable through static load commands, totaling 252.62 MB. The graph includes helpers and plugins as separate starting points. A second Graphify pass indexed 182 source files to trace packaging and launcher behavior. Its AST parser reported partial extraction in 52 files, so dependency conclusions rely on the observed binaries and direct inspection of the packaging scripts.

Startup's static closure omits libraries discovered at runtime. The packager separately includes GStreamer plugins and their scanner, GIO TLS and proxy modules, 12 GdkPixbuf loaders, GTK input methods and print backends, private X11 and Mesa drivers, Apple spelling support, accessibility services, and the WebKit web and network processes. Those paths require feature-specific coverage before pruning. No runtime libraries were removed in this change. [Packaging source](https://github.com/orbeavers14/xiphos-macos-gtk/blob/162ece2e7613b5406b2d2ca8bb3e9d185d7ac1e9/cmake/macos/bundle-runtime.py), [Launcher source](https://github.com/orbeavers14/xiphos-macos-gtk/blob/162ece2e7613b5406b2d2ca8bb3e9d185d7ac1e9/cmake/macos/bundle-launcher.c)

## Validation and blockers

- Both bundles passed strict recursive ad-hoc signature verification and the repository's bundle audit. All 467 images passed the architecture and dependency checks, with zero unresolved or escaping non-system links.
- On an Apple Silicon Mac running macOS 27.2.1, both bundles passed the repository's startup and navigation smoke test with fresh profiles and read access to MacPorts, Homebrew, and installed X11 paths blocked for the app and its children. The candidate ran from a re-extracted location containing spaces. Private X11, D-Bus, accessibility startup, Genesis 1:1 → Genesis 1:2 → John 1:1 → Genesis 1:1, and display-socket cleanup were observed.
- The measured candidate applied the branch's two packaging transformations to the checksum-verified release, then was re-signed, zipped, and re-extracted. The pinned MacPorts/XQuartz build stack was unavailable for a fresh end-to-end build.
- A separate clean Apple Silicon Mac or macOS 27 guest was unavailable. Finder launch, quarantine and Gatekeeper behavior, and a broader feature pass covering module downloads/TLS, media, printing and rich notes remain unverified.
- The preview and candidate use ad-hoc signatures. The existing distribution blocker for the full third-party license and corresponding-source inventory remains open. [Preview validation and distribution notes](https://github.com/orbeavers14/xiphos-macos-gtk/blob/162ece2e7613b5406b2d2ca8bb3e9d185d7ac1e9/doc/macos-packaging.md)

Candidate SHA-256 is `dfb156751eafbdd6475f2d348ca29dcff603d40252a8fc71765e93d984e197f9`.
