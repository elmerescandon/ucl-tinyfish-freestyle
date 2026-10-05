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
| Morrisons | ✅ but query dropped | untested | — | names stripped, redirected to /categories |
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

## Small fixups (fold into any of the above)

- Search fallback for generic ingredients: if `site:trolley.co.uk <name>`
  yields no product URL, retry once with `<name> in water|frozen|fresh` style
  qualifiers (fixes `tuna` → cat food).
- De-duplicate repeated ingredients across the shopping list (e.g. oil twice).
- `qty` display `"2 5"` for `2 5-ounce cans` should read `2x 5-oz` or similar.
- Cache dir `data/` is git-ignored; document in README that deleting it is safe.
