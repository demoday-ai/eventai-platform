"""Parse Excel schedule and merge with existing project data to create comprehensive CSV."""

import json
import csv
import re
from pathlib import Path
from collections import defaultdict

import pandas as pd

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
EXCEL_FILE = DATA_DIR / "Копия Прим сетка ДД 26.xlsx"
SEED_JSON = DATA_DIR / "seed" / "projects_seed.json"
TEST_PROJECTS_JSON = DATA_DIR / "test" / "projects.json"
OUTPUT_CSV = DATA_DIR / "seed" / "projects_full.csv"
OUTPUT_JSON = DATA_DIR / "seed" / "projects_full.json"


def normalize_title(title: str) -> str:
    """Normalize title for matching."""
    if not title:
        return ""
    # Remove quotes, extra spaces, lowercase
    title = re.sub(r'[""«»\']', '', title.strip().lower())
    title = re.sub(r'\s+', ' ', title)
    return title


def clean_room_name(room: str) -> str:
    """Clean room name, removing moderator/platform info."""
    if not room:
        return ""
    # Take only the first line if multi-line
    room = room.split('\n')[0].strip()
    # Remove "Платформа:", "Модератор:", etc.
    room = re.sub(r'(платформа|модератор|эксперты?):\s*.*$', '', room, flags=re.IGNORECASE).strip()
    return room


def extract_tags_from_text(text: str) -> list[str]:
    """Extract tags from description or cell text."""
    if not text:
        return []

    tags = []
    text_lower = text.lower()

    # Known tag patterns
    tag_patterns = {
        'EdTech': ['edtech', 'education', 'образован', 'обучен', 'курс', 'lms', 'moodle', 'трек: education'],
        'NLP': ['nlp', 'natural language', 'текст', 'llm', 'gpt', 'bert', 'языков', 'чат-бот', 'chatbot', 'генераци'],
        'CV': ['cv', 'computer vision', 'изображен', 'видео', 'detection', 'распознав', 'yolo', 'ocr', 'сегментац'],
        'ML в промышленности': ['промышлен', 'производств', 'индустри', 'manufacturing', 'predictive maintenance', 'трек: индустриальный'],
        'FinTech': ['fintech', 'финанс', 'банк', 'trading', 'инвестиц', 'кредит', 'торгов'],
        'RecSys': ['recsys', 'рекомендат', 'recommender', 'recommendation', 'персонализ'],
        'MedTech': ['medtech', 'медицин', 'health', 'диагност', 'врач', 'пациент', 'здоров'],
        'Автономные агенты': ['агент', 'agent', 'автономн', 'multi-agent', 'мульти-агент', 'agentic'],
        'ASR': ['asr', 'speech', 'голос', 'voice', 'распознавание речи', 'whisper', 'транскриб'],
        'RAG': ['rag', 'retrieval', 'retrieval-augmented'],
        'Security': ['security', 'безопасност', 'защит', 'киберб', 'cyber', 'уязвим'],
        'BioTech': ['biotech', 'биолог', 'геном', 'genome', 'protein', 'белок', 'днк', 'dna'],
        'Стартап': ['трек: стартап', 'startup'],
        'Research': ['трек: научный', 'research', 'научн'],
        'HR': ['hr', 'рекрутинг', 'найм', 'резюме', 'вакансии'],
        'Gaming': ['game', 'игр', '3d', 'unity', 'unreal'],
        'Audio': ['audio', 'аудио', 'звук', 'музык', 'tts', 'text-to-speech'],
        'GeoAI': ['geo', 'карт', 'геолокац', 'gps', 'satellite', 'спутник'],
    }

    for tag, patterns in tag_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                tags.append(tag)
                break

    return list(set(tags))


def is_header_or_noise(text: str) -> bool:
    """Check if text is a header or noise, not a real project."""
    if not text:
        return True

    text_lower = text.lower().strip()

    # Header patterns to skip
    skip_patterns = [
        'комната', 'зал', 'время', 'room', 'модератор', 'эксперты:', 'эксперт:',
        'платформа:', 'research трек', 'ai talent conf', 'постерная сессия',
        'описание', 'тематика', 'формат', 'nan', 'none', 'спешлчат',
    ]

    for pattern in skip_patterns:
        if pattern in text_lower:
            return True

    # Skip if it's just a time pattern (11:00, 12:15 - 13:15, etc.)
    if re.match(r'^\d{1,2}[:.]\d{2}(\s*-\s*\d{1,2}[:.]\d{2})?$', text.strip()):
        return True

    # Skip if it starts with @ (telegram username)
    if text.strip().startswith('@'):
        return True

    # Skip if it looks like a user reference
    if re.match(r'^@?user_\d+$', text_lower):
        return True

    # Skip if it's just a student reference
    if re.match(r'^студент_\d+$', text_lower):
        return True

    return False


def parse_excel_schedule(excel_path: Path) -> list[dict]:
    """Parse the Demo Day schedule from Excel."""
    projects = []

    # Read all sheets
    xl = pd.ExcelFile(excel_path)
    print(f"Sheets in Excel: {xl.sheet_names}")

    for sheet_name in xl.sheet_names:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
        print(f"\nParsing sheet: {sheet_name} ({len(df)} rows, {len(df.columns)} cols)")

        # Determine day based on sheet name
        if '23' in sheet_name or 'Conf' in sheet_name:
            day = '2026-01-23'
            track = 'AI Talent Conf' if 'Conf' in sheet_name else 'Demo Day'
        else:
            day = '2026-01-22'
            track = 'Demo Day'

        # Find room columns (usually have "комната", "зал", or room names)
        room_cols = {}
        time_col = None

        # Look at first few rows for headers
        for row_idx in range(min(5, len(df))):
            row = df.iloc[row_idx]
            for col_idx, cell in enumerate(row):
                cell_str = str(cell).lower() if pd.notna(cell) else ''
                if 'время' in cell_str or 'time' in cell_str:
                    time_col = col_idx
                elif any(x in cell_str for x in ['комната', 'зал', 'room', 'edtech', 'nlp', 'recsys', 'fintech', 'cv', 'ml в пром', 'research']):
                    # This might be a room header
                    room_name = str(cell).strip() if pd.notna(cell) else f'Room_{col_idx}'
                    room_cols[col_idx] = room_name
                    print(f"  Found room column {col_idx}: {room_name}")

        # If no time column found, assume first column
        if time_col is None:
            time_col = 0

        # If no room columns found, try to detect from structure
        if not room_cols:
            # Check row 1-2 for room names
            for row_idx in [0, 1, 2]:
                if row_idx < len(df):
                    row = df.iloc[row_idx]
                    for col_idx in range(1, len(row)):
                        cell = row[col_idx]
                        if pd.notna(cell) and len(str(cell)) > 2:
                            cell_str = str(cell).strip()
                            if not any(x in cell_str.lower() for x in ['время', 'time', 'nan']):
                                room_cols[col_idx] = cell_str
            print(f"  Auto-detected room columns: {room_cols}")

        # Parse project data
        current_time = None
        for row_idx in range(len(df)):
            row = df.iloc[row_idx]

            # Get time from time column
            time_cell = row[time_col] if time_col < len(row) else None
            if pd.notna(time_cell):
                time_str = str(time_cell).strip()
                # Check if it looks like a time (HH:MM or similar)
                if re.match(r'\d{1,2}[:.]\d{2}', time_str):
                    current_time = time_str.replace('.', ':')

            # Parse each room column
            for col_idx, room_name in room_cols.items():
                if col_idx >= len(row):
                    continue

                cell = row[col_idx]
                if pd.isna(cell) or str(cell).strip() == '':
                    continue

                cell_str = str(cell).strip()

                # Skip header-like cells and noise
                if is_header_or_noise(cell_str):
                    continue

                # Skip very short cells (likely not projects)
                if len(cell_str) < 10:
                    continue

                # Parse project info
                # Format might be: "Project Name\nTeam: Person1, Person2"
                lines = cell_str.split('\n')
                title = lines[0].strip()

                # Extract team members if present
                team = []
                description = ''
                for line in lines[1:]:
                    line = line.strip()
                    if any(x in line.lower() for x in ['команда:', 'team:', 'состав:']):
                        team_str = re.sub(r'^(команда|team|состав)[:\s]*', '', line, flags=re.IGNORECASE)
                        team = [m.strip() for m in team_str.split(',') if m.strip()]
                    else:
                        description += line + ' '

                # Check next column for description/team if pattern suggests
                if col_idx + 1 < len(row):
                    next_cell = row[col_idx + 1]
                    if pd.notna(next_cell):
                        next_str = str(next_cell).strip()
                        if len(next_str) > 10 and next_str not in [str(v) for v in room_cols.values()]:
                            # Might be description or team
                            if not description:
                                description = next_str

                # Extract tags
                tags = extract_tags_from_text(title + ' ' + description)

                # Add room-based tag
                room_lower = room_name.lower()
                room_tags = {
                    'edtech': 'EdTech',
                    'nlp': 'NLP',
                    'cv': 'CV',
                    'recsys': 'RecSys',
                    'рекомендат': 'RecSys',
                    'fintech': 'FinTech',
                    'промышлен': 'ML в промышленности',
                    'research': 'Research',
                    'conf': 'Research',
                    'прожарка': 'Прожарка',
                    'бизнес': 'Бизнес-партнёры',
                    'аспирант': 'Research',
                }
                for pattern, tag in room_tags.items():
                    if pattern in room_lower:
                        tags.append(tag)
                        break

                tags = list(set(tags))

                project = {
                    'title': title,
                    'room': clean_room_name(room_name),
                    'day': day,
                    'track': track,
                    'time_slot': current_time or '',
                    'team': team,
                    'description': description.strip(),
                    'tags': tags,
                    'source': 'excel_schedule',
                }
                projects.append(project)

    return projects


def load_seed_projects(json_path: Path) -> dict[str, dict]:
    """Load existing seed projects indexed by normalized title."""
    if not json_path.exists():
        return {}

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}
    for item in data:
        title = item.get('title', '').strip()
        # Skip noise entries
        if is_header_or_noise(title):
            continue
        title_norm = normalize_title(title)
        if title_norm and len(title_norm) > 3:
            result[title_norm] = item

    return result


def load_test_projects(json_path: Path) -> dict[str, dict]:
    """Load test projects with evaluations indexed by normalized title."""
    if not json_path.exists():
        return {}

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}
    for item in data:
        title = normalize_title(item.get('title', ''))
        if title:
            result[title] = item

    return result


def merge_projects(excel_projects: list[dict], seed_data: dict, test_data: dict) -> list[dict]:
    """Merge all project data sources."""
    merged = {}

    # First, add all excel projects
    for proj in excel_projects:
        title_norm = normalize_title(proj['title'])
        if title_norm in merged:
            # Merge with existing
            existing = merged[title_norm]
            existing['rooms'] = list(set(existing.get('rooms', []) + [proj['room']]))
            existing['days'] = list(set(existing.get('days', []) + [proj['day']]))
            existing['time_slots'] = list(set(existing.get('time_slots', []) + [proj['time_slot']] if proj['time_slot'] else []))
            existing['tags'] = list(set(existing.get('tags', []) + proj['tags']))
            if proj['team'] and not existing.get('team'):
                existing['team'] = proj['team']
            if proj['description'] and not existing.get('description'):
                existing['description'] = proj['description']
        else:
            merged[title_norm] = {
                'title': proj['title'],
                'rooms': [proj['room']],
                'days': [proj['day']],
                'tracks': [proj['track']],
                'time_slots': [proj['time_slot']] if proj['time_slot'] else [],
                'team': proj['team'],
                'description': proj['description'],
                'tags': proj['tags'],
                'author': '',
                'telegram_contact': '',
                'avg_score': 0,
                'expert_count': 0,
            }

    # Enrich with seed data (descriptions, authors, contacts)
    for title_norm, seed in seed_data.items():
        if title_norm in merged:
            proj = merged[title_norm]
            description = seed.get('description', '')
            if description and (not proj['description'] or len(description) > len(proj['description'])):
                proj['description'] = description
            if seed.get('author'):
                proj['author'] = seed['author']
            if seed.get('telegram_contact'):
                proj['telegram_contact'] = seed['telegram_contact']
            # Extract tags from enriched description
            extracted_tags = extract_tags_from_text(proj['title'] + ' ' + proj['description'])
            seed_tags = seed.get('tags', [])
            proj['tags'] = list(set(proj['tags'] + seed_tags + extracted_tags))
        else:
            # Add seed-only project
            description = seed.get('description', '')
            title = seed.get('title', '')
            # Extract tags from description if not already present
            extracted_tags = extract_tags_from_text(title + ' ' + description)
            existing_tags = seed.get('tags', [])
            all_tags = list(set(existing_tags + extracted_tags))

            merged[title_norm] = {
                'title': title,
                'rooms': [],
                'days': [],
                'tracks': [],
                'time_slots': [],
                'team': [],
                'description': description,
                'tags': all_tags,
                'author': seed.get('author', ''),
                'telegram_contact': seed.get('telegram_contact', ''),
                'avg_score': 0,
                'expert_count': 0,
            }

    # Enrich with test data (evaluations, scores)
    for title_norm, test in test_data.items():
        if title_norm in merged:
            proj = merged[title_norm]
            if test.get('avg_score'):
                proj['avg_score'] = test['avg_score']
            if test.get('expert_count'):
                proj['expert_count'] = test['expert_count']
            if test.get('rooms'):
                proj['rooms'] = list(set(proj['rooms'] + test['rooms']))
            if test.get('tags'):
                proj['tags'] = list(set(proj['tags'] + test['tags']))

    # Filter out bad entries and clean up rooms
    result = []
    for proj in merged.values():
        # Skip if title is noise
        if is_header_or_noise(proj['title']):
            continue
        # Skip if title is too short
        if len(proj['title'].strip()) < 5:
            continue
        # Clean room names
        proj['rooms'] = [clean_room_name(r) for r in proj['rooms'] if clean_room_name(r)]
        proj['rooms'] = list(set(proj['rooms']))  # Deduplicate
        result.append(proj)

    return result


def main():
    print("=" * 60)
    print("Parsing Demo Day projects from all sources")
    print("=" * 60)

    # Parse Excel
    print("\n1. Parsing Excel schedule...")
    excel_projects = parse_excel_schedule(EXCEL_FILE)
    print(f"   Found {len(excel_projects)} entries from Excel")

    # Load existing data
    print("\n2. Loading seed projects...")
    seed_data = load_seed_projects(SEED_JSON)
    print(f"   Found {len(seed_data)} seed projects")

    print("\n3. Loading test projects...")
    test_data = load_test_projects(TEST_PROJECTS_JSON)
    print(f"   Found {len(test_data)} test projects")

    # Merge all data
    print("\n4. Merging all sources...")
    merged = merge_projects(excel_projects, seed_data, test_data)
    print(f"   Total unique projects: {len(merged)}")

    # Write CSV
    print(f"\n5. Writing CSV to {OUTPUT_CSV}...")
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['title', 'rooms', 'days', 'tracks', 'time_slots', 'team', 'description', 'tags', 'author', 'telegram_contact', 'avg_score', 'expert_count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for proj in sorted(merged, key=lambda x: x['title']):
            row = proj.copy()
            # Convert lists to strings for CSV
            row['rooms'] = '; '.join(row['rooms'])
            row['days'] = '; '.join(row['days'])
            row['tracks'] = '; '.join(row.get('tracks', []))
            row['time_slots'] = '; '.join(row['time_slots'])
            row['team'] = '; '.join(row['team'])
            row['tags'] = '; '.join(row['tags'])
            writer.writerow(row)

    # Write JSON too
    print(f"6. Writing JSON to {OUTPUT_JSON}...")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(sorted(merged, key=lambda x: x['title']), f, ensure_ascii=False, indent=2)

    # Print statistics
    print("\n" + "=" * 60)
    print("Statistics:")
    print("=" * 60)

    # Count by tags
    tag_counts = defaultdict(int)
    for proj in merged:
        for tag in proj['tags']:
            tag_counts[tag] += 1

    print("\nProjects by tag:")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")

    # Count by day
    day_counts = defaultdict(int)
    for proj in merged:
        for day in proj['days']:
            day_counts[day] += 1

    print("\nProjects by day:")
    for day, count in sorted(day_counts.items()):
        print(f"  {day}: {count}")

    # Count by room
    room_counts = defaultdict(int)
    for proj in merged:
        for room in proj['rooms']:
            room_counts[room] += 1

    print("\nProjects by room:")
    for room, count in sorted(room_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {room}: {count}")

    print("\nDone! Output files:")
    print(f"  - {OUTPUT_CSV}")
    print(f"  - {OUTPUT_JSON}")


if __name__ == '__main__':
    main()
