from __future__ import annotations

"""A model that would run with a meaning other than the one written is refused.

Each case here was accepted once and then simulated as something else: delays
dropped by the v1 engine, a NaN that hangs it, a duplicated key that silently
replaces a task, a task name that merges two critical paths, a version that is
truncated. The gate is validation (and the shared loader for duplicate keys),
so every case is asserted there; where the user meets it, it is also
asserted at the CLI.
"""

import copy
import json
import math
from pathlib import Path

import pytest

from simquence.model import Model
from simquence.validate import ModelValidationError, validate_model


def _model(version: int = 2) -> dict:
    return {
        "schema_version": version,
        "entry_event": "go",
        "contexts": {"ui": {"concurrency": 1}},
        "events": {"go": {"tags": ["ui"]}, "done": {"tags": ["ui"]}},
        "tasks": {
            "t": {
                "context": "ui",
                "duration_ms": {"dist": "fixed", "value": 1.0},
                "emit": ["done"],
            }
        },
        "wiring": {"go": ["t"]},
    }


def _validate(raw: dict) -> None:
    validate_model(Model.from_json(raw))


def _cli(tmp_path: Path, model_text: str) -> int:
    from simquence.cli import main

    model_path = tmp_path / "m.json"
    model_path.write_text(model_text, encoding="utf-8")
    return main(
        [
            "simulate",
            "--model",
            str(model_path),
            "--runs",
            "3",
            "--seed",
            "1",
            "--out-summary",
            str(tmp_path / "summary.json"),
            "--out-runs",
            str(tmp_path / "runs.csv"),
        ]
    )


# Y-2: the v1 engine walks the flat wiring map, which carries no delay.


def test_a_v1_model_with_a_wiring_delay_is_refused() -> None:
    raw = _model(version=1)
    raw["wiring"] = {"go": [{"task": "t", "delay_ms": 1000}]}
    with pytest.raises(ModelValidationError, match="schema_version 2"):
        _validate(raw)


def test_a_v2_model_with_a_wiring_delay_is_still_accepted() -> None:
    raw = _model(version=2)
    raw["wiring"] = {"go": [{"task": "t", "delay_ms": 1000}]}
    _validate(raw)


# Y-3 and Y-9: every distribution parameter must be a finite number.

_NON_FINITE_CASES = [
    ("fixed", {"dist": "fixed", "value": math.nan}),
    ("fixed", {"dist": "fixed", "value": math.inf}),
    ("normal mean", {"dist": "normal", "mean": math.nan, "std": 1.0}),
    ("normal std", {"dist": "normal", "mean": 1.0, "std": math.inf}),
    ("normal min", {"dist": "normal", "mean": 1.0, "std": 1.0, "min": math.nan}),
    ("lognormal sigma", {"dist": "lognormal", "mu": 1.0, "sigma": math.nan}),
    ("lognormal mu", {"dist": "lognormal", "mu": -math.inf, "sigma": 1.0}),
]


@pytest.mark.parametrize(
    "dist", [c[1] for c in _NON_FINITE_CASES], ids=[c[0] for c in _NON_FINITE_CASES]
)
@pytest.mark.parametrize("version", [1, 2])
def test_a_non_finite_duration_parameter_is_refused(dist: dict, version: int) -> None:
    raw = _model(version=version)
    raw["tasks"]["t"]["duration_ms"] = dist
    with pytest.raises(ModelValidationError, match="finite"):
        _validate(raw)


def test_a_non_finite_delay_parameter_is_refused() -> None:
    raw = _model(version=2)
    raw["wiring"] = {"go": [{"task": "t", "delay_ms": math.nan}]}
    with pytest.raises(ModelValidationError, match="finite"):
        _validate(raw)


def test_the_nan_literal_in_a_model_file_never_reaches_the_engine(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The v1 engine hangs forever on a NaN duration; the CLI must refuse it."""
    text = json.dumps(_model(version=1)).replace('"value": 1.0', '"value": NaN')
    assert "NaN" in text
    assert _cli(tmp_path, text) != 0
    assert "finite" in capsys.readouterr().err


def test_a_lognormal_whose_median_overflows_is_refused() -> None:
    raw = _model(version=2)
    raw["tasks"]["t"]["duration_ms"] = {"dist": "lognormal", "mu": 1000, "sigma": 0}
    with pytest.raises(ModelValidationError, match="mu"):
        _validate(raw)


def test_the_v2_engine_reports_an_overflowing_draw_as_v1_does() -> None:
    """A huge sigma can still overflow one draw; v2 must not raise where v1 gives inf."""
    import random

    from simquence.model import DurationDist
    from simquence.sim_v2 import _sample_ms

    class _HugeDraw(random.Random):
        def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
            return 1.0e6

    dist = DurationDist(dist="lognormal", params={"mu": 0.0, "sigma": 1.0})
    assert _sample_ms(_HugeDraw(), dist) == math.inf


@pytest.mark.parametrize("version_raw", [2.9, 1.5, True])
def test_a_non_integral_version_is_refused(version_raw: object) -> None:
    raw = _model()
    raw["schema_version"] = version_raw
    with pytest.raises(ValueError, match="integer"):
        Model.from_json(raw)


def test_an_integral_float_version_is_still_read() -> None:
    raw = _model()
    raw["schema_version"] = 2.0
    assert Model.from_json(raw).version == 2


# Y-12: a negative normal mean is clamped to the minimum on every draw.


def test_a_negative_normal_mean_is_refused() -> None:
    raw = _model()
    raw["tasks"]["t"]["duration_ms"] = {"dist": "normal", "mean": -5.0, "std": 1.0}
    with pytest.raises(ModelValidationError, match="mean"):
        _validate(raw)


# Y-8: critical paths are identified by names joined with ">".


def test_a_task_name_containing_the_path_separator_is_refused() -> None:
    raw = _model()
    raw["tasks"]["a>b"] = raw["tasks"].pop("t")
    raw["wiring"] = {"go": ["a>b"]}
    with pytest.raises(ModelValidationError, match="'>'"):
        _validate(raw)


def test_an_event_name_containing_the_path_separator_is_refused() -> None:
    """Event names reach the path through the synthetic delay(event->task) node."""
    raw = _model()
    raw["events"]["x>y"] = {"tags": []}
    with pytest.raises(ModelValidationError, match="'>'"):
        _validate(raw)


# Y-4: duplicate keys used to keep the last silently.

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


def test_the_cli_refuses_a_model_with_a_duplicated_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _cli(tmp_path, _DUPLICATE_TASK) != 0
    assert "duplicate key 't'" in capsys.readouterr().err
    assert not (tmp_path / "summary.json").exists()


def test_the_shared_loader_refuses_a_duplicated_key_at_any_depth() -> None:
    from simquence.io import parse_model_json

    with pytest.raises(ModelValidationError, match="duplicate key 'wiring'"):
        parse_model_json('{"wiring": {"go": ["t"]}, "wiring": {"go": []}}')
    assert parse_model_json('{"a": {"b": 1}}') == {"a": {"b": 1}}


def test_the_shared_loader_reads_a_file(tmp_path: Path) -> None:
    from simquence.io import read_model_json

    path = tmp_path / "m.json"
    path.write_text(json.dumps(_model()), encoding="utf-8")
    assert read_model_json(path) == _model()


# Y-12: a malformed model reached the CLI user as a raw traceback.


@pytest.mark.parametrize(
    "text",
    [
        "{not json",
        json.dumps({k: v for k, v in _model().items() if k != "schema_version"}),
        json.dumps({**_model(), "tasks": {"t": {"context": "ui"}}}),
        json.dumps({**_model(), "contexts": []}),
        json.dumps({**_model(), "entry_event": "missing"}),
    ],
    ids=["bad-json", "no-version", "no-duration", "contexts-list", "invalid"],
)
def test_the_cli_reports_a_malformed_model_without_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    assert _cli(tmp_path, text) == 2
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert str(tmp_path / "m.json") in err


def test_the_cli_reports_a_missing_model_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from simquence.cli import main

    missing = tmp_path / "nope.json"
    rc = main(
        [
            "simulate",
            "--model",
            str(missing),
            "--runs",
            "1",
            "--seed",
            "1",
            "--out-summary",
            str(tmp_path / "s.json"),
            "--out-runs",
            str(tmp_path / "r.csv"),
        ]
    )
    assert rc == 2
    assert str(missing) in capsys.readouterr().err


def test_every_shipped_example_still_validates_under_the_tighter_rules() -> None:
    from simquence.io import read_model_json

    examples = sorted(Path("examples").glob("*.json"))
    assert examples
    for path in examples:
        _validate(copy.deepcopy(read_model_json(path)))
