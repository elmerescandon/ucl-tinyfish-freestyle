# AGENT.md — guidelines for agents working on TODO.md

Read `README.md`, `TODO.md` and skim `bin/meals` before doing anything.
You will work directly on `main` (no feature branches, no PRs).

## Claim a name (required)

Before touching any code, pick a unique agent name (chess pieces are the
convention) and write it into `TODO.md` on the task you claim, in the same
style as "**Owner.** Agent **bishop** — t2 in progress". One agent = one
task; a task already owned by another agent is off-limits. Use that name in
commits (`git -c user.name='<name>' ...`) and in your final report.

## Ground rules (non-negotiable)

- **Stack discipline**: stdlib Python 3.13 + the `tinyfish` CLI (`search`,
  `fetch`, `agent`) via `subprocess`. No new pip/npm dependencies, no servers,
  no web UI, no docker. If you think you need a framework — you don't.
- **Use the lightest tinyfish tool**: `search` → `fetch` → `agent`, in that
  order. `agent` is slow and costs more; only reach for it when `fetch`
  returns `bot_blocked` or empty content. Never leave an `agent` call running
  longer than ~90s without a fallback plan.
- **Tinyfish quirks**: every subprocess call needs a timeout (see `run()` in
  `bin/meals`). Output is JSON by default; use `--pretty` only when regex-ing
  URLs. Cache fetches to disk (see `fetch_text()`); `data/` is git-ignored.
- **Keep interfaces stable**: `price_item(name) -> {store: {price, unit}}` and
  the JSON output shape in README are contracts. Other tasks depend on them.
  Extend, don't break.

## Ownership map (task per file scope)

Work only inside your task's file scope:

| Task | Owns | May touch |
|------|------|-----------|
| T1 price sources | `price_item()`, search fallbacks | `bin/meals` (pricing section only) |
| T2 recipe cache | `bin/recipes` (new), `lib/common.py` (new) | `bin/meals` (recipe-discovery section only) |
| T3 output fix | reporting/`main()` in `bin/meals` | stdout/stderr layout only |

- If you need helpers that live in `bin/meals`, **move** them into
  `lib/common.py` and import — but move only what you need, verbatim, and
  leave thin wrappers in `bin/meals` so other tasks keep working. Do not
  reformat or "improve" code you don't own.
- Never rename functions, flags, or JSON keys that appear in README.
- Keep commits scoped to your section.

## Verification before you claim done

```bash
python3 -c "import ast; ast.parse(open('bin/meals').read())"   # parses
./bin/meals 'mashed potatoes with tuna'                        # end-to-end
```

- Run the end-to-end at least once with a **cold cache**
  (`rm -rf data/`) and once warm. Both must succeed.
- Each TODO task lists its own acceptance criteria — that is the bar. If you
  cannot meet it, say so honestly instead of faking it.
- Network is real: expect occasional tinyfish failures. Retry once, then
  degrade gracefully (empty quotes + `not_priced`), never crash.

## Report back

Keep it short — facts, not narrative: what you tried, what failed, latency
numbers if relevant, and any follow-ups for TODO.md.
