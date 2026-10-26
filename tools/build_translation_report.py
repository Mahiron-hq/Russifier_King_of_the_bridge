"""Writes docs/ПЕРЕВОД.md: every translated string and image of the mod, where it lives, original and Russian."""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))

from toc_images import ARROWS, CAPTIONS  # noqa: E402

FINAL = os.path.join(REPO, "translations", "ru.json")
IMAGES = os.path.join(REPO, "translations", "images.json")
STRINGS = os.path.join(REPO, "reference", "strings")
OUT = os.path.join(REPO, "docs", "ПЕРЕВОД.md")
STRING_BUNDLE = "StreamingAssets/aa/StandaloneWindows64/localization-string-tables-russian(ru)_assets_all.bundle"
PAGES_BUNDLE = "StreamingAssets/aa/StandaloneWindows64/localization-assets-russian(ru)_assets_all.bundle"
EXTRA = "StreamingAssets/ru/ru_extra.json"
SPRITES = "StreamingAssets/ru/sprites"


def cell(text):
    return str(text).replace("|", "\\|").replace("\r", "").replace("\n", "<br>") if text not in (None, "") else "-"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def load_english(table_name):
    # One exported key carries a trailing newline after "Page4Key"; the mod's data uses the bare key.
    data = json.load(open(os.path.join(STRINGS, table_name + ".json"), encoding="utf-8"))
    return {key.strip(): value for key, value in data.items()}


def page_order(name):
    groups = ("page_contents", "page_tutorial", "page", "secretpage")
    group = next(i for i, g in enumerate(groups) if name.startswith(g))
    number = "".join(c for c in name if c.isdigit())
    return group, int(number or 0)


def main():
    final = json.load(open(FINAL, encoding="utf-8"))
    images = json.load(open(IMAGES, encoding="utf-8"))
    parts = ["# Русификатор King of the Bridge: все переводы", "",
             "Все тексты и картинки, которые меняет русификатор. Пути указаны от папки `King of the Bridge_Data`. "
             "Файл собирается командой `tools/build_translation_report.py` из `translations/ru.json` и "
             "`translations/images.json`.", ""]
    total = 0

    plural_keys = set(final["plurals"])
    parts += ["## 1. Тексты игры (таблицы локализации)", "",
              "Файл: `%s`, таблицы `<Имя>_ru`. Строки с числом берут формы из раздела 2." % STRING_BUNDLE, ""]
    for name, entries in final["tables"].items():
        english = load_english(name)
        rows = []
        for key in english:
            ru = entries.get(key)
            if ru is None:
                continue
            if key in plural_keys:
                ru = "(формы по числу, см. раздел 2)"
            rows.append((key, english[key].get("en"), ru))
        total += len(rows)
        parts += ["### %s_ru (%d)" % (name, len(rows)), "", table(("Ключ", "Оригинал", "Перевод"), rows), ""]

    rows = []
    for key, p in final["plurals"].items():
        table_name = next(t for t, e in final["tables"].items() if key in e)
        english = load_english(table_name)[key]["en"]
        rows.append((key, english, p["one"], p["few"], p["many"]))
    parts += ["## 2. Склонение по числу", "",
              "Файл: `%s`, запись SmartFormat `{%s:plural(ru):...}`. `{n}` - число." % (STRING_BUNDLE, "var"), "",
              table(("Ключ", "Оригинал", "1, 21, 31", "2-4, 22-24", "5-20, 25-30"), rows), ""]

    time_en = {"hours": "hours / hour", "minutes": "minutes / minute", "seconds": "seconds / second"}
    rows = [(unit, time_en.get(unit), f["one"], f["few"], f["many"]) for unit, f in final["time"].items()]
    parts += ["## 3. Время в финальных титрах", "",
              "Файл: `%s` (`time`), собирает `Managed/KotbRussian.dll`. Начало строки: «%s»." % (
                  EXTRA, final["tables"]["CreditsTable"]["TimeCountTextKey"]), "",
              table(("Единица", "Оригинал", "1, 21", "2-4", "5-20"), rows), ""]

    rule_en = load_english("RuleBreakTable")
    chess_en = load_english("ChessTable")
    rows = [(k, chess_en.get(k, {}).get("en"), f["m"], f["f"]) for k, f in final["colors"].items()]
    parts += ["## 4. Строка обвинения (согласование с родом фигуры)", "",
              "Файл: `%s` (`colors`, `piece_gender`, `rules_by_id`), собирает `Managed/KotbRussian.dll`." % EXTRA, "",
              "### Цвет", "", table(("Ключ", "Оригинал", "Мужской род", "Женский род"), rows), ""]
    gender_name = {"m": "мужской", "f": "женский"}
    rows = [(k, chess_en.get(k, {}).get("en"), final["tables"]["ChessTable"].get(k), gender_name.get(g, g))
            for k, g in final["piece_gender"].items()]
    parts += ["### Род фигур", "", table(("Ключ", "Оригинал", "Перевод", "Род"), rows), ""]
    rows = [(k, rule_en.get(k, {}).get("en"), f["m"], f["f"]) for k, f in final["rules"].items()]
    total += len(final["rules"])
    parts += ["### Нарушенные правила", "", table(("Ключ", "Оригинал", "Мужской род", "Женский род"), rows), ""]

    rows = list(final["achievements"].items())
    total += len(rows)
    parts += ["## 5. Достижения (названия и описания)", "",
              "Файл: `%s` (`achievements`). Игра берёт английский текст из Steam, `KotbRussian.dll` подменяет его "
              "по этой таблице." % EXTRA, "", table(("Оригинал", "Перевод"), rows), ""]

    parts += ["## 6. Прочие тексты", "", table(("Где", "Оригинал", "Перевод"), [
        ("`sharedassets0.assets`, список языков в настройках", "ENGLISH / DUTCH", "Русский"),
        ("`Managed/KotbRussian.dll`, правый нижний угол последней карточки титров", "-",
         "Перевёл игру ваш любимый Mahiron"),
        ("`sharedassets0.assets`, шрифт `alagard SDF`", "латиница", "кириллица, дорисованы многоточие, « », тире"),
    ]), ""]

    pages = sorted(images["pages"].items(), key=lambda item: page_order(item[0]))
    total += len(pages)
    parts += ["## 7. Страницы книги правил (%d)" % len(pages), "",
              "Файл: `%s`, текстуры с теми же именами, что у английских страниц. Текст нарисован на картинках; "
              "зачёркнутое на странице записано как ~~так~~, надписи на рисунках - в скобках." % PAGES_BUNDLE, "",
              table(("Текстура", "Оригинал", "Перевод"),
                    [("`%s`" % name, texts["en"], texts["ru"]) for name, texts in pages]), ""]

    rows = []
    for key, lines in CAPTIONS.items():
        ru = " / ".join(line for line in lines if line).replace("~~", "").replace(ARROWS, "(значок: диагональные стрелки)")
        rows.append(("`link_%s_l`, `link_%s_r`" % (key, key), images["toc_en"].get(key), ru))
    total += len(rows)
    tiles = [("`%s/%s.png`" % (SPRITES, name), t["en"], t["ru"]) for name, t in images["tiles"].items()]
    total += len(tiles)
    parts += ["## 8. Оглавление книги и мост", "",
              "Файлы: `%s/*.png`. `KotbRussian.dll` подменяет эти спрайты, когда выбран русский язык." % SPRITES, "",
              "### Подписи оглавления (%d)" % len(rows), "", table(("Спрайт", "Оригинал", "Перевод"), rows), "",
              "### Надпись на мосту", "", table(("Спрайт", "Оригинал", "Перевод"), tiles), ""]

    parts += ["## Без перевода", "",
              "- Логотип «king of the bridge» оставлен на английском.",
              "- `page31` (только цифры), `page_contents_1` (пустая страница), значок `×` в оглавлении.",
              "- Стартовые заглушки `page0`, `page1`, `secretpage0_eng` в сценах: игра заменяет их страницей "
              "на выбранном языке до показа.", ""]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts))
    print(OUT, "entries:", total)


if __name__ == "__main__":
    main()
