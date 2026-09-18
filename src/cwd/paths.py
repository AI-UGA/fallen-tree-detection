"""Locate the project data root by content rather than by hardcoded path.

Every notebook in this project ran in Google Colab against a mounted Google
Drive, where the absolute path to the project folder differs between accounts
and changes when the folder is accessed through a shortcut. Hardcoding
'/content/drive/MyDrive/...' broke repeatedly during development, so the root
is discovered by looking for a directory that contains both marker
subdirectories.

The data itself is not distributed with this repository. See docs/DATA.md.
"""

from __future__ import annotations

import os
from pathlib import Path

# A directory is the project root only if it contains BOTH of these.
MARKERS = {"01. Dataset", "04. Results"}

# Directories that must never be walked into. Drive's shortcut and trash
# folders cause either duplicate hits or a hang.
SKIP = {
    ".shortcut-targets-by-id",
    ".Trash",
    "__pycache__",
    ".ipynb_checkpoints",
    ".git",
}

# Search bases, in order. The second entry covers folders reached through a
# Drive shortcut, where the project sits one level deeper than usual.
DEFAULT_BASES = (
    "/content/drive/MyDrive",
    "/content/drive/.shortcut-targets-by-id",
    os.path.expanduser("~"),
    ".",
)


def _is_root(path: str) -> bool:
    try:
        return os.path.isdir(path) and MARKERS <= set(os.listdir(path))
    except OSError:
        return False


def _file_weight(path: str, cap: int = 500) -> int:
    """Count files under path, stopping early at cap.

    Used to break ties between candidate roots. A Drive restore incident in
    this project left empty duplicate folders alongside the live one; both
    matched the markers, and the populated copy is always the correct one.
    """
    total = 0
    for _, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        total += len(filenames)
        if total > cap:
            break
    return total


def find_root(bases=DEFAULT_BASES, max_depth: int = 3) -> Path | None:
    """Return the project root, or None if no candidate contains the markers.

    Candidates are ranked by file count so that an empty duplicate folder
    never wins over the populated one.
    """
    candidates: list[str] = []

    for base in bases:
        if not os.path.isdir(base):
            continue

        if _is_root(base):
            candidates.append(base)

        for current, dirnames, _ in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP]

            depth = current[len(base) :].count(os.sep)
            if depth >= max_depth:
                dirnames[:] = []
                continue

            for dirname in list(dirnames):
                candidate = os.path.join(current, dirname)
                if _is_root(candidate):
                    candidates.append(candidate)

    if not candidates:
        return None

    candidates = sorted(set(candidates), key=_file_weight, reverse=True)
    return Path(candidates[0])


def require_root(bases=DEFAULT_BASES) -> Path:
    """Return the project root, raising if it cannot be found."""
    root = find_root(bases)
    if root is None:
        raise RuntimeError(
            "Project root not found. A directory containing both "
            f"{sorted(MARKERS)} must be reachable. If running in Colab, "
            "mount Drive first; if the folder is shared, add a shortcut to "
            "My Drive."
        )
    return root


def site_run_dir(root: Path | None = None) -> Path:
    """Directory holding the site-wide inventory outputs."""
    root = Path(root) if root is not None else require_root()
    return root / "04. Results" / "site_run"


def figures_dir(root: Path | None = None) -> Path:
    """Directory where paper figures are written."""
    root = Path(root) if root is not None else require_root()
    path = root / "05. Paper" / "Figures"
    path.mkdir(parents=True, exist_ok=True)
    return path


if __name__ == "__main__":
    print("root:", find_root())
