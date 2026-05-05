"""Create single clean projects file - one row per project, no garbage."""

import json
import csv
import re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_JSON = DATA_DIR / "seed" / "projects_complete.json"
OUTPUT_CSV = DATA_DIR / "projects_clean.csv"
OUTPUT_JSON = DATA_DIR / "projects_clean.json"


def is_garbage_title(title: str) -> bool:
    """Check if title is garbage (tech category, not a real project)."""
    if not title:
        return True

    title_clean = title.strip()
    title_lower = title_clean.lower()

    # Too short
    if len(title_clean) < 3:
        return True

    # Looks like tech area list, not project name
    tech_patterns = [
        r'^cv\s*\(?computer vision\)?',
        r'^nlp\s*$',
        r'^ml\s*$',
        r'^asr[,\s]',
        r'^backend[,\s]',
        r'^frontend[,\s]',
        r'^data\s*(scientist|engineer)',
        r'^classic\s*ml',
        r'^computer vision',
        r'^speech',
        r'^rag\s*$',
        r'^llm\s*$',
        r'^\d+$',  # Just numbers
        r'^студент_\d+',
        r'^@user_',
        r'^user_\d+',
        r'^\d{1,2}:\d{2}',  # Time
    ]

    for pattern in tech_patterns:
        if re.match(pattern, title_lower):
            return True

    # Contains multiple tech areas separated by commas (likely a category list)
    tech_keywords = ['cv', 'nlp', 'asr', 'tts', 'rag', 'llm', 'ml']
    comma_parts = [p.strip().lower() for p in title_clean.split(',')]
    if len(comma_parts) >= 2:
        tech_count = sum(1 for p in comma_parts if any(t in p for t in tech_keywords))
        if tech_count >= 2:
            return True

    # Check for patterns like "CV (Computer Vision), ML в промышленности"
    if re.search(r'\([^)]+\)\s*,\s*\w', title_clean):
        if any(t in title_lower for t in tech_keywords):
            return True

    return False


def is_valid_project(project: dict) -> bool:
    """Check if project entry is valid and has meaningful data."""
    title = project.get('title', '').strip()

    if is_garbage_title(title):
        return False

    # Must have at least some useful data
    has_description = bool(project.get('description', '').strip())
    has_score = project.get('avg_score', 0) > 0
    has_links = bool(project.get('links'))
    has_room = bool(project.get('rooms'))
    has_author = bool(project.get('author', '').strip())
    has_expected = bool(project.get('expected_result', '').strip())

    # Project should have at least description OR score OR be in schedule
    return has_description or has_score or has_room or has_links or has_expected


def clean_title(title: str) -> str:
    """Clean up title string."""
    # Remove extra quotes
    title = re.sub(r'^["\'"«»]+|["\'"»«]+$', '', title.strip())
    # Remove newlines
    title = re.sub(r'[\n\r]+', ' ', title)
    # Collapse whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def clean_description(desc: str) -> str:
    """Clean up description, remove [Трек: ...] prefix."""
    if not desc:
        return ""
    # Remove track prefix
    desc = re.sub(r'^\[Трек:\s*[^\]]+\]\s*', '', desc.strip())
    # Remove extra quotes
    desc = re.sub(r'^["\'"]+|["\'"]+$', '', desc)
    return desc.strip()


def extract_track(project: dict) -> str:
    """Extract track from various fields."""
    # Direct track field
    track = project.get('track', '').strip()
    if track and track not in ['Unknown', 'Demo Day', 'AI Talent Conf']:
        return track

    # From description
    desc = project.get('description', '')
    match = re.search(r'\[Трек:\s*([^\]]+)\]', desc)
    if match:
        return match.group(1).strip()

    # From tracks list
    tracks = project.get('tracks', [])
    for t in tracks:
        if t and t not in ['Demo Day', 'AI Talent Conf']:
            return t

    # Infer from room name
    rooms = project.get('rooms', []) or []
    rooms_str = ' '.join(rooms).lower()

    if any(x in rooms_str for x in ['research', 'conf', 'аспирант', 'постер']):
        return 'Научный'
    if any(x in rooms_str for x in ['прожарка', 'бизнес']):
        return 'Demo Day (Бизнес)'
    if any(x in rooms_str for x in ['стартап', 'startup']):
        return 'Стартап'
    if rooms_str:  # Has room but couldn't determine track
        return 'Demo Day'

    return ""


def normalize_tags(tags: list, rooms: list = None) -> list:
    """Normalize and deduplicate tags, also extract from rooms."""
    all_tags = list(tags) if tags else []

    # Extract tags from room names
    if rooms:
        rooms_str = ' '.join(rooms).lower()
        room_tag_map = {
            'edtech': 'EdTech',
            'fintech': 'FinTech',
            'nlp': 'NLP',
            'recsys': 'RecSys',
            'рекомендат': 'RecSys',
            'audio': 'Audio',
            'agent': 'Агенты',
            'multiagent': 'Агенты',
            'медицин': 'MedTech',
            'cv': 'CV',
            'промышлен': 'ML в промышленности',
            'security': 'Security',
        }
        for pattern, tag in room_tag_map.items():
            if pattern in rooms_str:
                all_tags.append(tag)

    # Normalize tag names
    tag_map = {
        'ml в промышленности': 'ML в промышленности',
        'автономные агенты': 'Агенты',
        'стартап': 'Стартап',
        'research': 'Research',
        'edtech': 'EdTech',
        'fintech': 'FinTech',
        'medtech': 'MedTech',
        'biotech': 'BioTech',
        'geoai': 'GeoAI',
        'recsys': 'RecSys',
        'gaming': 'Gaming',
        'audio': 'Audio',
        'security': 'Security',
        'business': 'Business',
        'hr': 'HR',
    }

    normalized = []
    seen = set()
    for tag in all_tags:
        tag_clean = tag.strip()
        tag_lower = tag_clean.lower()

        # Skip garbage tags
        if not tag_clean or len(tag_clean) < 2:
            continue

        # Map to normalized form
        tag_final = tag_map.get(tag_lower, tag_clean)

        if tag_final.lower() not in seen:
            seen.add(tag_final.lower())
            normalized.append(tag_final)

    return sorted(normalized)


def merge_duplicates(projects: list) -> list:
    """Merge duplicate projects by normalized title."""
    merged = {}

    for p in projects:
        title = clean_title(p.get('title', ''))
        key = title.lower().strip()

        if key in merged:
            # Merge data - keep the richer version
            existing = merged[key]

            # Keep longer description
            if len(p.get('description', '')) > len(existing.get('description', '')):
                existing['description'] = p['description']

            # Merge lists
            for field in ['rooms', 'days', 'time_slots', 'links', 'tags', 'tech_areas']:
                existing_list = existing.get(field, []) or []
                new_list = p.get(field, []) or []
                existing[field] = list(set(existing_list + new_list))

            # Keep non-empty values
            for field in ['author', 'telegram_contact', 'track', 'course', 'expected_result', 'repository']:
                if p.get(field) and not existing.get(field):
                    existing[field] = p[field]

            # Keep higher scores
            if (p.get('avg_score') or 0) > (existing.get('avg_score') or 0):
                existing['avg_score'] = p['avg_score']
                existing['expert_count'] = p.get('expert_count', 0)
                existing['scores_by_criterion'] = p.get('scores_by_criterion', {})

            # Merge comments
            existing_comments = existing.get('expert_comments', []) or []
            new_comments = p.get('expert_comments', []) or []
            existing['expert_comments'] = list(set(existing_comments + new_comments))

            # Keep mentor involvement
            if p.get('mentor_involvement') and not existing.get('mentor_involvement'):
                existing['mentor_involvement'] = p['mentor_involvement']
        else:
            merged[key] = p.copy()
            merged[key]['title'] = title  # Use cleaned title

    return list(merged.values())


def main():
    print("Loading data...")
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"  Loaded {len(data)} entries")

    # Filter valid projects
    print("\nFiltering garbage...")
    valid = [p for p in data if is_valid_project(p)]
    print(f"  Valid projects: {len(valid)} (removed {len(data) - len(valid)} garbage)")

    # Merge duplicates
    print("\nMerging duplicates...")
    merged = merge_duplicates(valid)
    print(f"  After merge: {len(merged)} unique projects")

    # Clean up each project
    print("\nCleaning data...")
    clean_projects = []
    for p in merged:
        project = {
            'title': clean_title(p.get('title', '')),
            'track': extract_track(p),
            'course': p.get('course', ''),
            'rooms': '; '.join(sorted(set(p.get('rooms', []) or []))),
            'days': '; '.join(sorted(set(p.get('days', []) or []))),
            'time_slots': '; '.join(sorted(set(p.get('time_slots', []) or []))),
            'description': clean_description(p.get('description', '')),
            'expected_result': p.get('expected_result', '').strip(),
            'tags': '; '.join(normalize_tags(p.get('tags', []), p.get('rooms', []))),
            'tech_areas': '; '.join(sorted(set(p.get('tech_areas', []) or []))),
            'author': p.get('author', ''),
            'telegram': p.get('telegram_contact', ''),
            'links': '; '.join(sorted(set(p.get('links', []) or []))),
            'repository': p.get('repository', ''),
            'avg_score': p.get('avg_score', 0) or '',
            'expert_count': p.get('expert_count', 0) or '',
            'mentor_score': p.get('mentor_involvement', '') or '',
            'expert_comments': ' | '.join(p.get('expert_comments', []) or []),
        }

        # Add individual criterion scores
        scores = p.get('scores_by_criterion', {}) or {}
        project['score_актуальность'] = scores.get('актуальность', '')
        project['score_практ_значимость'] = scores.get('практ_значимость', '')
        project['score_новизна'] = scores.get('новизна', '')
        project['score_импакт'] = scores.get('импакт', '')
        project['score_rd_сложность'] = scores.get('rd_сложность', '')
        project['score_масштабирование'] = scores.get('масштабирование', '')
        project['score_критерий_7'] = scores.get('критерий_7', '')

        clean_projects.append(project)

    # Sort by title
    clean_projects.sort(key=lambda x: x['title'].lower())

    # Write CSV
    print(f"\nWriting CSV: {OUTPUT_CSV}")
    fieldnames = [
        'title', 'track', 'course', 'rooms', 'days', 'time_slots',
        'description', 'expected_result', 'tags', 'tech_areas',
        'author', 'telegram', 'links', 'repository',
        'avg_score', 'expert_count', 'mentor_score',
        'score_актуальность', 'score_практ_значимость', 'score_новизна',
        'score_импакт', 'score_rd_сложность', 'score_масштабирование', 'score_критерий_7',
        'expert_comments',
    ]

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean_projects)

    # Write JSON
    print(f"Writing JSON: {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(clean_projects, f, ensure_ascii=False, indent=2)

    # Stats
    print("\n" + "=" * 60)
    print("CLEAN DATA SUMMARY")
    print("=" * 60)
    print(f"Total projects: {len(clean_projects)}")

    with_desc = sum(1 for p in clean_projects if p['description'])
    with_scores = sum(1 for p in clean_projects if p['avg_score'])
    with_links = sum(1 for p in clean_projects if p['links'])
    with_rooms = sum(1 for p in clean_projects if p['rooms'])

    print(f"With description: {with_desc}")
    print(f"With expert scores: {with_scores}")
    print(f"With links: {with_links}")
    print(f"In DD schedule: {with_rooms}")

    # By track
    tracks = defaultdict(int)
    for p in clean_projects:
        tracks[p['track'] or 'Не указан'] += 1
    print("\nBy track:")
    for t, c in sorted(tracks.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    print("\nFiles created:")
    print(f"  {OUTPUT_CSV} ({OUTPUT_CSV.stat().st_size / 1024:.1f} KB)")
    print(f"  {OUTPUT_JSON} ({OUTPUT_JSON.stat().st_size / 1024:.1f} KB)")


if __name__ == '__main__':
    main()
