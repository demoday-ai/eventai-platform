"""Parse ALL data sources and create comprehensive projects database."""

import json
import csv
import re
from pathlib import Path
from collections import defaultdict
from typing import Any

import pandas as pd

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
EXCEL_SCHEDULE = DATA_DIR / "Копия Прим сетка ДД 26.xlsx"
CHECKPOINT12 = DATA_DIR / "test" / "checkpoint12_anon.xlsx"
CHECKPOINT3 = DATA_DIR / "test" / "checkpoint3_anon.xlsx"
EXPERTS_22JAN = DATA_DIR / "test" / "experts_22jan_anon.xlsx"
EXPERTS_23JAN = DATA_DIR / "test" / "experts_23jan_anon.xlsx"
SEED_JSON = DATA_DIR / "seed" / "projects_seed.json"
TEST_PROJECTS_JSON = DATA_DIR / "test" / "projects.json"
STUDENTS_JSON = DATA_DIR / "test" / "students.json"
OUTPUT_CSV = DATA_DIR / "seed" / "projects_complete.csv"
OUTPUT_JSON = DATA_DIR / "seed" / "projects_complete.json"


def normalize_title(title: str) -> str:
    """Normalize title for matching."""
    if not title:
        return ""
    title = re.sub(r'[""«»\'"\n\r]', ' ', title.strip().lower())
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def extract_links(text: str) -> list[str]:
    """Extract all URLs from text."""
    if not text:
        return []
    # Match URLs
    url_pattern = r'https?://[^\s<>"\')\]]+|www\.[^\s<>"\')\]]+'
    urls = re.findall(url_pattern, text)
    # Clean trailing punctuation
    urls = [re.sub(r'[.,;:!?\)]+$', '', u) for u in urls]
    return list(set(urls))


def extract_expected_result(text: str) -> str:
    """Extract 'Ожидаемый результат' section from description."""
    if not text:
        return ""
    # Look for pattern
    match = re.search(r'Ожидаемый результат[:\s]*(.+?)(?:\n\n|$)', text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def extract_track_from_description(text: str) -> str:
    """Extract track from [Трек: XXX] pattern."""
    if not text:
        return ""
    match = re.search(r'\[Трек:\s*([^\]]+)\]', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_tags_from_text(text: str) -> list[str]:
    """Extract tags from text content."""
    if not text:
        return []

    tags = []
    text_lower = text.lower()

    tag_patterns = {
        'EdTech': ['edtech', 'education', 'образован', 'обучен', 'курс', 'lms', 'moodle', 'трек: education'],
        'NLP': ['nlp', 'natural language', 'текст', 'llm', 'gpt', 'bert', 'языков', 'чат-бот', 'chatbot', 'генераци текст'],
        'CV': ['cv', 'computer vision', 'изображен', 'видео', 'detection', 'распознав', 'yolo', 'ocr', 'сегментац'],
        'ML в промышленности': ['промышлен', 'производств', 'индустри', 'manufacturing', 'predictive maintenance', 'трек: индустриальный'],
        'FinTech': ['fintech', 'финанс', 'банк', 'trading', 'инвестиц', 'кредит', 'торгов'],
        'RecSys': ['recsys', 'рекомендат', 'recommender', 'recommendation', 'персонализ'],
        'MedTech': ['medtech', 'медицин', 'health', 'диагност', 'врач', 'пациент', 'здоров'],
        'Автономные агенты': ['агент', 'agent', 'автономн', 'multi-agent', 'мульти-агент', 'agentic'],
        'ASR': ['asr', 'speech', 'голос', 'voice', 'распознавание речи', 'whisper', 'транскриб'],
        'RAG': ['rag', 'retrieval', 'retrieval-augmented'],
        'Security': ['security', 'безопасност', 'защит', 'киберб', 'cyber', 'уязвим', 'jailbreak', 'adversarial'],
        'BioTech': ['biotech', 'биолог', 'геном', 'genome', 'protein', 'белок', 'днк', 'dna'],
        'Стартап': ['трек: стартап'],
        'Research': ['трек: научный', 'научн'],
        'HR': ['hr', 'рекрутинг', 'найм', 'резюме', 'вакансии'],
        'Gaming': ['game', 'игр', '3d', 'unity', 'unreal'],
        'Audio': ['audio', 'аудио', 'звук', 'музык', 'tts', 'text-to-speech', 'вокализац'],
        'GeoAI': ['geo', 'карт', 'геолокац', 'gps', 'satellite', 'спутник'],
        'LLM': ['llm', 'large language model', 'языковая модель'],
        'VLM': ['vlm', 'vision language', 'мультимодал'],
    }

    for tag, patterns in tag_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                tags.append(tag)
                break

    return list(set(tags))


def is_valid_project_title(title: str) -> bool:
    """Check if title is a valid project name."""
    if not title or len(title.strip()) < 5:
        return False

    title_lower = title.lower().strip()

    # Skip patterns
    skip_patterns = [
        'комната', 'зал', 'время', 'room', 'модератор', 'эксперты:', 'эксперт:',
        'платформа:', 'research трек', 'ai talent conf', 'постерная сессия',
        'описание', 'тематика', 'формат', 'nan', 'none', 'спешлчат',
    ]

    for pattern in skip_patterns:
        if pattern in title_lower:
            return False

    # Skip time patterns
    if re.match(r'^\d{1,2}[:.]\d{2}(\s*-\s*\d{1,2}[:.]\d{2})?$', title.strip()):
        return False

    # Skip telegram usernames
    if title.strip().startswith('@') or re.match(r'^@?user_\d+$', title_lower):
        return False

    # Skip student IDs as titles
    if re.match(r'^студент_\d+$', title_lower):
        return False

    return True


def load_students_data(json_path: Path) -> dict[str, dict]:
    """Load students data indexed by project title."""
    if not json_path.exists():
        return {}

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}
    for item in data:
        project = item.get('project', '').strip()
        if project and is_valid_project_title(project):
            title_norm = normalize_title(project)
            result[title_norm] = {
                'student_id': item.get('anon_id', ''),
                'track': item.get('track', ''),
                'course': item.get('course', ''),
                'tech_areas': item.get('tech_areas', []),
                'mentor_involvement': item.get('mentor_involvement'),
                'goal_achievement': item.get('goal_achievement'),
                'review_formats': item.get('review_formats', []),
            }
    return result


def load_seed_projects(json_path: Path) -> dict[str, dict]:
    """Load seed projects with full data."""
    if not json_path.exists():
        return {}

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}
    for item in data:
        title = item.get('title', '').strip()
        if not is_valid_project_title(title):
            continue

        title_norm = normalize_title(title)
        description = item.get('description', '')

        result[title_norm] = {
            'title': title,
            'description': description,
            'author': item.get('author', ''),
            'telegram_contact': item.get('telegram_contact', ''),
            'tags': item.get('tags', []),
            'track': extract_track_from_description(description),
            'expected_result': extract_expected_result(description),
            'links': extract_links(description),
        }
    return result


def load_test_projects(json_path: Path) -> dict[str, dict]:
    """Load test projects with evaluations."""
    if not json_path.exists():
        return {}

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = {}
    for item in data:
        title = item.get('title', '').strip()
        if not is_valid_project_title(title):
            continue

        title_norm = normalize_title(title)

        # Process evaluations
        evaluations = item.get('evaluations', [])
        scores_detail = {}
        comments = []

        for ev in evaluations:
            scores = ev.get('scores', {})
            for criterion, score in scores.items():
                if criterion not in scores_detail:
                    scores_detail[criterion] = []
                scores_detail[criterion].append(score)
            comment = ev.get('comment', '').strip()
            if comment:
                comments.append(comment)

        # Calculate average scores per criterion
        avg_scores = {}
        for criterion, values in scores_detail.items():
            avg_scores[criterion] = round(sum(values) / len(values), 2) if values else 0

        result[title_norm] = {
            'rooms': item.get('rooms', []),
            'days': item.get('days', []),
            'formats': item.get('formats', []),
            'time_slots': item.get('time_slots', []),
            'tags': item.get('tags', []),
            'avg_score': item.get('avg_score', 0),
            'expert_count': item.get('expert_count', 0),
            'scores_by_criterion': avg_scores,
            'expert_comments': comments,
        }
    return result


def parse_excel_schedule(excel_path: Path) -> list[dict]:
    """Parse Demo Day schedule from Excel."""
    if not excel_path.exists():
        return []

    projects = []
    xl = pd.ExcelFile(excel_path)

    for sheet_name in xl.sheet_names:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
        if df.empty:
            continue

        # Determine day
        if '23' in sheet_name or 'Conf' in sheet_name:
            day = '2026-01-23'
            track = 'AI Talent Conf' if 'Conf' in sheet_name else 'Demo Day'
        else:
            day = '2026-01-22'
            track = 'Demo Day'

        # Find room columns
        room_cols = {}
        time_col = 0

        for row_idx in range(min(5, len(df))):
            row = df.iloc[row_idx]
            for col_idx, cell in enumerate(row):
                cell_str = str(cell).lower() if pd.notna(cell) else ''
                if 'время' in cell_str or 'time' in cell_str:
                    time_col = col_idx
                elif any(x in cell_str for x in ['комната', 'зал', 'room', 'edtech', 'nlp', 'recsys', 'fintech', 'cv', 'ml в пром', 'research']):
                    room_name = str(cell).split('\n')[0].strip() if pd.notna(cell) else f'Room_{col_idx}'
                    room_cols[col_idx] = room_name

        # Auto-detect if needed
        if not room_cols:
            for row_idx in [0, 1, 2]:
                if row_idx < len(df):
                    row = df.iloc[row_idx]
                    for col_idx in range(1, len(row)):
                        cell = row[col_idx]
                        if pd.notna(cell) and len(str(cell)) > 2:
                            cell_str = str(cell).strip()
                            if not any(x in cell_str.lower() for x in ['время', 'time', 'nan']):
                                room_cols[col_idx] = cell_str.split('\n')[0]

        # Parse projects
        current_time = None
        for row_idx in range(len(df)):
            row = df.iloc[row_idx]

            # Get time
            time_cell = row[time_col] if time_col < len(row) else None
            if pd.notna(time_cell):
                time_str = str(time_cell).strip()
                if re.match(r'\d{1,2}[:.]\d{2}', time_str):
                    current_time = time_str.replace('.', ':')

            # Parse each room
            for col_idx, room_name in room_cols.items():
                if col_idx >= len(row):
                    continue

                cell = row[col_idx]
                if pd.isna(cell) or str(cell).strip() == '':
                    continue

                cell_str = str(cell).strip()

                if not is_valid_project_title(cell_str):
                    continue

                if len(cell_str) < 10:
                    continue

                # Parse project
                lines = cell_str.split('\n')
                title = lines[0].strip()

                team = []
                description = ''
                for line in lines[1:]:
                    line = line.strip()
                    if any(x in line.lower() for x in ['команда:', 'team:', 'состав:']):
                        team_str = re.sub(r'^(команда|team|состав)[:\s]*', '', line, flags=re.IGNORECASE)
                        team = [m.strip() for m in team_str.split(',') if m.strip()]
                    else:
                        description += line + ' '

                # Clean room name
                room_clean = room_name.split('\n')[0].strip()
                room_clean = re.sub(r'(платформа|модератор|эксперты?):\s*.*$', '', room_clean, flags=re.IGNORECASE).strip()

                projects.append({
                    'title': title,
                    'room': room_clean,
                    'day': day,
                    'track': track,
                    'time_slot': current_time or '',
                    'team': team,
                    'description': description.strip(),
                })

    return projects


def parse_checkpoint_excel(excel_path: Path) -> dict[str, dict]:
    """Parse checkpoint Excel files for additional project info."""
    if not excel_path.exists():
        return {}

    result = {}

    try:
        xl = pd.ExcelFile(excel_path)
        for sheet_name in xl.sheet_names:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            if df.empty:
                continue

            # Look for project-related columns
            project_col = None
            for col in df.columns:
                col_lower = str(col).lower()
                if any(x in col_lower for x in ['проект', 'project', 'название']):
                    project_col = col
                    break

            if not project_col:
                continue

            for _, row in df.iterrows():
                title = str(row.get(project_col, '')).strip()
                if not is_valid_project_title(title):
                    continue

                title_norm = normalize_title(title)

                # Extract all available fields
                info = {'title': title}
                for col in df.columns:
                    val = row.get(col)
                    if pd.notna(val):
                        col_lower = str(col).lower()
                        if 'репозитор' in col_lower or 'github' in col_lower or 'repo' in col_lower:
                            info['repository'] = str(val).strip()
                        elif 'ссылк' in col_lower or 'link' in col_lower or 'url' in col_lower:
                            if 'links' not in info:
                                info['links'] = []
                            info['links'].append(str(val).strip())
                        elif 'описани' in col_lower or 'description' in col_lower:
                            info['checkpoint_description'] = str(val).strip()
                        elif 'команд' in col_lower or 'team' in col_lower:
                            info['team_info'] = str(val).strip()
                        elif 'трек' in col_lower or 'track' in col_lower:
                            info['track'] = str(val).strip()
                        elif 'тематик' in col_lower or 'topic' in col_lower:
                            info['topic'] = str(val).strip()
                        elif 'стек' in col_lower or 'stack' in col_lower or 'технолог' in col_lower:
                            info['tech_stack'] = str(val).strip()

                if title_norm not in result or len(info) > len(result[title_norm]):
                    result[title_norm] = info

    except Exception as e:
        print(f"Warning: Could not parse {excel_path}: {e}")

    return result


def merge_all_data(
    excel_projects: list[dict],
    seed_data: dict,
    test_data: dict,
    students_data: dict,
    checkpoint_data: dict,
) -> list[dict]:
    """Merge all data sources into comprehensive project list."""
    merged = {}

    # 1. Start with Excel schedule projects
    for proj in excel_projects:
        title_norm = normalize_title(proj['title'])
        if title_norm in merged:
            existing = merged[title_norm]
            existing['rooms'] = list(set(existing.get('rooms', []) + [proj['room']] if proj['room'] else []))
            existing['days'] = list(set(existing.get('days', []) + [proj['day']]))
            if proj['time_slot']:
                existing['time_slots'] = list(set(existing.get('time_slots', []) + [proj['time_slot']]))
            if proj['team']:
                existing['team'] = proj['team']
        else:
            merged[title_norm] = {
                'title': proj['title'],
                'rooms': [proj['room']] if proj['room'] else [],
                'days': [proj['day']],
                'tracks': [proj['track']],
                'time_slots': [proj['time_slot']] if proj['time_slot'] else [],
                'team': proj['team'],
                'description': proj['description'],
                'tags': [],
                'author': '',
                'telegram_contact': '',
                'track': proj['track'],
                'course': '',
                'tech_areas': [],
                'expected_result': '',
                'links': [],
                'repository': '',
                'avg_score': 0,
                'expert_count': 0,
                'scores_by_criterion': {},
                'expert_comments': [],
                'mentor_involvement': None,
            }

    # 2. Enrich with seed data
    for title_norm, seed in seed_data.items():
        if title_norm in merged:
            proj = merged[title_norm]
            if seed.get('description') and (not proj['description'] or len(seed['description']) > len(proj['description'])):
                proj['description'] = seed['description']
            if seed.get('author'):
                proj['author'] = seed['author']
            if seed.get('telegram_contact'):
                proj['telegram_contact'] = seed['telegram_contact']
            if seed.get('tags'):
                proj['tags'] = list(set(proj['tags'] + seed['tags']))
            if seed.get('track'):
                proj['track'] = seed['track']
            if seed.get('expected_result'):
                proj['expected_result'] = seed['expected_result']
            if seed.get('links'):
                proj['links'] = list(set(proj.get('links', []) + seed['links']))
        else:
            merged[title_norm] = {
                'title': seed['title'],
                'rooms': [],
                'days': [],
                'tracks': [],
                'time_slots': [],
                'team': [],
                'description': seed.get('description', ''),
                'tags': seed.get('tags', []),
                'author': seed.get('author', ''),
                'telegram_contact': seed.get('telegram_contact', ''),
                'track': seed.get('track', ''),
                'course': '',
                'tech_areas': [],
                'expected_result': seed.get('expected_result', ''),
                'links': seed.get('links', []),
                'repository': '',
                'avg_score': 0,
                'expert_count': 0,
                'scores_by_criterion': {},
                'expert_comments': [],
                'mentor_involvement': None,
            }

    # 3. Enrich with test data (evaluations)
    for title_norm, test in test_data.items():
        if title_norm in merged:
            proj = merged[title_norm]
            if test.get('rooms'):
                proj['rooms'] = list(set(proj['rooms'] + test['rooms']))
            if test.get('days'):
                proj['days'] = list(set(proj['days'] + test['days']))
            if test.get('time_slots'):
                proj['time_slots'] = list(set(proj['time_slots'] + test['time_slots']))
            if test.get('tags'):
                proj['tags'] = list(set(proj['tags'] + test['tags']))
            if test.get('avg_score'):
                proj['avg_score'] = test['avg_score']
            if test.get('expert_count'):
                proj['expert_count'] = test['expert_count']
            if test.get('scores_by_criterion'):
                proj['scores_by_criterion'] = test['scores_by_criterion']
            if test.get('expert_comments'):
                proj['expert_comments'] = test['expert_comments']
        else:
            title = test.get('title', title_norm)
            merged[title_norm] = {
                'title': title,
                'rooms': test.get('rooms', []),
                'days': test.get('days', []),
                'tracks': [],
                'time_slots': test.get('time_slots', []),
                'team': [],
                'description': '',
                'tags': test.get('tags', []),
                'author': '',
                'telegram_contact': '',
                'track': '',
                'course': '',
                'tech_areas': [],
                'expected_result': '',
                'links': [],
                'repository': '',
                'avg_score': test.get('avg_score', 0),
                'expert_count': test.get('expert_count', 0),
                'scores_by_criterion': test.get('scores_by_criterion', {}),
                'expert_comments': test.get('expert_comments', []),
                'mentor_involvement': None,
            }

    # 4. Enrich with students data
    for title_norm, student in students_data.items():
        if title_norm in merged:
            proj = merged[title_norm]
            if student.get('track') and not proj['track']:
                proj['track'] = student['track']
            if student.get('course'):
                proj['course'] = student['course']
            if student.get('tech_areas'):
                proj['tech_areas'] = student['tech_areas']
            if student.get('mentor_involvement') is not None:
                proj['mentor_involvement'] = student['mentor_involvement']
            if student.get('student_id') and not proj.get('author'):
                proj['author'] = student['student_id']

    # 5. Enrich with checkpoint data
    for title_norm, checkpoint in checkpoint_data.items():
        if title_norm in merged:
            proj = merged[title_norm]
            if checkpoint.get('repository'):
                proj['repository'] = checkpoint['repository']
            if checkpoint.get('links'):
                proj['links'] = list(set(proj.get('links', []) + checkpoint['links']))
            if checkpoint.get('tech_stack') and 'tech_stack' not in proj:
                proj['tech_stack'] = checkpoint['tech_stack']
            if checkpoint.get('topic') and 'topic' not in proj:
                proj['topic'] = checkpoint['topic']

    # 6. Extract tags from all text fields
    for title_norm, proj in merged.items():
        text = ' '.join([
            proj.get('title', ''),
            proj.get('description', ''),
            proj.get('expected_result', ''),
            proj.get('track', ''),
            ' '.join(proj.get('tech_areas', [])),
        ])
        extracted_tags = extract_tags_from_text(text)
        proj['tags'] = list(set(proj.get('tags', []) + extracted_tags))

    # 7. Filter out invalid entries
    result = []
    for proj in merged.values():
        if not is_valid_project_title(proj.get('title', '')):
            continue
        result.append(proj)

    return result


def main():
    print("=" * 70)
    print("Comprehensive Project Data Extraction")
    print("=" * 70)

    # 1. Parse Excel schedule
    print("\n1. Parsing Excel schedule...")
    excel_projects = parse_excel_schedule(EXCEL_SCHEDULE)
    print(f"   Found {len(excel_projects)} entries")

    # 2. Load seed projects
    print("\n2. Loading seed projects...")
    seed_data = load_seed_projects(SEED_JSON)
    print(f"   Found {len(seed_data)} projects")

    # 3. Load test projects (with evaluations)
    print("\n3. Loading test projects with evaluations...")
    test_data = load_test_projects(TEST_PROJECTS_JSON)
    print(f"   Found {len(test_data)} projects")

    # 4. Load students data
    print("\n4. Loading students data...")
    students_data = load_students_data(STUDENTS_JSON)
    print(f"   Found {len(students_data)} student-project mappings")

    # 5. Parse checkpoint Excel files
    print("\n5. Parsing checkpoint Excel files...")
    checkpoint_data = {}
    for checkpoint_file in [CHECKPOINT12, CHECKPOINT3]:
        if checkpoint_file.exists():
            data = parse_checkpoint_excel(checkpoint_file)
            print(f"   {checkpoint_file.name}: {len(data)} entries")
            checkpoint_data.update(data)

    # 6. Merge all data
    print("\n6. Merging all data sources...")
    merged = merge_all_data(excel_projects, seed_data, test_data, students_data, checkpoint_data)
    print(f"   Total unique projects: {len(merged)}")

    # Sort by title
    merged = sorted(merged, key=lambda x: x.get('title', '').lower())

    # 7. Write JSON
    print(f"\n7. Writing JSON to {OUTPUT_JSON}...")
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # 8. Write CSV
    print(f"8. Writing CSV to {OUTPUT_CSV}...")

    # Flatten for CSV
    fieldnames = [
        'title', 'track', 'course', 'rooms', 'days', 'time_slots', 'team',
        'description', 'expected_result', 'tags', 'tech_areas',
        'author', 'telegram_contact', 'links', 'repository',
        'avg_score', 'expert_count', 'mentor_involvement',
        'score_актуальность', 'score_практ_значимость', 'score_новизна',
        'score_импакт', 'score_rd_сложность', 'score_масштабирование', 'score_критерий_7',
        'expert_comments',
    ]

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for proj in merged:
            row = {
                'title': proj.get('title', ''),
                'track': proj.get('track', ''),
                'course': proj.get('course', ''),
                'rooms': '; '.join(proj.get('rooms', [])),
                'days': '; '.join(proj.get('days', [])),
                'time_slots': '; '.join(proj.get('time_slots', [])),
                'team': '; '.join(proj.get('team', [])),
                'description': proj.get('description', ''),
                'expected_result': proj.get('expected_result', ''),
                'tags': '; '.join(proj.get('tags', [])),
                'tech_areas': '; '.join(proj.get('tech_areas', [])),
                'author': proj.get('author', ''),
                'telegram_contact': proj.get('telegram_contact', ''),
                'links': '; '.join(proj.get('links', [])),
                'repository': proj.get('repository', ''),
                'avg_score': proj.get('avg_score', 0),
                'expert_count': proj.get('expert_count', 0),
                'mentor_involvement': proj.get('mentor_involvement', ''),
                'expert_comments': ' | '.join(proj.get('expert_comments', [])),
            }

            # Add criterion scores
            scores = proj.get('scores_by_criterion', {})
            row['score_актуальность'] = scores.get('актуальность', '')
            row['score_практ_значимость'] = scores.get('практ_значимость', '')
            row['score_новизна'] = scores.get('новизна', '')
            row['score_импакт'] = scores.get('импакт', '')
            row['score_rd_сложность'] = scores.get('rd_сложность', '')
            row['score_масштабирование'] = scores.get('масштабирование', '')
            row['score_критерий_7'] = scores.get('критерий_7', '')

            writer.writerow(row)

    # Statistics
    print("\n" + "=" * 70)
    print("Statistics")
    print("=" * 70)

    # By track
    track_counts = defaultdict(int)
    for proj in merged:
        track = proj.get('track') or 'Unknown'
        track_counts[track] += 1
    print("\nProjects by track:")
    for track, count in sorted(track_counts.items(), key=lambda x: -x[1]):
        print(f"  {track}: {count}")

    # By tag
    tag_counts = defaultdict(int)
    for proj in merged:
        for tag in proj.get('tags', []):
            tag_counts[tag] += 1
    print("\nProjects by tag (top 15):")
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {tag}: {count}")

    # With evaluations
    with_scores = sum(1 for p in merged if p.get('avg_score', 0) > 0)
    with_comments = sum(1 for p in merged if p.get('expert_comments'))
    with_links = sum(1 for p in merged if p.get('links'))
    with_repo = sum(1 for p in merged if p.get('repository'))

    print(f"\nData completeness:")
    print(f"  With expert scores: {with_scores}")
    print(f"  With expert comments: {with_comments}")
    print(f"  With links: {with_links}")
    print(f"  With repository: {with_repo}")

    print(f"\nDone! Output files:")
    print(f"  - {OUTPUT_JSON} ({OUTPUT_JSON.stat().st_size / 1024:.1f} KB)")
    print(f"  - {OUTPUT_CSV} ({OUTPUT_CSV.stat().st_size / 1024:.1f} KB)")


if __name__ == '__main__':
    main()
