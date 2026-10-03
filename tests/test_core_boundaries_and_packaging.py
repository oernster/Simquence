from __future__ import annotations

"""Two structural rules about the distributable core.

The first keeps the model layer pure: `model`, `types` and `validate` describe
and check a model and must not read the filesystem. `io` sits beside them at the
same level, so nothing about the layout stops one of them reaching for it; the
moment one does the core stops being testable without a temporary
directory.

The second pins what the wheel contains. The packaging rule once globbed the
LGPL front end into a GPL wheel for several releases while every document said
otherwise. The glob is fixed; this is the test whose absence let it happen.
"""

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# The modules that describe and validate a model, as opposed to loading one.
PURE_CORE_MODULES = ("model", "types", "validate")

# Everything those modules may import, exactly. An allowlist rather than a
# list of known escapes: a denylist passed `from .io import x`, `import
# tempfile`, `import subprocess` and `importlib`, because nobody had thought to
# name them. Anything new here has to be added on purpose.
ALLOWED_IMPORTS = frozenset(
    {"__future__", "dataclasses", "typing", "math", "latencylab.model"}
)

# Builtins that reach a file or import a module by string, which no import
# statement shows.
FORBIDDEN_CALLS = frozenset({"open", "__import__", "exec", "eval"})


def _imported_names(path: Path) -> set[str]:
    """Every module named by an import in `path`; relative ones keep their dots."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add("." * node.level + (node.module or ""))
    return names


def _called_builtins(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    } & FORBIDDEN_CALLS


def _violations(path: Path) -> list[str]:
    problems = [
        f"imports {name}" for name in sorted(_imported_names(path) - ALLOWED_IMPORTS)
    ]
    problems += [f"calls {name}()" for name in sorted(_called_builtins(path))]
    return problems


PLANTS = {
    "relative io": "from .io import write_summary_json\n",
    "builtin open": "def f(p):\n    return open(p).read()\n",
    "http": "import http.client\n",
    "importlib": "import importlib\nos = importlib.import_module('os')\n",
    "dunder import": "os = __import__('os')\n",
    "tempfile": "import tempfile\n",
    "subprocess": "import subprocess\n",
    "os": "import os\n",
}


@pytest.mark.parametrize("plant", sorted(PLANTS))
def test_the_purity_guard_bites_on_each_planted_escape(
    plant: str, tmp_path: Path
) -> None:
    planted = tmp_path / "planted.py"
    planted.write_text(
        "from __future__ import annotations\n\n" + PLANTS[plant], encoding="utf-8"
    )
    assert _violations(planted), f"the guard missed the plant: {plant}"


def test_the_purity_guard_passes_the_modules_as_they_stand() -> None:
    for module in PURE_CORE_MODULES:
        path = REPO_ROOT / "latencylab" / f"{module}.py"
        assert _violations(path) == [], module


def test_pure_core_modules_do_not_touch_the_filesystem() -> None:
    offenders: list[str] = []
    for module in PURE_CORE_MODULES:
        path = REPO_ROOT / "latencylab" / f"{module}.py"
        assert path.is_file(), f"{path} is missing, so this test checks nothing"
        for problem in _violations(path):
            offenders.append(f"- latencylab/{module}.py {problem}")

    assert not offenders, (
        "The model layer must stay free of I/O. Loading belongs in "
        "latencylab/io.py.\n" + "\n".join(offenders)
    )


def test_io_is_still_the_module_that_does_the_loading() -> None:
    """Guards the rule above from passing because nothing loads anything.

    If `io.py` ever stops reading files, the forbidden list has been satisfied
    by moving the problem rather than by keeping the boundary.
    """
    io_imports = _imported_names(REPO_ROOT / "latencylab" / "io.py")
    assert io_imports & {"json", "pathlib", "os"}, (
        "latencylab/io.py no longer imports anything that reads a file, so the "
        "purity rule above may be checking an empty boundary"
    )


def test_the_wheel_contains_only_the_headless_core() -> None:
    """What setuptools would ship, checked rather than described.

    `latencylab*` also globs `latencylab_ui`, so the Qt front end is excluded by
    name in pyproject.toml. That exclusion is the difference between a GPL wheel
    and one carrying LGPL code, so it is worth a test rather than a comment.
    """
    from setuptools import find_packages

    discovered = sorted(
        find_packages(
            where=str(REPO_ROOT),
            include=["latencylab*"],
            exclude=["plans*", "examples*", "tests*", "latencylab_ui*"],
        )
    )

    assert discovered == ["latencylab"], (
        "The distributable must be the headless core alone. Discovered: "
        f"{discovered}"
    )
