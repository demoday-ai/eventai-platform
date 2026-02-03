"""Rebuild projects_final with tags from room_theme when empty."""

import pandas as pd
import json
import re
import csv
from pathlib import Path
from difflib import SequenceMatcher

DATA_DIR = Path(__file__).parent.parent / "data"


def normalize(title):
    if not title:
        return ""
    t = title.lower().strip()
    t = re.sub(r'[""«»\'"\-–—\(\)\[\]]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def main():
    # 1. Parse Excel schedule with room_theme
    print('1. Parsing Excel...')
    df1 = pd.read_excel(DATA_DIR / 'Копия Прим сетка ДД 26.xlsx', sheet_name=0, header=None)

    room_cols = [
        (0, 1, 2, 'Комната 1', 'EdTech'),
        (5, 6, 7, 'Комната 2', 'RecSys'),
        (10, 11, 12, 'Комната 3', 'LLM/VLM'),
        (15, 16, 17, 'Комната 4', 'NLP'),
        (20, 21, 22, 'Комната 5', 'ML в промышленности'),
        (25, 26, 27, 'Комната 6', 'FinTech'),
    ]

    schedule = []
    for row_idx in range(4, len(df1)):
        row = df1.iloc[row_idx]
        for time_col, proj_col, tag_col, room_name, room_theme in room_cols:
            proj_val = row.iloc[proj_col] if proj_col < len(row) else None
            if pd.isna(proj_val) or not str(proj_val).strip():
                continue
            proj_str = str(proj_val).strip()
            if 'Проект' in proj_str or len(proj_str) < 5:
                continue

            lines = proj_str.split('\n')
            title = lines[0].replace('        ', ' ').strip()
            team = lines[1].strip() if len(lines) > 1 else ''

            time_val = row.iloc[time_col] if time_col < len(row) else None
            time_str = str(time_val).replace(':00:00', ':00').strip() if pd.notna(time_val) else ''

            tag_val = row.iloc[tag_col] if tag_col < len(row) else None
            tags = str(tag_val).strip() if pd.notna(tag_val) else ''

            # If tags empty, use room_theme
            if not tags:
                tags = room_theme

            schedule.append({
                'title': title,
                'team': team,
                'time': time_str,
                'room': room_name,
                'room_theme': room_theme,
                'tags': tags,
                'day': '2026-01-22',
            })

    # Sheet 2 - AI Talent Conf
    df2 = pd.read_excel(DATA_DIR / 'Копия Прим сетка ДД 26.xlsx', sheet_name=1, header=None)
    room_cols_2 = [
        (1, 2, 3, 'Research 1', 'Audio'),
        (6, 7, 8, 'Research 2', 'Security'),
        (11, 12, 13, 'Research 3', 'NLP'),
        (17, 18, 19, 'Research 4', 'Agents'),
    ]

    for row_idx in range(2, len(df2)):
        row = df2.iloc[row_idx]
        for time_col, proj_col, tag_col, room_name, room_theme in room_cols_2:
            proj_val = row.iloc[proj_col] if proj_col < len(row) else None
            if pd.isna(proj_val) or not str(proj_val).strip():
                continue
            proj_str = str(proj_val).strip()
            if 'Проект' in proj_str or len(proj_str) < 5:
                continue

            lines = proj_str.split('\n')
            title = lines[0].replace('        ', ' ').strip()
            team = lines[1].strip() if len(lines) > 1 else ''

            time_val = row.iloc[time_col] if time_col < len(row) else None
            time_str = str(time_val).strip() if pd.notna(time_val) else ''

            tag_val = row.iloc[tag_col] if tag_col < len(row) else None
            tags = str(tag_val).strip() if pd.notna(tag_val) else ''

            if not tags:
                tags = room_theme

            schedule.append({
                'title': title,
                'team': team,
                'time': time_str,
                'room': room_name,
                'room_theme': room_theme,
                'tags': tags,
                'day': '2026-01-23',
            })

    print(f'   {len(schedule)} entries from schedule')
    with_tags = sum(1 for p in schedule if p['tags'])
    print(f'   С тегами: {with_tags}/{len(schedule)}')

    # 2. Deduplicate
    projects = {}
    for p in schedule:
        key = normalize(p['title'])
        if key in projects:
            existing = projects[key]
            if p['room'] not in existing['rooms']:
                existing['rooms'].append(p['room'])
            if p['time'] and p['time'] not in existing['times']:
                existing['times'].append(p['time'])
            if p['day'] not in existing['days']:
                existing['days'].append(p['day'])
        else:
            projects[key] = {
                'title': p['title'],
                'team': p['team'],
                'rooms': [p['room']],
                'times': [p['time']] if p['time'] else [],
                'days': [p['day']],
                'tags': p['tags'],
                'room_theme': p['room_theme'],
            }

    print(f'   {len(projects)} unique projects')

    # 3. Load enrichment data
    # Use original seed with full descriptions
    seed_path = DATA_DIR / 'seed' / 'projects_seed_original.json'
    if not seed_path.exists():
        seed_path = DATA_DIR / 'seed' / 'projects_seed.json'
    with open(seed_path, 'r', encoding='utf-8') as f:
        seed_orig = json.load(f)
    # Use OLD seed before we overwrote it - but it's already overwritten
    # So we load from test data which has original titles

    seed_index = {normalize(s['title']): s for s in seed_orig if s.get('title') and len(s['title']) > 3}

    with open(DATA_DIR / 'test' / 'projects.json', 'r', encoding='utf-8') as f:
        test = json.load(f)
    test_index = {normalize(t['title']): t for t in test if t.get('title') and len(t['title']) > 3}

    with open(DATA_DIR / 'test' / 'students.json', 'r', encoding='utf-8') as f:
        students = json.load(f)
    students_index = {normalize(s['project']): s for s in students if s.get('project') and len(s['project']) > 3}

    # 4. Enrich
    enriched_desc = 0
    enriched_scores = 0
    enriched_students = 0

    for key, proj in projects.items():
        # From seed (fuzzy)
        best_seed = None
        if key in seed_index:
            best_seed = seed_index[key]
        else:
            best_score = 0
            for st, sd in seed_index.items():
                score = similarity(key, st)
                if score > best_score and score > 0.65:
                    best_score = score
                    best_seed = sd

        if best_seed:
            desc = best_seed.get('description', '')
            proj['description'] = re.sub(r'^\[Трек:\s*[^\]]+\]\s*', '', desc).strip()
            match = re.search(r'Ожидаемый результат[:\s]*(.+?)(?:\n\n|$)', desc, re.DOTALL)
            proj['expected_result'] = match.group(1).strip() if match else ''
            proj['author'] = best_seed.get('author', '')
            proj['telegram'] = best_seed.get('telegram_contact', '')
            urls = re.findall(r'https?://[^\s<>"\')\]]+', desc)
            proj['links'] = '; '.join(set(urls))
            enriched_desc += 1
        else:
            proj['description'] = ''
            proj['expected_result'] = ''
            proj['author'] = ''
            proj['telegram'] = ''
            proj['links'] = ''

        # From test (scores)
        best_test = None
        if key in test_index:
            best_test = test_index[key]
        else:
            for tt, td in test_index.items():
                if similarity(key, tt) > 0.65:
                    best_test = td
                    break

        if best_test:
            proj['avg_score'] = best_test.get('avg_score', 0)
            proj['expert_count'] = best_test.get('expert_count', 0)
            evals = best_test.get('evaluations', [])
            scores_by_c = {}
            comments = []
            for ev in evals:
                for c, s in ev.get('scores', {}).items():
                    scores_by_c.setdefault(c, []).append(s)
                if ev.get('comment'):
                    comments.append(ev['comment'])
            proj['scores_by_criterion'] = {c: round(sum(v)/len(v), 2) for c, v in scores_by_c.items()}
            proj['expert_comments'] = ' | '.join(comments)
            enriched_scores += 1
        else:
            proj['avg_score'] = 0
            proj['expert_count'] = 0
            proj['scores_by_criterion'] = {}
            proj['expert_comments'] = ''

        # From students
        best_stud = None
        if key in students_index:
            best_stud = students_index[key]
        else:
            for st, sd in students_index.items():
                if similarity(key, st) > 0.65:
                    best_stud = sd
                    break

        if best_stud:
            proj['track'] = best_stud.get('track', '')
            proj['course'] = best_stud.get('course', '')
            proj['tech_areas'] = '; '.join(best_stud.get('tech_areas', []))
            proj['mentor_involvement'] = best_stud.get('mentor_involvement') or ''
            enriched_students += 1
        else:
            proj['track'] = ''
            proj['course'] = ''
            proj['tech_areas'] = ''
            proj['mentor_involvement'] = ''

    print(f'   Enriched: desc={enriched_desc}, scores={enriched_scores}, students={enriched_students}')

    # 5. Build final
    final = []
    for proj in projects.values():
        entry = {
            'title': proj['title'],
            'team': proj['team'],
            'track': proj.get('track', ''),
            'course': proj.get('course', ''),
            'rooms': '; '.join(proj['rooms']),
            'days': '; '.join(proj['days']),
            'times': '; '.join(proj['times']),
            'tags': proj['tags'],
            'tech_areas': proj.get('tech_areas', ''),
            'description': proj.get('description', ''),
            'expected_result': proj.get('expected_result', ''),
            'author': proj.get('author', ''),
            'telegram': proj.get('telegram', ''),
            'links': proj.get('links', ''),
            'avg_score': proj.get('avg_score', 0),
            'expert_count': proj.get('expert_count', 0),
            'mentor_involvement': proj.get('mentor_involvement', ''),
        }
        scores = proj.get('scores_by_criterion', {})
        entry['score_актуальность'] = scores.get('актуальность', '')
        entry['score_практ_значимость'] = scores.get('практ_значимость', '')
        entry['score_новизна'] = scores.get('новизна', '')
        entry['score_импакт'] = scores.get('импакт', '')
        entry['score_rd_сложность'] = scores.get('rd_сложность', '')
        entry['score_масштабирование'] = scores.get('масштабирование', '')
        entry['score_критерий_7'] = scores.get('критерий_7', '')
        entry['expert_comments'] = proj.get('expert_comments', '')
        final.append(entry)

    final.sort(key=lambda x: (x['days'], x['times'], x['title']))

    # Save JSON
    with open(DATA_DIR / 'projects_final.json', 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    # Save CSV
    with open(DATA_DIR / 'projects_final.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(final[0].keys()))
        writer.writeheader()
        writer.writerows(final)

    # Update seed
    seed_new = []
    for p in final:
        seed_new.append({
            'title': p['title'],
            'description': p['description'] or f"Проект: {p['title']}",
            'author': p['author'] or p['team'].split(',')[0].strip() if p['team'] else 'Неизвестен',
            'telegram_contact': p['telegram'] or '@unknown',
            'tags': [t.strip() for t in p['tags'].split(';') if t.strip()] if p['tags'] else []
        })

    with open(DATA_DIR / 'seed' / 'projects_seed.json', 'w', encoding='utf-8') as f:
        json.dump(seed_new, f, ensure_ascii=False, indent=2)

    # Stats
    print('\n=== ИТОГ ===')
    print(f'Проектов: {len(final)}')
    print(f'С тегами: {sum(1 for p in final if p["tags"])}/{len(final)}')
    print(f'С описанием: {sum(1 for p in final if p["description"])}/{len(final)}')
    print(f'С оценками: {sum(1 for p in final if p["avg_score"])}/{len(final)}')
    print(f'С треком: {sum(1 for p in final if p["track"])}/{len(final)}')


if __name__ == '__main__':
    main()
