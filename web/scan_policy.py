# -*- coding: utf-8 -*-
"""Single-newest-record selection for Base scan/poll (004-08).

Pure, dependency-free decision logic shared by the manual ``/api/base/scan``
handler and the auto-poll job so both apply exactly the same rule:

  - Order candidate records by date descending; records sharing a date sort by
    content ascending; records with no date sort last.
  - Walk newest -> oldest and pick the first actionable candidate:
      * no task yet                     -> action ``create``
      * task in ``error``/``interrupted`` -> action ``retry`` (same task id)
      * task ``done`` or in-progress    -> skip it and keep looking

There is no CLI/DB/HTTP dependency here: the server passes rows from
``base_client.scan_records`` and a ``task_lookup`` callback backed by the task
table, so the whole policy is unit-testable without lark-cli.
"""

from __future__ import annotations

RETRYABLE = {"error", "interrupted"}


def _order(rows: list[dict]) -> list[dict]:
    """date desc, then content asc; records with no date sort last.

    Two stable sorts: ascending by content first, then descending by date.
    The later sort is stable, so equal dates keep the content-ascending tie
    order; empty dates ('' ) fall to the end under a descending sort.
    """
    by_content = sorted(rows, key=lambda r: (r.get("content") or ""))
    return sorted(by_content, key=lambda r: (r.get("date") or ""), reverse=True)


def pick_candidate(rows: list[dict], task_lookup) -> dict:
    """Choose the single newest actionable record.

    ``task_lookup(record_id) -> task dict | None``. Returns::

        {
          "record":  row dict | None,   # the chosen candidate (None if none)
          "action":  "create" | "retry" | None,
          "task_id": str | None,        # set when action == "retry"
          "skipped": [{"record_id", "title", "reason"}, ...],  # newest-first
        }
    """
    skipped: list[dict] = []
    for row in _order(rows):
        rid = row.get("record_id") or ""
        title = row.get("title") or ""
        content = row.get("content") or ""
        if not rid:
            skipped.append({"record_id": "", "title": title, "reason": "缺少记录号"})
            continue
        if not content.strip():
            skipped.append({"record_id": rid, "title": title, "reason": "文案字段为空"})
            continue
        task = task_lookup(rid)
        if task is None:
            return {"record": row, "action": "create", "task_id": None,
                    "skipped": skipped}
        if task["status"] == "done":
            skipped.append({"record_id": rid, "title": title,
                            "reason": "已生成视频"})
            continue
        if task["status"] in RETRYABLE:
            return {"record": row, "action": "retry",
                    "task_id": task["id"], "skipped": skipped}
        skipped.append({"record_id": rid, "title": title,
                        "reason": "生成中"})
    return {"record": None, "action": None, "task_id": None,
            "skipped": skipped}