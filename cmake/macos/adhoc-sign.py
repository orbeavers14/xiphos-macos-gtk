#!/usr/bin/env python3
"""Ad-hoc sign a staged macOS app, including nested Mach-O code.

This deliberately does not claim notarization or dependency portability.
Run after all copying and install_name_tool changes have finished.
"""
import argparse
from pathlib import Path
import plistlib
import subprocess

MACHO = {
    b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca",
}


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    args = parser.parse_args()
    app = args.app.resolve(strict=True)
    if app.suffix != ".app" or not (app / "Contents/Info.plist").is_file():
        parser.error("expected a staged .app with Contents/Info.plist")
    paths = list(app.rglob("*"))
    # An escaping symlink can hide an unbundled dependency or accidentally
    # cause a packaging step to modify a file outside the staging directory.
    for path in paths:
        if path.is_symlink() and not path.resolve().is_relative_to(app):
            parser.error(f"symlink escapes app: {path}")
    binaries = []
    for path in paths:
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as source:
            if source.read(4) in MACHO and "Mach-O" in subprocess.check_output(
                    ["/usr/bin/file", "-b", str(path)], text=True):
                binaries.append(path)
    if not binaries:
        parser.error("no Mach-O code found")
    bundles = [path for path in paths if path.is_dir() and not path.is_symlink()
               and path.suffix in {".app", ".framework", ".xpc", ".appex"}]
    bundle_executables = set()
    for bundle in bundles + [app]:
        info = bundle / "Contents/Info.plist"
        if info.is_file():
            metadata = plistlib.loads(info.read_bytes())
            name = metadata.get("CFBundleExecutable")
            if name:
                bundle_executables.add(bundle / "Contents/MacOS" / name)
    # Signing a bundle's designated executable implicitly signs that bundle.
    # Defer it until its helpers have signatures.
    for path in sorted(set(binaries) - bundle_executables):
        run("/usr/bin/codesign", "--force", "--sign", "-", "--timestamp=none", str(path))
    for path in sorted(bundles, key=lambda value: len(value.parts), reverse=True):
        run("/usr/bin/codesign", "--force", "--sign", "-", "--timestamp=none", str(path))
    run("/usr/bin/codesign", "--force", "--sign", "-", "--timestamp=none", str(app))
    run("/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app))
    print(f"Verified ad-hoc signatures: {len(binaries)} Mach-O files in {app}")
    print("Not notarized. Signature verification does not verify dependency portability.")


if __name__ == "__main__":
    main()
