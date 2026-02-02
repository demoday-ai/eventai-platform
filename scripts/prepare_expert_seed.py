"""Merge expert-mapping.json + experts-public.json → data/seed/experts_seed.json."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SEED_DIR = DATA / "seed"

MAPPING_FILE = DATA / "expert-mapping.json"
PUBLIC_FILE = DATA / "experts-public.json"
OUTPUT_FILE = SEED_DIR / "experts_seed.json"


def main():
    mapping = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
    public = json.loads(PUBLIC_FILE.read_text(encoding="utf-8"))

    # Index public data by id
    public_by_id = {item["id"]: item for item in public}

    merged = []
    with_tags = 0
    without_tags = 0

    for item in mapping:
        exp_id = item["id"]
        pub = public_by_id.get(exp_id, {})

        tags = pub.get("expertise_tags", [])
        if tags:
            with_tags += 1
        else:
            without_tags += 1

        # Normalize telegram: strip @ if present
        telegram = item.get("telegram", "")
        if telegram and telegram.startswith("@"):
            telegram = telegram[1:]

        merged.append({
            "id": exp_id,
            "name": item.get("name", ""),
            "telegram": telegram,
            "position": pub.get("position", ""),
            "expertise_tags": tags,
            "dd_status": pub.get("dd_status", ""),
            "inviter": item.get("inviter"),
        })

    SEED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Merged {len(merged)} experts -> {OUTPUT_FILE}")
    print(f"  With tags: {with_tags}")
    print(f"  Without tags: {without_tags}")


if __name__ == "__main__":
    main()
