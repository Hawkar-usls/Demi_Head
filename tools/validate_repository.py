from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
LOCAL_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_json_documents() -> None:
    paths = [ROOT / "PROJECT_STATUS.json"]
    paths.extend(sorted((ROOT / "configs").glob("*.json")))
    paths.extend(sorted((ROOT / "schemas").glob("*.json")))
    for path in paths:
        load_json(path)


def validate_schemas() -> None:
    schemas = {
        path.name: load_json(path) for path in sorted((ROOT / "schemas").glob("*.json"))
    }
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)

    config = load_json(ROOT / "configs" / "example.config.json")
    Draft202012Validator(
        schemas["config.schema.json"], format_checker=FormatChecker()
    ).validate(config)


def validate_markdown_links() -> None:
    missing: list[str] = []
    for markdown in sorted(ROOT.rglob("*.md")):
        if any(part.startswith(".") for part in markdown.relative_to(ROOT).parts):
            continue
        text = markdown.read_text(encoding="utf-8")
        for match in LOCAL_LINK.finditer(text):
            raw_link = match.group(1).strip("<>")
            if raw_link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = unquote(raw_link.split("#", 1)[0])
            if not path_part:
                continue
            target = (markdown.parent / path_part).resolve()
            if not target.exists():
                missing.append(f"{markdown.relative_to(ROOT)} -> {raw_link}")

    if missing:
        details = "\n".join(f"- {item}" for item in missing)
        raise ValueError(f"Missing local Markdown targets:\n{details}")


def main() -> None:
    validate_json_documents()
    validate_schemas()
    validate_markdown_links()
    print("Repository contracts and local documentation links are valid.")


if __name__ == "__main__":
    main()
