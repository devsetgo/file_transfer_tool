from __future__ import annotations

from datetime import datetime
import re


def ask_with_default(prompt: str, default: str) -> str:
    value = input(prompt).strip()
    return value if value else default


def slugify_theme(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9\s-]", "", lowered)
    slug = re.sub(r"[\s-]+", "-", lowered).strip("-")
    return slug or "untitled"


def format_bytes(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{num_bytes} B"


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def choose_menu_index(title: str, options: list[str]) -> int:
    if not options:
        raise ValueError("No options were provided.")

    print(f"\n{title}\n")
    for index, option in enumerate(options, start=1):
        print(f"{index}. {option}")

    while True:
        choice = input("\nSelect option number: ").strip()
        if not choice.isdigit():
            print("Please enter a valid number.")
            continue
        selected = int(choice)
        if 1 <= selected <= len(options):
            return selected - 1
        print("Selection out of range.")
