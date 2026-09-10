# -*- coding: utf-8 -*-
"""Unit tests for the single-newest selection policy (004-08)."""

from web.scan_policy import pick_candidate


def _row(rid, content, date):
    return {"record_id": rid, "title": content or date, "content": content,
            "date": date}


def _lookup(*tasks):
    """task_lookup built from (record_id -> task dict) pairs."""
    return lambda rid: {t["record_id"]: t for t in tasks}.get(rid)


def test_picks_newest_date_desc():
    rows = [
        _row("old", "旧文案", "2026-01-01"),
        _row("new", "新文案", "2026-01-05"),
    ]
    d = pick_candidate(rows, _lookup())
    assert d["action"] == "create"
    assert d["record"]["record_id"] == "new"


def test_tie_breaks_by_content_ascending():
    same_date = "2026-03-01"
    rows = [
        _row("z", "乙文案", same_date),
        _row("a", "甲文案", same_date),
    ]
    # content asc -> 乙(U+4E59) < 甲(U+7532), so "乙文案" is the smaller content
    d = pick_candidate(rows, _lookup())
    assert d["record"]["record_id"] == "z"


def test_further_look_back_ignored_until_newest_done():
    rows = [
        _row("new", "新文案", "2026-01-05"),
        _row("mid", "中文案", "2026-01-04"),
        _row("old", "旧文案", "2026-01-03"),
    ]
    done = {"record_id": "new", "status": "done"}
    d = pick_candidate(rows, _lookup(done))
    assert d["action"] == "create"
    assert d["record"]["record_id"] == "mid"
    assert d["skipped"] == [{"record_id": "new", "title": "新文案",
                             "reason": "已生成视频"}]


def test_retries_failed_newest_task():
    rows = [_row("a", "文案", "2026-01-01")]
    failed = {"id": "t1", "record_id": "a", "status": "error"}
    d = pick_candidate(rows, _lookup(failed))
    assert d["action"] == "retry"
    assert d["task_id"] == "t1"
    assert d["record"]["record_id"] == "a"


def test_retries_interrupted_as_well():
    rows = [_row("a", "文案", "2026-01-01")]
    interrupted = {"id": "t2", "record_id": "a", "status": "interrupted"}
    d = pick_candidate(rows, _lookup(interrupted))
    assert d["action"] == "retry"
    assert d["task_id"] == "t2"


def test_skips_in_flight_and_keeps_looking():
    rows = [
        _row("new", "新文案", "2026-01-05"),
        _row("old", "旧文案", "2026-01-03"),
    ]
    queued = {"record_id": "new", "status": "queued"}
    d = pick_candidate(rows, _lookup(queued))
    assert d["action"] == "create"
    assert d["record"]["record_id"] == "old"
    assert d["skipped"] == [{"record_id": "new", "title": "新文案",
                             "reason": "生成中"}]


def test_returns_none_when_all_done():
    rows = [
        _row("a", "甲", "2026-01-01"),
        _row("b", "乙", "2026-01-02"),
    ]
    lookup = _lookup({"record_id": "a", "status": "done"},
                     {"record_id": "b", "status": "done"})
    d = pick_candidate(rows, lookup)
    assert d["record"] is None
    assert d["action"] is None
    assert len(d["skipped"]) == 2


def test_empty_date_sorts_last():
    rows = [
        _row("dated", "有日期", "2026-01-01"),
        _row("nodate", "无日期", ""),
    ]
    d = pick_candidate(rows, _lookup())
    assert d["record"]["record_id"] == "dated"
    assert d["skipped"] == []


def test_newest_broken_records_skipped_with_reasons():
    rows = [
        {"record_id": "", "title": "无记录号", "content": "正文", "date": "2026-01-03"},
        {"record_id": "empty", "title": "空文案", "content": "", "date": "2026-01-02"},
        _row("ok", "正常文案", "2026-01-01"),
    ]
    d = pick_candidate(rows, _lookup())
    assert d["record"]["record_id"] == "ok"
    reasons = [s["reason"] for s in d["skipped"]]
    assert "缺少记录号" in reasons and "文案字段为空" in reasons


def test_records_older_than_pick_are_left_for_later_rounds():
    rows = [
        _row("ok", "正常文案", "2026-01-03"),
        {"record_id": "", "title": "无记录号", "content": "正文", "date": "2026-01-01"},
    ]
    d = pick_candidate(rows, _lookup())
    assert d["record"]["record_id"] == "ok"
    assert d["skipped"] == []