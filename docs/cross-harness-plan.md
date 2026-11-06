# Cross-harness support: plan

Goal: let cs show and drive sessions from other coding harnesses (Codex, OpenCode, pi, Hermes), not only Claude Code.

## Where Claude is wired in today

Everything is in one script, `claude-sessions`, and it assumes Claude Code in five places:

| Area | How it works now | Code |
|---|---|---|
| Finding sessions | Reads `~/.claude/sessions/*.json` (pid, status), then `~/.claude/projects/*/<sid>.jsonl` | `collect()`, `transcript()` |
| Parsing a transcript | Reads Claude's JSONL format for model, context, tokens, task, subagents and the chat log | `stats()`, `chatlog()` |
| Sessions cs runs itself | `claude -p --input-format stream-json`, with permission prompts going through `--permission-prompt-tool stdio` | `own_start/answer/mode/stop` |
| Typing into a live session | Finds the session's tty in Terminal or iTerm2 (not tied to a harness) | `session_send()` |
| Extras | `show_files` MCP, usage-limit bar, `generate` commit message, the small chat helper, inbox and tasks, all through `claude -p` | various |

pi is already partly supported: `tr_chats()` reads `~/.pi/agent/sessions`, but only to put names on ThinkRail chats.

## The harnesses

| Harness | Version checked | Where it stores sessions | How a program can drive it (to verify) |
|---|---|---|---|
| Codex | 0.146.0 | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | `codex exec --json` / `exec resume`, or `codex app-server` (JSON-RPC, with approvals) |
| OpenCode | 1.3.3 | `~/.local/share/opencode/opencode.db` (SQLite) | `opencode serve` (HTTP + SSE, with permissions), `opencode run --format json` |
| pi | not on PATH (`~/.pi` exists) | `~/.pi/agent/sessions/<cwd>/<t>_<id>.jsonl` | `pi --mode rpc` (JSON over stdin/stdout) |
| Hermes | 0.11.0 | `~/.hermes/state.db` + `sessions/` | not checked yet |

The "how to drive it" column comes from memory and still has to be checked against each installed version.

## The proposed seam

One small adapter per harness, with three functions:

```
find()       -> rows      # live + recent sessions, in the same row shape collect() returns now
log(path)    -> entries   # the same (kind, text) entries chatlog() returns now
run(...)     -> optional  # start / send / answer a permission / stop
```

Claude becomes the first adapter (the code that exists today, moved as-is). Each row gets a `harness` field, and the UI shows a small badge per tile. Nothing else in the TUI or web changes, because it already works with rows and log entries.

## Phases

1. **Read-only visibility.** Codex, OpenCode, pi and Hermes sessions show up as tiles and in transcripts/Focus, with whatever stats each format has (model, tokens, cwd, title, branch). Typing into Terminal and iTerm2 sessions works for free.
2. **Run them from cs.** New Session gets a harness picker, and ended sessions can be resumed. Each harness has its own protocol for streaming and permission prompts.
3. **Extras.** `show_files` over MCP (Codex, OpenCode and Hermes all support MCP), and maybe a setting to use a different harness for the commit message and chat helper.

## Decision for phase 2: ACP or each harness's own protocol

- **ACP (Agent Client Protocol):** cs would have one client, and OpenCode, Codex (through an adapter), pi (adapter) and Claude (adapter) would all speak it. It covers prompts, streaming and permission requests in one shape. The cost is extra adapter installs, and it doesn't help with phase 1 (finding sessions started in a terminal).
- **Each harness's own protocol:** no extra installs, but four protocols to maintain.

Lean: each harness's own protocol for phase 1 (it's only file readers anyway), and a proper look at ACP before starting phase 2.

## Open questions

1. Scope: is phase 1 enough to start with, or is launching Codex/OpenCode sessions from cs needed from day one?
2. Priority: which harness is used most? Do that one first, end to end.
3. pi: used on its own, or only through ThinkRail?
4. Hermes: a coding harness in a repo, or a general assistant? That decides whether its sessions belong in a coding dashboard.

## Not checked yet / risks

- Hermes's session format, whether OpenCode 1.3.3 still writes `storage/` or only SQLite, and the details of each harness's programmatic mode.
- Context and usage bars won't mean the same thing across harnesses, so some tiles will show `-`.
