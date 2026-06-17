#!/usr/bin/env python3
"""Import projects from a Talent Track export (projects.csv + project-NNN.md files).

CSV columns: название, описание (= md filename), трек.
Each project's full description is the contents of its .md file.

Upsert by (event_id, title):
  - new title  -> insert (embedding/parsed_content NULL -> picked up by
                  embed_projects.py and parse_artifacts.py afterwards)
  - existing   -> update description + track, and RESET embedding/parsed_content
                  to NULL so they get re-embedded / re-enriched.

Run order (inside botcli, after docker cp'ing the data in):
    python -m scripts.import_projects --csv /tmp/w2/projects.csv --md-dir /tmp/w2
    python -m scripts.parse_artifacts      # parsed_content + tech_stack
    python -m scripts.embed_projects       # embeddings (idempotent)
"""
import argparse
import asyncio
import csv
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("BOT_TOKEN", "import")

from sqlalchemy import select  # noqa: E402

from src.core.database import async_session  # noqa: E402
from src.core.sanitize import sanitize_text  # noqa: E402
from src.models.event import Event  # noqa: E402
from src.models.project import Project  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

MAX_DESC = 40000  # store at most this many chars of description (Text col is fine,
# but a 200KB md is wasteful; the аннотация/решение are well within this).


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--md-dir", required=True)
    ap.add_argument("--event-id", default=None, help="defaults to the active event")
    args = ap.parse_args()

    md_dir = Path(args.md_dir)
    rows = list(csv.DictReader(open(args.csv, encoding="utf-8")))
    logger.info("CSV rows: %d", len(rows))

    async with async_session() as db:
        if args.event_id:
            event_id = args.event_id
        else:
            ev = (await db.execute(select(Event).where(Event.is_active.is_(True)))).scalars().first()
            if not ev:
                logger.error("No active event and --event-id not given")
                return
            event_id = ev.id
        logger.info("Target event: %s", event_id)

        # Existing titles for this event -> Project, for upsert.
        existing = {
            p.title: p
            for p in (
                await db.execute(select(Project).where(Project.event_id == event_id))
            ).scalars().all()
        }

        inserted = updated = skipped = 0
        for row in rows:
            title = (row.get("название") or "").strip()
            md_name = (row.get("описание") or "").strip()
            track = (row.get("трек") or "").strip() or None
            if not title or not md_name:
                skipped += 1
                continue
            md_path = md_dir / md_name
            if not md_path.exists():
                logger.warning("md not found: %s (project %s)", md_name, title)
                skipped += 1
                continue
            desc = md_path.read_text(encoding="utf-8", errors="replace").strip()[:MAX_DESC]
            desc = sanitize_text(desc) or desc

            proj = existing.get(title)
            if proj:
                proj.description = desc
                proj.track = track
                proj.parsed_content = None   # re-enrich
                proj.embedding = None         # re-embed
                updated += 1
            else:
                db.add(Project(
                    event_id=event_id,
                    title=title[:512],
                    description=desc,
                    track=track,
                ))
                inserted += 1

        await db.commit()
        logger.info("Done. inserted=%d updated=%d skipped=%d", inserted, updated, skipped)
        logger.info("Next: python -m scripts.parse_artifacts && python -m scripts.embed_projects")


if __name__ == "__main__":
    asyncio.run(main())
