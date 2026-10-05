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
-cheapest logic is currently best-effort.
