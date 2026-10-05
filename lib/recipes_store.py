"""recipes_store - persistent recipe store shared by bin/meals and bin/recipes.

Shape: data/recipes.json
  { "<dish>": {title, url, servings_base, ingredients: [{raw, name, qty, unit}], cached_at} }
"""

import json
import os

RECIPES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "recipes.json"
)


def load_recipes():
    try:
        with open(RECIPES_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_recipes(dish, recipe):
    recipes = load_recipes()
    recipes[dish] = recipe
    with open(RECIPES_PATH, "w") as f:
        json.dump(recipes, f, indent=2, ensure_ascii=False)
    return recipes
