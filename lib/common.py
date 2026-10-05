"""common - helpers shared by bin/meals, bin/recipes.

Rules (see AGENT.md): helpers moved here verbatim from bin/meals; thin
wrappers remain in bin/meals. stdlib only.
"""

import json
import re
import subprocess
import time

UNIT_RE = re.compile(
    r"^(?P<q1>\d+\s+\d*[\/\d]*)?(?P<q2>[\d\/.½¼¾⅓⅔⅛⅜⅝⅞]+)?\s*"
    r"(?P<u>ounces?|oz|pounds?|lbs?|cups?|tablespoons?|tbsp|teaspoons?|tsp|"
    r"g|kg|ml|l|litre[s]?|cans?|tins?|packs?|pack|cloves?|sticks?|sheets?|slices?)?\s*(?P<rest>.+)$"
)
PREP_WORDS = re.compile(
    r"\b(peeled|peel|chopped|finely|roughly|drained|divided|packed|"
    r"cut into|plus more|for serving|for dipping|for garnish|to taste|deseeded|"
    r"cubed|sliced|grated|ground|boiled|mashed|at room temp)\b"
)
LEAD_MEASURE = re.compile(
    r"^(?:cans?|tins?|packs?|pack(?:et)?s?|ounces?|oz|cups?|tablespoons?|tbsp|"
    r"teaspoons?|tsp|cloves?|sheets?|sticks?|slices?|large|small|medium)\s+"
)
HYPHEN_UNIT = re.compile(r"(\d)\s*-\s*(ounce|oz|pound|lb|gram|kg|ml|litre|cup|tablespoon|tbsp|teaspoon|tsp)s?\b")


def _cut_prep_words(name):
    matches = list(PREP_WORDS.finditer(name))
    if not matches:
        return name
    m0 = matches[0]
    if m0.start() > 0:
        return name[: m0.start()]
    if len(matches) > 1:
        return name[m0.end(): matches[1].start()]
    return name[m0.end():]


def _strip_leading_measures(name):
    for _ in range(4):
        stripped = LEAD_MEASURE.sub("", name, count=1).strip()
        if stripped == name:
            break
        name = stripped
    return name


def run(args, timeout=60):
    try:
        p = subprocess.run(
            ["tinyfish"] + args, capture_output=True, text=True, timeout=timeout
        )
        return p.stdout or ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def search(q):
    out = run(["search", "query", q, "--pretty"])
    return re.findall(r"https?://\S+", out)


def fetch_text(url):
    # tiny disk cache (TTL 12h) so re-runs don't re-hit trolley/recipe pages
    import hashlib, os

    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    key = hashlib.md5(url.encode()).hexdigest()
    path = os.path.join(cache_dir, key + ".txt")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < 12 * 3600:
        with open(path) as f:
            return f.read()

    out = run(["fetch", "content", "get", "--format", "markdown", url])
    try:
        i = out.find('{"results"')
        if i < 0:
            return ""
        # keep only the first JSON object on the line ( defensively drop stray suffixes )
        depth = 0
        end = len(out)
        for j in range(i, len(out)):
            if out[j] == "{":
                depth += 1
            elif out[j] == "}":
                depth -= 1
                if depth == 0:
                    end = j + 1
                    break
        data = json.loads(out[i:end])
        results = data.get("results", [])
        text = results[0].get("text", "") if results else ""
        if text:
            with open(path, "w") as f:
                f.write(text)
        return text
    except Exception:
        return ""


def find_recipe(dish):
    for url in search(f"{dish} recipe")[:5]:
        if any(k in url for k in ("recipe", "bbcgoodfood", "allrecipes", "jamieoliver", "seriouseats")):
            text = fetch_text(url)
            if extract_ingredients(text):
                return url, extract_title(text) or dish, extract_ingredients(text)
    return dish, dish, []


def extract_title(text):
    m = re.search(r"^# (.+)$", text, re.M)
    return m.group(1).strip() if m else None


def extract_ingredients(text):
    lines = text.split("\n")
    start = None
    for i, l in enumerate(lines):
        if re.match(r"^#{0,4}\s*\**ingredients\**\s*$", l.strip(), re.I):
            start = i + 1
            break
    if start is None:
        return []
    items = []
    for l in lines[start:]:
        s = l.strip()
        if re.match(r"^#", s):
            break
        s = re.sub(r"^[*\-•]\s*", "", s).replace("▢", " ").strip()
        if not s or s.startswith("!"):
            continue
        if s.startswith("**"):  # prose explanantions, not quantities
            continue
        items.append(s)
    # preference: keep lines that start with a quantity if any exist
    with_qty = [i for i in items if UNIT_RE.match(i)]
    return with_qty if with_qty else items


def clean_item(line):
    line = HYPHEN_UNIT.sub(r"\1 \2 ", line)
    m = UNIT_RE.match(line)
    if m:
        qty = (m.group("q1") or m.group("q2") or "")
        unit = (m.group("u") or "").lower()
        name = m.group("rest").strip()
    else:
        qty, unit, name = "", "", line.strip()
    name = _cut_prep_words(name)
    name = _strip_leading_measures(name)
    name = name.strip(" -,:")
    return (name or line.strip(" -,:")), qty.strip(), unit
