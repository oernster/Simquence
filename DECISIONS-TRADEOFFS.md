# Decisions and trade-offs

The deliberate choices Simquence rests on: what was chosen, what was given up
for it and why. Each entry is the decision as the product makes it today.
The detail behind each one, with the tests that hold it, lives in
[ARCHITECTURE.md](ARCHITECTURE.md); [TECH_DEBT.md](TECH_DEBT.md) records what
only looks like debt and is deliberately left as it is.

## The product as a whole

### Simulate the design, not the code

Simquence runs a small written model of an architecture: the work, the events
that trigger it and the resources it queues behind. It never reads, instruments
or profiles a running program.

- **Rather than:** a profiler, a tracer or a runtime observer.
- **Gains:** a decision can be tested before any of it is built; the same tool
  serves a web checkout, a desktop interface thread or an event pipeline.
- **Costs:** the answer is only as good as the model. Somebody has to write the
  structure down before anything can run.

### Findings, not advice

The tool reports how long the flow took and which chain of work held it up. It
does not suggest a fix.

- **Rather than:** generated recommendations.
- **Gains:** every figure on screen comes from the runs themselves; nothing is
  a guess dressed as a conclusion.
- **Costs:** deciding what to change is left entirely to the reader.

### A headless core with a desktop shell over it

The simulator is a command-line program and library with no interface of its
own. The desktop application is a client of it; every number it shows comes
from the same run the command line would have produced.

- **Rather than:** an engine written inside the desktop application.
- **Gains:** the core can be scripted, tested and published on its own; the
  interface cannot quietly change a result.
- **Costs:** two front doors to keep in step.

## The model and the simulation

### Models are plain JSON in four parts

A model is a system with its entry event, the contexts work runs on, the tasks
and the wiring between events and tasks. The desktop composer writes the same
JSON a person could write by hand.

- **Rather than:** a format of the tool's own; models held only inside the
  application.
- **Gains:** a model can be read, diffed and kept under version control beside
  the design it describes.
- **Costs:** a malformed hand-written file is only caught when it is loaded and
  validated.

### Durations are distributions

Every task's duration is drawn from a fixed value, a normal distribution with
an optional floor or a lognormal one; so is every delay. Nothing else is
accepted.

- **Rather than:** a single number per task; an open list of distribution
  shapes.
- **Gains:** real variation is in the model from the start; three shapes are
  few enough to validate completely.
- **Costs:** a shape outside those three has to be approximated by one of them.

### Queues are first in, first out

Each context has a concurrency limit and serves its queue in arrival order.
Validation refuses any other queueing policy.

- **Rather than:** priorities or other scheduling rules.
- **Gains:** one queue rule to reason about when reading a result.
- **Costs:** a system that relies on priority scheduling cannot be modelled
  faithfully.

### A delay is a node that can be blamed

A delay on a wiring edge, such as a debounce or a retry backoff, becomes a task
of its own on a context with no capacity limit. It appears in the trace and on
the critical path like any other work.

- **Rather than:** delays folded silently into the timing of the next task.
- **Gains:** a delay that owns the latency is named as the culprit, which is
  the kind of finding the tool exists to surface.
- **Costs:** synthetic entries in the trace that no real code corresponds to.

### Every run seeded from its own index

Each run's random generator is seeded from the run seed and the run's index.
The same model on the same seed gives the same result, which a test holds.

- **Rather than:** one generator shared across all the runs.
- **Gains:** a change to the model can be compared on identical randomness, so
  the difference is the change rather than luck; a run can be stopped at its
  boundary without leaving another one half drawn.
- **Costs:** none recorded.

### Two schema versions, the first frozen

Models declaring schema version 1 run on the original NumPy engine, kept
unchanged and pinned by a golden snapshot. Version 2 runs on a standard library
engine that adds delayed wiring. Validation accepts only those two; a version 1
model that declares a delay is refused, because the version 1 engine would run
it without the delay and say nothing.

- **Rather than:** migrating old models to the new engine; dropping version 1.
- **Gains:** an old model still means exactly what it meant; the snapshot makes
  the determinism claim checkable.
- **Costs:** two engines in the tree. NumPy is needed for version 1 models and
  nothing else.

### One seam between the core and its engines

The core asks a single dispatch point for an engine by schema version and never
imports an engine directly. The NumPy engine is loaded only when a version 1
model asks for it.

- **Rather than:** the core calling an engine by name.
- **Gains:** the core stays standard library only; another engine can be added
  without touching the model.
- **Costs:** an abstraction with only two implementations behind it.

### A runaway model fails rather than runs forever

Each run has a ceiling on how many task instances it may create. A run that
passes it is marked failed with the reason.

- **Rather than:** no limit, which a model with a cycle in its wiring would
  turn into an endless run.
- **Gains:** a mistake in the wiring fails loudly instead of consuming the
  machine.
- **Costs:** a genuinely enormous run needs the ceiling raised on the command
  line.

## The results

### Failed runs are counted, never averaged in

The summary states how many runs were asked for, how many succeeded and how
many failed. Percentiles are taken over the successful runs alone.

- **Rather than:** dropping failures silently; letting them distort the
  percentiles.
- **Gains:** the percentiles describe runs that completed; the failures are
  still visible beside them.
- **Costs:** a model where many runs fail gives percentiles over a smaller set
  than the reader may assume.

### The critical path is counted across runs

For every run the chain of work that kept it from finishing sooner is recorded.
The summary lists the ten most frequent chains with how often each held the
flow up.

- **Rather than:** one critical path from one run; an average path.
- **Gains:** the reader sees which chain dominates and how often, which is the
  question a design decision turns on.
- **Costs:** chains outside the ten most frequent are not listed in the
  summary.

### A cancelled run set is never aggregated

Stopping a run is checked between one run and the next. A stop raises with the
number of runs completed rather than returning the shorter set; the desktop
application reports that count.

- **Rather than:** percentiles over whatever had finished.
- **Gains:** no figure on screen can come from a set nobody asked for.
  Percentiles over half the runs would look exactly like real ones.
- **Costs:** a stop throws away the runs already done. The worst wait before a
  stop takes effect is one run.

### Distributions show the runs, nothing more

The distributions panel draws a histogram of how long each run took, binned by
the Freedman-Diaconis rule, plus how often each critical path occurred. It
reads the runs already made. The bins are widened when that rule would need
more than 200 of them, which one heavy tail can: it once asked for millions.

- **Rather than:** resimulating, smoothing or fitting a curve.
- **Gains:** every bar is a count of real runs.
- **Costs:** a small run set gives a ragged picture.

### Export as one archive of plain text

The desktop application exports the last results as a single zip holding a
summary and one text file per run. The command line writes a JSON summary, a
CSV of runs and an optional CSV trace.

- **Rather than:** a format of the application's own.
- **Gains:** results open in anything that reads text or a spreadsheet.
- **Costs:** none recorded.

## Privacy and the network

### One way out: the update check

The only outbound request is the update check against GitHub's releases. It
carries no token or account; it is asked about three seconds after the window
opens, then once a day, with a five second timeout. A failure on the automatic
path says nothing.

- **Rather than:** no check at all; telemetry or usage figures.
- **Gains:** updates are found without anything about the user or the model
  leaving the machine.
- **Costs:** one unprompted request a day. The Flatpak, which once asked for no
  network at all, now needs the network grant for this one call.

### Only published releases count; a skip is remembered

The check reads GitHub's latest release, which excludes drafts and
pre-releases. The user can download, skip that version or decide later; a
skipped version never prompts again on the automatic path. A check somebody
asks for from the Help menu always answers.

- **Rather than:** prompting for every tag; asking again about a version
  already declined.
- **Gains:** a tag pushed mid-development never prompts anyone; a declined
  version stays declined.
- **Costs:** the skip lives in a settings file in the user's home folder.

### Donations go through the browser

The top bar carries a donate button beside the theme toggle. Pressing it hands
one fixed address to the desktop's browser; the application fetches nothing
itself. If the desktop declines, the application says so and shows the
address. Nothing is held back behind a donation.

- **Rather than:** a band of its own at the foot of the window; a payment page
  inside the application.
- **Gains:** the ask sits in the tray that already exists; the update check
  stays the application's only outbound request.
- **Costs:** one more control on a crowded bar; a picture that needs its
  tooltip to say it leaves the application.

## The interface

### Run is inert until there is a model

The Run button is disabled until a model is loaded. A disabled control wears a
red ring and its tooltip says why.

- **Rather than:** a button that can always be pressed and answers with a
  complaint.
- **Gains:** the question is answered before it is asked.
- **Costs:** none recorded.

### The composer names a model's parts

The composer is a modal dialog with two panes: the parts of the model on the
left, the editor for the one selected on the right. It is shown without a
nested event loop.

- **Rather than:** a dock down the side holding every section at once.
  Measured with the checkout example loaded, that column asked for 4,822 pixels
  of height in a viewport of about 880.
- **Gains:** measured the same way afterwards, every section fits without
  scrolling.
- **Costs:** only one part of the model is on screen at a time; the main
  window is out of reach while the composer is open.

### Composing and editing are one surface

Edit opens the loaded model in the same dialog that composes a new one. An open
editor follows the next model opened, unless it holds work typed from scratch.

- **Rather than:** an editor that could only build and export; a second dialog
  for changing an existing model.
- **Gains:** a model that has just been opened can be changed; typed work is
  never replaced by a refresh.
- **Costs:** reading a model back in has to accept every spelling the file
  format allows.

### Scrolling past a control never changes it

The wheel is denied to any input that does not have focus and is handed to the
nearest area that can scroll. The guard is installed once for the whole
application.

- **Rather than:** the toolkit's default, which rewrote concurrencies and
  distributions as the reader scrolled past them.
- **Gains:** reading a model cannot alter it.
- **Costs:** a value has to be clicked or tabbed into before the wheel will
  change it.

### One explicit keyboard ring

Tab and Right step forward, Shift+Tab and Left step back; the ring wraps at
both ends and skips anything disabled. The main window starts with nothing
focused; a dialog opens on its first usable control.

- **Rather than:** the toolkit's natural tab order.
- **Gains:** the whole application works from the keyboard in one predictable
  order, including the centred chart button on the toolbar.
- **Costs:** Left and Right are taken by the ring. That is why Examples is a
  menu of its own rather than a submenu of File.

### Examples come from the folder

Every model in the examples folder is on the Examples menu, labelled from its
file name. The test that validates the examples walks the same folder.

- **Rather than:** a list of examples written into the code.
- **Gains:** adding a model to the folder puts it on the menu and under test at
  once; a fresh install has something to run.
- **Costs:** labels are derived from file names rather than written as
  captions.

### Toolbar actions wear pictures, not emoji

Every action on the toolbar wears a supplied picture. A disabled action is
drawn grey and faded, keeping none of its colour; a missing picture falls back
to the action's name in words.

- **Rather than:** emoji or glyphs drawn in code.
- **Gains:** the bar looks the same on every machine, since an emoji is
  whatever font happens to be installed; a disabled action never reads as
  half-available.
- **Costs:** the pictures ship as files beside the application.

### The distributions switch sits centre

The chart button in the middle of the toolbar opens and closes the
distributions panel. Its checked state follows the panel itself, not the click.

- **Rather than:** one more small button in the left-hand group.
- **Gains:** the most prominent control is the one that matters after a run; it
  tells the truth when the panel is closed some other way.
- **Costs:** the chart's yellow bar is partly lost on the yellow checked fill;
  its outline keeps the picture readable.

### Point once at what to do next

When a model loads, the Run button's border flashes twice and stops. It never
flashes a disabled control.

- **Rather than:** no cue; a pulse that continues until it is obeyed.
- **Gains:** the eye is drawn across the window without nagging.
- **Costs:** a user looking elsewhere for those few seconds misses it.

### One copy runs

A second launch asks the first copy to come forward and exits. It uses a local
socket rather than a lock file. On Windows the application claims the same
taskbar identity the installer's shortcut carries.

- **Rather than:** several copies; a bare lock that leaves the second launch
  with nothing.
- **Gains:** the click does what the user meant; the pinned icon and the
  window are one taskbar item.
- **Costs:** the networking module has to ship for a local socket, which is
  what forced the Flatpak to build Kerberos.

### One token set, two themes

Light and dark themes are generated from one stylesheet template and one set of
colour tokens. Menus, tooltips and popups have a surface and border of their
own; a test checks that contrast against rendered pixels.

- **Rather than:** colours written where they are used; popups painted in the
  window colour, which measured at zero luminance difference in the dark theme.
- **Gains:** the two themes cannot drift apart; a floating surface is always
  distinguishable from the page behind it.
- **Costs:** a new colour has to be added as a token in both themes.

### Two guides rather than one

The Guide says which button to press and why one setting rather than another.
How to Read says what the output means. Both live as text apart from their
dialogs; long text scrolls itself gently and stops the moment the reader takes
over.

- **Rather than:** one help document answering both questions.
- **Gains:** each answers the question asked at its own moment; the words can
  change without touching the widgets.
- **Costs:** two documents to keep true.

### Open and Export start in Downloads

File dialogs open in the user's Downloads folder, falling back to the home
folder.

- **Rather than:** the working directory or the install folder.
- **Gains:** a model arrives where downloaded models land; an export is easy to
  find.
- **Costs:** none recorded.

## Building and installing

### The published wheel is the core alone

The Python package contains the simulator and nothing else. Its runtime
dependencies are empty; NumPy is an optional extra for version 1 models. A
test asserts the wheel holds the core alone.

- **Rather than:** shipping the desktop interface in the package.
- **Gains:** installing the library pulls in no interface toolkit at all.
- **Costs:** the desktop application has to be installed separately or run
  from a clone.

### Two licences plus a commercial one

The core is GPL-3.0 and the desktop front end LGPL-3.0; the application shows
both under Help. A commercial licence for the author's own code is offered
separately.

- **Rather than:** one licence for everything.
- **Gains:** the interface layer carries the same lighter terms as the toolkit
  it is built on.
- **Costs:** two licence texts to keep straight.

### Nuitka on Windows, wrapped in a setup program of its own

Windows gets a Nuitka standalone build, started headless as a smoke test before
it ships. A bespoke setup program carries it as a zip, because a Nuitka onefile
build strips loose executables out of an included folder.

- **Rather than:** a generic installer; shipping the folder unzipped.
- **Gains:** a build that dies on start fails the build rather than reaching a
  user; the setup program wears the application's own look.
- **Costs:** the setup program is Simquence's own to maintain.

### Installed for one user, without administrator rights

The setup program installs into the user's local application data and
registers under the current user's registry. Install, upgrade, repair and
removal are one screen; every action is refused while the application is
running. The work happens on the interface thread.

- **Rather than:** a machine-wide install; a multi-page wizard; a worker
  thread.
- **Gains:** no administrator prompt; no half-applied install over a running
  copy. An install measured in seconds does not need a worker; leaving one out
  removes the deadlock that hung two earlier installers.
- **Costs:** each account installs separately; the window is busy while it
  works.

### macOS builds are notarised or fail

The macOS disk image is built with PyInstaller, signed, notarised and stapled,
both the image and the application inside it. The build refuses to run without
notarisation credentials unless a local test build is asked for explicitly;
that output is labelled unreleasable. Credentials come from a per-app keychain
profile unless an account and app-specific password are supplied for a machine
with no keychain.

- **Rather than:** skipping notarisation when credentials were missing, which
  shipped images that would not open on any other machine.
- **Gains:** a released image opens offline; on the keychain route no secret
  sits in the environment or in process arguments.
- **Costs:** an Apple developer account; a different packager from Windows.

### The Flatpak builds offline, Kerberos included

The Flatpak installs pre-downloaded wheels with no network inside the build
sandbox. It builds Kerberos from a source pinned by address and checksum,
because the toolkit's networking library
links against it and the runtime does not ship it.

- **Rather than:** fetching packages inside the build; leaving the library out.
- **Gains:** a reproducible build; the application reaches its first window.
  Without the library it failed only inside the Flatpak and only at start-up.
- **Costs:** a module built for a library the application never calls.

### One version string

The root VERSION file is the only place a version is written. The core, the
interface and the package metadata read it; the website is stamped from it by
script. A test checks they agree.

- **Rather than:** a version written in several places.
- **Gains:** the number cannot disagree with itself.
- **Costs:** the static site has to be stamped after every change.

### The site's stylesheet is versioned by its content

The stamper links each stylesheet and script on the site with a hash of its
content, with line endings folded so Windows and GitHub agree.

- **Rather than:** relying on the browser to notice a changed file.
- **Gains:** a new page is never paired with an old cached stylesheet.
- **Costs:** none recorded.

### One master picture for every icon

A single PNG is the origin of the application icon. One script derives every
platform's icon from it and the site's logo too. The macOS icons sit on an
opaque tile; the others stay transparent.

- **Rather than:** platform icons drawn or exported separately; a site logo
  kept apart from the application's.
- **Gains:** the site and the application cannot show two different marks.
- **Costs:** the master is shipped inside every build, since every build ships
  the assets folder whole.

### A renamed product clears up after its old name, only when asked

Simquence was LatencyLab. Its new name is a new identity on every platform, so
an update would otherwise stand beside the old install. On Windows, setup looks
for the old install, lists exactly what it would remove and removes it only on
the user's say. It removes only what it can show is the old install's own;
anything else is reported and left.

- **Rather than:** keeping the old identity under a new name; removing the old
  install silently; leaving two installs side by side.
- **Gains:** one program, one Apps entry and one set of shortcuts, with nothing
  taken that the user was not shown.
- **Costs:** the old settings file is not carried over, which costs at most one
  repeated update prompt. On macOS and Linux the old application stays until
  the user removes it.

## Engineering

### The core never imports the interface

The simulator may not import Qt or the desktop package; its pure modules may
not reach for the filesystem. Structural tests scan the source for both.

- **Rather than:** convention alone.
- **Gains:** the core runs and is tested with no toolkit installed; the
  boundary cannot erode one import at a time.
- **Costs:** the interface has to pass in anything the core needs from it,
  such as the cancel flag.

### Complete coverage, without padding

The suite fails below full coverage. The threshold lives in the project's test
configuration, so running the suite at all enforces it. The delivery scripts
and the setup program are left out of the measurement.

- **Rather than:** an opt-in command line; a figure padded with fake coverage
  of build recipes that only mean anything against a real toolchain.
- **Gains:** nobody can run the suite and skip the gate; the figure covers code
  the suite can actually exercise.
- **Costs:** the setup program and the build scripts are proved by building
  rather than by tests.

### Small files, cut well below the cap

No Python file may exceed four hundred lines, tests included. A file within
five per cent of the cap fails too, so a split goes to a size with room in it.
Delivery scripts at the repository root are exempt by name; a test fails if an
exempt name stops existing.

- **Rather than:** letting files grow; shaving a file to just under the limit.
- **Gains:** modules split at real seams; a rename cannot leave a hole that
  exempts whatever takes the name next.
- **Costs:** families of small modules where one class might otherwise have
  been one file.
