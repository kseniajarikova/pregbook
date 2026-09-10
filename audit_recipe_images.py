#!/usr/bin/env python3
"""Check the recipe-card -> image contract used by the static book."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "index.html"


class RecipeParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.recipes = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and "recipe" in attrs.get("class", "").split():
            self.current = {"id": attrs.get("id", ""), "name": attrs.get("data-name", "")}

    def handle_endtag(self, tag):
        if tag == "article" and self.current is not None:
            self.recipes.append(self.current)
            self.current = None


ADDITIONS = {
    "d14-lunch": ("свёкла", "салат"),
    "d19-lunch": ("бурый рис", "капуста", "яблоко"),
    "d22-lunch": ("тыквенное пюре", "свёкла"),
    "d35-dinner": ("нут", "печёные овощи", "тахини"),
}


def normalize(value):
    return re.sub(r"\s+", " ", value.lower().replace("ё", "е")).strip()


def audit():
    parser = RecipeParser()
    parser.feed(HTML.read_text(encoding="utf-8"))
    recipes = parser.recipes
    paths = [f"img/recipes/{r['id']}.jpg" for r in recipes]
    counts = Counter(paths)
    failures = []
    checklist = []

    if "img/recipes/${recipe.id}.jpg" not in HTML.read_text(encoding="utf-8"):
        failures.append("runtime image override is missing")
    if len(recipes) != 105:
        failures.append(f"expected 105 recipe cards, found {len(recipes)}")

    for recipe, path in zip(recipes, paths):
        issues = []
        image_path = ROOT / path
        if not recipe["id"] or not recipe["name"]:
            issues.append("missing recipe id or name")
        if not image_path.is_file():
            issues.append("image file is missing")
        else:
            try:
                with Image.open(image_path) as image:
                    image.verify()
            except Exception as exc:
                issues.append(f"unreadable image: {exc}")
        if counts[path] != 1:
            issues.append("image path is reused")
        checklist.append({
            "id": recipe["id"],
            "file": path,
            "subject": [normalize(recipe["name"]), *map(normalize, ADDITIONS.get(recipe["id"], ()))],
        })
        if issues:
            failures.append(f"{recipe['id']}: " + "; ".join(issues))

    return {
        "recipe_count": len(recipes),
        "unique_image_paths": len(set(paths)),
        "failures": failures,
        "visual_checklist": checklist,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Рецептов: {result['recipe_count']}")
        print(f"Уникальных изображений: {result['unique_image_paths']}")
        print(f"Ошибок: {len(result['failures'])}")
        for failure in result["failures"]:
            print(f"- {failure}")
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
