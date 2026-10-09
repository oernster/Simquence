# <img width="64" height="64" alt="Simquence" src="docs/assets/simquence.png" /> Simquence

Simulate your architecture's latency before you build it.

Simquence is a design-time latency simulator. You describe a software architecture as a small, explicit model: the units of work, the events that trigger them and the shared resources they queue behind. Simquence runs that model thousands of times with realistic timing variation and reports how long the flow takes across percentiles, which chain of work held each run up and how often each chain is the culprit. It works on the design rather than the code, so it applies to any event-driven software.

It is not a profiler, tracer or runtime observer. It exists to prevent confident people from shipping bad architecture.

> **Commercial licences available.** Simquence is free and open source under GPL-3.0, with its interface layer under LGPL-3.0. If those terms do not suit what you are building, such as a closed-source product, a commercial licence can be bought from me separately. It covers my own code; PySide6 keeps its own LGPL-3.0 licence. See [commercial licensing](https://ernster.dev/commercial-licensing.html).

## The workflow

Model, run, read, change one thing, run again on the same seed, compare. The randomness is identical between the two runs, so any shift in the percentiles or the dominant critical path is the cost or benefit of the design change rather than luck.

Each run records the **makespan** (how long the whole flow took, which is how long the user waited) and the **critical path** (the chain of tasks and waits that set the finish time; expensive work off that chain delayed nobody). One run tells you nothing; the spread across runs is the finding.

## What is a model?

Your architecture written down small enough to argue about, in four parts:

- **System:** a name and the entry event that starts a run.
- **Contexts:** what work runs on (a thread pool, a database connection, a UI thread), each with a **concurrency**: how many things it can genuinely do at once. Concurrency 1 means everything waits in line; that is where most surprising latency comes from.
- **Tasks:** units of work, each with a context, a duration distribution and the events it emits when it finishes.
- **Wiring:** which events trigger which tasks, optionally after a delay (debounces, backoffs, poll intervals). The wiring is the architecture.

A useful model is often 10 to 20 tasks. Models are plain JSON; the desktop app's Composer builds them without hand-writing any. An excerpt of the shipped [Checkout example](examples/checkout.json) (the full model has ten tasks):

```json
{
  "schema_version": 2,
  "entry_event": "user.checkout_clicked",
  "contexts": {
    "ui": { "concurrency": 1 },
    "db": { "concurrency": 1 }
  },
  "tasks": {
    "ui.handle_click": {
      "context": "ui",
      "duration_ms": { "dist": "fixed", "value": 4.0 },
      "emit": ["checkout.started"]
    },
    "db.load_cart": {
      "context": "db",
      "duration_ms": { "dist": "lognormal", "mu": 4.4, "sigma": 0.45 },
      "emit": ["cart.loaded"]
    },
    "ui.render_cart": {
      "context": "ui",
      "duration_ms": { "dist": "normal", "mean": 18.0, "std": 4.0, "min": 1.0 },
      "emit": ["ui.section_rendered"]
    }
  },
  "wiring": {
    "user.checkout_clicked": ["ui.handle_click"],
    "checkout.started": ["db.load_cart"],
    "cart.loaded": ["ui.render_cart"]
  }
}
```

## Who this is for

Senior engineers, architects and CTOs making structural decisions about event-driven software while those decisions are still cheap to change: a web checkout, a desktop UI thread, a microservice fan-out, an embedded pipeline. If you have ever said "we will profile it later", this is what later should have looked like. The reasoning behind it is on the site: [Why Simquence exists](https://ernster.dev/Simquence/why.html).

## Who this is not for

- Anyone tuning code that already exists. Use a profiler.
- Anyone who wants a dashboard that reassures them everything is fine.
- Anyone expecting generated recommendations. It will not tell you how to make a function faster.
- Anyone unwilling to commit to explicit structure. The model has to be written down before it can be run.

## Capabilities

The core is a CLI that reads a JSON model and writes `summary.json` (aggregate latency and contention statistics), `runs.csv` (per-run metrics) and an optional `trace.csv` (per-task-instance timing and causality).

The PySide6 desktop application adds inspection rather than capability; every number it shows comes from the same engine:

- **Examples menu.** Every shipped model, so a fresh install has something to run. Start with **Checkout**, where a 150 ms debounce added for politeness turns out to own the median.
- **Model Composer.** A two-pane dialog: the four parts of a model on the left, the editor for the selected one on the right. Edit opens the loaded model in the same dialog.
- **Guide and How to Read.** Six numbered steps to a first run, then a companion on reading the output. Both read themselves at a pace you can follow and hand control back the moment you touch them.
- **Distributions.** A makespan histogram binned by the Freedman-Diaconis rule (capped at 200 bins) plus a critical-path frequency chart. No resimulation, smoothing or inference. The chart button in the middle of the toolbar opens it.
- **Cancel that cancels.** Stopping takes effect between one run and the next and reports how many completed; a partial set is never aggregated.
- **Full keyboard navigation.** One focus ring: Tab and Right forward, Shift+Tab and Left back, wrapping at both ends. A disabled control is skipped and wears a red ring.
- **Light and dark themes** from one token set.
- **Update check.** Shortly after launch, then daily, the app asks GitHub anonymously whether a newer published release exists (also Help > Check for Updates). You choose Download, Skip This Version or Later. A failed check stays silent.
- **No other connections.** Models and results never leave your machine. Open and Export start in your Downloads folder.

On Windows, setup installs per user with no administrator rights. If it finds an install from when the product was called LatencyLab, it lists exactly what it would remove and removes it only when you say so.

## Stack

| Concern | Choice |
|---|---|
| Language | Python 3.10 or newer |
| Core engine | Standard library only, no Qt and no third-party runtime dependency |
| Legacy v1 engine | NumPy, optional and lazily imported; runs `schema_version: 1` models and is the frozen oracle the snapshot test pins |
| Desktop UI | PySide6, a client of the headless core |
| Tests | pytest with pytest-cov, gate configured in `pyproject.toml` |
| Style | black and flake8 at 88 columns |
| Packaging | setuptools, version read from the root `VERSION` file |
| Delivery | Nuitka plus a bespoke installer (Windows), disk image (macOS), Flatpak (Linux) |
| Licence | core GPL-3.0, UI LGPL-3.0 |

## Install and run

```bash
python -m pip install -e .[dev]
python -m pip install -r requirements.txt
python -m simquence_ui
```

`requirements.txt` brings in PySide6, which only the desktop UI needs; the simulation core has no runtime dependency. `python runner.py` is the same launch through the shim the frozen build starts at. The UI is deliberately not part of the published wheel, so run it from a clone or install a desktop build.

Models at `schema_version: 1` run on a frozen NumPy engine, installed with `python -m pip install -e .[legacy]` (the `dev` extra already includes it). Without it a v1 model fails with a message naming the extra; `schema_version: 2` never needs it.

## Tests

```bash
python -m pytest
```

The 100% line coverage gate is configured in `pyproject.toml`, so this command enforces it and there is no way to run the suite without it. See [TESTING.md](TESTING.md).

## Build

```bash
python -m pip install build
python -m build
```

The wheel contains the headless core `simquence/` and nothing else. The desktop builds need the `build` extra, kept out of `dev` so running the suite does not install a compiler:

```bash
python -m pip install -e .[build]
python generate_icons.py
python buildexe.py
python buildinstaller.py
```

`builddmg.py` builds the macOS disk image on macOS; `build_flatpak.sh` builds the Linux Flatpak. Each build in order, the generated assets and cutting a release are in [DEVELOPMENT.md](DEVELOPMENT.md).

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): the layers, the invariants and the tests that enforce them.
- [DEVELOPMENT.md](DEVELOPMENT.md): running from source, each build in order and cutting a release.
- [TESTING.md](TESTING.md): the checks, what the gate holds and how a test is written.
- [TECH_DEBT.md](TECH_DEBT.md): what is still open, what is deliberately left and what only looks like debt.
- [DECISIONS-TRADEOFFS.md](DECISIONS-TRADEOFFS.md): the decisions Simquence rests on, with what each gains and costs.

## Supporting the project

Simquence is free and stays free. There is no paid tier, no licence key and no feature held back behind a donation. If it has saved you time, a donation supports its maintenance and continued development. The same link sits in the app's top bar; pressing it hands the address to your browser and Simquence itself opens no connection.

<a href="https://www.paypal.com/ncp/payment/Y275VZ7R2NUNW"><img src="docs/donate.png" alt="Donate to Simquence" width="120"></a>

## Licence

Licensed by component, as the running application shows under Help:

- The simulation core in `simquence/` (and so the published wheel) is **GPL-3.0**: [LICENSE](LICENSE).
- The PySide6 desktop front end in `simquence_ui/` is **LGPL-3.0**: [`simquence_ui/LGPL3.txt`](simquence_ui/LGPL3.txt).

A commercial licence for my own code is also available, separately from the open-source licences: see [commercial licensing](https://ernster.dev/commercial-licensing.html).
