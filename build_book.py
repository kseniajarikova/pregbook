# -*- coding: utf-8 -*-
"""Parse the DOCX extract and build a 5-week recipe book HTML."""
from __future__ import annotations

import html
import io
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
EXTRACT = Path(r"c:\Users\user\Desktop\апп\docx-extract.txt")
ASSETS = Path(r"C:\Users\user\.cursor\projects\c-Users-user-Desktop\assets")
IMG_DIR = ROOT / "img"
OUT_HTML = ROOT / "index.html"
OUT_JSON = ROOT / "recipes.json"

WEEKDAYS = {
    "понедельник": "пн",
    "вторник": "вт",
    "среда": "ср",
    "четверг": "чт",
    "пятница": "пт",
    "суббота": "сб",
    "воскресенье": "вс",
}
MEAL_SLUG = {"Завтрак": "breakfast", "Обед": "lunch", "Ужин": "dinner"}
MEAL_ORDER = ["Завтрак", "Обед", "Ужин"]
CATS = [
    "Мясо и рыба",
    "Яйца и молочные продукты",
    "Крупы, злаки и хлеб",
    "Овощи",
    "Фрукты и ягоды",
    "Фрукты",
    "Бобовые и консервы",
    "Бобовые, консервы и заморозка",
    "Масла, соусы и специи",
    "Орехи и семечки",
    "Свежая зелень",
]
CAT_RE = re.compile(r"^(" + "|".join(re.escape(c) for c in CATS) + r")\s*:?\s*$")
WEEK_RE = re.compile(r"^НЕДЕЛЯ\s+(\d+)", re.I)
DAY_RE = re.compile(r"^День\s+(\d+)\.?\s*(.*)$")
MEAL_RE = re.compile(r"^(Завтрак|Обед|Ужин)(?:\s*[—–-]\s*(.*))?$")
SHOP_RE = re.compile(r"^СПИСОК ПОКУПОК")

IMAGE_RULES = [
    (r"боул с киноа, авокадо", "dish-quinoa.jpg"),
    (r"глазурью из мисо", "dish-salmon-miso.jpg"),
    (r"лосось.*фенхел", "dish-salmon-fennel.jpg"),
    (r"лосось.*тыквен|тыквенное пюре", "dish-salmon-pumpkin-beet.jpg"),
    (r"лосось с кунжутом", "dish-salmon-sesame.jpg"),
    (r"лосось терияки", "dish-salmon.jpg"),
    (r"лосос", "dish-salmon.jpg"),
    (r"говядина запечённая", "dish-beef.jpg"),
    (r"чернослив", "dish-beef-polenta.jpg"),
    (r"говядина.*гриб", "dish-beef-mushroom-polenta.jpg"),
    (r"стейк", "dish-steak-mash.jpg"),
    (r"говядина.*перцем.*булгур", "dish-beef-bulgur.jpg"),
    (r"говядина, тушёная с томатами", "dish-beef-quinoa.jpg"),
    (r"стейк|говядин", "dish-beef.jpg"),
    (r"куриные бёдра с апельсином|курица с апельсином", "dish-chicken-cauliflower.jpg"),
    (r"курица с цветной капустой", "dish-chicken-curry.jpg"),
    (r"куриные бёдра с чесноком", "dish-chicken-cauliflower.jpg"),
    (r"куриные бёдра с лимоном|курица с лимоном", "dish-chicken-capers-potato.jpg"),
    (r"куриные бёдра в соусе из арахиса|курица в арахисовом", "dish-chicken-peanut-rice.jpg"),
    (r"куриные бёдра с медово", "dish-chicken.jpg"),
    (r"куриный суп", "dish-chicken-noodle.jpg"),
    (r"индейк", "dish-turkey-bulgur.jpg"),
    (r"куриц|бёдр", "dish-chicken.jpg"),
    (r"треска в томатах", "dish-cod-tomato-rice.jpg"),
    (r"треска с соусом из каперсов|треска с каперсным", "dish-cod-capers.jpg"),
    (r"треск", "dish-cod.jpg"),
    (r"крем-суп из цветной", "dish-cauliflower-soup.jpg"),
    (r"чечевичный суп", "dish-lentil-soup.jpg"),
    (r"крем-суп из батата", "dish-sweet-potato-soup.jpg"),
    (r"суп|крем-суп", "dish-soup.jpg"),
    (r"киноа-каша", "dish-quinoa-porridge.jpg"),
    (r"овсяноблин", "dish-oat-pancake.jpg"),
    (r"запечённая овсянка", "dish-baked-oats-blueberry.jpg"),
    (r"овсянка с ягодами", "dish-oatmeal-berries.jpg"),
    (r"ленивая овсянка с бананом", "dish-overnight-oats-banana.jpg"),
    (r"сырники с яблочным", "dish-syrniki-apple.jpg"),
    (r"йогурт с гранолой, бананом", "dish-yogurt-banana.jpg"),
    (r"яичниц", "dish-fried-eggs-tomato.jpg"),
    (r"блинчики цельнозерновые", "dish-wholegrain-pancakes.jpg"),
    (r"творожная запеканка", "dish-cottage-casserole.jpg"),
    (r"творожная миска с грушей и грецкими", "dish-cottage-pear-walnut.jpg"),
    (r"яйца со шпинатом", "dish-spinach-toast.jpg"),
    (r"сырник", "dish-syrniki.jpg"),
    (r"шакшук", "dish-shakshuka.jpg"),
    (r"омлет", "dish-omelette.jpg"),
    (r"йогурт|гранол", "dish-yogurt.jpg"),
    (r"запечённ\w* яблок", "dish-apples.jpg"),
    (r"творожн|творог", "dish-tvorog.jpg"),
    (r"авокадо", "dish-avocado.jpg"),
    (r"тост|гренк", "dish-toast.jpg"),
    (r"чечевиц", "dish-lentils.jpg"),
    (r"паста", "dish-pasta.jpg"),
    (r"свёкл", "dish-beet.jpg"),
    (r"нут", "dish-chickpea.jpg"),
    (r"киноа|боул", "dish-quinoa.jpg"),
]


def compress_images() -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    mapping = {"cover-breakfast.jpg": "dish-toast.jpg"}
    sources = list(ASSETS.glob("dish-*.jpg")) + [ASSETS / "cover-breakfast.jpg"]
    for src in sources:
        if not src.exists():
            continue
        name = mapping.get(src.name, src.name)
        dst = IMG_DIR / name
        im = Image.open(src).convert("RGB")
        im.thumbnail((880, 880), Image.Resampling.LANCZOS)
        saved = False
        for q in range(78, 38, -4):
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
            if buf.tell() <= 280_000:
                dst.write_bytes(buf.getvalue())
                saved = True
                break
        if not saved:
            im.thumbnail((720, 720), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=55, optimize=True, progressive=True)
            dst.write_bytes(buf.getvalue())
        print(f"  {name}: {dst.stat().st_size // 1024} KB")


def split_weeks(lines: list[str]) -> list[dict]:
    weeks, current = [], None
    for line in lines:
        m = WEEK_RE.match(line)
        if m:
            if current:
                weeks.append(current)
            current = {"num": int(m.group(1)), "lines": [line]}
        elif current:
            current["lines"].append(line)
    if current:
        weeks.append(current)
    return weeks


def split_time(title: str) -> tuple[str, str | None]:
    title = re.sub(r"\s*⏱", " ⏱", title)
    m = re.search(r"⏱\s*(.+)$", title)
    if m:
        return title[: m.start()].strip(" —–-"), m.group(1).strip()
    return title.strip(), None


def parse_toc(lines: list[str]) -> list[dict]:
    days = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i].strip()
        if not line or line in {"День", "Завтрак", "Обед", "Ужин"}:
            i += 1
            continue
        m = DAY_RE.match(line)
        if not m:
            i += 1
            continue
        num = int(m.group(1))
        weekday = m.group(2).strip(" .")
        i += 1
        if not weekday and i < n and lines[i].strip().lower() in WEEKDAYS:
            weekday = lines[i].strip()
            i += 1
        meals = []
        while len(meals) < 3 and i < n:
            nxt = lines[i].strip()
            if not nxt or DAY_RE.match(nxt) or SHOP_RE.match(nxt) or WEEK_RE.match(nxt):
                break
            if nxt.lower() in WEEKDAYS:
                weekday = nxt
                i += 1
                continue
            meals.append(nxt)
            i += 1
        days.append(
            {
                "num": num,
                "weekday": weekday,
                "weekday_short": WEEKDAYS.get(weekday.lower(), ""),
                "meals": meals,
            }
        )
    return days


def parse_shop(lines: list[str]) -> list[dict]:
    cats: list[dict] = []
    current = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        cm = CAT_RE.match(line.rstrip(":"))
        if not cm:
            cm = CAT_RE.match(line)
        if cm or (line.rstrip(":") in CATS):
            name = line.rstrip(":").strip()
            current = {"name": name, "items": []}
            cats.append(current)
            continue
        if current is None:
            current = {"name": "Продукты", "items": []}
            cats.append(current)
        item = line.lstrip("·•- ").strip().rstrip(";.")
        if item:
            current["items"].append(item)
    return cats


def looks_like_new_block(line: str) -> bool:
    return bool(
        MEAL_RE.match(line)
        or DAY_RE.match(line)
        or WEEK_RE.match(line)
        or SHOP_RE.match(line)
    )


def parse_meal(lines: list[str], i: int) -> tuple[dict, int]:
    m = MEAL_RE.match(lines[i].strip())
    meal = m.group(1)
    rest = (m.group(2) or "").strip()
    i += 1
    n = len(lines)
    if not rest:
        while i < n and not lines[i].strip():
            i += 1
        rest = lines[i].strip()
        i += 1
    title, time = split_time(rest)
    while i < n and not lines[i].strip():
        i += 1
    if i < n and lines[i].strip().startswith("⏱"):
        time = lines[i].strip().replace("⏱", "").strip()
        i += 1

    sections: list[dict] = []
    steps: list[str] = []
    leftover: list[str] = []
    notes: list[str] = []

    while i < n and not lines[i].strip():
        i += 1

    if i < n and lines[i].strip().startswith("Ингредиенты"):
        head = lines[i].strip()
        after = head.split(":", 1)[1].strip() if ":" in head else ""
        current_name = "Ингредиенты"
        current_items: list[str] = []
        if after:
            current_items.append(after.rstrip(";."))
        i += 1
        while i < n:
            raw = lines[i].strip()
            if not raw:
                i += 1
                continue
            if raw.startswith("Приготовление") or looks_like_new_block(raw):
                break
            if raw.startswith("Для ") and raw.endswith(":"):
                current_name = raw[:-1]
                current_items = []
                i += 1
                continue
            current_items.append(raw.lstrip("·•- ").rstrip(";."))
            i += 1
        if current_items:
            sections.append({"name": current_name, "items": current_items})

    # Keep garnish/sub-recipe labels out of ingredient bullet lists.
    normalized_sections: list[dict] = []
    for section in sections:
        current = {"name": section["name"], "items": []}
        for item in section["items"]:
            marker = item.strip().rstrip(":").lower()
            if marker in {"на гарнир", "для гарнира"}:
                if current["items"]:
                    normalized_sections.append(current)
                current = {"name": "На гарнир", "items": []}
            else:
                current["items"].append(item)
        if current["items"]:
            normalized_sections.append(current)
    sections = normalized_sections

    while i < n and not lines[i].strip():
        i += 1

    leftover_mode = False
    if i < n and lines[i].strip().startswith("Приготовление"):
        head = lines[i].strip()
        after = head.split(":", 1)[1].strip() if ":" in head else ""
        if after:
            steps.append(after.rstrip("."))
        i += 1
        while i < n:
            raw = lines[i].strip()
            if not raw:
                i += 1
                continue
            if looks_like_new_block(raw) and not raw.startswith("Для "):
                break
            if raw.startswith("!"):
                notes.append(raw.lstrip("! ").strip())
                leftover_mode = False
                i += 1
                continue
            if raw.startswith("Оставить") or raw.startswith("Отложить"):
                leftover_mode = True
                leftover.append(raw.rstrip(":"))
                i += 1
                continue
            if leftover_mode:
                leftover.append(raw.rstrip(";."))
                i += 1
                continue
            steps.append(raw)
            i += 1

    blob = " ".join(
        [title]
        + [it for s in sections for it in s["items"]]
        + steps
    ).lower()
    leftover_flag = "готовили" in blob
    return {
        "meal": meal,
        "slug": MEAL_SLUG[meal],
        "title": title,
        "time": time or ("10 минут" if leftover_flag else ""),
        "sections": sections,
        "steps": steps,
        "leftover": leftover,
        "notes": notes,
        "is_leftover": leftover_flag,
    }, i


def parse_recipes(lines: list[str]) -> list[dict]:
    days: list[dict] = []
    i, n = 0, len(lines)
    current = None
    while i < n:
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        dm = DAY_RE.match(line)
        if dm:
            weekday = dm.group(2).strip(" .")
            current = {
                "num": int(dm.group(1)),
                "weekday": weekday,
                "weekday_short": WEEKDAYS.get(weekday.lower(), ""),
                "recipes": [],
            }
            days.append(current)
            i += 1
            continue
        if MEAL_RE.match(line) and current is not None:
            meal, i = parse_meal(lines, i)
            current["recipes"].append(meal)
            continue
        i += 1
    return days


def recipe_image(title: str) -> str:
    t = title.lower()
    for pat, name in IMAGE_RULES:
        if re.search(pat, t):
            return f"img/{name}"
    return "img/dish-quinoa.jpg"


def safety_note(recipe: dict) -> str | None:
    blob = " ".join(
        [recipe["title"]]
        + [it for s in recipe["sections"] for it in s["items"]]
        + recipe["steps"]
        + recipe["notes"]
    ).lower()
    bits = []
    if any(w in blob for w in ("яйц", "омлет", "яичниц", "шакшук")):
        bits.append("яйца готовить полностью — желток и белок должны схватиться")
    if any(w in blob for w in ("лосос", "треск", "рыб")):
        bits.append("рыбу готовить полностью, без сырой и слабосолёной")
    if any(w in blob for w in ("куриц", "индейк", "бёдр")):
        bits.append("птицу готовить полностью — сок должен быть прозрачным")
    if "стейк" in blob:
        bits.append(
            "для курса беременных не использовать формулировку «желаемая прожарка»: "
            "согласовать с профильным редактором безопасную внутреннюю температуру и "
            "готовить с термометром"
        )
    if not bits:
        return None
    return "Важно при беременности: " + "; ".join(bits) + "."


def apply_editorial_overrides(days: list[dict]) -> None:
    for day in days:
        if day["num"] != 8:
            continue
        for recipe in day["recipes"]:
            title = recipe["title"].lower()
            if recipe["meal"] != "Ужин" or "харисс" not in title:
                continue

            for section in recipe["sections"]:
                items = []
                for item in section["items"]:
                    lower = item.lower()
                    if lower.startswith("зира") or lower.startswith("чеснок"):
                        continue
                    if lower.startswith("курин"):
                        item = "куриные бёдра без кости — 500 г"
                    elif lower.startswith("харисса"):
                        item = (
                            "харисса — 2 ст. л. ("
                            "готовая или домашняя: измельчённые хлопья чили, зира, "
                            "кориандр, сухой чеснок и паприка)"
                        )
                    elif lower.startswith("батат"):
                        item = "батат — 500 г"
                    items.append(item)
                section["items"] = items

            recipe["steps"] = [
                "Курицу смешать с хариссой, солью и 1 ст. л. масла. Оставить мариноваться 20 минут.",
                "Красный лук нарезать тонкими кольцами, залить уксусом, сахаром и щепоткой соли. Оставить на 20 минут.",
                "Батат очистить, нарезать дольками, смешать с оставшимся маслом, посолить.",
                "Разогреть духовку до 200 °C.",
                "Батат выложить на противень, запекать 15 минут.",
                "Добавить курицу на противень к батату, запекать ещё 30 минут до полной готовности.",
                "Йогурт смешать с рубленой зеленью и щепоткой соли.",
                "Подавать курицу с бататом, маринованным луком, йогуртовым соусом и зеленью.",
            ]


def apply_manual_overrides(weeks: list[dict]) -> None:
    """Keep the checked corrections in the generated source as well as in index.html."""
    def recipe(day_num: int, meal: str) -> dict | None:
        for week in weeks:
            for day in week["days"]:
                if day["num"] == day_num:
                    return next((r for r in day["recipes"] if r["meal"] == meal), None)
        return None

    d14_lunch = recipe(14, "Обед")
    if d14_lunch and "салат со свёклой" not in d14_lunch["title"].lower():
        d14_lunch["title"] += ", салат со свёклой"
    d19_lunch = recipe(19, "Обед")
    if d19_lunch:
        d19_lunch["title"] = d19_lunch["title"].replace("картофелем", "бурым рисом")
    d19_dinner = recipe(19, "Ужин")
    if d19_dinner and "киноа" not in d19_dinner["title"].lower():
        d19_dinner["title"] += ", киноа"
    if d19_dinner:
        d19_dinner["steps"] = [
            s.replace("150 г киноа", "100 г киноа").replace("300 мл кипятка", "200 мл кипятка")
            for s in d19_dinner["steps"]
        ]
    d20_lunch = recipe(20, "Обед")
    if d20_lunch:
        d20_lunch["steps"] = [s.replace("Картофель", "Киноа") for s in d20_lunch["steps"]]
    d35_dinner = recipe(35, "Ужин")
    if d35_dinner:
        d35_dinner["title"] = "боул с киноа, нутом, печёными овощами и соусом тахини"
    d34_breakfast = recipe(34, "Завтрак")
    if d34_breakfast:
        d34_breakfast["steps"] = [
            "Яйца взбить с молоком и щепоткой соли.",
            "Просеять муку, постепенно вмешать в яично-молочную смесь.",
            "Добавить растопленное масло. Тесто должно быть жидким — жиже сметаны.",
            "Оставить тесто на 15 минут — клейковина набухнет, и блины будут эластичнее.",
            "Творог смешать с мёдом, ванилью и апельсиновой цедрой до однородности.",
            "Разогреть сковороду, смазать тонким слоем масла.",
            "Налить тонкий слой теста, распределить по всей сковороде.",
            "Жарить 1,5–2 минуты с первой стороны и 1 минуту со второй.",
            "Выложить на блин ложку творожной начинки, завернуть или сложить треугольником.",
            "По желанию добавить ломтики апельсина при подаче.",
        ]
        d34_breakfast["leftover"] = []

    for week in weeks:
        for toc in week["toc"]:
            if toc["num"] == 18 and len(toc["meals"]) >= 3:
                toc["meals"][2] = "Треска в томатах с оливками, каперсами и бурым рисом"
            elif toc["num"] == 19 and len(toc["meals"]) >= 3:
                toc["meals"][1] = "Треска с томатами и бурым рисом, салат из капусты с яблоком"
                toc["meals"][2] = "Говядина, тушёная с томатами, чесноком и розмарином, киноа"
            elif toc["num"] == 14 and len(toc["meals"]) >= 2:
                toc["meals"][1] = "Курица с цветной капустой, салат со свёклой"

    for day_num, meal in ((8, "Ужин"), (13, "Ужин")):
        r = recipe(day_num, meal)
        if not r:
            continue
        r["leftover"] = [
            text.replace("батат — 150 г", "батат — 100 г")
            .replace("цветная капуста с соусом — 150 г", "цветная капуста с соусом — 100 г")
            for text in r["leftover"]
        ]

    for r in (recipe(18, "Обед"), recipe(26, "Обед"), recipe(32, "Обед")):
        if not r:
            continue
        r["steps"] = [
            (s[:1].upper() + s[1:] if s else s).replace("воды если", "воды, если")
            for s in r["steps"]
        ]
    d20_dinner = recipe(20, "Ужин")
    if d20_dinner:
        seen_smooth = False
        cleaned = []
        for step in d20_dinner["steps"]:
            if "Пробить погружным блендером до абсолютно гладкой консистенции" in step:
                if seen_smooth:
                    step = "Проверить консистенцию и при необходимости добавить немного сливок."
                seen_smooth = True
            cleaned.append(step)
        d20_dinner["steps"] = cleaned

    d2_dinner = recipe(2, "Ужин")
    if d2_dinner:
        for section in d2_dinner["sections"]:
            section["items"] = [
                "говяжий бульон — 400 мл (или вода)"
                if item.lower().startswith("говяжий бульон")
                else item
                for item in section["items"]
            ]
        broth_note = (
            "Бульон можно взять готовый, заменить водой или сварить самостоятельно "
            "из свежих овощей и зелени. После приготовления быстро остудить, "
            "перелить в закрытую ёмкость и хранить в холодильнике при температуре "
            "до 4 °C не более 3–4 дней; если не планируешь использовать его за это "
            "время, заморозить."
        )
        if broth_note not in d2_dinner["notes"]:
            d2_dinner["notes"].append(broth_note)
        potato_note = (
            "Картофель можно сварить отдельно или добавить в кастрюлю к говядине "
            "за 25 минут до конца приготовления."
        )
        if potato_note not in d2_dinner["notes"]:
            d2_dinner["notes"].append(potato_note)

    d3_breakfast = recipe(3, "Завтрак")
    if d3_breakfast:
        for section in d3_breakfast["sections"]:
            section["items"] = [
                "шпинат свежий — 40 г" if item.lower().startswith("шпинат свежий") else item
                for item in section["items"]
            ]
        d3_breakfast["steps"] = [
            step.replace(
                "желток должен полностью приготовиться",
                "белок и желток должны полностью схватиться",
            )
            for step in d3_breakfast["steps"]
        ]
        note = "Для двух порций можно взять около 75 г свежего шпината."
        if note not in d3_breakfast["notes"]:
            d3_breakfast["notes"].append(note)

    d29_dinner = recipe(29, "Ужин")
    if d29_dinner:
        d29_dinner["steps"] = [
            step.replace("Выложить курицу к батату", "Выложить курицу рядом с бататом")
            for step in d29_dinner["steps"]
        ]

    for week in weeks:
        for day in week["days"]:
            for r in day["recipes"]:
                blob = " ".join(
                    [r["title"]]
                    + [item for section in r["sections"] for item in section["items"]]
                    + r["steps"]
                    + r["leftover"]
                ).lower()
                if "батат" in blob:
                    for section in r["sections"]:
                        section["items"] = [
                            item + " (или картофель в том же количестве)"
                            if item.lower().startswith("батат")
                            and "картоф" not in item.lower()
                            else item
                            for item in section["items"]
                        ]
                    r["leftover"] = [
                        item + " (или картофель в том же количестве)"
                        if item.lower().startswith("батат") and "картоф" not in item.lower()
                        else item
                        for item in r["leftover"]
                    ]
                    for i, step in enumerate(r["steps"]):
                        if "батат" in step.lower() and "картоф" not in step.lower():
                            r["steps"][i] = re.sub(
                                r"\bбатат\b",
                                "батат (или картофель)",
                                step,
                                count=1,
                                flags=re.IGNORECASE,
                            )
                            break
                    note = "Батат можно заменить картофелем в том же количестве."
                    if note not in r["notes"]:
                        r["notes"].append(note)
                if "кинз" in blob:
                    note = "Кинзу можно заменить любой свежей зеленью."
                    if note not in r["notes"]:
                        r["notes"].append(note)

    for week in weeks:
        for cat in week["shop"]:
            cat["items"] = [
                (
                    item + " (или картофель в том же количестве)"
                    if item.lower().startswith("батат") and "картоф" not in item.lower()
                    else (
                        item + " (или любая свежая зелень)"
                        if item.lower().startswith("кинза —") and "или" not in item.lower()
                        else item
                    )
                )
                .replace("и/ или", "и/или")
                .replace(" (или оливки / маринованный огурец). (или оливки / маринованный огурец)", " (или оливки / маринованный огурец)")
                for item in cat["items"]
                if "─────────────────────" not in item
                and not (week["num"] == 3 and "чернослив без косточек" in item)
                and not (week["num"] == 5 and "белое вино" in item)
            ]
        if week["num"] == 1:
            next((c for c in week["shop"] if c["name"] == "Масла, соусы и специи"), {"items": []})["items"].append("лавровый лист — 1 шт")
        if week["num"] == 3:
            def add(name: str, item: str) -> None:
                cat = next(c for c in week["shop"] if c["name"] == name)
                if not any(item.split(" — ", 1)[0] in x for x in cat["items"]):
                    cat["items"].append(item)
            add("Крупы, злаки и хлеб", "бурый рис — 100 г")
            add("Овощи", "сельдерей — 1 стебель")
            add("Яйца и молочные продукты", "моцарелла — 100 г")
            for cat in week["shop"]:
                cat["items"] = [
                    "киноа — 160 г" if item.startswith("киноа —") else item
                    for item in cat["items"]
                ]


def parse_all() -> list[dict]:
    lines = [ln.strip() for ln in EXTRACT.read_text(encoding="utf-8").splitlines()]
    weeks_out = []
    for w in split_weeks(lines):
        wlines = w["lines"]
        shop_i = next(i for i, l in enumerate(wlines) if SHOP_RE.match(l))
        rec_i = None
        for i in range(shop_i + 1, len(wlines)):
            if DAY_RE.match(wlines[i]):
                if any(x.startswith("Завтрак") for x in wlines[i + 1 : i + 6]):
                    rec_i = i
                    break
        toc = parse_toc(wlines[1:shop_i])
        shop = parse_shop(wlines[shop_i + 1 : rec_i])
        days = parse_recipes(wlines[rec_i:])
        apply_editorial_overrides(days)
        # finish last recipe if the extract was cut
        if days and days[-1]["recipes"]:
            last = days[-1]["recipes"][-1]
            if last["title"].lower().startswith("боул с киноа") and last["steps"]:
                if "собрать" not in " ".join(last["steps"]).lower():
                    last["steps"].append(
                        "Собрать боул: киноа, печёные овощи и нут, авокадо. "
                        "Полить соусом тахини, посыпать зеленью, кунжутом и семечками. "
                        "Подавать с долькой лимона."
                    )
        for d in days:
            for r in d["recipes"]:
                r["image"] = f"img/recipes/d{d['num']}-{r['slug']}.jpg"
                note = safety_note(r)
                if not r["time"]:
                    r["time"] = "10 минут" if r["is_leftover"] else "35 минут"
                if note and not any("беременност" in n.lower() for n in r["notes"]):
                    r["safety"] = note
                else:
                    r["safety"] = None
        weeks_out.append(
            {
                "num": w["num"],
                "toc": toc,
                "shop": shop,
                "days": days,
            }
        )
    apply_manual_overrides(weeks_out)
    return weeks_out


def e(text: str) -> str:
    text = text or ""
    text = re.sub(r"(?<=\d)г\b", " г", text)
    text = text.replace("и/ или", "и/или")
    text = re.sub(r"\bшт(?!\.)\b", "шт.", text)
    text = re.sub(r"\bст\. л(?!\.)\b", "ст. л.", text)
    text = re.sub(r"\bч\. л(?!\.)\b", "ч. л.", text)
    text = re.sub(r" {2,}", " ", text)
    return html.escape(text)


def render_ingredient(item: str, recipe_id: str | None = None) -> str:
    match = re.match(
        r"^(.*?)\s+(\([^)]*готовили в (?:(\d+)\s+д(?:ень|не)|д(?:ень|не)\s+(\d+))\))(\s+—.*)$",
        item,
        flags=re.IGNORECASE,
    )
    if not match:
        return e(item)
    label, reference, day_before, day_after, suffix = match.groups()
    day = int(day_before or day_after)
    target = f"d{day}-dinner"
    label_lower = label.lower()
    if recipe_id == "d2-lunch" and "маринованный лук" in label_lower:
        target = "d1-lunch"
    elif recipe_id == "d10-lunch" and "булгур" in label_lower:
        target = "d9-lunch"
    elif recipe_id == "d12-lunch" and label_lower == "рис":
        target = "d11-lunch"
    return (
        f'<a class="prep-link" href="#{target}">{e(label)}</a> '
        f'{e(reference)}{e(suffix)}'
    )


def render_recipe(day_num: int, recipe: dict) -> str:
    rid = f"d{day_num}-{recipe['slug']}"
    leftover_pill = (
        '<span class="pill leftover">из заготовки</span>' if recipe["is_leftover"] else ""
    )
    time_pill = (
        f'<span class="pill">{e(recipe["time"])}</span>' if recipe["time"] else ""
    )
    ings = []
    for sec in recipe["sections"]:
        if sec["name"] and sec["name"] != "Ингредиенты":
            ings.append(f'<p class="ing-sub">{e(sec["name"])}</p>')
        ings.append("<ul>" + "".join(f"<li>{render_ingredient(it, rid)}</li>" for it in sec["items"]) + "</ul>")
    rendered_steps = []
    for step in recipe["steps"]:
        if step.strip().lower().rstrip(":") in {"приготовление поленты", "для поленты"}:
            rendered_steps.append(f'<li class="step-sub">{e(step.rstrip(":"))}</li>')
        else:
            rendered_steps.append(f"<li>{e(step)}</li>")
    steps = "<ol>" + "".join(rendered_steps) + "</ol>"
    leftover = ""
    if recipe["leftover"]:
        leftover = (
            '<p class="note leftover-note"><strong>↪ На завтра:</strong> '
            + e(" · ".join(recipe["leftover"]))
            + "</p>"
        )
    extra_notes = "".join(f'<p class="note">{e(n)}</p>' for n in recipe["notes"])
    safety = f'<p class="note">{e(recipe["safety"])}</p>' if recipe.get("safety") else ""
    return f"""
    <article class="recipe{' leftover' if recipe['is_leftover'] else ''}" id="{rid}" data-name="{e(recipe['title'].lower())}">
      <div class="recipe-hero">
        <figure class="recipe-photo">
          <div class="badge-arc"><span>#sekta</span></div>
          <img src="{e(recipe['image'])}" alt="{e(recipe['title'])}" loading="lazy" />
        </figure>
        <div class="recipe-head">
          <p class="eyebrow">{e(recipe['meal'].lower())}</p>
          <h3>{e(recipe['title'].lower())}</h3>
          <div class="pills">{time_pill}{leftover_pill}</div>
        </div>
      </div>
      <div class="recipe-body">
        <div>
          <h4>Ингредиенты</h4>
          {''.join(ings)}
        </div>
        <div>
          <h4>Приготовление</h4>
          {steps}
        </div>
        {leftover}{extra_notes}{safety}
      </div>
    </article>
    """


def render_week(week: dict) -> str:
    n = week["num"]
    chips = [f'<a href="#week-{n}-toc">меню</a>', f'<a href="#week-{n}-shop">покупки</a>']
    for d in week["days"]:
        chips.append(
            f'<a href="#d{d["num"]}">{e(d["weekday_short"] or ("день " + str(d["num"])))}</a>'
        )

    rows = []
    meal_keys = ["Завтрак", "Обед", "Ужин"]
    slugs = ["breakfast", "lunch", "dinner"]
    for i, toc in enumerate(week["toc"]):
        day = week["days"][i] if i < len(week["days"]) else None
        day_num = day["num"] if day else toc["num"]
        cells = []
        for mi, meal in enumerate(meal_keys):
            title = toc["meals"][mi] if mi < len(toc["meals"]) else ""
            href = f"#d{day_num}-{slugs[mi]}"
            cells.append(f'<td><a href="{href}">{e(title)}</a></td>')
        rows.append(
            f"""<tr>
              <th><a href="#d{day_num}"><span class="dow">{e(toc['weekday_short'] or toc['weekday'])}</span>
              <span class="dnum">день {day_num}</span></a></th>
              {''.join(cells)}
            </tr>"""
        )

    shop_cols = []
    for ci, cat in enumerate(week["shop"]):
        items = []
        for ii, item in enumerate(cat["items"]):
            cid = f"w{n}-c{ci}-i{ii}"
            items.append(
                f'<li><label><input type="checkbox" id="{cid}" /> <span>{e(item)}</span></label></li>'
            )
        shop_cols.append(
            f'<details class="shop-cat"><summary>{e(cat["name"])}</summary><ul>{"".join(items)}</ul></details>'
        )

    days_html = []
    for d in week["days"]:
        recs = "".join(render_recipe(d["num"], r) for r in d["recipes"])
        days_html.append(
            f"""
        <section class="day" id="d{d['num']}">
          <header class="day-head">
            <p class="eyebrow">неделя {n}</p>
            <h3>день {d['num']} · {e(d['weekday'].lower())}</h3>
            <a class="back" href="#week-{n}-toc">к меню недели</a>
          </header>
          <div class="recipes-grid">{recs}</div>
        </section>"""
        )

    return f"""
    <section class="week" id="week-{n}">
      <header class="week-banner">
        <div>
          <p class="eyebrow">меню на 7 дней</p>
          <h2>неделя {n}</h2>
        </div>
        <nav class="week-chips" aria-label="По неделе {n}">{''.join(chips)}</nav>
      </header>

      <div class="week-toc" id="week-{n}-toc">
        <div class="block-head">
          <h3>Содержание недели</h3>
          <p>Три приёма пищи в день. Нажмите на блюдо — откроется рецепт.</p>
        </div>
        <div class="toc-wrap">
          <table class="toc-table">
            <thead>
              <tr>
                <th>день</th>
                <th>завтрак</th>
                <th>обед</th>
                <th>ужин</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
        </div>
      </div>

      <div class="shop" id="week-{n}-shop">
        <div class="block-head">
          <h3>Список покупок</h3>
          <p>На неделю вперёд. Отмечайте купленное — галочки сохраняются в браузере.</p>
          <button type="button" class="ghost-btn" data-reset="week-{n}-shop">сбросить отметки</button>
        </div>
        <div class="shop-grid">{''.join(shop_cols)}</div>
      </div>

      {''.join(days_html)}
    </section>
    """


CSS = r"""
:root {
  --terra: #d99a9b;
  --terra-deep: #b97880;
  --cream: #f2ede4;
  --cream-soft: #f7f3ec;
  --blue: #c2d6e3;
  --ink: #2b231d;
  --ink-soft: rgba(43, 35, 29, 0.72);
  --ink-mute: rgba(43, 35, 29, 0.5);
  --line: rgba(43, 35, 29, 0.14);
  --pad: clamp(1rem, 3.5vw, 2.4rem);
  --radius-pill: 999px;
  --page: 1280px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: "Montserrat", system-ui, sans-serif;
  background: var(--cream-soft);
  color: var(--ink);
  line-height: 1.5;
}
img { max-width: 100%; display: block; }
a { color: inherit; }
.intro {
  display: grid;
  grid-template-columns: 128px minmax(8rem, 0.7fr) minmax(16rem, 1.5fr);
  width: calc(100% - 2 * var(--pad));
  max-width: calc(var(--page) - 2 * var(--pad));
  margin: 0.85rem auto 0;
  background: var(--cream);
  overflow: hidden;
}
.intro-photo {
  min-height: 128px;
  background:
    linear-gradient(180deg, transparent 55%, rgba(43, 35, 29, 0.18) 100%),
    url("img/dish-toast.jpg") center / cover no-repeat;
}
.badge-arc {
  width: 4rem; height: 4rem;
  background: var(--blue);
  border-radius: 0 0 100% 0;
  display: flex; align-items: flex-start; justify-content: flex-start;
  padding: 0.5rem 0 0 0.5rem;
}
.badge-arc span { font-size: 0.55rem; font-weight: 600; letter-spacing: 0.03em; }
.intro-mid {
  background: var(--terra); color: var(--cream);
  display: flex; flex-direction: column; justify-content: center;
  padding: 0.75rem 1.05rem;
}
.intro-mid .eyebrow { font-size: 0.64rem; font-weight: 500; opacity: 0.9; margin-bottom: 0.15rem; }
.intro-mid h1 {
  font-size: clamp(1.12rem, 1.9vw, 1.45rem);
  font-weight: 700; line-height: 1.15; letter-spacing: -0.02em;
  text-transform: lowercase;
}
.intro-mid .rule { width: 1.6rem; height: 2px; background: var(--cream); margin-top: 0.55rem; opacity: 0.85; }
.intro-side {
  display: flex; align-items: center;
  padding: 0.75rem 1.15rem;
}
.intro-side .lead {
  font-size: clamp(0.78rem, 1.15vw, 0.9rem);
  line-height: 1.4; color: var(--ink-soft); max-width: 52ch;
}
.weeks-nav {
  position: sticky; top: 0; z-index: 40;
  background: rgba(247, 243, 236, 0.94);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--line);
}
.weeks-nav-inner {
  max-width: var(--page);
  margin: 0 auto;
  padding: 0.55rem var(--pad);
  display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center;
}
.weeks-nav a, .weeks-nav button, .search input {
  font: inherit; font-size: 0.72rem; font-weight: 600;
  padding: 0.38rem 0.85rem;
  border: 1.5px solid var(--line);
  border-radius: var(--radius-pill);
  background: transparent; color: var(--ink);
  text-decoration: none; cursor: pointer;
}
.weeks-nav a.is-active, .weeks-nav a:hover {
  border-color: var(--terra);
  background: rgba(198, 102, 69, 0.1);
}
.search { margin-left: auto; display: flex; gap: 0.35rem; align-items: center; }
.search input {
  width: min(16rem, 42vw);
  font-weight: 500;
  background: #fff;
}
.search input { flex: 1 1 12rem; min-width: 0; }
.search select {
  font: inherit; font-size: 0.72rem; font-weight: 600;
  padding: 0.38rem 0.7rem;
  border: 1.5px solid var(--line); border-radius: var(--radius-pill);
  background: #fff; color: var(--ink); cursor: pointer;
}
.search-empty {
  margin: 1rem 0;
  padding: 0.8rem 1rem;
  background: #fff;
  border-left: 3px solid var(--terra);
  color: var(--ink-soft);
  font-size: 0.78rem;
}
.page { max-width: var(--page); margin: 0 auto; padding: 1rem var(--pad) 4rem; }
.how {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.85rem 1.1rem;
  align-items: start;
  margin: 1rem 0 1.1rem;
  padding: 1rem 1.15rem;
  background: var(--terra);
  color: var(--cream);
}
.how .eyebrow { font-size: 0.66rem; letter-spacing: 0.1em; text-transform: uppercase; opacity: 0.82; margin-bottom: 0.3rem; }
.how h2 { font-size: clamp(1.02rem, 1.8vw, 1.28rem); line-height: 1.18; font-weight: 700; max-width: 32ch; }
.how ol { font-size: 0.76rem; line-height: 1.45; padding-left: 1.1rem; opacity: 0.95; }
.how li + li { margin-top: 0.2rem; }
.reminder {
  margin: 0 0 1.4rem;
  padding: 0.7rem 0.9rem;
  background: rgba(194, 214, 227, 0.35);
  border-left: 3px solid var(--blue);
  font-size: 0.78rem; line-height: 1.45;
}
.week { margin-bottom: 2.4rem; scroll-margin-top: 3.4rem; }
.week-banner {
  display: flex; flex-wrap: wrap; justify-content: space-between; align-items: end;
  gap: 0.8rem; margin-bottom: 0.85rem;
  padding-bottom: 0.7rem; border-bottom: 1px solid var(--line);
}
.week-banner .eyebrow { font-size: 0.68rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-mute); }
.week-banner h2 {
  font-size: clamp(1.6rem, 3vw, 2.2rem);
  font-weight: 800; letter-spacing: -0.04em; text-transform: lowercase;
}
.week-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.week-chips a {
  font-size: 0.68rem; font-weight: 600;
  padding: 0.28rem 0.7rem;
  border: 1.5px solid var(--line); border-radius: var(--radius-pill);
  text-decoration: none;
}
.week-chips a:hover { border-color: var(--terra); }
.block-head { margin: 0.4rem 0 0.75rem; }
.block-head h3 {
  font-size: 0.92rem; font-weight: 700; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--ink-mute);
}
.block-head p { font-size: 0.78rem; color: var(--ink-soft); margin-top: 0.2rem; max-width: 62ch; }
.ghost-btn {
  margin-top: 0.45rem;
  font: inherit; font-size: 0.68rem; font-weight: 600;
  padding: 0.28rem 0.7rem;
  border: 1.5px solid var(--line); border-radius: var(--radius-pill);
  background: transparent; cursor: pointer;
}
.toc-wrap { overflow-x: auto; margin-bottom: 1.3rem; background: #fff; }
.toc-toggle {
  display: none;
  align-items: center; justify-content: center;
  font: inherit; font-size: 0.68rem; font-weight: 600;
  padding: 0.35rem 0.7rem;
  border: 1.5px solid var(--line); border-radius: var(--radius-pill);
  background: transparent; color: var(--ink); cursor: pointer;
}
.toc-table { width: 100%; border-collapse: collapse; min-width: 720px; }
.toc-table th, .toc-table td {
  text-align: left; vertical-align: top;
  padding: 0.7rem 0.8rem;
  border-bottom: 1px solid var(--line);
  font-size: 0.78rem;
}
.toc-table thead th {
  font-size: 0.66rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--ink-mute); background: var(--cream);
}
.toc-table tbody th { width: 7.2rem; background: var(--cream-soft); }
.toc-table .dow { display: block; font-size: 0.82rem; font-weight: 700; text-transform: lowercase; }
.toc-table .dnum { display: block; font-size: 0.64rem; font-weight: 500; color: var(--ink-mute); margin-top: 0.12rem; }
.toc-table a { text-decoration: none; }
.toc-table td a { color: var(--ink); }
.toc-table td a:hover { color: var(--terra-deep); }
.shop { margin-bottom: 1.5rem; padding: 1rem 1.05rem 1.1rem; background: #fff; }
.shop-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.9rem 1.1rem;
}
.shop-cat > summary { list-style: none; cursor: pointer; display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;
  font-size: 0.7rem; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--terra-deep); margin-bottom: 0.4rem;
}
.shop-cat > summary::-webkit-details-marker { display: none; }
.shop-cat > summary::after { content: "+"; font-size: 1rem; font-weight: 500; color: var(--terra-deep); }
.shop-cat[open] > summary::after { content: "−"; }
.shop-cat[open] { padding-bottom: 0.35rem; }
.shop-cat ul { list-style: none; }
.shop-cat li { font-size: 0.74rem; color: var(--ink-soft); line-height: 1.35; margin-bottom: 0.28rem; }
.shop-cat label { display: flex; gap: 0.4rem; align-items: flex-start; cursor: pointer; }
.shop-cat input { margin-top: 0.18rem; accent-color: var(--terra); }
.shop-cat input:checked + span { text-decoration: line-through; opacity: 0.55; }
.day { scroll-margin-top: 3.5rem; margin-bottom: 1.35rem; }
.day-head {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.4rem 0.9rem;
  margin: 0.4rem 0 0.7rem;
}
.day-head .eyebrow { font-size: 0.64rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-mute); }
.day-head h3 { font-size: 1.15rem; font-weight: 800; letter-spacing: -0.03em; text-transform: lowercase; }
.day-head .back { margin-left: auto; font-size: 0.68rem; color: var(--terra-deep); text-decoration: none; }
.recipes-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.75rem; align-items: start; }
.recipe {
  background: #fff; border-radius: 10px; overflow: hidden;
  display: flex; flex-direction: column; height: auto;
  box-shadow: 0 12px 28px rgba(43, 35, 29, 0.05);
}
.recipe.hidden { display: none; }
.recipe-hero { display: grid; grid-template-columns: 84px minmax(0, 1fr); min-height: 84px; }
.recipe-photo { position: relative; min-height: 0; aspect-ratio: 1 / 1; overflow: hidden; }
.recipe-photo img { width: 100%; height: 100%; object-fit: cover; }
.recipe-photo .badge-arc { position: absolute; top: 0; left: 0; width: 3.2rem; height: 3.2rem; padding: 0.38rem 0 0 0.38rem; }
.recipe-photo .badge-arc span { font-size: 0.48rem; }
.recipe-head {
  background: var(--terra); color: var(--cream);
  display: flex; flex-direction: column; justify-content: center; gap: 0.28rem;
  padding: 0.65rem 0.75rem; min-width: 0;
}
.recipe-head .eyebrow { font-size: 0.62rem; font-weight: 500; opacity: 0.88; }
.recipe-head h3 {
  font-size: clamp(0.84rem, 1.12vw, 1rem);
  font-weight: 700; line-height: 1.18; letter-spacing: -0.025em;
}
.pills { display: flex; flex-wrap: wrap; gap: 0.25rem; }
.pill {
  display: inline-flex; align-items: center;
  padding: 0.18rem 0.5rem;
  border: 1.5px solid rgba(242, 237, 228, 0.7);
  border-radius: var(--radius-pill);
  font-size: 0.6rem; font-weight: 500; color: var(--cream); width: fit-content;
}
.pill.leftover { border-color: var(--blue); background: rgba(194, 214, 227, 0.22); }
.recipe-body { padding: 0.65rem 0.75rem 0.8rem; display: grid; gap: 0.55rem; }
.recipe-body h4 {
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--ink-mute); margin-bottom: 0.35rem;
}
.recipe-body ul, .recipe-body ol {
  padding-left: 0.95rem; color: var(--ink-soft);
  font-size: 0.68rem; line-height: 1.32;
}
.recipe-body li + li { margin-top: 0.12rem; }
.recipe-body li.step-sub {
  list-style: none;
  margin-left: -0.95rem;
  margin-top: 0.65rem;
  font-weight: 700;
  color: var(--ink);
}
.recipe-body .prep-link {
  color: var(--terra-deep);
  font-weight: 600;
  text-decoration: underline;
  text-decoration-style: dotted;
  text-underline-offset: 0.16em;
}
.recipe-body .prep-link:hover { color: var(--ink); text-decoration-style: solid; }
.ing-sub { font-size: 0.64rem; font-weight: 600; margin: 0.35rem 0 0.2rem; color: var(--ink); }
.note {
  grid-column: 1 / -1;
  margin-top: 0.15rem; padding: 0.5rem 0.65rem;
  background: rgba(194, 214, 227, 0.35);
  border-left: 3px solid var(--blue);
  font-size: 0.64rem; line-height: 1.4;
}
.leftover-note { background: rgba(217, 154, 155, 0.18); border-left-color: var(--terra); }
.footer-note {
  margin-top: 1.5rem; padding: 1rem 1.2rem;
  background: var(--cream); border: 1px solid var(--line);
  font-size: 0.78rem; color: var(--ink-soft); text-align: center;
}
.back-to-top {
  position: fixed; left: 1rem; bottom: 1rem; z-index: 60;
  display: inline-flex; align-items: center; gap: 0.35rem;
  padding: 0.5rem 0.7rem;
  border: 1px solid rgba(255, 255, 255, 0.75);
  border-radius: var(--radius-pill);
  background: var(--terra); color: var(--cream);
  box-shadow: 0 8px 22px rgba(43, 35, 29, 0.18);
  font: inherit; font-size: 0.7rem; font-weight: 700;
  text-decoration: none;
  opacity: 0; pointer-events: none;
  transform: translateY(0.5rem);
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.back-to-top.is-visible { opacity: 1; pointer-events: auto; transform: translateY(0); }
@media (max-width: 980px) {
  .recipes-grid, .shop-grid { grid-template-columns: 1fr 1fr; }
  .how { grid-template-columns: 1fr; }
}
@media (max-width: 820px) {
  .intro { grid-template-columns: 96px 1fr 1.4fr; }
  .search { margin-left: 0; width: 100%; }
  .search input { width: auto; }
}
@media (max-width: 560px) {
  body { overflow-x: hidden; }
  .intro { grid-template-columns: 72px minmax(0, 1fr); }
  .intro-photo { grid-row: span 2; min-height: 72px; aspect-ratio: 1 / 1; }
  .intro-mid, .intro-side { min-width: 0; padding: 0.65rem 0.75rem; }
  .intro-mid h1 { font-size: 1.08rem; overflow-wrap: anywhere; }
  .intro-side .lead { font-size: 0.75rem; }
  .week-banner { align-items: flex-start; }
  .week-chips { width: 100%; }
  .recipes-grid, .shop-grid { grid-template-columns: 1fr; }
  .week-toc .block-head {
    display: grid; grid-template-columns: minmax(0, 1fr) auto;
    align-items: end; gap: 0.35rem 0.6rem;
  }
  .week-toc .block-head p { grid-column: 1 / -1; }
  .toc-toggle { display: inline-flex; grid-column: 2; grid-row: 1; }
  .week-toc .toc-wrap { display: none; overflow: visible; margin-top: 0.75rem; }
  .week-toc.is-open .toc-wrap { display: block; }
  .toc-table { min-width: 0; display: block; }
  .toc-table thead { display: none; }
  .toc-table tbody, .toc-table tr { display: block; }
  .toc-table tr {
    padding: 0.55rem 0.7rem;
    border-bottom: 1px solid var(--line);
  }
  .toc-table tbody th, .toc-table tbody td {
    display: block; width: auto; padding: 0.3rem 0;
    border: 0; font-size: 0.76rem;
  }
  .toc-table tbody th { padding-bottom: 0.45rem; background: transparent; }
  .toc-table tbody td::before {
    display: block; margin-bottom: 0.1rem;
    font-size: 0.6rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--ink-mute);
  }
  .toc-table tbody td:nth-child(2)::before { content: "завтрак"; }
  .toc-table tbody td:nth-child(3)::before { content: "обед"; }
  .toc-table tbody td:nth-child(4)::before { content: "ужин"; }
  .toc-table td a { display: block; line-height: 1.35; overflow-wrap: anywhere; }
  .recipe { min-width: 0; }
  .recipe-hero { grid-template-columns: 76px minmax(0, 1fr); min-height: 76px; }
  .recipe-photo { width: 76px; height: 76px; }
  .recipe-head { min-width: 0; padding: 0.55rem 0.65rem; overflow: hidden; }
  .recipe-head h3 { font-size: 0.8rem; line-height: 1.2; overflow-wrap: anywhere; }
  .recipe-body { min-width: 0; }
  .recipe-body ul, .recipe-body ol { font-size: 0.72rem; line-height: 1.4; overflow-wrap: anywhere; }
  .note { font-size: 0.68rem; }
  .back-to-top { left: max(0.75rem, env(safe-area-inset-left)); bottom: max(0.75rem, env(safe-area-inset-bottom)); }
}
@media print {
  .weeks-nav, .search, .how, .ghost-btn, .day-head .back { display: none !important; }
  .week { break-before: page; }
  .recipe { break-inside: avoid; box-shadow: none; }
}
"""

JS = r"""
const boxes = document.querySelectorAll('.shop input[type="checkbox"]');
boxes.forEach(cb => {
  cb.checked = localStorage.getItem(cb.id) === '1';
  cb.addEventListener('change', () => localStorage.setItem(cb.id, cb.checked ? '1' : '0'));
});
document.querySelectorAll('[data-reset]').forEach(btn => {
  btn.addEventListener('click', () => {
    const root = document.getElementById(btn.dataset.reset);
    root.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      cb.checked = false;
      localStorage.removeItem(cb.id);
    });
  });
});
document.querySelectorAll('.week-toc').forEach(toc => {
  const wrap = toc.querySelector('.toc-wrap');
  const head = toc.querySelector('.block-head');
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'toc-toggle';
  button.setAttribute('aria-expanded', 'false');
  button.setAttribute('aria-controls', wrap.id || 'week-menu');
  button.textContent = 'показать меню';
  head.append(button);
  button.addEventListener('click', () => {
    const open = toc.classList.toggle('is-open');
    button.setAttribute('aria-expanded', String(open));
    button.textContent = open ? 'скрыть меню' : 'показать меню';
  });
});
document.querySelectorAll('.week-chips a[href$="-toc"]').forEach(link => {
  link.addEventListener('click', () => {
    const toc = document.querySelector(link.getAttribute('href'));
    if (!toc) return;
    toc.classList.add('is-open');
    const button = toc.querySelector('.toc-toggle');
    if (button) {
      button.setAttribute('aria-expanded', 'true');
      button.textContent = 'скрыть меню';
    }
  });
});
const normalizeSearch = value => value.toLowerCase().replaceAll('ё', 'е').replace(/[^а-яa-z0-9]+/g, ' ').trim();
const search = document.getElementById('q');
const weekFilter = document.getElementById('week-filter');
const emptyMessage = document.getElementById('search-empty');
const tokenMatches = (haystack, query) => {
  const hay = normalizeSearch(haystack).split(/\s+/).filter(Boolean);
  return normalizeSearch(query).split(/\s+/).filter(Boolean).every(token => {
    const root = token.length > 5 ? token.slice(0, -2) : token;
    return hay.some(word => word === token || word.startsWith(root) || token.startsWith(word.slice(0, -1)));
  });
};
const applyFilters = () => {
  const query = search.value.trim();
  const chosenWeek = weekFilter.value;
  let visibleRecipes = 0;
  document.querySelectorAll('.week').forEach(week => {
    const weekNumber = week.id.replace('week-', '');
    const weekAllowed = chosenWeek === 'all' || chosenWeek === weekNumber;
    let weekHasVisibleDay = false;
    week.querySelectorAll('.day').forEach(day => {
      let dayHasVisibleRecipe = false;
      day.querySelectorAll('.recipe').forEach(recipe => {
        const searchable = recipe.innerText || recipe.textContent || '';
        const matches = !query || tokenMatches(searchable, query);
        recipe.classList.toggle('hidden', !matches);
        if (matches) { dayHasVisibleRecipe = true; visibleRecipes += 1; }
      });
      day.style.display = weekAllowed && dayHasVisibleRecipe ? '' : 'none';
      if (weekAllowed && dayHasVisibleRecipe) weekHasVisibleDay = true;
    });
    week.style.display = weekAllowed && (weekHasVisibleDay || !query) ? '' : 'none';
  });
  emptyMessage.hidden = Boolean(!query || visibleRecipes);
};
search.addEventListener('input', applyFilters);
weekFilter.addEventListener('change', applyFilters);
applyFilters();
const setShopItem = (id, text) => {
  const input = document.getElementById(id);
  if (input) input.nextElementSibling.textContent = text;
};
const removeShopItem = id => document.getElementById(id)?.closest('li')?.remove();
const addShopItem = (shopId, id, text) => {
  if (document.getElementById(id)) return;
  const categoryIndex = Number(id.match(/-c(\d+)-/)?.[1] || 0) + 1;
  const category = document.querySelector(`#${shopId} .shop-grid .shop-cat:nth-child(${categoryIndex})`);
  if (!category) return;
  const li = document.createElement('li');
  li.innerHTML = `<label><input type="checkbox" id="${id}" /> <span>${text}</span></label>`;
  category.querySelector('ul').append(li);
};
const fixShopLists = () => {
  setShopItem('w1-c5-i3', 'каперсы — 2 ст. л. (или оливки / маринованный огурец)');
  setShopItem('w3-c5-i2', 'каперсы — 2 ст. л. (или оливки / маринованный огурец)');
  setShopItem('w3-c2-i2', 'киноа — 160 г');
  setShopItem('w3-c7-i0', 'грецкие орехи и/или миндаль — 70 г');
  addShopItem('week-1-shop', 'w1-c6-bay-leaf', 'лавровый лист — 1 шт.');
  addShopItem('week-3-shop', 'w3-c2-brown-rice', 'бурый рис — 100 г');
  addShopItem('week-3-shop', 'w3-c3-celery', 'сельдерей — 1 стебель');
  addShopItem('week-3-shop', 'w3-c1-mozzarella', 'моцарелла — 100 г');
  removeShopItem('w2-c8-i6');
  removeShopItem('w3-c5-i3');
  removeShopItem('w5-c6-i12');
};
fixShopLists();
document.querySelectorAll('.shop input[type="checkbox"]').forEach(cb => {
  cb.checked = localStorage.getItem(cb.id) === '1';
  cb.addEventListener('change', () => localStorage.setItem(cb.id, cb.checked ? '1' : '0'));
});
const normalizeEditorialText = text => text
  .replace(/(?<=\d)г\b/g, ' г')
  .replace(/и\/ или/g, 'и/или')
  .replace(/\bшт(?!\.)\b/g, 'шт.')
  .replace(/\bст\. л(?!\.)\b/g, 'ст. л.')
  .replace(/\bч\. л(?!\.)\b/g, 'ч. л.')
  .replace(/ {2,}/g, ' ');
document.querySelectorAll('.recipe, .shop, .toc-table, .how').forEach(root => {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach(node => { node.nodeValue = normalizeEditorialText(node.nodeValue); });
});
document.querySelectorAll('.recipe').forEach(recipe => {
  const image = recipe.querySelector('img');
  if (image) image.src = `img/recipes/${recipe.id}.jpg`;
});
const steakStep = document.querySelector('#d28-dinner .recipe-body ol li:nth-child(12)');
if (steakStep) steakStep.textContent = 'Жарить стейк до безопасной внутренней температуры, согласованной с профильным редактором курса; проверить термометром. Формулировку про среднюю или желаемую прожарку для беременных не использовать до согласования.';
const steakBody = document.querySelector('#d28-dinner .recipe-body');
if (steakBody && !steakBody.querySelector('.safety-note')) {
  const note = document.createElement('p');
  note.className = 'note safety-note';
  note.innerHTML = 'Безопасность: для беременных не подавать стейк сырым или недоготовленным. Согласовать с профильным редактором безопасную внутреннюю температуру и готовить с термометром.';
  steakBody.append(note);
}
const weekLinks = [...document.querySelectorAll('.weeks-nav a[href^="#week-"]')];
const weeks = [...document.querySelectorAll('.week')];
const io = new IntersectionObserver(entries => {
  const vis = entries.filter(e => e.isIntersecting).sort((a,b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!vis) return;
  weekLinks.forEach(a => a.classList.toggle('is-active', a.getAttribute('href') === '#' + vis.target.id));
}, { rootMargin: '-20% 0px -65% 0px', threshold: [0, 0.1, 0.3] });
weeks.forEach(w => io.observe(w));
const topButton = document.querySelector('.back-to-top');
const updateTopButton = () => topButton.classList.toggle('is-visible', window.scrollY > 450);
window.addEventListener('scroll', updateTopButton, { passive: true });
updateTopButton();
"""


def build_html(weeks: list[dict]) -> str:
    week_links = "".join(
        f'<a href="#week-{w["num"]}">неделя {w["num"]}</a>' for w in weeks
    )
    body = "".join(render_week(w) for w in weeks)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Рецепты на 5 недель — курс для беременных</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <style>{CSS}</style>
</head>
<body>
  <header class="intro" id="top">
    <div class="intro-photo" aria-hidden="true">
      <div class="badge-arc"><span>#sekta</span></div>
    </div>
    <div class="intro-mid">
      <p class="eyebrow">курс для</p>
      <h1>беременных</h1>
      <div class="rule" aria-hidden="true"></div>
    </div>
    <div class="intro-side">
      <p class="lead">Пять недель меню по рекомендациям курса: содержание на каждый день, список продуктов на неделю и три рецепта — завтрак, обед и ужин.</p>
    </div>
  </header>

  <nav class="weeks-nav" aria-label="Недели">
    <div class="weeks-nav-inner">
      {week_links}
      <label class="search">
        <input id="q" type="search" placeholder="найти блюдо" />
        <select id="week-filter" aria-label="Искать в неделе">
          <option value="all">все недели</option>
          {''.join(f'<option value="{w["num"]}">неделя {w["num"]}</option>' for w in weeks)}
        </select>
      </label>
    </div>
  </nav>

  <main class="page">
    <p id="search-empty" class="search-empty" role="status" hidden>Ничего не найдено.</p>
    <aside class="how">
      <div>
        <p class="eyebrow">как пользоваться</p>
        <h2>Сначала неделя, потом закупка, потом день</h2>
      </div>
      <ol>
        <li>Выберите неделю в меню сверху.</li>
        <li>Откройте содержание — там все 7 дней и три блюда в каждом.</li>
        <li>Закупите продукты по списку недели: галочки запоминаются.</li>
        <li>Готовьте по дням. Обед часто собирается из вчерашнего ужина — это уже заложено в меню.</li>
      </ol>
    </aside>
    <p class="reminder"><strong>Напоминание:</strong> при беременности яйца, рыбу и птицу всегда готовить полностью. Хлеб рекомендуем ржаной или цельнозерновой.</p>
    {body}
    <p class="footer-note">35 дней · 105 рецептов · 5 списков покупок. Обеды с пометкой «из заготовки» — разогрев вчерашнего ужина.</p>
    <a class="back-to-top" href="#top" aria-label="Вернуться наверх">↑ наверх</a>
  </main>
  <script>{JS}</script>
</body>
</html>
"""


def main() -> None:
    print("Compressing images...")
    compress_images()
    print("Parsing recipes...")
    weeks = parse_all()
    OUT_JSON.write_text(json.dumps(weeks, ensure_ascii=False, indent=2), encoding="utf-8")
    for w in weeks:
        rec_n = sum(len(d["recipes"]) for d in w["days"])
        shop_n = sum(len(c["items"]) for c in w["shop"])
        print(
            f"  week {w['num']}: toc={len(w['toc'])} days={len(w['days'])} "
            f"recipes={rec_n} shop_cats={len(w['shop'])} shop_items={shop_n}"
        )
        for d in w["days"]:
            meals = [r["meal"] for r in d["recipes"]]
            if meals != MEAL_ORDER:
                print(f"    WARN day {d['num']} meals={meals}")
            for r in d["recipes"]:
                if not r["title"] or not r["steps"]:
                    print(f"    WARN incomplete {d['num']} {r['meal']}: {r['title']!r} steps={len(r['steps'])}")
    OUT_HTML.write_text(build_html(weeks), encoding="utf-8")
    print(f"Wrote {OUT_HTML} ({OUT_HTML.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
