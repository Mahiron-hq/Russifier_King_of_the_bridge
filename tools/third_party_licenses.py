"""Collects the licences of every Rust library linked into the installer, for its licence page.

Usage: third_party_licenses.py <output.txt>
"""
import glob
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = "x86_64-pc-windows-msvc"
LICENSE_FILES = ("LICENSE*", "LICENCE*", "COPYING*", "UNLICENSE*")
FONTS = [
    "Alagard - шрифт Хьюитта Цоя (Hewett Tsoi), кириллическая версия Alagard-12px-unicode.",
    "BubbleSans - шрифт надписей на переведённых страницах книги правил.",
]


def linked_packages(meta):
    """Packages linked into the installer. `cargo tree` resolves features the way a release build does, so the
    test-only dependencies and the features they switch on stay out."""
    tree = subprocess.run(
        ["cargo", "tree", "--locked", "-p", "installer", "-e", "normal", "--target", TARGET, "--prefix", "none",
         "-f", "{p}"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    linked = {tuple(line.split()[:2]) for line in tree.splitlines() if line.strip()}
    workspace = set(meta["workspace_members"])
    return [p for p in meta["packages"]
            if (p["name"], "v" + p["version"]) in linked and p["id"] not in workspace]


def license_texts(package):
    root = os.path.dirname(package["manifest_path"])
    files = sorted({f for pattern in LICENSE_FILES for f in glob.glob(os.path.join(root, pattern))})
    return [open(f, encoding="utf-8", errors="replace").read().strip() for f in files if os.path.isfile(f)]


def main(out):
    meta = json.loads(subprocess.run(
        ["cargo", "metadata", "--format-version", "1", "--locked", "--filter-platform", TARGET],
        cwd=REPO, capture_output=True, text=True, check=True).stdout)
    packages = sorted(linked_packages(meta), key=lambda p: (p["name"].lower(), p["version"]))

    lines = ["Сторонние компоненты", ""] + FONTS + ["", "Библиотеки Rust, из которых собран установщик:", ""]
    lines += ["%s %s - %s" % (p["name"], p["version"], p.get("license") or "см. текст ниже") for p in packages]

    by_text = {}
    for p in packages:
        for text in license_texts(p):
            by_text.setdefault(text, []).append("%s %s" % (p["name"], p["version"]))
    for text, users in sorted(by_text.items(), key=lambda item: item[1][0].lower()):
        lines += ["", "-" * 60, ", ".join(users), "", text]

    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("%s: %d packages, %d distinct licence texts" % (out, len(packages), len(by_text)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
