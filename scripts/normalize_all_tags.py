"""Normalize tags in projects_final.json and projects_seed.json."""

import json
import sys
from pathlib import Path
from collections import Counter

# Add data dir to path
DATA_DIR = Path(__file__).parent.parent / "data"
sys.path.insert(0, str(DATA_DIR))

from tag_normalization import normalize_tags, normalize_tag, CANONICAL_TAGS


def normalize_final():
    """Normalize tags in projects_final.json."""
    path = DATA_DIR / "projects_final.json"
    with open(path, "r", encoding="utf-8") as f:
        projects = json.load(f)

    unknown_tags = Counter()

    for p in projects:
        tags_str = p.get("tags", "")
        if not tags_str:
            continue

        # Parse tags
        raw_tags = []
        for t in tags_str.replace(";", ",").split(","):
            t = t.strip()
            if t:
                raw_tags.append(t)

        # Normalize
        normalized = normalize_tags(raw_tags)

        # Track unknown
        for t in raw_tags:
            norm = normalize_tag(t)
            if norm and norm not in CANONICAL_TAGS:
                unknown_tags[t] += 1

        # Update
        p["tags"] = "; ".join(normalized) if normalized else ""

    # Save
    with open(path, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)

    print(f"projects_final.json: {len(projects)} projects updated")

    if unknown_tags:
        print("\nUnknown tags (kept as-is):")
        for tag, count in unknown_tags.most_common(10):
            print(f"  {count:3d}  {tag}")

    # Stats
    all_tags = []
    for p in projects:
        if p["tags"]:
            all_tags.extend(p["tags"].split("; "))

    counter = Counter(all_tags)
    print(f"\nNormalized tag distribution ({len(counter)} unique):")
    for tag, count in counter.most_common():
        print(f"  {count:3d}  {tag}")


def normalize_seed():
    """Normalize tags in projects_seed.json."""
    path = DATA_DIR / "seed" / "projects_seed.json"
    with open(path, "r", encoding="utf-8") as f:
        projects = json.load(f)

    for p in projects:
        raw_tags = p.get("tags", [])
        if not raw_tags:
            continue

        # Normalize
        normalized = normalize_tags(raw_tags)
        p["tags"] = normalized

    # Save
    with open(path, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)

    print(f"\nprojects_seed.json: {len(projects)} projects updated")

    # Stats
    all_tags = []
    for p in projects:
        all_tags.extend(p.get("tags", []))

    counter = Counter(all_tags)
    print(f"Tag distribution ({len(counter)} unique):")
    for tag, count in counter.most_common():
        print(f"  {count:3d}  {tag}")


if __name__ == "__main__":
    print("=== NORMALIZING TAGS ===\n")
    normalize_final()
    normalize_seed()
    print("\nDone!")
