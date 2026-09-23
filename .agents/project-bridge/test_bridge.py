#!/usr/bin/env python3
"""Project Bridge tests — run: python3 .agents/project-bridge/test_bridge.py"""

from __future__ import annotations

import json
import os
import sqlite3
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bridge  # noqa: E402
import server  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name} {detail}")


def fresh_root() -> Path:
    td = Path(tempfile.mkdtemp(prefix="pb-test-"))
    subprocess.check_call(["git", "init", "-q"], cwd=td)
    subprocess.check_call(["git", "config", "user.email", "t@example.com"], cwd=td)
    subprocess.check_call(["git", "config", "user.name", "T"], cwd=td)
    (td / "README.md").write_text("x\n")
    subprocess.check_call(["git", "add", "README.md"], cwd=td)
    subprocess.check_call(["git", "commit", "-q", "-m", "init"], cwd=td)
    # minimal .agents layout
    (td / ".agents" / "config").mkdir(parents=True)
    (td / ".agents" / "config" / "bridge.json").write_text(
        json.dumps(
            {
                "claim_ttl_seconds": 14400,
                "recent_changes_default_limit": 5,
                "recent_changes_max_limit": 50,
                "status_max_changes": 5,
                "status_max_claims": 5,
                "status_max_decisions": 3,
            }
        )
    )
    return td


def test_record_and_discover() -> None:
    print("Test 1: Codex records A → OpenCode discovers A")
    root = fresh_root()
    r = bridge.record_change(
        root,
        agent="codex",
        task="auth",
        summary="Codex modified authentication",
        files=["lib/auth.ts"],
        tests=["pnpm test"],
        decisions=["use session cookies"],
        next_action="review",
    )
    check("record ok", r.get("ok") is True, str(r))
    out = bridge.recent_changes(root, limit=5)
    agents = [c["agent"] for c in out["changes"]]
    check("codex visible", "codex" in agents, str(out))
    check("summary present", any("authentication" in (c["summary"] or "") for c in out["changes"]))
    shutil.rmtree(root, ignore_errors=True)


def test_second_and_third_discover() -> None:
    print("Test 2: OpenCode records B → AGY sees A+B")
    root = fresh_root()
    bridge.record_change(root, agent="codex", summary="change A", task="a")
    bridge.record_change(root, agent="opencode", summary="change B", task="b")
    out = bridge.recent_changes(root, limit=10)
    agents = {c["agent"] for c in out["changes"]}
    check("has codex", "codex" in agents, str(agents))
    check("has opencode", "opencode" in agents, str(agents))
    st = bridge.project_status(root, agent="agy")
    check("agy sees changes", len(st["recent_changes"]) >= 2)
    shutil.rmtree(root, ignore_errors=True)


def test_claim_conflict() -> None:
    print("Test 3: AGY claims C → Codex sees conflict")
    root = fresh_root()
    r1 = bridge.claim_task(
        root, task="review-contact-form", scope=["components/ContactForm.tsx"], agent="agy"
    )
    check("agy claim ok", r1.get("ok") is True, str(r1))
    check("no conflict first", r1.get("conflict") is False, str(r1))
    r2 = bridge.claim_task(
        root,
        task="fix-contact",
        scope=["components/ContactForm.tsx"],
        agent="codex",
    )
    check("codex claim ok", r2.get("ok") is True, str(r2))
    check("conflict detected", r2.get("conflict") is True, str(r2))
    check(
        "warning mentions agy",
        "agy" in (r2.get("warning") or ""),
        str(r2.get("warning")),
    )
    act = bridge.active_tasks(root)
    check("two active", len(act["tasks"]) == 2, str(act))
    rel = bridge.release_task(root, task="review-contact-form", agent="agy")
    check("release", rel.get("released") == 1, str(rel))
    shutil.rmtree(root, ignore_errors=True)


def test_git_authoritative() -> None:
    print("Test 4: Git still shows reality without record_change")
    root = fresh_root()
    # modify without recording
    (root / "README.md").write_text("changed without bridge\n")
    wt = bridge.working_tree_counts(root)
    check("git sees modified", wt["modified"] >= 1, str(wt))
    out = bridge.git_json(root, "status", "--short")
    check("porcelain lists file", "README.md" in out, out)
    # bridge has no change record for this
    rec = bridge.recent_changes(root, limit=10)
    check("no forced bridge record", all(c["summary"] != "changed without bridge" for c in rec["changes"]))
    shutil.rmtree(root, ignore_errors=True)


def test_persistence() -> None:
    print("Test 5: Persistence across 'restart' (new connection)")
    root = fresh_root()
    bridge.record_change(root, agent="codex", summary="persist me")
    # new connection / simulate process restart by calling again
    out = bridge.recent_changes(root, limit=5)
    check("still there", any("persist me" in (c["summary"] or "") for c in out["changes"]))
    db = root / ".agents" / "state" / "project-bridge.sqlite"
    check("db file exists", db.is_file(), str(db))
    shutil.rmtree(root, ignore_errors=True)


def test_offline() -> None:
    print("Test 6: Offline (no network imports/calls)")
    src = Path(__file__).read_text(encoding="utf-8")
    bsrc = (Path(__file__).parent / "bridge.py").read_text(encoding="utf-8")
    ssrc = (Path(__file__).parent / "server.py").read_text(encoding="utf-8")
    bad = ["requests", "urllib.request", "http.client", "socket."]
    check("bridge no net imports", not any(x in bsrc for x in bad))
    check("server no net imports", not any(x in ssrc for x in bad))
    # still functional
    root = fresh_root()
    st = bridge.project_status(root)
    check("status works offline", "branch" in st)
    shutil.rmtree(root, ignore_errors=True)


def test_mcp_roundtrip() -> None:
    print("Extra: MCP initialize + tools/list + tools/call")
    root = fresh_root()
    os.environ["PROJECT_BRIDGE_ROOT"] = str(root)
    try:
        # rebind server ROOT
        server.ROOT = root
        init = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            }
        )
        check("initialize", init and "result" in init, str(init))
        lst = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = [t["name"] for t in lst["result"]["tools"]]
        check("13 tools", len(tools) == 13, str(tools))
        expected = {
            "project_status",
            "recent_changes",
            "record_change",
            "claim_task",
            "release_task",
            "active_tasks",
            "get_decisions",
            "record_decision",
            "request_handoff",
            "get_handoffs",
            "accept_handoff",
            "complete_handoff",
            "cancel_handoff",
        }
        check("tool names", set(tools) == expected, str(tools))
        call = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "record_change",
                    "arguments": {"agent": "opencode", "summary": "via mcp"},
                },
            }
        )
        check("call ok", call and call["result"].get("isError") is False, str(call))
        # path traversal
        bad = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "recent_changes",
                    "arguments": {"path": "../../etc/passwd"},
                },
            }
        )
        text = bad["result"]["content"][0]["text"]
        check("path traversal rejected", "invalid path" in text, text)
    finally:
        os.environ.pop("PROJECT_BRIDGE_ROOT", None)
    shutil.rmtree(root, ignore_errors=True)


def test_timing() -> None:
    print("Perf: project_status < 500ms, record_change < 500ms")
    root = fresh_root()
    t0 = time.perf_counter()
    bridge.project_status(root)
    t1 = time.perf_counter()
    bridge.record_change(root, agent="codex", summary="perf")
    t2 = time.perf_counter()
    check("status <500ms", (t1 - t0) < 0.5, f"{(t1-t0)*1000:.1f}ms")
    check("record <500ms", (t2 - t1) < 0.5, f"{(t2-t1)*1000:.1f}ms")
    shutil.rmtree(root, ignore_errors=True)


def test_schema_migration() -> None:
    print("Phase 2: schema 1 → schema 2 migration preserves old data")
    root = fresh_root()
    db = root / ".agents" / "state" / "project-bridge.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE schema_version (version INTEGER NOT NULL);
        INSERT INTO schema_version VALUES (1);
        CREATE TABLE changes (id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL, timestamp TEXT NOT NULL, task TEXT, summary TEXT, files TEXT, tests TEXT, decisions TEXT, issues TEXT, next_action TEXT, git_head TEXT, branch TEXT, auto INTEGER DEFAULT 0);
        CREATE TABLE claims (id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL, task TEXT NOT NULL, scope TEXT, created_at TEXT NOT NULL, expires_at TEXT NOT NULL, released INTEGER DEFAULT 0);
        CREATE TABLE decisions (id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL, timestamp TEXT NOT NULL, title TEXT NOT NULL, detail TEXT, git_head TEXT, branch TEXT);
        INSERT INTO changes(agent,timestamp,summary) VALUES ('codex','2026-01-01T00:00:00Z','old change');
        INSERT INTO decisions(agent,timestamp,title) VALUES ('codex','2026-01-01T00:00:00Z','old decision');
        """
    )
    conn.commit(); conn.close()
    bridge.connect(root).close()
    conn = sqlite3.connect(db)
    version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
    old_change = conn.execute("SELECT summary FROM changes").fetchone()[0]
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    check("schema version 2", version == 2, str(version))
    check("old change preserved", old_change == "old change", str(old_change))
    check("handoff tables exist", {"handoffs", "handoff_results", "handoff_sequence"} <= tables, str(tables))
    bridge.connect(root).close()
    check("second migration is no-op", bridge.db_schema_version(root) == 2)
    shutil.rmtree(root, ignore_errors=True)


def test_handoff_lifecycle() -> None:
    print("Phase 2: handoff lifecycle, filters, result and source warning")
    root = fresh_root()
    created = bridge.request_handoff(
        root, to_agent="opencode", type="review", task="review-auth-refactor",
        title="Review authentication changes", summary="Review correctness and regressions.",
        scope=["lib/auth.ts"], priority="normal", from_agent="codex",
    )
    check("request ok", created.get("ok") is True, str(created))
    hid = created.get("handoff", {}).get("id")
    check("generated id", bool(hid and hid.startswith("H-")), str(hid))
    check("source captured", created.get("handoff", {}).get("source", {}).get("head") == bridge.git_head(root))
    check("branch captured", created.get("handoff", {}).get("source", {}).get("branch") == bridge.git_branch(root))
    inbox = bridge.get_handoffs(root, agent="opencode")
    check("recipient sees pending", inbox.get("count") == 1 and inbox["handoffs"][0]["status"] == "pending", str(inbox))
    wrong = bridge.accept_handoff(root, hid, agent="codex")
    check("wrong recipient rejected", wrong.get("conflict") is True, str(wrong))
    accepted = bridge.accept_handoff(root, hid, agent="opencode")
    check("accept ok", accepted.get("ok") is True and accepted["handoff"]["status"] == "accepted", str(accepted))
    double = bridge.accept_handoff(root, hid, agent="opencode")
    check("double accept conflict", double.get("conflict") is True, str(double))
    result = bridge.complete_handoff(
        root, hid, summary="Authentication review completed.", outcome="changes_requested",
        findings=[{"severity": "high", "file": "lib/auth.ts", "line": 83, "summary": "Expiration validation is missing."}],
        tests=["pnpm test", "pnpm type-check"], recommended_action="Fix expiration validation.", agent="opencode",
    )
    check("complete ok", result.get("ok") is True and result["handoff"]["status"] == "completed", str(result))
    outgoing = bridge.get_handoffs(root, from_agent="codex", status="completed", agent="codex")
    check("source receives result", outgoing.get("handoffs", [{}])[0].get("result", {}).get("outcome") == "changes_requested", str(outgoing))
    # A second handoff provides a controlled HEAD-change warning and a cancel path.
    changed = bridge.request_handoff(root, "agy", "investigate", "inspect-contact", "Inspect contact", "Investigate", from_agent="codex")
    changed_id = changed["handoff"]["id"]
    (root / "README.md").write_text("changed\n")
    subprocess.check_call(["git", "add", "README.md"], cwd=root)
    subprocess.check_call(["git", "commit", "-q", "-m", "advance"], cwd=root)
    warning = bridge.get_handoffs(root, handoff_id=changed_id, agent="agy")
    check("HEAD changed warning", warning["handoffs"][0].get("source_state_changed") is True and "SOURCE STATE CHANGED" in warning["handoffs"][0].get("warning", ""), str(warning))
    cancel_wrong = bridge.cancel_handoff(root, changed_id, agent="opencode")
    check("wrong cancellation rejected", cancel_wrong.get("conflict") is True, str(cancel_wrong))
    cancelled = bridge.cancel_handoff(root, changed_id, reason="no longer needed", agent="codex")
    check("cancel ok", cancelled.get("ok") is True and cancelled["handoff"]["status"] == "cancelled", str(cancelled))
    shutil.rmtree(root, ignore_errors=True)


def test_handoff_validation_and_isolation() -> None:
    print("Phase 2: validation, limits, secrets, persistence and isolation")
    root = fresh_root(); other = fresh_root()
    bad_path = bridge.request_handoff(root, "opencode", "review", "x", "x", "x", scope=["../outside"], from_agent="codex")
    check("scope traversal rejected", bad_path.get("ok") is False, str(bad_path))
    bad_abs = bridge.request_handoff(root, "opencode", "review", "x", "x", "x", scope=["/tmp/outside"], from_agent="codex")
    check("absolute scope rejected", bad_abs.get("ok") is False, str(bad_abs))
    too_many = bridge.request_handoff(root, "opencode", "review", "x", "x", "x", scope=["a"] * 51, from_agent="codex")
    check("scope limit rejected", too_many.get("ok") is False, str(too_many))
    secret = bridge.request_handoff(root, "opencode", "review", "x", "x", "api_key=supersecret", from_agent="codex")
    encoded = json.dumps(secret)
    check("secret filtered", "supersecret" not in encoded, encoded)
    secret_finding = bridge.request_handoff(root, "opencode", "review", "findings", "Findings", "Findings", from_agent="codex")
    secret_result = bridge.accept_handoff(root, secret_finding["handoff"]["id"], agent="opencode")
    secret_complete = bridge.complete_handoff(root, secret_finding["handoff"]["id"], "done", "changes_requested", findings=[{"severity": "high", "file": ".env", "summary": "secret file"}], agent="opencode")
    check("secret finding path rejected", secret_result.get("ok") is True and secret_complete.get("ok") is False, str(secret_complete))
    handoff = bridge.request_handoff(root, "opencode", "review", "persist", "Persist", "Persist", from_agent="codex")
    hid = handoff["handoff"]["id"]
    check("other repo isolated", bridge.get_handoffs(other, handoff_id=hid, agent="opencode").get("count") == 0)
    pending_complete = bridge.complete_handoff(root, hid, "not accepted", "failed", agent="opencode")
    check("complete pending rejected", pending_complete.get("conflict") is True, str(pending_complete))
    check("no auto spawn", "codex exec" not in (Path(bridge.__file__).read_text() + Path(server.__file__).read_text()))
    shutil.rmtree(root, ignore_errors=True); shutil.rmtree(other, ignore_errors=True)


def test_concurrent_accept() -> None:
    print("Phase 2: concurrent accept is one success and one conflict")
    root = fresh_root()
    created = bridge.request_handoff(root, "opencode", "test", "concurrent", "Concurrent", "Concurrent", from_agent="codex")
    hid = created["handoff"]["id"]
    def accept():
        return bridge.accept_handoff(root, hid, agent="opencode")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: accept(), range(2)))
    check("one accept success", sum(1 for r in results if r.get("ok") is True) == 1, str(results))
    check("one accept conflict", sum(1 for r in results if r.get("conflict") is True) == 1, str(results))
    check("sqlite remains readable", bridge.get_handoffs(root, handoff_id=hid, agent="opencode").get("count") == 1)
    shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    test_record_and_discover()
    test_second_and_third_discover()
    test_claim_conflict()
    test_git_authoritative()
    test_persistence()
    test_offline()
    test_mcp_roundtrip()
    test_timing()
    test_schema_migration()
    test_handoff_lifecycle()
    test_handoff_validation_and_isolation()
    test_concurrent_accept()
    print(f"\nTOTAL: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
