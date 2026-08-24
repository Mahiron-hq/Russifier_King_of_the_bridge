#!/usr/bin/env python3
"""Compare translation.txt with the game's English Unity String Tables."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from audit_game_assets import iter_named_objects


def normalize(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def load_translation(path: Path) -> tuple[dict[str, str], list[str]]:
    translations: dict[str, str] = {}
    duplicates: list[str] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw_line or raw_line.startswith("#") or "=" not in raw_line:
            continue
        source, translated = raw_line.split("=", 1)
        if source in translations:
            duplicates.append(f"{line_number}: {source}")
        translations[source] = translated
    return translations, duplicates


def load_english_strings(game_path: Path) -> list[dict]:
    bundle_dir = game_path / "King of the Bridge_Data" / "StreamingAssets" / "aa" / "StandaloneWindows64"
    records = []
    for bundle in bundle_dir.glob("localization-string-tables-english*.bundle"):
        for obj, object_type, _, _ in iter_named_objects(bundle):
            if object_type != "MonoBehaviour":
                continue
            tree = obj.read_typetree()
            table = tree.get("m_Name", "")
            for entry in tree.get("m_TableData", []):
                records.append(
                    {
                        "table": table,
                        "id": entry["m_Id"],
                        "source": entry["m_Localized"],
                    }
                )
    return records


DEFERRED_FRAGMENTS = {
    "It took you",
    "hour,",
    "hours,",
    "minute and",
    "minutes and",
    "second.",
    "seconds.",
}


def is_covered(record: dict, translations: dict[str, str]) -> bool:
    source = record["source"]
    normalized = normalize(source)
    if normalized in DEFERRED_FRAGMENTS:
        return True
    if record["table"] == "RuleBreakTable_en":
        return True
    if not re.search(r"[A-Za-z]", normalized):
        return True
    if normalized in translations or normalized.strip() in translations:
        return True
    if normalized.startswith("SPECIAL THANKS\n") or normalized.startswith("ADDITIONAL DESIGN\n"):
        return True

    for pattern in translations:
        if pattern.endswith(" ") and normalized.startswith(pattern):
            return True
        if "{" not in pattern:
            continue
        expression = re.escape(pattern)
        expression = re.sub(r"\\\{[A-Za-z_][A-Za-z0-9_]*\\\}", r".+?", expression)
        if re.fullmatch(expression, normalized):
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--translation", type=Path, default=Path("translation.txt"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    translations, duplicates = load_translation(args.translation)
    records = load_english_strings(args.game)
    missing = [record for record in records if not is_covered(record, translations)]
    report = {
        "translation_count": len(translations),
        "game_string_count": len(records),
        "covered_count": len(records) - len(missing),
        "missing_count": len(missing),
        "duplicates": duplicates,
        "missing": missing,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
