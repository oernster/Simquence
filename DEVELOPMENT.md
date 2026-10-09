# Development

How to run Simquence from source, build it and cut a release. What it is is in [README.md](README.md); how it is put together is in [ARCHITECTURE.md](ARCHITECTURE.md); the tests are in [TESTING.md](TESTING.md). Commands run from the repository root.

## Tools

| Tool | What for | Where from |
|---|---|---|
| Python 3.10 or newer | everything | [python.org](https://www.python.org/downloads/) |
| PySide6 | the desktop interface only; the core needs nothing | `requirements.txt` |
| NumPy | the legacy v1 engine and the tests that use it as an oracle | the `legacy` extra, the `dev` extra or `requirements-dev.txt` |
| pytest, pytest-cov, black, flake8, setuptools | the checks | the `dev` extra or `requirements-dev.txt` |
| Pillow, Nuitka 4.2.1 or newer, PyInstaller | the desktop builds: icons, Windows, macOS | the `build` extra (kept out of `dev` so the suite does not install a compiler) |
| Xcode command-line tools, Homebrew, a Developer ID and notarization credentials | the macOS build | Apple |
| flatpak, flatpak-builder | the Linux build | installed by `build_flatpak.sh` when missing |

## Running from source

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m pip install -r requirements.txt
python -m simquence_ui
```

The headless core runs as the `simquence` console script or `python -m simquence`. The interface is not in the published package, so it runs only from a clone or an installed desktop build. From a clone, `python runner.py` is the same launch through the shim the frozen build starts at. Running it from source uses your real settings: the update check keeps a skipped version in `.simquence\settings.json` in your home directory.

## The package

The distributable is the headless core alone; the interface is excluded by name in `pyproject.toml` and a structural test holds the wheel to that.

```powershell
python -m pip install build
python -m build
```

## Desktop builds

Install the toolchain first with `python -m pip install -e .[build]`.

### Windows

```powershell
python buildexe.py
python buildinstaller.py
```

`buildexe.py`:

1. stops unless it is on Windows with Nuitka 4.2.1 or newer, before anything is touched;
2. stamps the version into the site under `docs/`;
3. clears the previous bundle and Nuitka's scratch;
4. compiles the application with Nuitka;
5. stages the bundle as `installer/payload/Simquence/Simquence.exe`;
6. starts that executable headless for a few seconds and refuses to finish if it dies, which is where a packaging fault shows up. No window opens.

Set `SIMQUENCE_BUILD_DEBUG=1` first to keep a console attached for tracebacks.

`buildinstaller.py` makes the same checks, stamps again, zips the staged bundle as the setup program's payload and compiles the setup program with Nuitka as one executable carrying that zip: `dist-installer/SimquenceSetup.exe`. The zip is deliberate: a Nuitka onefile build strips loose executables and DLLs out of an included directory.

### macOS (on a Mac)

```bash
python builddmg.py
```

Checks for PyInstaller, `create-dmg`, the Xcode signing tools, every runtime dependency and the notarization credentials before building, then stamps, builds the bundle with PyInstaller, signs, notarizes and writes `simquence.dmg`.

- Notarization uses the keychain profile `Simquence`, stored once with `xcrun notarytool store-credentials`. `APPLE_KEYCHAIN_PROFILE` names a different profile (such as one stored under the old name `LatencyLab`).
- Setting both `APPLE_ID` and `APPLE_APP_PASSWORD` (an app-specific password) uses that pair instead, for a machine with no keychain.
- `DEVELOPER_ID_APPLICATION` names the signing identity.
- `ALLOW_UNNOTARIZED=1` builds without notarizing, for local testing only.

### Linux

```bash
./build_flatpak.sh
./clean_flatpak.sh
```

`build_flatpak.sh` installs flatpak and flatpak-builder when missing, adds Flathub, installs the runtime and builds the Flatpak; `clean_flatpak.sh` removes only what it produced.

## Generated assets

`generate_icons.py` derives every platform icon from the master `assets/application-icon.png` (including the opaque macOS variants and the site's logo at `docs/assets/simquence.png`) plus the donate button's artwork from its own master, `donate.png`. The toolbar's action pictures (`assets/simquence_*.png` other than the icon set) are supplied finished and read as they are. Every build ships `assets/` whole. After changing a master:

```powershell
python generate_icons.py
```

## Versioning

`VERSION` at the repository root is the only place a version is written; a test fails if the core or the interface reports anything else. The runtime and `pyproject.toml` read it; `stamp_version.py` writes it into the delimited tokens of the site under `docs/`. The Windows and macOS builds stamp before they build; otherwise run `python stamp_version.py` after a bump.

## Cutting a release

1. Bump `VERSION`.
2. Run the checks in [TESTING.md](TESTING.md); all three must exit 0.
3. Build on each platform as above.
4. Publish the artefacts as a GitHub release. The update check reads GitHub's latest release, which excludes drafts and prereleases.

## Standing rules

Each is held by a structural test named in [TESTING.md](TESTING.md):

- The core in `simquence/` imports no Qt and never references the interface.
- The pure core modules never touch the filesystem; `io` does the loading.
- The wheel contains the headless core and nothing else.
- No module goes over 400 lines, nor sits in the band just below it; build scripts are exempt by name.

---

See also [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md) and [TESTING.md](TESTING.md).
