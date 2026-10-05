# TECHNICAL.md — what we use from TinyFish, and why

This project has no recipe API and no price API. **TinyFish is the entire
"internet" layer** of the tool: everything we know about recipes and prices
was read from a web page at some point. This doc explains exactly which
TinyFish calls exist, where they live, and what each one does — in plain
words.

## The big picture

```
            ┌──────────────────────────────────────────────────────┐
            │  bin/meals  (the pipeline)                           │
            │                                                      │
            │  1. find a recipe      → tinyfish search + fetch     │
            │  2. price ingredients  → tinyfish search + fetch     │
            │  3. fallback pricing   → tinyfish fetch (direct)     │
            └──────────────────────────────────────────────────────┘
                                    │
                                    ▼  (subprocess)
                        tinyfish  search | fetch
```

Everything else (parsing, caching, totals) is plain stdlib Python.

## The two TinyFish subcommands we actually call

### 1. `tinyfish search` — web search

Gives us URLs for a query.

```python
# lib/common.py:60
run(["search", "query", q, "--pretty"])
return re.findall(r"https?://\S+", out)
```

- Runs as a **subprocess** with a timeout (`run()`, 60s default) — a hung
  TinyFish call must never hang the CLI.
- Output is JSON by default, but we pass `--pretty` here because we only
  want to **regex out URLs** (`https?://\S+`), not parse the JSON.
- Used for two completely different jobs:
  - **Recipe discovery** (`find_recipe`, lib/common.py:104): query is
    `"<dish> recipe"`, then we filter the URLs to recipe-ish domains
    (`bbcgoodfood`, `allrecipes`, `jamieoliver`, `seriouseats`, or any URL
    containing `recipe`) and try the first 5.
  - **Price lookup** (`price_item`, bin/meals:124): query is
    `site:trolley.co.uk <ingredient>` — a search-engine operator to only
    get product pages from the price-comparison site — then we pick the
    first URL containing `trolley.co.uk/product/`.

### 2. `tinyfish fetch` — page reader

Turns a URL into text (markdown), without a browser.

```python
# lib/common.py:65
run(["fetch", "content", "get", "--format", "markdown", url])
```

- Output is JSON like `{"results": [{"text": "...page text..."}]}`. We do
  **brace-depth counting** to slice out the first JSON object (defensive:
  drops any stray suffix on the line), `json.loads` it, and take
  `results[0].text`. If the shape is off, we return `""` — a fetch failure
  degrades to "no quote", never a crash.
- Everything goes through a **disk cache with a 12-hour TTL**
  (`data/cache/<md5(url)>.txt`, git-ignored). First run pays the network
  cost; re-runs of the same dish are near-instant and don't hammer recipe
  or trolley pages.
- Used by:
  - Recipe pages (step 1 of the pipeline).
  - Trolley.co.uk product pages, once per ingredient (step 2).
  - **Fallback pricing** (bin/meals:103): when a store didn't show up on
    trolley, we `fetch` the store's *own search URL* directly
    (`waitrose.com/.../search?...`, `iceland.co.uk/search?q=...`) and parse
    the price out of the text. This is a cheap fetch — much lighter than
    the `agent` subcommand documented in AGENT.md, which we intentionally
    don't use unless everything else fails.

## What we deliberately do *not* use

- **`tinyfish agent`** (LLM-browser automation): slow and expensive, and
  the house rule (AGENT.md) is `search` → `fetch` → `agent` in that order.
  The current pipeline never needs it.
- Any HTTP library, API key, SDK, or package install. TinyFish is the only
  thing that talks to the web, and only through `subprocess`.

## What TinyFish gives us vs. what we do ourselves

| TinyFish does | We do ourselves |
|---|---|
| Search the web, return URLs | Pick the "recipe-ish" URLs, rank tries |
| Render/fetch a page as markdown text | Parse ingredients out of the markdown (`lib/common.py:118`) |
| — | Parse prices out of trolley/store page text (regex over lines, `bin/meals:154`) |
| — | Cache: recipes in `data/recipes.json`, page texts in `data/cache/` (12h TTL) |
| — | Compare and rank stores (coverage-aware, so totals over different item subsets aren't compared) |

The split is clean: **TinyFish = get text from the internet**. Everything
after that — turning free-form page text into structured data
(`name, qty, unit`, `{store: {price, unit}}`) — is deterministic local code.

## Operational quirks worth knowing

- **Every subprocess call has a timeout** (`run()` in `lib/common.py:50`).
  On timeout or missing binary we get `""` back, which downstream code
  treats as "no data".
- **Output format**: TinyFish emits JSON by default. Raw JSON works fine
  with `json.loads` (`fetch` path); `--pretty` is only used on the
  `search` path because we regex URLs out of it instead of parsing.
- **Rate/failure reality**: occasional empty results or blocks are
  expected. Policy: retry strategy lives in the caller, and on persistent
  failure the ingredient is simply listed as `not priced` rather than
  guessed.
- **Caching is our responsibility**, not TinyFish's: URL → md5 → file, so
  the same page is fetched once per 12h window across all ingredients.
