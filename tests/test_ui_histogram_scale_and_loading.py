from __future__ import annotations

"""The makespan chart stays drawable and honest; the app loads models strictly.

The histogram once had no ceiling on its bin count, so one heavy tail put the
tail's bars thousands of pixels off the plot (and could exhaust memory). Its
bars and percentile markers were placed on two different scales, so a
marker sat over the wrong bar. The app's two model readers also took the last
of any duplicated JSON key silently.
"""

import json
from pathlib import Path

import pytest


def _ensure_qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# Y-5


def test_a_heavy_tail_cannot_ask_for_more_bins_than_the_ceiling() -> None:
    from latencylab_ui.distributions_agg import (
        MAX_HISTOGRAM_BINS,
        freedman_diaconis_bins,
    )

    # A tight cluster plus one far outlier: tiny IQR, huge span.
    values = [100.0 + i * 0.001 for i in range(199)] + [60_000.0]
    bins = freedman_diaconis_bins(values)

    assert len(bins) <= MAX_HISTOGRAM_BINS
    assert sum(b.count for b in bins) == len(values)
    assert bins[0].lo == min(values)
    assert bins[-1].hi == pytest.approx(max(values))
    assert bins[-1].count == 1


def test_an_ordinary_spread_still_gets_the_freedman_diaconis_count() -> None:
    from latencylab_ui.distributions_agg import freedman_diaconis_bins

    values = [float(i) for i in range(1000)]
    # IQR 499.5, n^(1/3) 10: width 99.9, span 999, so ten bins.
    assert len(freedman_diaconis_bins(values)) == 10


# Y-6


def _bars_left_of(img, *, row: int, x_end: int, base_rgb: tuple[int, int, int]):
    """Count the one-pixel gaps (base colour) between bars left of `x_end`."""
    gaps = 0
    for x in range(x_end):
        c = img.pixelColor(x, row)
        if (c.red(), c.green(), c.blue()) == base_rgb:
            gaps += 1
    return gaps


def test_a_percentile_marker_sits_over_the_bar_that_holds_its_value() -> None:
    _ensure_qapp()
    from PySide6.QtWidgets import QWidget

    from latencylab_ui.distributions_agg import HistogramBin
    from latencylab_ui.distributions_dock import _MakespanHistogramWidget, _Marker

    bin_count = 27
    target = 20
    bins = [
        HistogramBin(lo=float(i), hi=float(i + 1), count=5) for i in range(bin_count)
    ]
    host = QWidget()
    chart = _MakespanHistogramWidget(host)
    chart.resize(520, 300)
    chart.set_data(bins=bins, markers=[_Marker(label="p99", value=target + 0.5)])
    img = chart.grab().toImage()

    row = 12
    marker_rgb = (220, 60, 60)
    marker_xs = [
        x
        for x in range(img.width())
        if (
            img.pixelColor(x, row).red(),
            img.pixelColor(x, row).green(),
            img.pixelColor(x, row).blue(),
        )
        == marker_rgb
    ]
    assert len(marker_xs) == 1, marker_xs
    base = chart.palette().base().color()
    base_rgb = (base.red(), base.green(), base.blue())

    # Pixels left of the plot (the 8 px margin) are base too; skip them.
    plot_left = 8
    gaps = _bars_left_of(
        img, row=row, x_end=marker_xs[0], base_rgb=base_rgb
    ) - _bars_left_of(img, row=row, x_end=plot_left, base_rgb=base_rgb)
    assert gaps == target, f"marker drawn over bar {gaps}, its value is in {target}"


def test_more_bins_than_pixels_are_still_drawn_and_stay_on_the_plot() -> None:
    """At one pixel per bar the old code drew zero-width bars: an empty chart."""
    _ensure_qapp()
    from PySide6.QtWidgets import QWidget

    from latencylab_ui.distributions_agg import HistogramBin
    from latencylab_ui.distributions_dock import _MakespanHistogramWidget

    bins = [HistogramBin(lo=float(i), hi=float(i + 1), count=1) for i in range(700)]
    host = QWidget()
    chart = _MakespanHistogramWidget(host)
    chart.resize(520, 300)
    chart.set_data(bins=bins, markers=[])
    img = chart.grab().toImage()
    base = chart.palette().base().color()
    margin = 8
    painted = [x for x in range(img.width()) if img.pixelColor(x, margin + 4) != base]
    assert painted, "no bar was drawn at all"
    assert min(painted) >= margin
    assert max(painted) < img.width() - margin


# Y-4


_DUPLICATE_TASK = (
    '{"schema_version": 2, "entry_event": "go",'
    ' "contexts": {"ui": {"concurrency": 1}},'
    ' "events": {"go": {"tags": []}},'
    ' "tasks": {'
    '  "t": {"context": "ui", "duration_ms": {"dist": "fixed", "value": 500}},'
    '  "t": {"context": "ui", "duration_ms": {"dist": "fixed", "value": 1}}'
    " },"
    ' "wiring": {"go": ["t"]}}'
)


def test_the_run_worker_refuses_a_duplicated_key_with_a_message(
    tmp_path: Path,
) -> None:
    _ensure_qapp()
    import latencylab_ui.run_controller as rc

    path = tmp_path / "dup.json"
    path.write_text(_DUPLICATE_TASK, encoding="utf-8")
    worker = rc.RunWorker(
        run_token=1,
        request=rc.RunRequest(model_path=path, runs=2, seed=1),
        cancel=rc.CancelFlag(),
    )
    seen: dict[str, object] = {}
    worker.succeeded.connect(lambda *_a: seen.__setitem__("succeeded", True))
    worker.failed.connect(lambda _tok, text: seen.__setitem__("failed", text))
    worker.run()

    assert "succeeded" not in seen
    assert "duplicate key 't'" in str(seen["failed"])
    assert "Traceback" not in str(seen["failed"])


class _FakeWindow:
    """Records which of the two load outcomes the loader reported."""

    def __init__(self) -> None:
        self.outcome: tuple[str, str] | None = None

    def _set_model_load_failed(self, path, *, version_text, validation_text):
        self.outcome = ("failed", validation_text)

    def _set_model_load_ok(self, path, model):
        self.outcome = ("ok", "")


def test_opening_a_model_with_a_duplicated_key_is_reported_invalid(
    tmp_path: Path,
) -> None:
    from latencylab_ui.main_window_file_io import load_model

    path = tmp_path / "dup.json"
    path.write_text(_DUPLICATE_TASK, encoding="utf-8")
    window = _FakeWindow()
    load_model(window, path)

    assert window.outcome is not None
    assert window.outcome[0] == "failed"
    assert window.outcome[1].startswith("Invalid:")
    assert "duplicate key 't'" in window.outcome[1]


def test_opening_a_clean_model_still_succeeds(tmp_path: Path) -> None:
    from latencylab_ui.main_window_file_io import load_model

    path = tmp_path / "ok.json"
    path.write_text(json.dumps(json.loads(_DUPLICATE_TASK)), encoding="utf-8")
    window = _FakeWindow()
    load_model(window, path)
    assert window.outcome == ("ok", "")
