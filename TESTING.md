# Testing

How Simquence is tested: the checks, how to read them, what the gate holds and how a test or guard is written. The layer rules are in [ARCHITECTURE.md](ARCHITECTURE.md); setting up the environment is in [DEVELOPMENT.md](DEVELOPMENT.md).

## Running the checks

From the repository root, with the venv active:

```powershell
python -m pytest
python -m black --check .
python -m flake8 .
```

`pytest` alone is the gated run: `pyproject.toml` adds the coverage measurement and the floor, so the suite cannot run without the gate. A full run takes under half a minute (714 tests in about 18 seconds on Windows).

**black and flake8 are not part of the suite** and there is no CI, so a lint regression passes `pytest` untouched. Run all three and read each exit code. A default-rules `ruff check` reports a backlog; ruff has not been adopted, so its findings are a reading rather than a regression ([TECH_DEBT.md](TECH_DEBT.md) says why).

**Read the exit code, never the text.** Coverage rows are named after modules, so searching the output for a result word is not safe. `0` means the tests passed AND the floor was met; anything else means read the failures above the coverage table.

## What the gate holds

The floor is 100% LINE coverage (`--cov-fail-under=100`); `.coveragerc` does not switch on branch measurement. It is measured over the whole repository less a named list, so the core in `simquence/`, the interface in `simquence_ui/` and the root shims `runner.py` and `stamp_version.py` are all inside it.

| Outside the floor | Why |
|---|---|
| `tests/`, the virtual environments | not product code |
| `buildexe.py`, `buildinstaller.py`, `builddmg.py`, `build_utils.py`, `dmg_icon.py`, `generate_icons.py` | build scripts, proved by a build against a real toolchain |
| `installer/*` | the setup program, for the same reason: it acts on a real filesystem and registry |
| `generate_scripts.py` | a gitignored local helper, not part of the product |

Lines marked `# pragma: no cover` are also excluded: 48 outside `tests/`, most in the interface (16 in `simquence_ui/focus_cycle.py`), 8 in the installer's operations and 3 in the legacy engine. Read 100% as "100% of the lines measured".

## Running it by hand

- **No window, provided the platform is unset.** `tests/conftest.py` sets `QT_QPA_PLATFORM` to `offscreen` with `setdefault`; a shell that already sets it to something else puts every window on screen.
- **Your settings are never written.** The update check keeps its settings at `.simquence\settings.json` in your home directory. Tests that save settings point the store at `tmp_path`; the update-check tests pass a fake store. No guard holds this, so a new test has to keep to it.
- **Nothing leaves the machine.** The GitHub release source is handed a stand-in opener.
- **The legacy engine needs NumPy.** The golden snapshot in `test_determinism.py` and the oracle checks in `test_migration_oracle_invariants.py` run the frozen v1 engine; the `dev` extra and `requirements-dev.txt` both bring NumPy in.

## Where the tests live

All 94 files sit flat in `tests/` (92 test modules plus `conftest.py` and `scroller_harness.py`):

| Kind | What it tests | Against |
|---|---|---|
| the core | the simulator, the model schema, distributions, the legacy engine and its golden snapshot | models built in the test, the shipped examples |
| the interface (`test_ui_*`) | windows, panes, the toolbar, the focus cycle, the update check, single instance | a real `QApplication` and real widgets, offscreen |
| the setup program (`test_installer_*`) | payload reading, licence lookup, version comparison, Repair, its dialogs' keyboard and the rules for removing an install left under the LatencyLab name | real files in a temporary folder, readings built in the test |

## Writing a test

- **No mocking library.** A collaborator is stood in for by a small fake written in the test (`FakeSettings` in the update-check tests is the pattern); environment and attributes are redirected with `monkeypatch`.
- **Anything that writes takes `tmp_path`.** Never let a store fall back to its default path under your home directory.

## Guards

A structural test checks the source tree rather than behaviour, so a rule holds for code nobody has written yet.

| Guard | Holds |
|---|---|
| `test_ui_dependency_boundaries.py` | the core imports no Qt and never references the interface package |
| `test_core_boundaries_and_packaging.py` | the pure core modules (`model`, `types`, `validate`) import only an exact allowlist and call no `open`, `__import__`, `exec` or `eval`; `io` stays the module that loads; the wheel contains only the headless core |
| `test_codebase_size_limits.py` | the 400 line cap, the danger band below it and no stale entry in the build-script exemption |
| `test_version_single_source.py` | the core and the interface report the number in `VERSION`; the site stamping behaves. It does not scan other files for a stray version |
| `test_ui_focus_ring_selectors.py` | no stylesheet in the application or the installer puts a focus, hover or disabled border on a text view, an item view, a container class or `*` |
| `test_ui_panes_are_not_stops.py` | on every window and dialog of the application and the installer: no pane is a stop, a reading pane is one only by Tab and only while it overflows, a click never focuses one and no dialog opens on one |

**A guard is not trusted until it has been seen to fail.** Prove a new guard by planting the violation it exists to catch, reading the failure, then restoring the tree in a `finally` block. A test written for a defect is run before the fix, where it has to fail for the reason named.

---

See also [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md) and [DEVELOPMENT.md](DEVELOPMENT.md).
