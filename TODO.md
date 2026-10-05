# TODO

Project context: read `README.md` and `bin/meals` before starting any task.
The whole stack is `tinyfish` CLI (`search`, `fetch`) + stdlib Python — no
servers, no frameworks. Reproduce current behavior with:

```bash
./bin/meals 'mashed potatoes with tuna'
```

---

## T1 — Find price sources beyond trolley.co.uk

**Owner.** Agent **bishop** — t1 in progress.

**Problem.** We price items via `search site:trolley.co.uk <item>` → fetch the
trolley product page → regex the per-store prices. Known issues:

- Generic queries match wrong products (`tuna` → cat food, `potatoes` → seed potatoes).
- One missed trolley URL means zero quotes for that item.
- Aggregators may lag or miss discounters (Aldi/Lidl coverage is thin).

**Task.** Research and prototype alternative price sources for UK supermarket
shelf prices, keeping the constraint "no official APIs" — options to evaluate
(use `tinyfish search` / `tinyfish fetch` / `tinyfish agent run` for the probe):

1. Other aggregators: basketr.app, allsupers.co.uk, trolley alternatives.
2. Direct store search pages (tesco.com, sainsburys.co.uk, asda.com,
   morrisons.com, waitrose.com, aldi.co.uk, lidl.co.uk) — test whether
   `tinyfish fetch` gets results or whether `tinyfish agent run` is needed
   (agent worked for nothing yet: earlier probe on tesco.com was slow; measure
   time and cost per call).
3. Hybrid: trolley first, per-store fallback.

**Deliverable.**
- Short comparison table: source × stores covered × fetch vs agent × latency ×
  match quality for: `tuna`, `potatoes`, `panko breadcrumbs`, `salt`.
- If a better source exists, patch `price_item()` in `bin/meals` behind the
  same interface (returns `{store: {price, unit}}`) — do not change the CLI.

**Findings (bishop, 2026-10-05).** Probe results for `tuna in water` via
plain `tinyfish fetch` vs `tinyfish agent run` (fetch = free; agent ≈ $0.11
at 0.016/step):

| Source | fetch | agent | Fetch latency | Notes |
|---|---|---|---|---|
| Waitrose search | ✅ full | not needed | 2–4s | names + shelf + unit price, reliable |
| Iceland search | ✅ full | not needed | ~13s | names + prices + unit price; **not on trolley** |
| Tesco search | 🚫 bot_blocked | ✅ 7 steps, 54s | — | accurate, per-call cost real ($) |
| Asda search | 🚫 bot_blocked | untested | — | same class as Tesco |
| Sainsbury's | 🚫 page_not_found | untested | — | SPA, no fetchable URL |
| Morrisons | ✅ but query dropped | untested | ~3s | names stripped, redirected to /categories |
| Aldi | ✅ but always home | ⚠️ ran, 0 results | 3–43s | no indexed grocery pages; JS-only search |
| Lidl | ✅ but redirects home | ⚠️ no priced search results | 37s+ | no per-item prices; **agent CAN read offer carousels** (`ods-price` on landing pages, e.g. /c/food-drink/s10068374) → future offer-feed source, not an item callback |

Decision: trolley/aggregator probing found no better single source; the
winning playbook is the **hybrid** — keep trolley as primary, add a
**per-store straight-fetch callback** for Waitrose (thin on trolley) and
Iceland (absent from trolley). Tesco reachable via agent is possible but
slow+costly; leave for when coverage matters more than cost.

**Implemented.** `price_item()` in `bin/meals` now: trolley first → for any
missing fallback store, fetch its public search page and parse shelf+unit
price (cheapest match per store). Same interface `{store: {price, unit}}`,
CLI unchanged. Verified end-to-end: `tuna` and `salt` (previously 0-store
items) now quote via fallback; JSON shape unchanged.

---

## T3 — Fix output presentation

**Owner.** Agent **knight** — t3 in progress.

**Problem.** Current output is misleading:

- Totals per store sum *different item subsets* (e.g. "Co-op £2.40 cheapest"
  was based on 1 priced item while Tesco had 3) — the `cheapest` verdict is
  wrong whenever coverage differs.
- Raw JSON dumps to stdout even for humans; the human summary only goes to
  stderr at the very end.
- No per-item visibility: you cannot see which store won on which item, nor
  unit prices side by side.

**Task.** Rework the reporting layer in `bin/meals` (keep `--json` for machine
output; keep stdout clean):

1. Per-item × per-store price table: rows = items, columns = stores, cell =
   `£x.xx` (or `—`), unit price on a second line or in parentheses.
2. Coverage-aware totals: only rank stores that priced ≥ N items (default N =
   half of priced items); print item counts next to totals
   (`Tesco £7.80 (3/11 items)`); only print `← cheapest` when at least two
   stores have equal coverage.
3. `not_priced` items listed with a suggested next step (e.g. "try
   `tuna chunks in water`").
4. Human summary prints to stdout; JSON only with `--json`.

**Acceptance.** `./bin/meals 'mashed potatoes with tuna'` prints a readable
table where the cheapest verdict is defensible from the table alone.

---

## T4 — Weekly meal plan: several dishes, one basket, a budget

**Owner.** Agent **rook** — t4 in progress.

**Problem.** `bin/meals` prices exactly one dish per run. Planning a week
means N separate runs, N separate baskets, and no idea what the week costs —
and shared ingredients (oil, potatoes, salt) get priced and bought twice.

**Task.** Add `bin/mealplan` (new file — `bin/meals` stays untouched; you
consume it, you don't modify it):

```bash
./bin/mealplan 'fish pie' 'mashed potatoes with tuna' 'leek and potato soup' \
  [--servings 2] [--budget 30] [--json]
```

1. Per dish: run `./bin/meals '<dish>' --json` as a subprocess (use
   `lib.common.run`-style timeouts, one thread per dish) and treat its JSON
   output as the input contract — do not re-implement recipe search or
   pricing, and do not import from `bin/meals`. A dish that fails (exit 1 /
   no recipe) degrades to a warning; the plan continues with the rest.
2. Shared-ingredient reuse across meals (the point of the plan): canonicalise
   names (fold singular/plural: `potato` → `potatoes`) and merge the same
   base ingredient bought for different meals — potatoes for the mash and
   potatoes for frying become **one combined line, priced once**, with
   `feeds: dish A, dish B` so you can see what each purchase covers.
   Quantities combine: same unit → sum (`olive oil 2 tbsp + 3 tbsp → 5 tbsp`);
   different units → one line per unit, sharing the price quote.
   Be conservative — merge only the same purchasable product: `tomatoes` ≠
   `chopped tomatoes` (tin), `potatoes` ≠ `sweet potatoes`.
3. One basket, priced once: per-store totals summed over the merged list,
   reusing the quotes each `meals` run already returned (identical item
   names across dishes = one item, one quote). Same coverage rule as
   `bin/meals`: rank only stores that priced ≥ half of priced items;
   `← cheapest` only when coverage ties.
4. Weekly budget: with `--budget N` print the projected weekly total against
   N for the cheapest comparable store, plus a per-meal cost table and
   `£X.XX of £N.NN — under/over by £Y.YY`.
5. `--json`: machine-readable plan shape, documented in README: `dishes[]`,
   `merged_shopping_list[]` (each item: `name`, combined `qty`/`unit`,
   `used_in: [dishes]`, `shared: bool`), `quotes`, `totals_gbp`, `cheapest`,
   `weekly_total_gbp`, `budget_gbp`, `under_budget`.

**Deliverable.** `bin/mealplan` working end-to-end; a "Weekly planner"
section in README with a real example run and the `--json` shape.

**Acceptance.**
- `./bin/mealplan 'fish pie' 'mashed potatoes with tuna'` prints per-meal
  costs, per-store totals over the merged basket, and a weekly total.
- Two dishes that both use potatoes (e.g. a mash and a fried-potato dish)
  produce a **single** `potatoes` line with combined quantity and
  `feeds: <dish A>, <dish B>` — never two lines, never two prices. A marker
  shows which merged items are shared (`shared × 2 meals`) so reuse is
  visible at a glance.
- `tomatoes` and `chopped tomatoes` in the same plan stay as separate lines
  (different products), each priced separately.
- `--budget N` gives an explicit under/over verdict.
- Warm re-run reuses recipe cache hits (visible on stderr) and does not
  re-scrape; cold-cache run (`rm -rf data/`) also succeeds.
- `python3 -c "import ast; ast.parse(open('bin/mealplan').read())"` passes.
- `bin/meals` untouched — knight owns it. If a change there seems needed,
  report it instead of making it.

**Scope.** Owns `bin/mealplan` (new), optionally `lib/plan_store.py` (new,
only if you persist plans). Reads `lib/common.py` freely, but edits to it or
to `bin/meals` are off-limits for this task.

---

## Small fixups (fold into any of the above)

- `--servings` is advertised in README as "scale for more people" but
  `bin/meals` never scales quantities — they're parsed raw. Either scale by
  `servings / servings_base` (recipes.json already stores the base) or fix
  the README claim.
- **UNIT_RE eats the `l` of words after a quantity** (found by t4): the unit
  alternation matches a bare `l` (litre) inside the following word, so
  `5 large potatoes` parses as qty=5, unit=`l`, name=`arge potatoes` (same
  for `1 large handful` → `arge handful`). Add a word boundary / require the
  rest to start on a word boundary after the unit. This directly hurts
  `bin/mealplan` merging: `arge potatoes` can't be recognised as `potatoes`
  (and 5 potatoes become "5 l").
- `250 mil single cream 1 cup` → `mil` typo unrecognised, name becomes the
  whole `mil single cream 1 cup`; prose tail (`or more if you prefer...`,
  `leave out if you don't like them`, `I used 1 x 200gms packet of`) leaks
  into names, which both blocks merging and yields 0-store prices. Trim the
  name at ` or |leave out|optional|I used|– ` style separators.

- Search fallback for generic ingredients: if `site:trolley.co.uk <name>`
  yields no product URL, retry once with `<name> in water|frozen|fresh` style
  qualifiers (fixes `tuna` → cat food).
- De-duplicate repeated ingredients across the shopping list (e.g. oil twice).
- `qty` display `"2 5"` for `2 5-ounce cans` should read `2x 5-oz` or similar.
- Cache dir `data/` is git-ignored; document in README that deleting it is safe.
