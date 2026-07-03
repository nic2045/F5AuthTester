from f5authtester.models import (
    CheckResult,
    CheckSource,
    Report,
    Status,
    TargetResult,
    Variant,
    aggregate_status,
)


def test_aggregate_picks_most_severe():
    assert aggregate_status([Status.OK, Status.WARN, Status.FAIL]) == Status.FAIL
    assert aggregate_status([Status.OK, Status.WARN]) == Status.WARN
    assert aggregate_status([Status.OK, Status.OK]) == Status.OK


def test_aggregate_ignores_skipped_unless_only_option():
    assert aggregate_status([Status.OK, Status.SKIPPED]) == Status.OK
    assert aggregate_status([Status.SKIPPED, Status.SKIPPED]) == Status.UNKNOWN
    assert aggregate_status([]) == Status.UNKNOWN


def test_unknown_beats_warn_and_ok():
    assert aggregate_status([Status.OK, Status.UNKNOWN, Status.WARN]) == Status.UNKNOWN


def _check(status: Status) -> CheckResult:
    return CheckResult(source=CheckSource.ACTIVE_PROBE, status=status)


def test_target_result_from_checks():
    tr = TargetResult.from_checks(
        "App", Variant.HEADER, "https://x/", [_check(Status.OK), _check(Status.FAIL)]
    )
    assert tr.status == Status.FAIL
    assert len(tr.checks) == 2


def test_report_summary_counts():
    report = Report(
        results=[
            TargetResult.from_checks("a", Variant.FORMS, "u", [_check(Status.OK)]),
            TargetResult.from_checks("b", Variant.FORMS, "u", [_check(Status.FAIL)]),
            TargetResult.from_checks("c", Variant.FORMS, "u", [_check(Status.OK)]),
        ]
    )
    assert report.summary["ok"] == 2
    assert report.summary["fail"] == 1
    assert report.model_dump_web()["summary"]["ok"] == 2
