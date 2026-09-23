#!/usr/bin/env python3
"""Project Bridge domain logic — coordination metadata only.

Git is authoritative for code state. This module stores:
  - changes (who/what/when + optional agent-declared metadata)
  - claims  (advisory task locks with TTL)
  - decisions (short durable technical decisions)
  - handoffs (small structured work items between known agents)

Never stores: secrets, prompts, full chat, file contents.

Portable by design: the repository root is discovered at runtime
(PROJECT_BRIDGE_ROOT env -> module location -> git toplevel -> walk-up),
never hardcoded.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

PROJECT_BRIDGE_VERSION = "1.1.0"
SCHEMA_VERSION = 2

VALID_AGENTS = {"codex", "opencode", "agy", "unknown"}
VALID_HANDOFF_AGENTS = {"codex", "opencode", "agy"}
HANDOFF_TYPES = {"review", "implement", "investigate", "test", "second_opinion"}
HANDOFF_STATUSES = {"pending", "accepted", "in_progress", "completed", "declined", "cancelled"}
HANDOFF_SEVERITIES = {"critical", "high", "medium", "low", "info"}
HANDOFF_PRIORITIES = {"low", "normal", "high"}
HANDOFF_TRANSITIONS = {
    "pending": {"accepted", "declined", "cancelled"},
    "accepted": {"in_progress", "completed", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "declined": set(),
    "cancelled": set(),
}
SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|credential|authorization|cookie|private[_-]?key)",
    re.I,
)
SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9]{8,}|Bearer\s+[A-Za-z0-9._\-]{8,}|-----BEGIN[A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9_\-]{12,}|xox[baprs]-[A-Za-z0-9-]{12,})"
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd|credential|authorization|cookie|private[_-]?key)\s*[:=]\s*([^\s,;]+)"
)

_FLAT_KEYS = (
    "claim_ttl_seconds",
    "recent_changes_default_limit",
    "recent_changes_max_limit",
    "status_max_changes",
    "status_max_claims",
    "status_max_decisions",
    "status_max_bytes",
    "handoff_default_limit",
    "handoff_max_limit",
)

_DEFAULT_CONFIG: dict[str, Any] = {
    "claim_ttl_seconds": 14400,
    "recent_changes_default_limit": 5,
    "recent_changes_max_limit": 50,
    "status_max_changes": 5,
    "status_max_claims": 5,
    "status_max_decisions": 3,
    "status_max_bytes": 2048,
    "handoff_default_limit": 5,
    "handoff_max_limit": 50,
}


def _bridge_root_from_file() -> Path | None:
    """Locate the repo root from this module's location: <root>/.agents/project-bridge/bridge.py"""
    try:
        here = Path(__file__).resolve()
    except OSError:
        return None
    candidate = here.parent.parent.parent
    if (candidate / ".agents" / "project-bridge" / "bridge.py").is_file():
        return candidate
    return None


def repo_root(start: Path | None = None) -> Path:
    """Resolve the repository root, independent of the process CWD.

    Priority:
      1. PROJECT_BRIDGE_ROOT (explicit override, must be an existing dir)
      2. location of this module (<root>/.agents/project-bridge/bridge.py)
      3. `git rev-parse --show-toplevel` from the start dir
      4. walk up looking for .git
      5. the start dir
    """
    env_root = os.environ.get("PROJECT_BRIDGE_ROOT")
    if env_root:
        ep = Path(env_root).expanduser()
        if ep.is_dir():
            return ep.resolve()

    from_file = _bridge_root_from_file()
    if from_file is not None:
        return from_file

    p = (start or Path.cwd()).resolve()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(p),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        root = Path(out.strip())
        if root.is_dir():
            return root
    except (subprocess.CalledProcessError, OSError):
        pass

    cur = p
    for _ in range(16):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return p


def load_config(root: Path) -> dict[str, Any]:
    """Load .agents/config/bridge.json.

    Supports the current nested schema (schema_version 1) and the legacy flat
    layout, so an in-place upgrade never breaks the running bridge.
    """
    cfg: dict[str, Any] = dict(_DEFAULT_CONFIG)
    cfg["project_name"] = root.name
    cfg["agy_project_name"] = root.name
    cfg["schema_version"] = SCHEMA_VERSION
    cfg["disabled_agents"] = []

    cfg_path = root / ".agents" / "config" / "bridge.json"
    if cfg_path.is_file():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        if isinstance(data, dict):
            bridge_section = data.get("bridge") if isinstance(data.get("bridge"), dict) else {}
            for key in _FLAT_KEYS:
                if key in bridge_section:
                    cfg[key] = bridge_section[key]
                elif key in data:  # legacy flat layout
                    cfg[key] = data[key]
            project = data.get("project") if isinstance(data.get("project"), dict) else {}
            name = project.get("name")
            if isinstance(name, str) and name.strip():
                cfg["project_name"] = name.strip()
            agy_name = project.get("agy_project_name")
            if isinstance(agy_name, str) and agy_name.strip():
                cfg["agy_project_name"] = agy_name.strip()
            if isinstance(data.get("schema_version"), int):
                cfg["schema_version"] = data["schema_version"]
            agents = data.get("agents") if isinstance(data.get("agents"), dict) else {}
            disabled = [
                key
                for key, value in agents.items()
                if isinstance(value, dict) and value.get("enabled") is False
            ]
            cfg["disabled_agents"] = disabled
    return cfg


def bridge_version() -> str:
    vf = Path(__file__).resolve().parent / "VERSION"
    if vf.is_file():
        try:
            value = vf.read_text(encoding="utf-8").strip()
            if value:
                return value
        except OSError:
            pass
    return PROJECT_BRIDGE_VERSION


def detect_agent(explicit: str | None = None) -> str:
    if explicit:
        a = explicit.strip().lower()
        if a in VALID_AGENTS:
            return a
    env_a = (os.environ.get("PROJECT_BRIDGE_AGENT") or "").strip().lower()
    if env_a in VALID_AGENTS:
        return env_a
    if os.environ.get("CODEX_SANDBOX") or os.environ.get("CODEX_HOME") or os.environ.get("CODEX_THREAD_ID"):
        return "codex"
    if os.environ.get("OPENCODE") or os.environ.get("OPENCODE_SESSION_ID") or os.environ.get("OPENCODE_AGENT"):
        return "opencode"
    if (
        os.environ.get("AGY_CLI")
        or os.environ.get("ANTIGRAVITY")
        or os.environ.get("ANTIGRAVITY_CONVERSATION_ID")
    ):
        return "agy"
    try:
        pid = os.getppid()
        for _ in range(4):
            if pid <= 1:
                break
            comm_path = Path(f"/proc/{pid}/comm")
            if comm_path.is_file():
                comm = comm_path.read_text(encoding="utf-8", errors="ignore").strip().lower()
                if "codex" in comm:
                    return "codex"
                if "opencode" in comm:
                    return "opencode"
                if comm in {"agy", "antigravity"} or "antigravity" in comm:
                    return "agy"
            stat = Path(f"/proc/{pid}/stat")
            if not stat.is_file():
                break
            raw = stat.read_text(encoding="utf-8", errors="ignore")
            rparen = raw.rfind(")")
            if rparen == -1:
                break
            fields = raw[rparen + 2 :].split()
            if len(fields) < 2:
                break
            pid = int(fields[1])
    except (OSError, ValueError):
        pass
    return "unknown"


def _db_path(root: Path) -> Path:
    d = root / ".agents" / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d / "project-bridge.sqlite"


def connect(root: Path) -> sqlite3.Connection:
    path = _db_path(root)
    conn = sqlite3.connect(str(path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=3000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    # SQLite DDL is transactional, but executescript() implicitly commits. Keep
    # migration statements explicit so a failed schema-1 -> schema-2 upgrade
    # leaves the old database usable.
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        current = int(row[0]) if row else 1
        if current > SCHEMA_VERSION:
            raise RuntimeError(f"unsupported schema version: {current}")

        conn.execute(
            """CREATE TABLE IF NOT EXISTS changes (
              id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL,
              timestamp TEXT NOT NULL, task TEXT, summary TEXT, files TEXT,
              tests TEXT, decisions TEXT, issues TEXT, next_action TEXT,
              git_head TEXT, branch TEXT, auto INTEGER DEFAULT 0)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS claims (
              id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL,
              task TEXT NOT NULL, scope TEXT, created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL, released INTEGER DEFAULT 0)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS decisions (
              id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT NOT NULL,
              timestamp TEXT NOT NULL, title TEXT NOT NULL, detail TEXT,
              git_head TEXT, branch TEXT)"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_changes_ts ON changes(timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_active ON claims(released, expires_at)")

        if current < 2:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS handoffs (
                  id TEXT PRIMARY KEY, from_agent TEXT NOT NULL, to_agent TEXT NOT NULL,
                  type TEXT NOT NULL, task TEXT NOT NULL, title TEXT NOT NULL,
                  summary TEXT NOT NULL, scope TEXT NOT NULL, priority TEXT NOT NULL,
                  source_branch TEXT NOT NULL, source_head TEXT NOT NULL,
                  base_commit TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL, acknowledged_at TEXT,
                  CHECK (status IN ('pending','accepted','in_progress','completed','declined','cancelled')),
                  CHECK (type IN ('review','implement','investigate','test','second_opinion')),
                  CHECK (from_agent IN ('codex','opencode','agy')),
                  CHECK (to_agent IN ('codex','opencode','agy'))
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS handoff_results (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, handoff_id TEXT NOT NULL UNIQUE,
                  completed_by TEXT NOT NULL, summary TEXT NOT NULL, outcome TEXT NOT NULL,
                  findings TEXT NOT NULL, tests TEXT NOT NULL, recommended_action TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY (handoff_id) REFERENCES handoffs(id) ON DELETE CASCADE,
                  CHECK (completed_by IN ('codex','opencode','agy'))
                )"""
            )
            conn.execute("CREATE TABLE IF NOT EXISTS handoff_sequence (next_id INTEGER NOT NULL)")
            if conn.execute("SELECT 1 FROM handoff_sequence LIMIT 1").fetchone() is None:
                conn.execute("INSERT INTO handoff_sequence (next_id) VALUES (1)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_handoffs_to_status ON handoffs(to_agent, status, updated_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_handoffs_from_status ON handoffs(from_agent, status, updated_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_handoffs_updated ON handoffs(updated_at DESC)")
            conn.execute("UPDATE schema_version SET version = 2")
            if row is None:
                conn.execute("INSERT INTO schema_version (version) VALUES (2)")
        elif row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def db_schema_version(root: Path) -> int:
    conn = connect(root)
    try:
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        return int(row[0]) if row else SCHEMA_VERSION
    finally:
        conn.close()


def _agy_projects_dir() -> Path:
    override = os.environ.get("AGY_PROJECTS_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".gemini" / "config" / "projects"


def agy_project_name(root: Path, cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or load_config(root)
    return str(cfg.get("agy_project_name") or cfg.get("project_name") or root.name)


def ensure_agy_binding(root: Path, name: str | None = None) -> dict[str, Any]:
    """Ensure ~/.gemini/config/projects has a binding for this repo.

    AGY only loads workspace customizations (hooks + plugin MCP) for a bound
    project. This makes `agy-project` transparent instead of requiring a manual
    `agy --new-project` per machine.
    """
    root = root.resolve()
    name = name or agy_project_name(root)
    folder_uri = "file://" + str(root)
    projects_dir = _agy_projects_dir()
    try:
        projects_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"ok": False, "error": f"cannot create {projects_dir}: {exc}"}

    for path in sorted(projects_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict) or data.get("name") != name:
            continue
        resources = data.setdefault("projectResources", {})
        if not isinstance(resources, dict):
            resources = {}
            data["projectResources"] = resources
        entries = resources.setdefault("resources", [])
        if not isinstance(entries, list):
            entries = []
            resources["resources"] = entries
        uris = [r.get("folderUri") for r in entries if isinstance(r, dict)]
        if folder_uri in uris:
            return {"ok": True, "action": "already-bound", "name": name, "file": str(path)}
        entries.append({"folderUri": folder_uri})
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            return {"ok": False, "error": f"cannot update {path}: {exc}"}
        return {"ok": True, "action": "updated", "name": name, "file": str(path)}

    project_id = str(uuid.uuid4())
    payload = {
        "id": project_id,
        "name": name,
        "projectResources": {"resources": [{"folderUri": folder_uri}]},
    }
    out = projects_dir / f"{project_id}.json"
    try:
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": f"cannot write {out}: {exc}"}
    return {"ok": True, "action": "created", "name": name, "file": str(out)}


def _iso(ts: float | None = None) -> str:
    t = ts if ts is not None else time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def _sanitize_str(v: Any, max_len: int = 500) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    s = SECRET_ASSIGNMENT_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", s)
    s = SECRET_VALUE_RE.sub("[REDACTED]", s)
    if len(s) > max_len:
        s = s[: max_len - 1] + "\u2026"
    return s


def _sanitize_list(v: Any, max_items: int = 40) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        parts = [p.strip() for p in v.split(",") if p.strip()]
    elif isinstance(v, (list, tuple)):
        parts = [str(p).strip() for p in v if str(p).strip()]
    else:
        parts = [str(v)]
    out = []
    for p in parts[:max_items]:
        if SECRET_VALUE_RE.search(p) or (SECRET_KEY_RE.search(p) and len(p) > 40):
            continue
        if len(p) > 300:
            p = p[:299] + "\u2026"
        out.append(p)
    return out


def _text_bytes(value: str) -> int:
    return len(value.encode("utf-8"))


def _validate_agent(agent: Any, field: str = "agent") -> str | None:
    value = str(agent or "").strip().lower()
    if value not in VALID_HANDOFF_AGENTS:
        return f"{field} must be one of: {', '.join(sorted(VALID_HANDOFF_AGENTS))}"
    return None


def _validate_handoff_scope(root: Path, scope: Any) -> tuple[list[str], str | None]:
    values = _sanitize_list(scope, max_items=51)
    if len(values) > 50:
        return [], "scope must contain at most 50 paths"
    out: list[str] = []
    for raw in values:
        path = safe_repo_path(root, raw)
        if not path:
            return [], f"invalid scope path: {raw}"
        if _is_secret_path(path):
            return [], f"secret-bearing scope path is not allowed: {raw}"
        out.append(path)
    return out, None


def _is_secret_path(path: str) -> bool:
    parts = {p.lower() for p in Path(path).parts}
    if any(p == ".env" or p.startswith(".env.") for p in parts):
        return True
    if any(p in parts for p in {"credentials", "secrets"}):
        return True
    return Path(path).suffix.lower() in {".pem", ".key", ".p12", ".pfx"}


def _validate_handoff_id(value: Any) -> str | None:
    handoff_id = str(value or "").strip()
    if not re.fullmatch(r"H-[0-9]{6,12}", handoff_id):
        return None
    return handoff_id


def _source_state(root: Path, source_head: str, source_branch: str) -> dict[str, Any]:
    current_head = git_head(root)
    changed = bool(source_head and source_head != "unknown" and source_head != current_head)
    result: dict[str, Any] = {
        "source_state_changed": changed,
        "current_head": current_head,
        "current_branch": git_branch(root),
    }
    if changed:
        result["warning"] = (
            "SOURCE STATE CHANGED: handoff was created at "
            f"{source_head[:12]}, current HEAD is {current_head[:12]}. "
            "Inspect the current Git state before proceeding."
        )
    return result


def safe_repo_path(root: Path, rel: str) -> str | None:
    if not rel or rel.strip() in {".", ".."}:
        return None
    rel = rel.strip().replace("\\", "/")
    if rel.startswith("/") or re.match(r"^[A-Za-z]:", rel):
        return None
    if ".." in rel.split("/"):
        return None
    try:
        target = (root / rel).resolve()
        root_res = root.resolve()
        target.relative_to(root_res)
    except (ValueError, OSError):
        return None
    return str(Path(rel).as_posix())


def git_json(root: Path, *args: str, timeout: float = 5.0) -> str:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=str(root),
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        )
        return out
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return ""


def git_head(root: Path) -> str:
    return git_json(root, "rev-parse", "HEAD").strip() or "unknown"


def git_branch(root: Path) -> str:
    b = git_json(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    return b or "unknown"


def working_tree_counts(root: Path) -> dict[str, int]:
    out = git_json(root, "status", "--porcelain")
    counts = {"modified": 0, "added": 0, "deleted": 0, "untracked": 0, "other": 0}
    for line in out.splitlines():
        if not line or len(line) < 2:
            continue
        x, y = line[0], line[1]
        if line.startswith("??"):
            counts["untracked"] += 1
        elif x == "A" or y == "A":
            counts["added"] += 1
        elif x == "D" or y == "D":
            counts["deleted"] += 1
        elif x in "M" or y in "M":
            counts["modified"] += 1
        else:
            counts["other"] += 1
    return counts


def _parse_json_field(raw: str | None) -> Any:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _expire_claims(conn: sqlite3.Connection, now_iso: str | None = None) -> None:
    now = now_iso or _iso()
    conn.execute(
        "UPDATE claims SET released=1 WHERE released=0 AND expires_at <= ?",
        (now,),
    )
    conn.commit()


def project_status(root: Path, agent: str | None = None) -> dict[str, Any]:
    cfg = load_config(root)
    agent = detect_agent(agent)
    conn = connect(root)
    try:
        _expire_claims(conn)
        wt = working_tree_counts(root)
        claims = conn.execute(
            "SELECT agent, task, scope, created_at, expires_at FROM claims "
            "WHERE released=0 AND expires_at > ? ORDER BY created_at DESC LIMIT ?",
            (_iso(), int(cfg["status_max_claims"])),
        ).fetchall()
        changes = conn.execute(
            "SELECT agent, timestamp, summary, task, auto FROM changes "
            "ORDER BY id DESC LIMIT ?",
            (int(cfg["status_max_changes"]),),
        ).fetchall()
        decisions = conn.execute(
            "SELECT agent, timestamp, title FROM decisions ORDER BY id DESC LIMIT ?",
            (int(cfg["status_max_decisions"]),),
        ).fetchall()
        agents_seen = conn.execute(
            "SELECT agent, MAX(timestamp) AS last FROM changes GROUP BY agent ORDER BY last DESC"
        ).fetchall()
        pending = []
        for c in changes:
            if c["summary"]:
                pending.append({"agent": c["agent"], "summary": c["summary"][:120]})
        handoffs = handoff_summary(root, agent)
        return {
            "project": cfg["project_name"],
            "root": str(root),
            "version": bridge_version(),
            "schema_version": db_schema_version(root),
            "branch": git_branch(root),
            "head": git_head(root)[:12],
            "working_tree": wt,
            "you_are": agent,
            "agents": [{"agent": r["agent"], "last": r["last"]} for r in agents_seen[:5]],
            "active_tasks": [
                {
                    "agent": r["agent"],
                    "task": r["task"],
                    "scope": _parse_json_field(r["scope"]),
                }
                for r in claims
            ],
            "recent_changes": [
                {
                    "agent": r["agent"],
                    "at": r["timestamp"],
                    "summary": r["summary"],
                    "task": r["task"],
                    "auto": bool(r["auto"]),
                }
                for r in changes
            ],
            "decisions": [
                {"agent": r["agent"], "at": r["timestamp"], "title": r["title"]}
                for r in decisions
            ],
            "pending": pending[:3],
            "handoffs": handoffs,
        }
    finally:
        conn.close()


def recent_changes(
    root: Path,
    limit: int | None = None,
    since: str | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    cfg = load_config(root)
    lim = int(limit or cfg["recent_changes_default_limit"])
    lim = max(1, min(lim, int(cfg["recent_changes_max_limit"])))
    conn = connect(root)
    try:
        q = "SELECT * FROM changes"
        clauses: list[str] = []
        params: list[Any] = []
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)
        if path:
            safe = safe_repo_path(root, path)
            if safe is None:
                return {"error": f"invalid path: {path}", "changes": []}
            clauses.append("files LIKE ?")
            params.append(f'%"{safe}"%')
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY id DESC LIMIT ?"
        params.append(lim)
        rows = conn.execute(q, params).fetchall()
        return {
            "count": len(rows),
            "changes": [
                {
                    "agent": r["agent"],
                    "at": r["timestamp"],
                    "task": r["task"],
                    "summary": r["summary"],
                    "files": _parse_json_field(r["files"]),
                    "tests": _parse_json_field(r["tests"]),
                    "decisions": _parse_json_field(r["decisions"]),
                    "issues": _parse_json_field(r["issues"]),
                    "next_action": r["next_action"],
                    "git_head": r["git_head"],
                    "branch": r["branch"],
                    "auto": bool(r["auto"]),
                }
                for r in rows
            ],
        }
    finally:
        conn.close()


def record_change(
    root: Path,
    agent: str | None = None,
    task: str = "",
    summary: str = "",
    files: Any = None,
    tests: Any = None,
    decisions: Any = None,
    issues: Any = None,
    next_action: str = "",
    auto: bool = False,
) -> dict[str, Any]:
    agent = detect_agent(agent)
    file_list = _sanitize_list(files)
    if auto and not file_list:
        out = git_json(root, "status", "--short")
        file_list = [ln[3:].strip() for ln in out.splitlines() if len(ln) > 3][:40]
        file_list = [f for f in file_list if f]
    if auto and not summary:
        summary = "auto git snapshot"
    summary = _sanitize_str(summary, 400)
    if not summary and not file_list:
        return {"ok": False, "error": "empty change (no summary or files)"}
    conn = connect(root)
    try:
        cur = conn.execute(
            """
            INSERT INTO changes
            (agent, timestamp, task, summary, files, tests, decisions, issues,
             next_action, git_head, branch, auto)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                agent,
                _iso(),
                _sanitize_str(task, 200),
                summary,
                json.dumps(file_list),
                json.dumps(_sanitize_list(tests)),
                json.dumps(_sanitize_list(decisions)),
                json.dumps(_sanitize_list(issues)),
                _sanitize_str(next_action, 300),
                git_head(root),
                git_branch(root),
                1 if auto else 0,
            ),
        )
        conn.commit()
        return {"ok": True, "id": cur.lastrowid, "agent": agent}
    finally:
        conn.close()


def claim_task(
    root: Path,
    task: str,
    scope: Any = None,
    agent: str | None = None,
    ttl_seconds: int | None = None,
) -> dict[str, Any]:
    agent = detect_agent(agent)
    task = _sanitize_str(task, 200)
    if not task:
        return {"ok": False, "error": "task is required"}
    cfg = load_config(root)
    ttl = int(ttl_seconds or cfg["claim_ttl_seconds"])
    ttl = max(60, min(ttl, 86400))
    scope_list = _sanitize_list(scope)
    safe_scope = []
    for s in scope_list:
        sp = safe_repo_path(root, s)
        if sp:
            safe_scope.append(sp)
    now = time.time()
    conn = connect(root)
    try:
        _expire_claims(conn, _iso(now))
        conflicts = []
        rows = conn.execute(
            "SELECT agent, task, scope FROM claims WHERE released=0 AND expires_at > ?",
            (_iso(now),),
        ).fetchall()
        for r in rows:
            if r["agent"] == agent:
                continue
            other_scope = _parse_json_field(r["scope"])
            overlap = False
            if r["task"] == task:
                overlap = True
            for a in safe_scope:
                for b in other_scope:
                    if a == b or a.startswith(b + "/") or b.startswith(a + "/"):
                        overlap = True
                        break
                if overlap:
                    break
            if overlap:
                conflicts.append(
                    {"agent": r["agent"], "task": r["task"], "scope": other_scope}
                )
        expires = _iso(now + ttl)
        conn.execute(
            "INSERT INTO claims (agent, task, scope, created_at, expires_at, released) "
            "VALUES (?,?,?,?,?,0)",
            (agent, task, json.dumps(safe_scope), _iso(now), expires),
        )
        conn.commit()
        result: dict[str, Any] = {
            "ok": True,
            "agent": agent,
            "task": task,
            "scope": safe_scope,
            "expires_at": expires,
        }
        if conflicts:
            lines = ["WARNING", "", "Another agent is currently working on:", ""]
            for c in conflicts:
                lines.append(f"- {c['agent']}: {c['task']}")
                for p in c["scope"]:
                    lines.append(f"    {p}")
            lines.append("")
            lines.append(
                "Claim recorded anyway (advisory coordination, not a hard lock)."
            )
            result["conflict"] = True
            result["warning"] = "\n".join(lines)
            result["conflicts"] = conflicts
        else:
            result["conflict"] = False
        return result
    finally:
        conn.close()


def release_task(root: Path, task: str, agent: str | None = None) -> dict[str, Any]:
    agent = detect_agent(agent)
    task = _sanitize_str(task, 200)
    conn = connect(root)
    try:
        cur = conn.execute(
            "UPDATE claims SET released=1 WHERE agent=? AND task=? AND released=0",
            (agent, task),
        )
        conn.commit()
        return {"ok": True, "released": cur.rowcount, "agent": agent, "task": task}
    finally:
        conn.close()


def active_tasks(root: Path) -> dict[str, Any]:
    conn = connect(root)
    try:
        _expire_claims(conn)
        rows = conn.execute(
            "SELECT agent, task, scope, created_at, expires_at FROM claims "
            "WHERE released=0 AND expires_at > ? ORDER BY created_at DESC LIMIT 20",
            (_iso(),),
        ).fetchall()
        return {
            "tasks": [
                {
                    "agent": r["agent"],
                    "task": r["task"],
                    "scope": _parse_json_field(r["scope"]),
                    "created_at": r["created_at"],
                    "expires_at": r["expires_at"],
                }
                for r in rows
            ]
        }
    finally:
        conn.close()


def record_decision(
    root: Path,
    title: str,
    detail: str = "",
    agent: str | None = None,
) -> dict[str, Any]:
    agent = detect_agent(agent)
    title = _sanitize_str(title, 200)
    if not title:
        return {"ok": False, "error": "title is required"}
    conn = connect(root)
    try:
        cur = conn.execute(
            "INSERT INTO decisions (agent, timestamp, title, detail, git_head, branch) "
            "VALUES (?,?,?,?,?,?)",
            (
                agent,
                _iso(),
                title,
                _sanitize_str(detail, 800),
                git_head(root),
                git_branch(root),
            ),
        )
        conn.commit()
        return {"ok": True, "id": cur.lastrowid, "agent": agent}
    finally:
        conn.close()


def get_decisions(root: Path, limit: int = 10) -> dict[str, Any]:
    lim = max(1, min(int(limit), 50))
    conn = connect(root)
    try:
        rows = conn.execute(
            "SELECT agent, timestamp, title, detail, git_head, branch FROM decisions "
            "ORDER BY id DESC LIMIT ?",
            (lim,),
        ).fetchall()
        return {
            "decisions": [
                {
                    "agent": r["agent"],
                    "at": r["timestamp"],
                    "title": r["title"],
                    "detail": r["detail"],
                    "git_head": r["git_head"],
                    "branch": r["branch"],
                }
                for r in rows
            ]
        }
    finally:
        conn.close()


def _handoff_result(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    keys = set(row.keys())
    summary_key = "result_summary" if "result_summary" in keys else "summary"
    created_key = "result_created_at" if "result_created_at" in keys else "created_at"
    return {
        "completed_by": row["completed_by"],
        "summary": row[summary_key],
        "outcome": row["outcome"],
        "findings": _parse_json_field(row["findings"]),
        "tests": _parse_json_field(row["tests"]),
        "recommended_action": row["recommended_action"],
        "created_at": row[created_key],
    }


def _handoff_payload(root: Path, row: sqlite3.Row, result: sqlite3.Row | None = None) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "from_agent": row["from_agent"],
        "to_agent": row["to_agent"],
        "type": row["type"],
        "task": row["task"],
        "title": row["title"],
        "summary": row["summary"],
        "scope": _parse_json_field(row["scope"]),
        "priority": row["priority"],
        "source": {
            "branch": row["source_branch"],
            "head": row["source_head"],
            "base_commit": row["base_commit"],
        },
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "acknowledged_at": row["acknowledged_at"],
    }
    if result is not None:
        payload["result"] = _handoff_result(result)
    payload.update(_source_state(root, row["source_head"], row["source_branch"]))
    return payload


def _next_handoff_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT next_id FROM handoff_sequence LIMIT 1").fetchone()
    number = int(row[0]) if row else 1
    if row is None:
        conn.execute("INSERT INTO handoff_sequence (next_id) VALUES (?)", (number + 1,))
    else:
        conn.execute("UPDATE handoff_sequence SET next_id=?", (number + 1,))
    return f"H-{number:06d}"


def request_handoff(
    root: Path,
    to_agent: str,
    type: str,
    task: str,
    title: str,
    summary: str,
    scope: Any = None,
    priority: str = "normal",
    base_commit: str | None = None,
    from_agent: str | None = None,
) -> dict[str, Any]:
    sender = detect_agent(from_agent)
    error = _validate_agent(sender, "from_agent")
    if error:
        return {"ok": False, "error": error}
    error = _validate_agent(to_agent, "to_agent")
    if error:
        return {"ok": False, "error": error}
    if sender == str(to_agent).strip().lower():
        return {"ok": False, "error": "from_agent and to_agent must differ"}
    handoff_type = str(type or "").strip().lower()
    if handoff_type not in HANDOFF_TYPES:
        return {"ok": False, "error": f"type must be one of: {', '.join(sorted(HANDOFF_TYPES))}"}
    priority_value = str(priority or "normal").strip().lower()
    if priority_value not in HANDOFF_PRIORITIES:
        return {"ok": False, "error": f"priority must be one of: {', '.join(sorted(HANDOFF_PRIORITIES))}"}

    raw_task, raw_title, raw_summary = str(task or "").strip(), str(title or "").strip(), str(summary or "").strip()
    if not raw_task or len(raw_task) > 200:
        return {"ok": False, "error": "task is required and must be <= 200 characters"}
    if not raw_title or len(raw_title) > 200:
        return {"ok": False, "error": "title is required and must be <= 200 characters"}
    if not raw_summary or _text_bytes(raw_summary) > 4096:
        return {"ok": False, "error": "summary is required and must be <= 4096 bytes"}
    safe_scope, scope_error = _validate_handoff_scope(root, scope)
    if scope_error:
        return {"ok": False, "error": scope_error}
    base = _sanitize_str(base_commit, 200) if base_commit else None
    now = _iso()
    conn = connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        handoff_id = _next_handoff_id(conn)
        conn.execute(
            """INSERT INTO handoffs
               (id, from_agent, to_agent, type, task, title, summary, scope, priority,
                source_branch, source_head, base_commit, status, created_at, updated_at, acknowledged_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)""",
            (
                handoff_id, sender, str(to_agent).strip().lower(), handoff_type,
                _sanitize_str(raw_task, 200), _sanitize_str(raw_title, 200),
                _sanitize_str(raw_summary, 4096), json.dumps(safe_scope), priority_value,
                git_branch(root), git_head(root), base, "pending", now, now,
            ),
        )
        conn.commit()
        return {"ok": True, "handoff": get_handoffs(root, handoff_id=handoff_id, agent=sender)["handoffs"][0]}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_handoffs(
    root: Path,
    status: str | None = None,
    to_agent: str | None = None,
    from_agent: str | None = None,
    limit: int | None = None,
    handoff_id: str | None = None,
    agent: str | None = None,
) -> dict[str, Any]:
    current = detect_agent(agent)
    error = _validate_agent(current, "current_agent")
    if error:
        return {"ok": False, "error": error, "handoffs": []}
    for value, field in ((to_agent, "to_agent"), (from_agent, "from_agent")):
        if value is not None:
            error = _validate_agent(value, field)
            if error:
                return {"ok": False, "error": error, "handoffs": []}
    if status is not None and str(status).strip().lower() not in HANDOFF_STATUSES:
        return {"ok": False, "error": f"invalid status: {status}", "handoffs": []}
    parsed_id = _validate_handoff_id(handoff_id) if handoff_id else None
    if handoff_id and parsed_id is None:
        return {"ok": False, "error": "invalid handoff id", "handoffs": []}
    cfg = load_config(root)
    lim = int(limit or cfg.get("handoff_default_limit", 5))
    lim = max(1, min(lim, int(cfg.get("handoff_max_limit", 50))))
    to_value = str(to_agent).strip().lower() if to_agent else None
    from_value = str(from_agent).strip().lower() if from_agent else None
    if parsed_id is None and to_value is None and from_value is None:
        to_value = current
    clauses: list[str] = []
    params: list[Any] = []
    if parsed_id:
        clauses.append("h.id = ?")
        params.append(parsed_id)
    if status:
        clauses.append("h.status = ?")
        params.append(str(status).strip().lower())
    if to_value:
        clauses.append("h.to_agent = ?")
        params.append(to_value)
    if from_value:
        clauses.append("h.from_agent = ?")
        params.append(from_value)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    conn = connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            "SELECT h.*, r.completed_by, r.summary AS result_summary, r.outcome, "
            "r.findings, r.tests, r.recommended_action, r.created_at AS result_created_at "
            "FROM handoffs h LEFT JOIN handoff_results r ON r.handoff_id=h.id" +
            where + " ORDER BY h.created_at DESC LIMIT ?",
            (*params, lim),
        ).fetchall()
        payloads: list[dict[str, Any]] = []
        for row in rows:
            result = row if row["completed_by"] is not None else None
            payloads.append(_handoff_payload(root, row, result))
        # Reading a completed result explicitly as its creator marks it seen.
        if from_value == current and status in {None, "completed"} and payloads:
            ids = [p["id"] for p in payloads if p["status"] == "completed" and p["from_agent"] == current and p["acknowledged_at"] is None]
            if ids:
                marks = ",".join("?" for _ in ids)
                conn.execute(
                    f"UPDATE handoffs SET acknowledged_at=?, updated_at=updated_at WHERE id IN ({marks})",
                    (_iso(), *ids),
                )
                for payload in payloads:
                    if payload["id"] in ids:
                        payload["acknowledged_at"] = _iso()
        conn.commit()
        return {"ok": True, "count": len(payloads), "handoffs": payloads}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def accept_handoff(root: Path, handoff_id: str, agent: str | None = None) -> dict[str, Any]:
    current = detect_agent(agent)
    if _validate_agent(current, "current_agent"):
        return {"ok": False, "error": "current agent must be codex, opencode or agy"}
    parsed_id = _validate_handoff_id(handoff_id)
    if parsed_id is None:
        return {"ok": False, "error": "invalid handoff id"}
    conn = connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM handoffs WHERE id=?", (parsed_id,)).fetchone()
        if row is None:
            conn.rollback()
            return {"ok": False, "error": "handoff not found", "conflict": False}
        if row["to_agent"] != current:
            conn.rollback()
            return {"ok": False, "error": "current agent is not the handoff recipient", "conflict": True}
        cur = conn.execute(
            "UPDATE handoffs SET status='accepted', updated_at=? WHERE id=? AND to_agent=? AND status='pending'",
            (_iso(), parsed_id, current),
        )
        if cur.rowcount != 1:
            conn.rollback()
            return {"ok": False, "error": f"handoff cannot be accepted from status {row['status']}", "conflict": True}
        updated = conn.execute("SELECT * FROM handoffs WHERE id=?", (parsed_id,)).fetchone()
        conn.commit()
        return {"ok": True, "handoff": _handoff_payload(root, updated)}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _validate_result(root: Path, summary: Any, outcome: Any, findings: Any, tests: Any, recommended_action: Any) -> tuple[dict[str, Any] | None, str | None]:
    raw_summary, raw_outcome, raw_action = str(summary or "").strip(), str(outcome or "").strip(), str(recommended_action or "").strip()
    if not raw_summary or _text_bytes(raw_summary) > 4096:
        return None, "result summary is required and must be <= 4096 bytes"
    if not raw_outcome or len(raw_outcome) > 200:
        return None, "outcome is required and must be <= 200 characters"
    if _text_bytes(raw_action) > 2048:
        return None, "recommended_action must be <= 2048 bytes"
    if findings is None:
        findings = []
    if not isinstance(findings, list) or len(findings) > 50:
        return None, "findings must be a list of at most 50 items"
    clean_findings: list[dict[str, Any]] = []
    for item in findings:
        if not isinstance(item, dict):
            return None, "each finding must be an object"
        severity = str(item.get("severity") or "").strip().lower()
        if severity not in HANDOFF_SEVERITIES:
            return None, f"finding severity must be one of: {', '.join(sorted(HANDOFF_SEVERITIES))}"
        file_path = safe_repo_path(root, str(item.get("file") or ""))
        if not file_path:
            return None, "finding file must be a safe repo-relative path"
        if _is_secret_path(file_path):
            return None, "finding file must not reference secret-bearing paths"
        if _text_bytes(str(item.get("summary") or "")) > 1000 or not str(item.get("summary") or "").strip():
            return None, "finding summary is required and must be <= 1000 bytes"
        finding: dict[str, Any] = {
            "severity": severity,
            "file": file_path,
            "summary": _sanitize_str(item.get("summary"), 1000),
        }
        if item.get("line") is not None:
            if isinstance(item.get("line"), bool) or not isinstance(item.get("line"), int) or item["line"] < 1:
                return None, "finding line must be a positive integer"
            finding["line"] = item["line"]
        clean_findings.append(finding)
    if tests is None:
        tests = []
    if not isinstance(tests, list) or len(tests) > 50:
        return None, "tests must be a list of at most 50 items"
    clean_tests = [_sanitize_str(value, 500) for value in tests]
    return {
        "summary": _sanitize_str(raw_summary, 4096),
        "outcome": _sanitize_str(raw_outcome, 200),
        "findings": clean_findings,
        "tests": clean_tests,
        "recommended_action": _sanitize_str(raw_action, 2048),
    }, None


def complete_handoff(
    root: Path,
    handoff_id: str,
    summary: str,
    outcome: str,
    findings: Any = None,
    tests: Any = None,
    recommended_action: str = "",
    agent: str | None = None,
) -> dict[str, Any]:
    current = detect_agent(agent)
    if _validate_agent(current, "current_agent"):
        return {"ok": False, "error": "current agent must be codex, opencode or agy"}
    parsed_id = _validate_handoff_id(handoff_id)
    if parsed_id is None:
        return {"ok": False, "error": "invalid handoff id"}
    clean, error = _validate_result(root, summary, outcome, findings, tests, recommended_action)
    if error:
        return {"ok": False, "error": error}
    conn = connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM handoffs WHERE id=?", (parsed_id,)).fetchone()
        if row is None:
            conn.rollback()
            return {"ok": False, "error": "handoff not found", "conflict": False}
        if row["to_agent"] != current:
            conn.rollback()
            return {"ok": False, "error": "current agent is not the handoff recipient", "conflict": True}
        if row["status"] not in {"accepted", "in_progress"}:
            conn.rollback()
            return {"ok": False, "error": f"handoff cannot be completed from status {row['status']}", "conflict": True}
        now = _iso()
        conn.execute(
            "INSERT INTO handoff_results (handoff_id, completed_by, summary, outcome, findings, tests, recommended_action, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (parsed_id, current, clean["summary"], clean["outcome"], json.dumps(clean["findings"]), json.dumps(clean["tests"]), clean["recommended_action"], now),
        )
        conn.execute("UPDATE handoffs SET status='completed', updated_at=? WHERE id=? AND status IN ('accepted','in_progress')", (now, parsed_id))
        updated = conn.execute("SELECT * FROM handoffs WHERE id=?", (parsed_id,)).fetchone()
        result = conn.execute("SELECT * FROM handoff_results WHERE handoff_id=?", (parsed_id,)).fetchone()
        conn.commit()
        return {"ok": True, "handoff": _handoff_payload(root, updated, result)}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cancel_handoff(root: Path, handoff_id: str, reason: str = "", agent: str | None = None) -> dict[str, Any]:
    current = detect_agent(agent)
    if _validate_agent(current, "current_agent"):
        return {"ok": False, "error": "current agent must be codex, opencode or agy"}
    parsed_id = _validate_handoff_id(handoff_id)
    if parsed_id is None:
        return {"ok": False, "error": "invalid handoff id"}
    conn = connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM handoffs WHERE id=?", (parsed_id,)).fetchone()
        if row is None:
            conn.rollback()
            return {"ok": False, "error": "handoff not found", "conflict": False}
        if current not in {row["from_agent"], row["to_agent"]}:
            conn.rollback()
            return {"ok": False, "error": "current agent is not a handoff participant", "conflict": True}
        if row["status"] not in {"pending", "accepted", "in_progress"}:
            conn.rollback()
            return {"ok": False, "error": f"handoff cannot be cancelled from status {row['status']}", "conflict": True}
        conn.execute("UPDATE handoffs SET status='cancelled', updated_at=? WHERE id=? AND status IN ('pending','accepted','in_progress')", (_iso(), parsed_id))
        updated = conn.execute("SELECT * FROM handoffs WHERE id=?", (parsed_id,)).fetchone()
        conn.commit()
        return {"ok": True, "handoff": _handoff_payload(root, updated), "reason": _sanitize_str(reason, 500)}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def handoff_summary(root: Path, agent: str | None = None) -> dict[str, Any]:
    current = detect_agent(agent)
    conn = connect(root)
    try:
        pending = conn.execute("SELECT to_agent, COUNT(*) AS count FROM handoffs WHERE status='pending' GROUP BY to_agent").fetchall()
        pending_by_agent = {row["to_agent"]: int(row["count"]) for row in pending}
        in_progress = int(conn.execute("SELECT COUNT(*) FROM handoffs WHERE status='in_progress'").fetchone()[0])
        unread = int(conn.execute("SELECT COUNT(*) FROM handoffs WHERE status='completed' AND from_agent=? AND acknowledged_at IS NULL", (current,)).fetchone()[0]) if current in VALID_HANDOFF_AGENTS else 0
        next_row = conn.execute("SELECT * FROM handoffs WHERE status='pending' AND to_agent=? ORDER BY priority DESC, created_at ASC LIMIT 1", (current,)).fetchone() if current in VALID_HANDOFF_AGENTS else None
        recent_results = conn.execute(
            "SELECT h.*, r.completed_by, r.summary AS result_summary, r.outcome, r.findings, r.tests, r.recommended_action, r.created_at AS result_created_at "
            "FROM handoffs h JOIN handoff_results r ON r.handoff_id=h.id WHERE h.from_agent=? AND h.status='completed' ORDER BY h.updated_at DESC LIMIT 2", (current,)
        ).fetchall() if current in VALID_HANDOFF_AGENTS else []
        return {
            "pending_by_agent": {a: pending_by_agent.get(a, 0) for a in sorted(VALID_HANDOFF_AGENTS)},
            "in_progress": in_progress,
            "completed_unread": unread,
            "next": _handoff_payload(root, next_row) if next_row else None,
            "recent_completed": [_handoff_payload(root, row, row) for row in recent_results],
        }
    finally:
        conn.close()


def compact_status_text(root: Path) -> str:
    cfg = load_config(root)
    st = project_status(root)
    lines = [
        "PROJECT",
        str(st["project"]),
        "",
        "ROOT",
        str(st["root"]),
        "",
        "PROJECT BRIDGE",
        f"{st['version']}  (schema {st['schema_version']})",
        "",
        "BRANCH",
        str(st["branch"]),
        f"HEAD {st['head']}",
        f"You are: {st['you_are']}",
        "",
        "Working tree:",
    ]
    wt = st["working_tree"]
    lines.append(
        f"  {wt['modified']} modified, {wt['added']} added, "
        f"{wt['deleted']} deleted, {wt['untracked']} untracked"
    )
    if st["active_tasks"]:
        lines += ["", "Active claims:"]
        for t in st["active_tasks"][:3]:
            lines.append(f"- {t['agent']} \u2192 {t['task']}")
    if st["recent_changes"]:
        lines += ["", "Recent changes:"]
        for c in st["recent_changes"][:3]:
            flag = " (auto)" if c["auto"] else ""
            sm = (c["summary"] or "")[:80]
            lines.append(f"- {c['agent']}: {sm}{flag}")
    if st["decisions"]:
        lines += ["", "Recent decisions:"]
        for d in st["decisions"][:2]:
            lines.append(f"- {d['title']}")
    hs = st.get("handoffs") or {}
    lines += ["", "HANDOFFS"]
    pending_for_you = int((hs.get("pending_by_agent") or {}).get(st["you_are"], 0))
    lines.append(f"Pending for {st['you_are'].capitalize():<8} {pending_for_you}")
    for name in ("codex", "opencode", "agy"):
        if name != st["you_are"]:
            lines.append(f"Pending for {name.capitalize():<8} {int((hs.get('pending_by_agent') or {}).get(name, 0))}")
    lines.append(f"In progress             {int(hs.get('in_progress') or 0)}")
    lines.append(f"Completed unread        {int(hs.get('completed_unread') or 0)}")
    next_handoff = hs.get("next")
    if next_handoff:
        lines += ["", "NEXT", next_handoff["id"], f"{next_handoff['from_agent']} → {next_handoff['to_agent']}", next_handoff["type"], next_handoff["task"]]
    completed = hs.get("recent_completed") or []
    if completed:
        lines += ["", "Completed results for you:"]
        for item in completed[:2]:
            result = item.get("result") or {}
            lines.append(f"- {item['id']} {item['from_agent']} completed {item['task']}")
            lines.append(f"  {result.get('outcome', 'completed')}")
    lines += [
        "",
        "Git is authoritative for code. Bridge is coordination only.",
        "Before substantial edits: check active_tasks / claim_task.",
    ]
    text = "\n".join(lines)
    limit = int(cfg.get("status_max_bytes") or 2048)
    return text if len(text) <= limit else text[: limit - 3] + "\u2026"


def _cli(argv: list[str]) -> int:
    root = repo_root()
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "status":
        print(compact_status_text(root))
    elif cmd == "auto-record":
        print(json.dumps(record_change(root, auto=True)))
    elif cmd == "json-status":
        print(json.dumps(project_status(root), indent=2))
    elif cmd == "version":
        print(f"Project Bridge {bridge_version()} (schema {db_schema_version(root)})")
    elif cmd == "handoffs":
        hs = handoff_summary(root)
        print("HANDOFFS")
        for name in ("codex", "opencode", "agy"):
            print(f"Pending for {name.capitalize():<8} {int((hs['pending_by_agent'] or {}).get(name, 0))}")
        print(f"In progress             {int(hs.get('in_progress') or 0)}")
        print(f"Completed unread        {int(hs.get('completed_unread') or 0)}")
        if hs.get("next"):
            nxt = hs["next"]
            print("\nNEXT")
            print(nxt["id"])
            print(f"{nxt['from_agent']} → {nxt['to_agent']}")
            print(nxt["type"])
            print(nxt["task"])
    elif cmd == "handoff":
        if len(argv) < 3:
            print("handoff id is required", file=sys.stderr)
            return 2
        print(json.dumps(get_handoffs(root, handoff_id=argv[2], agent=detect_agent()), indent=2))
    elif cmd == "agy-project-name":
        print(agy_project_name(root))
    elif cmd == "agy-ensure-binding":
        name = argv[2] if len(argv) > 2 else None
        print(json.dumps(ensure_agy_binding(root, name)))
    elif cmd == "agy-stop":
        # AGY Stop hook contract: the response must unmarshal into AGY's
        # StopHookResult proto. bridge's own {"ok": ...} payload is rejected
        # (unknown field "ok"), so record first, then emit an empty object
        # which means "do not block termination".
        record_change(root, auto=True)
        print("{}")
    elif cmd == "agy-preinvocation":
        # AGY PreInvocation hook contract: hook context arrives as JSON on
        # stdin, and the handler must emit {"injectSteps": [...]} on stdout
        # for the text to be injected into the model context.
        if not sys.stdin.isatty():
            try:
                sys.stdin.read()
            except Exception:
                pass
        print(
            json.dumps(
                {"injectSteps": [{"ephemeralMessage": compact_status_text(root)}]}
            )
        )
    else:
        print(f"unknown cmd: {cmd}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
