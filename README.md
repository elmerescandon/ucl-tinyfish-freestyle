# ucl-tinyfish-freestyle

A tiny meal planner. Ask it for a dish, it finds a recipe online, turns it
into a shopping list, and prices it across UK supermarkets — then tells you
which store is cheapest.

## Quick start

```bash
./bin/meals 'mashed potatoes with tuna'
```

That's it. You'll get the recipe, the shopping list, and a price comparison
like:

```
Tesco        £7.80
Aldi         £6.20   ← cheapest
Sainsbury's  £9.10
not priced: salt, black pepper
```

A couple of useful flags:

```bash
./bin/meals 'mashed potatoes with tuna' --servings 4   # scale for more people
./bin/meals 'mashed potatoes with tuna' --json        # machine-readable output
```

## Recipe cache

Recipes don't change often, so after the first run they're saved on disk.
The next time you ask for the same dish, the recipe lookup is instant:

```bash
./bin/meals 'mashed potatoes with tuna'   # first run: recipe: fetched
./bin/meals 'mashed potatoes with tuna'   # next run: recipe: cache hit (much faster)
```

There's a small tool to browse and manage the saved recipes:

```bash
./bin/recipes list                          # what's saved so far
./bin/recipes get 'mashed potatoes with tuna'  # see the full stored recipe
./bin/recipes rm 'mashed potatoes with tuna'   # forget it
./bin/recipes cache 'fish pie'              # save a recipe in advance
```

If `meals` ever picks up a stale recipe, run it with `--no-cache` to
re-fetch it fresh.

## Weekly planner

One dish per run is fine for tonight; for the week there's `bin/mealplan`.
Give it several dishes and it plans them as one basket — shared ingredients
are bought **once**:

```bash
./bin/mealplan 'fish pie' 'mashed potatoes with tuna' --budget 30
```

What you get:

- Per-meal reference cost (what each dish would cost on its own), then
  **one merged basket**: potatoes for the mash and potatoes for frying are a
  single line with a combined quantity (`500 g + ½ pound → 727 g`), priced
  once, marked `shared ×2 meals — feeds: <dish A>, <dish B>`.
- Merging is deliberately conservative: same product only. `tomatoes` and
  `chopped tomatoes` (a tin) stay separate; so do `potatoes` and `sweet
  potatoes`. Variety/cut words do merge (`yukon gold potatoes` = `potatoes`,
  `free-range eggs` = `eggs`), and units are converted where safe
  (`½ pound` + `500 g`, `tbsp` + `ml`).
- Per-store totals over the merged basket with the same coverage rule as
  `meals` (a store is only ranked if it priced at least half the items), a
  projected weekly total from the cheapest comparable store, and against
  `--budget N`: `£31.58 of £30.00 — over by £1.58`.

Machine-readable plan with `--json`: `dishes[]`, `merged_shopping_list[]`
(each item: `name`, combined `qty`/`unit`, `used_in`, `shared`), `quotes`,
`totals_gbp`, `cheapest`, `weekly_total_gbp`, `budget_gbp`, `under_budget`.

Notes: `--servings` and `--no-cache` pass through to `meals` for every dish;
a dish whose recipe can't be found is skipped with a warning and the plan
covers the rest; re-runs reuse the recipe/price caches, so planning the same
week twice is fast.

## Output

By default the human summary goes to stdout: a per-item × per-store price
table (unit prices in parentheses), store totals with item counts
(`Tesco £7.80 (3/11 items)`), and `not priced` items with a suggested
next-step query. A store is only ranked if it priced at least half of the
priced items, and `← cheapest` only appears when at least two ranked
stores covered the same number of items — totals over different item
subsets aren't comparable. Pass `--json` for the machine-readable dump
(same shape, plus `coverage` and `coverage_threshold`).

## Supermarkets covered

Tesco, Sainsbury's, Aldi, Lidl, Waitrose, and a couple of others that show
up on price pages. There are no official price APIs anywhere, so prices
come from public product pages — occasionally an item can't be found and
it's listed as `not priced` instead of guessed.

Prices are also cached on disk, so re-running the same dish doesn't
re-scrape everything.

## Status

Recipe search, ingredient parsing, and pricing all work end-to-end. The
meal-plan output is still simplified — one recipe is picked per dish, and
-cheapest logic is coverage-aware but price sources are still
trolley.co.uk-only.
