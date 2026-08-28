# -*- coding: utf-8 -*-
"""Audit recipe image assignments."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from build_book import parse_all, recipe_image

weeks = parse_all()

# Expected image by semantic analysis of title + ingredients + steps
SEMANTIC_RULES = [
    (r"сырник", "dish-syrniki.jpg", "сырники"),
    (r"шакшук", "dish-shakshuka.jpg", "шakshuka"),
    (r"омлет|яичниц", "dish-omelette.jpg", "яйца/омлет"),
    (r"яйц\w* вкрутую на тост|тост с авокадо|гренк", "dish-avocado.jpg", "тост+яйцо/авокадо"),
    (r"тост с гауд|тост с", "dish-toast.jpg", "тост"),
    (r"йогурт|гранол", "dish-yogurt.jpg", "йогурт"),
    (r"овсяноблин|блинчик", "dish-pancakes.jpg", "блины"),
    (r"ленивая овсян|запечённая овсян|киноа-каша|овсянк", "dish-oatmeal.jpg", "каша/овсянка"),
    (r"запечённ\w* яблок", "dish-apples.jpg", "запечённые яблоки"),
    (r"творожн\w* запеканк", "dish-casserole.jpg", "творожная запеканка"),
    (r"творог|творожн\w* миск", "dish-tvorog.jpg", "творог"),
    (r"лосос\w* терияки", "dish-salmon-teriyaki.jpg", "лосось терияки"),
    (r"лосос", "dish-salmon.jpg", "лосось"),
    (r"треск", "dish-cod.jpg", "треска"),
    (r"стейк|говяж\w* стейк", "dish-steak.jpg", "стейк"),
    (r"говядин", "dish-beef.jpg", "говядина"),
    (r"индейк", "dish-turkey.jpg", "индейка"),
    (r"куриц|бёдр|курин\w* суп", "dish-chicken.jpg", "курица"),
    (r"чечевичн\w* суп", "dish-lentil-soup.jpg", "чечевичный суп"),
    (r"чечевиц", "dish-lentils.jpg", "чечевица"),
    (r"паста|спагетти|пенне", "dish-pasta.jpg", "паста"),
    (r"крем-суп|суп из батат|курин\w* суп", "dish-soup.jpg", "суп"),
    (r"свёкл", "dish-beet.jpg", "свёкла"),
    (r"нут|тахини|сумах", "dish-chickpea.jpg", "нут/тахини"),
    (r"полент", "dish-polenta.jpg", "полента"),
    (r"пюре из цветной|цветной капуст", "dish-cauliflower.jpg", "цветная капуста"),
    (r"фенхел", "dish-salmon-fennel.jpg", "лосось+фенхель"),
    (r"булгур", "dish-bulgur.jpg", "булгур"),
    (r"рис|эдамаме", "dish-rice-bowl.jpg", "рис"),
    (r"арахис", "dish-peanut-chicken.jpg", "арахисовый соус"),
    (r"батат|сладк\w* картоф", "dish-sweet-potato.jpg", "батат"),
    (r"киноа|боул", "dish-quinoa.jpg", "киноа/боул"),
]


def expected_image(recipe: dict) -> tuple[str, str]:
    blob = " ".join(
        [recipe["title"]]
        + [it for s in recipe["sections"] for it in s["items"]]
        + recipe["steps"]
    ).lower()
    for pat, img, label in SEMANTIC_RULES:
        if re.search(pat, blob):
            return img, label
    return "dish-quinoa.jpg", "fallback"


rows = []
mismatches = []
by_img = defaultdict(list)
for w in weeks:
    for d in w["days"]:
        for r in d["recipes"]:
            cur = recipe_image(r["title"]).split("/")[-1]
            exp, reason = expected_image(r)
            by_img[cur].append(r["title"])
            ok = cur == exp
            row = {
                "week": w["num"],
                "day": d["num"],
                "meal": r["meal"],
                "title": r["title"],
                "current": cur,
                "expected": exp,
                "reason": reason,
                "ok": ok,
            }
            rows.append(row)
            if not ok:
                mismatches.append(row)

out = Path("_audit_report.txt")
lines = [
    f"TOTAL: {len(rows)} recipes",
    f"MISMATCHES: {len(mismatches)}",
    "",
    "=== MISMATCHES ===",
]
for m in mismatches:
    lines.append(
        f"W{m['week']} D{m['day']} {m['meal']}: {m['title'][:70]}\n"
        f"  current:  {m['current']}\n"
        f"  expected: {m['expected']} ({m['reason']})"
    )
lines += ["", "=== IMAGE USAGE ==="]
for img, titles in sorted(by_img.items(), key=lambda x: -len(x[1])):
    lines.append(f"{img}: {len(titles)} recipes")
    for t in titles[:3]:
        lines.append(f"  - {t[:65]}")
    if len(titles) > 3:
        lines.append(f"  ... +{len(titles)-3} more")

out.write_text("\n".join(lines), encoding="utf-8")
Path("_audit.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

needed = sorted({m["expected"] for m in mismatches} | {m["current"] for m in mismatches})
existing = {p.name for p in Path("img").glob("*.jpg")}
missing = sorted(set(needed) - existing - {"header-vegetables.jpg"})
print(f"mismatches={len(mismatches)}")
print("missing images:", missing)
print("unique expected images:", len(set(r['expected'] for r in rows)))
