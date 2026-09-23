// Project Bridge — OpenCode V2 hook plugin.
//
// On a session becoming idle it records a git-only coordination snapshot
// through the bridge engine (`bridge.py auto-record`), so other agents
// (Codex, AGY) can see where OpenCode left the working tree. It never invents
// decisions or tests: only git facts.
//
// Why no `import { Plugin } from "@opencode/plugin"`:
// OpenCode 2.0.14 loads a repo-local plugin only if it default-exports a
// definition with an `id` and a `setup`/`effect`. The published
// `@opencode/plugin` helper is not resolvable from a plain
// `.opencode/plugins/*.ts` file in this build, and Project Bridge must stay
// dependency-free, offline and portable (no node_modules). The runtime
// contract is declared locally below and the definition is exported directly
// — the exact shape the loader validates.
//
// V2 event used:
//   `ctx.event.subscribe({ signal })` yields the public server event stream.
//   The documented `session.idle` event exists in the 2.0.14 schema, but this
//   build emits `session.execution.succeeded` when a session finishes a turn
//   and goes idle. Both are treated as the idle signal so the hook keeps
//   working across builds.
//
// Portability: the repository root comes from OpenCode's own location
// (`ctx.location.project.canonical` / `ctx.location.directory`), re-resolved
// with git so a session started in a subdirectory still finds the root. No
// absolute path and no pilot project name is hardcoded.

import { execFile } from "node:child_process"
import { existsSync } from "node:fs"

const AGENT = "opencode"
const REL_SCRIPT = ".agents/project-bridge/bridge.py"
const IDLE_EVENTS = new Set(["session.idle", "session.execution.succeeded"])

type BridgeEvent = { type: string; sessionID?: string }

type PluginContext = {
  location?: {
    directory?: string
    project?: { id?: string; canonical?: string }
  }
  event: {
    subscribe(options?: { signal?: AbortSignal }): AsyncIterable<BridgeEvent>
  }
}

type PluginDefinition = {
  id: string
  setup(ctx: PluginContext): void | (() => void) | Promise<void | (() => void)>
}

type ExecResult = { code: number; stdout: string; stderr: string }

function exec(
  cmd: string,
  args: string[],
  opts: { cwd?: string; env?: Record<string, string | undefined> } = {},
): Promise<ExecResult> {
  return new Promise((resolve) => {
    execFile(
      cmd,
      args,
      { cwd: opts.cwd, env: opts.env, timeout: 10_000, maxBuffer: 1024 * 1024 },
      (err, stdout, stderr) => {
        const raw = (err as { code?: unknown } | null)?.code
        const code = typeof raw === "number" ? raw : err ? 1 : 0
        resolve({ code, stdout: String(stdout ?? ""), stderr: String(stderr ?? "") })
      },
    )
  })
}

async function resolveRoot(base: string): Promise<string> {
  const git = await exec("git", ["-C", base, "rev-parse", "--show-toplevel"])
  if (git.code === 0 && git.stdout.trim()) return git.stdout.trim()
  return base
}

const projectBridge: PluginDefinition = {
  id: "project-bridge",

  async setup(ctx) {
    const base = ctx.location?.project?.canonical || ctx.location?.directory
    if (!base) return

    // Git root is authoritative: works even when the session opens in a subdir.
    const root = await resolveRoot(base)
    const script = `${root}/${REL_SCRIPT}`
    if (!existsSync(script)) return

    const controller = new AbortController()
    // Minimal dedup: one auto-record per idle event, never two concurrently for
    // the same session (guards against duplicated event delivery / reloads).
    const inFlight = new Set<string>()

    void (async () => {
      try {
        for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
          if (!IDLE_EVENTS.has(event.type)) continue
          const sessionID = String(event.sessionID ?? "unknown")
          if (inFlight.has(sessionID)) continue
          inFlight.add(sessionID)
          try {
            const r = await exec("python3", [script, "auto-record"], {
              cwd: root,
              env: { ...process.env, PROJECT_BRIDGE_ROOT: root, PROJECT_BRIDGE_AGENT: AGENT },
            })
            if (r.code !== 0) {
              console.warn("[project-bridge] auto-record failed:", r.stderr.slice(0, 200))
            }
          } catch (err) {
            // Coordination must never break the session.
            console.warn("[project-bridge] auto-record error:", String(err).slice(0, 200))
          } finally {
            inFlight.delete(sessionID)
          }
        }
      } catch {
        // Aborted on unload/reload — expected.
      }
    })()

    return () => controller.abort()
  },
}

export default projectBridge
