# ucl-tinyfish-freestyle

Recipe + weekly meal planner that prices your shopping list across UK
supermarkets. There is no official price API at any of the stores we
target, so we use [TinyFish](https://tinyfish.ai) for web search, page
fetching, and browser automation against the public online catalogues.

## What it does

Give it a request like "5 dinners for 2, pescatarian, budget £60" and it returns:

1. A weekly meal plan (recipes found online, matching your constraints)
2. A consolidated shopping list (ingredients merged across recipes)
3. Prices for every item at each supermarket it supports
4. Per-store basket totals and the cheapest option

## Supermarkets

All scraped via their public online product pages (shelf prices, no
loyalty pricing, no accounts):

| Store | Source | Notes |
|---|---|---|
| Tesco | tesco.com | Full online catalogue |
| Sainsbury's | sainsburys.co.uk | Full online catalogue |
| Aldi | aldi.co.uk | Catalogue is online; shopping is in-store only |
| Lidl | lidl.co.uk | Smallest online catalogue; partial coverage |
| Waitrose | waitrose.com | Full online catalogue |

Matching across stores is best-effort: we compare on product name,
size, and unit price (£/kg, £/l, p/100g). Discounters' own-brand items
may have no direct equivalent — unmatched items are flagged, not guessed.

## Pipeline

```
request → find recipes → parse ingredients → consolidate shopping list
        → price each item at each store (TinyFish agent batch)
        → totals per store → cheapest store + plan + list
```

Tools used, lightest first:

- `tinyfish search` — find recipes matching the request
- `tinyfish fetch` — read recipe pages, extract ingredients
- `tinyfish agent run` — per item × per store: run the store's product
  search, extract `{name, price, unit_price, url}` as JSON
- `tinyfish agent batch` — fan the item × store grid out from a CSV

Prices are cached in `data/` (keyed by store + product query + date)
so re-running a plan does not re-scrape.

## Input contract

```json
{
  "meals": 5,
  "servings": 2,
  "diet": "pescatarian",
  "budget_gbp": 60
}
```

Only `meals` is required. `diet` accepts any recipe-search string
(e.g. `vegetarian`, `vegan`, `gluten-free`). `budget_gbp` is a soft
target, checked against the cheapest store's total.

## Output contract

```json
{
  "week": [{ "day": "Mon", "meal": "...", "recipe_url": "..." }],
  "shopping_list": [{ "item": "chickpeas", "qty": "2x400g tins" }],
  "prices": {
    "tesco":   [{ "item": "chickpeas", "match": "...", "price": 0.55, "unit_price": "£0.14/100g", "url": "..." }],
    "sainsburys": ["..."],
    "aldi": ["..."],
    "lidl": ["..."],
    "waitrose": ["..."]
  },
  "totals_gbp": { "tesco": 0, "sainsburys": 0, "aldi": 0, "lidl": 0, "waitrose": 0 },
  "cheapest": null
}
```

## Status

Scope defined. Recipe search/parse pipeline first, then price scraping
against one store, then the full grid.
