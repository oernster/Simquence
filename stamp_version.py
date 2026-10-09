#!/usr/bin/env python3
"""Stamp the single-source version into the GitHub Pages site.

The repository keeps exactly one real version string: the ``VERSION`` file at
the project root. Python code reads it at runtime through
``simquence.version`` and the packaging metadata reads it as a dynamic field.
Static files cannot read ``VERSION`` at render time, so they instead carry a
delimited token::

    <!--VERSION-->0.0.0<!--/VERSION-->

This script rewrites whatever sits between every such token's delimiters,
across the site under ``docs/`` and nowhere else. No documentation outside the
site carries version data, so the site is the whole stamped surface. It is
idempotent: stamping an already-current file changes nothing.

It also versions each page's asset links. GitHub Pages lets a browser keep a
stylesheet for ten minutes, so a fresh page can arrive beside its stale CSS and
render broken. Every local ``href="x.css"`` or ``src="x.js"`` therefore carries
``?v=<hash>`` of the file's content, taken with CRLF folded to LF so a Windows
checkout and the LF blob GitHub serves give the same hash.

Usage (from the project root)::

    python stamp_version.py

Run it after every version bump so the site never drifts from ``VERSION``.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from simquence.version import read_version

PROJECT_ROOT = Path(__file__).resolve().parent
DOCS_DIR = PROJECT_ROOT / "docs"

# Delimiters that bracket a stamped version in a static file. The text between
# them is owned by this script and is overwritten from VERSION on every run.
VERSION_TOKEN_OPEN = "<!--VERSION-->"
VERSION_TOKEN_CLOSE = "<!--/VERSION-->"
VERSION_TOKEN_PATTERN = re.compile(
    re.escape(VERSION_TOKEN_OPEN) + ".*?" + re.escape(VERSION_TOKEN_CLOSE),
    re.DOTALL,
)

# A stylesheet or script reference in a page; any query it already has is
# replaced. Only relative paths are local files: a scheme, `//` or a leading
# `/` is not, so those are left exactly as written.
ASSET_LINK_PATTERN = re.compile(
    r"""(?<![\w-])((?:href|src)=)(["'])"""
    r"""([^"'?#]+\.(?:css|js))(?:\?[^"'#]*)?(#[^"']*)?\2"""
)
NOT_RELATIVE_PATTERN = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|/)")
ASSET_HASH_LENGTH = 10


def target_files(docs_dir: Path = DOCS_DIR) -> list[Path]:
    """Return the site files that may carry a version token, deduplicated."""

    candidates: set[Path] = set(docs_dir.rglob("*.html"))
    candidates.update(docs_dir.rglob("*.md"))
    return sorted(candidates)


def stamp_file(path: Path, version: str) -> bool:
    """Rewrite version tokens in one file. Return True if the file changed."""

    original = path.read_bytes().decode("utf-8")
    stamped = VERSION_TOKEN_PATTERN.sub(
        lambda _match: f"{VERSION_TOKEN_OPEN}{version}{VERSION_TOKEN_CLOSE}",
        original,
    )
    if stamped == original:
        return False
    path.write_bytes(stamped.encode("utf-8"))
    return True


def asset_hash(path: Path) -> str:
    """Return the content hash of one asset, with CRLF folded to LF first."""

    if not path.is_file():
        raise FileNotFoundError(f"a site page links to a missing asset: {path}")
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()[:ASSET_HASH_LENGTH]


def version_assets(path: Path) -> bool:
    """Hash every local asset link in one page. Return True if it changed."""

    original = path.read_bytes().decode("utf-8")

    def _link(match: re.Match[str]) -> str:
        attribute, quote, target, fragment = match.groups()
        if NOT_RELATIVE_PATTERN.match(target):
            return match.group(0)
        digest = asset_hash(path.parent / target)
        return f"{attribute}{quote}{target}?v={digest}{fragment or ''}{quote}"

    linked = ASSET_LINK_PATTERN.sub(_link, original)
    if linked == original:
        return False
    path.write_bytes(linked.encode("utf-8"))
    return True


def main(docs_dir: Path = DOCS_DIR, version: str | None = None) -> int:
    """Stamp every site file and report what was touched."""

    resolved = version or read_version()
    changed = [path for path in target_files(docs_dir) if stamp_file(path, resolved)]
    print(f"[stamp_version] VERSION = {resolved}")
    if not changed:
        print("[stamp_version] No files needed stamping.")
    for path in changed:
        print(f"[stamp_version] Stamped {path.relative_to(docs_dir.parent)}")
    pages = [path for path in target_files(docs_dir) if path.suffix == ".html"]
    linked = [path for path in pages if version_assets(path)]
    if not linked:
        print("[stamp_version] No asset links needed versioning.")
    for path in linked:
        print(
            f"[stamp_version] Versioned assets in {path.relative_to(docs_dir.parent)}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
