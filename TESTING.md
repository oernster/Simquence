# Testing

How LatencyLab is tested: running the checks, reading what they say, what the
gate holds and what it leaves out, the rules a run by hand has to follow and
how a new test or guard is written. The layer rules themselves are in
[ARCHITECTURE.md](ARCHITECTURE.md); setting up the environment the tests run in
is in [DEVELOPMENT.md](DEVELOPMENT.md).

## Running the checks

From the repository root, with the venv active:

```powershell
python -m pytest
python -m black --check .
python -m flake8 .
```

`pytest` alone is the gated run: the options in `pyproject.toml` add the
coverage measurement and the floor, so there is no way to run the suite without
the gate. Add `-v` to see each test named as it runs.

**black and flake8 are not part of the suite.** No test runs them and there is
no CI, so a formatting or lint regression passes `pytest` untouched. Run all
three and read the exit code of each. A default-rules `ruff check` reports a
backlog here; ruff has not been adopted, so its findings are a reading rather
than a regression ([TECH_DEBT.md](TECH_DEBT.md) says why).

**A full run takes under half a minute.** Measured on 2026-10-03: 612 tests
passed in 19 seconds on Windows.

**Read the exit code, never the text.** The run prints the coverage table then
one summary line. A search of the output for a result word is still not safe,
since coverage rows are named after modules. `0` means the tests passed AND the
floor was met; anything else means read the failures above the table.

## What the gate holds

The floor is 100% LINE coverage (`--cov-fail-under=100`), not branch:
`.coveragerc` does not switch branch measurement on. It is measured over the
whole repository (`--cov=.`) less a named list in `.coveragerc`, so the
headless core in `latencylab/`, the desktop interface in `latencylab_ui/` and
the root shims `runner.py` and `stamp_version.py` are all inside it.

Outside the floor:

| Omitted | Why |
|---|---|
| `tests/`, the virtual environments | not product code |
| `buildexe.py`, `buildinstaller.py`, `builddmg.py`, `build_utils.py`, `dmg_icon.py`, `generate_icons.py`, `render_master_icon.py` | build scripts: linear recipes that only mean anything against a real toolchain, so a build proves them |
| `installer/*` | the setup program, for the same reason: it acts on a real filesystem and a real registry |
| `generate_scripts.py` | a local helper, not part of the product |

Then any line marked `# pragma: no cover`. Counted on 2026-10-03: 48 of them
outside `tests/`,
most in the interface (16 in `latencylab_ui/focus_cycle.py`), 7 in the
installer's operations and 3 in the legacy engine. Read 100% as "100% of the
lines measured".

## Running it by hand

- **No window, provided the platform is unset.** `tests/conftest.py` sets
  `QT_QPA_PLATFORM` to `offscreen` with `setdefault`, so it applies only when
  the variable is not already set. A shell that already has it set to
  something else puts every window on screen.
- **Your settings are never written.** The update check's settings live at
  `.latencylab\settings.json` in your home directory. The tests that save
  settings point the store at pytest's `tmp_path`; the update-check tests pass
  a fake store and the entry-point tests replace the update-check wiring
  entirely. Measured on 2026-10-02: after a full run the real file did not
  exist. No guard holds this, so a new test has to keep to it.
- **Nothing leaves the machine.** The GitHub release source is handed a
  stand-in opener; the one test that names `urlopen` only checks it is the
  default.
- **The legacy engine needs NumPy.** The golden snapshot in
  `test_determinism.py` and the oracle checks in
  `test_migration_oracle_invariants.py` run the frozen v1 engine, so NumPy must
  be installed; both the `dev` extra and
  `requirements-dev.txt` bring it in.

## Where the tests live

All 81 files sit flat in `tests/`. They fall into three kinds:

| Kind | What it tests | Against |
|---|---|---|
| the core | the simulator, the model schema, distributions, the legacy engine and its golden snapshot | values and models built in the test, the shipped examples |
| the interface (files named `test_ui_*`) | the windows, panes, focus cycle, update check and single instance | a real `QApplication` and real widgets, offscreen |
| the setup program's logic | payload reading and licence lookup | real files in a temporary folder |

## Writing a test

- **No mocking library.** A collaborator is stood in for by a small fake
  written in the test (`FakeSettings` in the update-check tests is the
  pattern). Environment and attributes are redirected with pytest's own
  `monkeypatch`.
- **Anything that writes takes `tmp_path`.** Never let a store fall back to
  its default path under your home directory.

## Guards

A structural test checks the source tree rather than behaviour, so a rule holds
for code nobody has written yet.

| Guard | Holds |
|---|---|
| `test_ui_dependency_boundaries.py` | the core imports no Qt and never references the interface package |
| `test_core_boundaries_and_packaging.py` | the pure core modules (`model`, `types`, `validate`) import only an exact allowlist and call no `open`, `__import__`, `exec` or `eval`, proved by planting each escape the old denylist missed; `io` stays the module that loads; the wheel contains only the headless core |
| `test_codebase_size_limits.py` | the 400 line cap, the danger band below it and no stale entry in the build-script exemption |
| `test_version_single_source.py` | the core and the interface report the number in `VERSION` and the site stamping behaves; it does not scan other files for a stray version |

**A guard is not trusted until it has been seen to fail.** A new guard is
proved by planting the violation it exists to catch and reading the failure,
then restoring the tree in a `finally` block so an interrupted proof cannot
leave the plant behind. A test written for a defect is run before the fix,
where it has to fail for the reason named, not merely fail.

---

See also [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md) and
[DEVELOPMENT.md](DEVELOPMENT.md).
