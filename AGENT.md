# AGENT.md — guidelines for agents working on TODO.md

You are one of several agents working **in parallel**, one task per tab.
Read `README.md`, `TODO.md` and skim `bin/meals` before doing anything.

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

## Isolation rules (you are NOT alone)

One task per branch. Work only inside your task's file scope:

| Task | Branch | Owns | May touch |
|------|--------|------|-----------|
| T1 price sources | `todo/t1-price-sources` | `price_item()`, search fallbacks | `bin/meals` (pricing section only) |
| T2 recipe cache | `todo/t2-recipe-cache` | `bin/recipes` (new), `lib/common.py` (new) | `bin/meals` (recipe-discovery section only) |
| T3 output fix | `todo/t3-output` | reporting/`main()` in `bin/meals` | stdout/stderr layout only |

- If T2 needs helpers that live in `bin/meals`, **move** them into
  `lib/common.py` and import — but move only what you need, verbatim, and
  leave thin wrappers in `bin/meals` so T1/T3 keep working. Do not reformat
  or "improve" code you don't own.
- Never rename functions, flags, or JSON keys that appear in README.
- If two tasks must touch the same lines, coordinate through small commits:
  keep each commit scoped to your section so git can merge cleanly.

## Git workflow

```bash
git checkout main && git pull
git checkout -b todo/t<N>-<slug>          # one branch per task
# ... work in small commits: "t1: try basketr for tuna" not "wip"
git push -u origin todo/t<N>-<slug>       # push early, push often
```

- Do **not** merge to `main` yourself; open a PR when the acceptance criteria
  in TODO.md pass. PR title = task ID + short summary.
- Rebase onto `main` at the start of your session; if `main` moved mid-task,
  rebase again before the PR.

## Verification before you claim done

```bash
python3 -c "import ast; ast.parse(open('bin/meals').read())"   # parses
./bin/meals 'mashed potatoes with tuna'                        # end-to-end
```

- Run the end-to-end at least once with a **cold cache**
  (`rm -rf data/`) and once warm. Both must succeed.
- Each TODO task lists its own acceptance criteria — that is the bar. If you
  cannot meet it, say so in the PR description instead of faking it.
- Network is real: expect occasional tinyfish failures. Retry once, then
  degrade gracefully (empty quotes + `not_priced`), never crash.

## Report back

In the PR description: what you tried (sources/prompts/regexes), what failed,
latency numbers if relevant, and any follow-ups for TODO.md. Keep it short —
facts, not narrative.
