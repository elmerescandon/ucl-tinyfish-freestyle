---
name: use-meals
description: Use this skill to run the meals CLI — price a dish across UK supermarkets, find a recipe, build a shopping list, or manage the recipe cache. Triggers include "price <dish>", "what does this dish cost", "cheapest supermarket", "shopping list", "meal plan", "bin/meals", "bin/recipes". Requires the tinyfish CLI (search/fetch/agent); throw an error and stop if tinyfish is missing or unauthenticated.
---

# use-meals — running the `meals` CLI

`bin/meals` answers one question: what does this dish cost to make? It finds a
recipe online, extracts the ingredients, prices each one across UK
supermarkets, and ranks the stores. Everything runs on the `tinyfish` CLI
(`search`, `fetch`, `agent`) driven by stdlib Python — nothing else touches
the network. Read `README.md` for the user-facing story and skim `bin/meals`
before running anything non-trivial.

## Step 0 — tinyfish is mandatory (hard gate)

Before doing anything else, verify tinyfish. If it is missing or not
authenticated, throw an error and stop. No fallbacks — no curl, no other web
tooling, no "just this once" workarounds. Every command below depends on it.

```bash
if ! command -v tinyfish >/dev/null 2>&1; then
  echo "error: tinyfish CLI not found. Install it: npm install -g @tiny-fish/cli" >&2
  exit 1
fi
tinyfish auth status | grep -q '"authenticated": *true' || {
  echo "error: tinyfish not authenticated. Run: tinyfish auth login (or set TINYFISH_API_KEY)" >&2
  exit 1
}
```

Prefer to smoke-test the actual API too (auth JSON can lie less than a real
call):

```bash
tinyfish search query "sanity check" >/dev/null 2>&1 \
  || { echo "error: tinyfish search call failed — check key/network" >&2; exit 1; }
```

If any preflight fails: report the exact error to the user and stop. Never
continue without tinyfish. Note that a tinyfish binary that vanishes mid-run
degrades silently (empty fetches → `not_priced` rows) — if you see mass
empties, re-run the preflight.

## Put the CLIs on your PATH

The executables in `bin/` are meant to be used bare — `meals`, `recipes`,
`mealplan` — not as `./bin/meals`. Add this repo's `bin/` to your PATH once:

```bash
# ~/.zshrc (or ~/.bashrc)
export PATH="$PATH:/Users/raulescandon/Projects/ucl-tinyfish-freestyle/bin"
```

Then reload (`source ~/.zshrc`) and run from anywhere:

```bash
meals 'mashed potatoes with tuna'
```

Prefer a symlink over PATH? `ln -s "$PWD/bin/meals" /usr/local/bin/meals`
(repeat for `recipes` and `mealplan`).

## Running it

```bash
meals 'mashed potatoes with tuna'            # human summary on stdout
meals 'fish pie' --json                      # machine-readable contract
meals 'fish pie' --servings 4                # scale for more people
meals 'fish pie' --no-cache                  # force a fresh recipe lookup
```

Split output discipline: stderr carries progress (`recipe: cache hit`,
per-item pricing counts); stdout carries the result — human table by
default, JSON only with `--json`. When automating, always pass `--json` and
parse that; never regex the human table. The `--json` shape documented in
README is a contract: expect `dish`, `shopping_list`, `quotes`, `totals_gbp`,
`cheapest`, `not_priced`, `coverage`. `cheapest` is only set when the verdict
is defensible (comparable coverage between ranked stores); `not_priced` lists
honest gaps with a suggested next-step query.

## Recipe cache helper

Recipes and fetches are cached on disk under `data/` (git-ignored; deleting
it is always safe). To inspect or manage:

```bash
./bin/recipes list                       # what's saved
./bin/recipes get 'fish pie'             # full stored recipe (JSON)
./bin/recipes rm 'fish pie'              # forget one
./bin/recipes cache 'fish pie'           # prime the cache in advance
```

## Failure modes (be honest, never invent)

- **Preflight failed** → stop and surface the error. That is the only
  unrecoverable state.
- `no recipe / ingredients found` → try a more specific dish name; the
  search leans on `<dish> recipe` URLs that contain an ingredients section.
- Items come back `not_priced` → network/tinyfish hiccup or obscure product.
  Retry once, then accept the gap and report it; the coverage-aware totals
  already handle partial data.
- Stale or wrong recipe → re-run with `--no-cache`.

## If you edit the code (read this first)

- Work directly on `main`. No servers, no frameworks, no new pip/npm
  dependencies — stdlib Python 3.13 plus the tinyfish CLI via `subprocess`.
- Use the lightest tinyfish tool in `search` → `fetch` → `agent` order;
  `agent` is slow and costs money, only when `fetch` returns `bot_blocked`
  or empty, and never let an agent call run past ~90s without a fallback.
- Every tinyfish subprocess call needs a timeout (see `run()` in
  `lib/common.py`). Output is JSON by default; `--pretty` only when
  regex-ing URLs. Cache fetches to disk (`data/`).
- Contracts you must not break: `price_item() -> {store: {price, unit}}`
  and the `--json` output shape in README. Extend, don't rename.
- Verify before claiming done:
  `python3 -c "import ast; ast.parse(open('bin/meals').read())"` plus one
  cold-cache run (`rm -rf data/`) and one warm run — both must succeed.
- Report back in short facts: what you tried, what failed, latencies,
  follow-ups.
