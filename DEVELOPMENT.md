# Development

How to run LatencyLab from source, build it and cut a release. What it is and
who it is for is in [README.md](README.md); how it is put together is in
[ARCHITECTURE.md](ARCHITECTURE.md); running and writing the tests is in
[TESTING.md](TESTING.md). Commands run from the repository root.

## Tools

| Tool | What for | Where from |
|---|---|---|
| Python 3.10 or newer | everything | [python.org](https://www.python.org/downloads/) |
| PySide6 | the desktop interface only; the core needs nothing | `requirements.txt` |
| NumPy | the legacy v1 engine, so also the tests that use it as an oracle | the `legacy` extra, the `dev` extra or `requirements-dev.txt` |
| pytest, pytest-cov, black, flake8 | the checks | the `dev` extra or `requirements-dev.txt` |
| Pillow, Nuitka 4.2.1 or newer, PyInstaller | the desktop builds: icons, Windows, macOS | the `build` extra |
| Xcode command-line tools, Homebrew, a Developer ID and notarization credentials | the macOS build | Apple; see Building |
| flatpak, flatpak-builder | the Linux build | installed by `build_flatpak.sh` when missing |

The `build` extra is kept out of `dev` so running the suite does not install a
compiler.

## Running from source

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m pip install -r requirements.txt
```

The headless core runs as `latencylab` (the console script) or
`python -m latencylab`. The desktop interface is not part of the published
package, so it runs only from a clone or an installed desktop build:

```powershell
python -m latencylab_ui
python runner.py
```

`runner.py` is the shim the frozen build starts at too. Running the interface
from source uses your real settings: the update check keeps the version you
chose to skip in `.latencylab\settings.json` in your home directory.

## The package

The distributable is the headless core alone; the interface is excluded by name
in `pyproject.toml` and a structural test holds the wheel to that.

```powershell
python -m pip install build
python -m build
```

## Desktop builds

Install the toolchain first:

```powershell
python -m pip install -e .[build]
```

**Windows.** Two scripts, in order:

```powershell
python buildexe.py
python buildinstaller.py
```

`buildexe.py`:

1. stops unless it is running on Windows with Nuitka 4.2.1 or newer
   installed (`require_nuitka` in `build_utils.py`), before anything is
   touched;
2. stamps the version into the site under `docs/` (`stamp_version.py`);
3. clears the previous bundle and Nuitka's scratch;
4. compiles the application with Nuitka;
5. stages the bundle as `installer/payload/LatencyLab/LatencyLab.exe`;
6. starts that executable headless for a few seconds and refuses to finish if
   it dies, which is where a packaging fault shows up. No window opens.

Set `LATENCYLAB_BUILD_DEBUG=1` first to keep a console attached for tracebacks.

`buildinstaller.py`:

1. makes the same two checks;
2. stamps the version again;
3. zips the staged bundle as the setup program's payload;
4. compiles the setup program with Nuitka as one executable carrying that zip;
5. publishes it as `dist-installer/LatencyLabSetup.exe`.

The zip is deliberate: a Nuitka onefile build strips loose executables and DLLs
out of an included directory, so a payload staged as loose files would lose
exactly the parts that matter.

**macOS** (run on a Mac):

```bash
python builddmg.py
```

Checks for PyInstaller, `create-dmg`, the Xcode signing tools, every runtime
dependency and the notarization credentials before building anything, then
stamps, builds the bundle with PyInstaller, signs it, notarizes it and writes
`latencylab.dmg`. `APPLE_ID` and `APPLE_APP_PASSWORD` must both be set;
`DEVELOPER_ID_APPLICATION` names the signing identity. `ALLOW_UNNOTARIZED=1`
builds without notarizing, for local testing only.

**Linux:**

```bash
./build_flatpak.sh
./clean_flatpak.sh
```

`build_flatpak.sh` installs flatpak and flatpak-builder through the system's
package manager when they are missing, adds Flathub and installs the runtime,
then builds the Flatpak; `clean_flatpak.sh` removes only what it produced.

## Generated assets

`generate_icons.py` derives every platform icon from the master
`latencylab.png`, including the opaque macOS variants the Dock, Finder and the
disk image need. It also derives the donate button's artwork from its own
master, `donate.png`, into `assets/`. Every build ships `assets/` whole.

The mark itself starts as the SVG on the site: `render_master_icon.py`
re-renders `latencylab.png` from it. After changing the mark, run both in
order:

```powershell
python render_master_icon.py
python generate_icons.py
```

## Versioning

`VERSION` at the repository root is the only place a version is written; a
structural test fails if another file declares one. The runtime and
`pyproject.toml` read it; `stamp_version.py` writes it into the delimited tokens
of the site under `docs/`. The Windows and macOS build scripts stamp before they
build. Run `python stamp_version.py` by hand after a bump otherwise.

## Cutting a release

1. Bump `VERSION`.
2. Run the checks in [TESTING.md](TESTING.md); all three must exit 0.
3. Build on each platform as above.
4. Publish the artefacts as a GitHub release. The interface's update check
   reads GitHub's latest release, which excludes drafts and prereleases.

## Standing rules

- The core in `latencylab/` imports no Qt and never references the interface.
- The pure core modules never touch the filesystem; `io` does the loading.
- The wheel contains the headless core and nothing else.
- No module goes over 400 lines, nor sits in the band just below it; build
  scripts are exempt by name.

Each of these is held by a structural test; [TESTING.md](TESTING.md) names
them.

---

See also [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md) and
[TESTING.md](TESTING.md).
