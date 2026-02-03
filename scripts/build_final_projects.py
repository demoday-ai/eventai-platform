"""Build final clean projects file from schedule + enrichment."""

import json
import re
import csv
from pathlib import Path
from difflib import SequenceMatcher

DATA_DIR = Path(__file__).parent.parent / "data"


def normalize(title):
    """Normalize title for matching."""
    if not title:
        return ""
    t = title.lower().strip()
    t = re.sub(r'[""«»\'"\-–—\(\)\[\]]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def similarity(a, b):
    """Calculate string similarity."""
    return SequenceMatcher(None, a, b).ratio()


def clean_description(desc):
    """Remove [Трек: X] prefix from description."""
    if not desc:
        return ""
    desc = re.sub(r'^\[Трек:\s*[^\]]+\]\s*', '', desc.strip())
    desc = re.sub(r'^["\'"]+|["\'"]+$', '', desc)
    return desc.strip()


def extract_expected_result(desc):
    """Extract expected result from description."""
    if not desc:
        return ""
    match = re.search(r'Ожидаемый результат[:\s]*(.+?)(?:\n\n|$)', desc, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_links(text):
    """Extract URLs from text."""
    if not text:
        return []
    urls = re.findall(r'https?://[^\s<>"\')\]]+', text)
    return list(set(urls))


def main():
    print("=" * 60)
    print("Building Final Projects File")
    print("=" * 60)

    # 1. Load schedule (base data)
    print("\n1. Loading schedule...")
    with open(DATA_DIR / "schedule_raw.json", 'r', encoding='utf-8') as f:
        schedule = json.load(f)
    print(f"   {len(schedule)} entries from schedule")

    # 2. Load seed data (descriptions)
    print("\n2. Loading seed data...")
    with open(DATA_DIR / "seed" / "projects_seed.json", 'r', encoding='utf-8') as f:
        seed = json.load(f)
    print(f"   {len(seed)} entries with descriptions")

    # 3. Load test data (scores)
    print("\n3. Loading test data (scores)...")
    with open(DATA_DIR / "test" / "projects.json", 'r', encoding='utf-8') as f:
        test = json.load(f)
    print(f"   {len(test)} entries with scores")

    # 4. Load students data
    print("\n4. Loading students data...")
    with open(DATA_DIR / "test" / "students.json", 'r', encoding='utf-8') as f:
        students = json.load(f)
    print(f"   {len(students)} student records")

    # Build indexes
    seed_index = {}
    for s in seed:
        t = normalize(s.get('title', ''))
        if t and len(t) > 3:
            seed_index[t] = s

    test_index = {}
    for t in test:
        title = normalize(t.get('title', ''))
        if title and len(title) > 3:
            test_index[title] = t

    students_index = {}
    for s in students:
        t = normalize(s.get('project', ''))
        if t and len(t) > 3:
            students_index[t] = s

    # 5. Deduplicate and merge schedule entries
    print("\n5. Deduplicating schedule...")
    projects = {}
    for p in schedule:
        title = p['title'].strip()
        key = normalize(title)

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
                'title': title,
                'team': p['team'],
                'rooms': [p['room']],
                'times': [p['time']] if p['time'] else [],
                'days': [p['day']],
                'room_theme': p['room_theme'],
                'tags': p['tags'],
                'format': p['format'],
            }

    print(f"   {len(projects)} unique projects")

    # 6. Enrich with descriptions (fuzzy match)
    print("\n6. Enriching with descriptions...")
    enriched_desc = 0
    for key, proj in projects.items():
        # Try exact match first
        if key in seed_index:
            s = seed_index[key]
            proj['description'] = clean_description(s.get('description', ''))
            proj['expected_result'] = extract_expected_result(s.get('description', ''))
            proj['author'] = s.get('author', '')
            proj['telegram'] = s.get('telegram_contact', '')
            proj['links'] = extract_links(s.get('description', ''))
            enriched_desc += 1
            continue

        # Fuzzy match
        best_match = None
        best_score = 0
        for st, seed_data in seed_index.items():
            score = similarity(key, st)
            if score > best_score and score > 0.65:
                best_score = score
                best_match = seed_data

        if best_match:
            proj['description'] = clean_description(best_match.get('description', ''))
            proj['expected_result'] = extract_expected_result(best_match.get('description', ''))
            proj['author'] = best_match.get('author', '')
            proj['telegram'] = best_match.get('telegram_contact', '')
            proj['links'] = extract_links(best_match.get('description', ''))
            enriched_desc += 1
        else:
            proj['description'] = ''
            proj['expected_result'] = ''
            proj['author'] = ''
            proj['telegram'] = ''
            proj['links'] = []

    print(f"   {enriched_desc} enriched with descriptions")

    # 7. Enrich with scores
    print("\n7. Enriching with scores...")
    enriched_scores = 0
    for key, proj in projects.items():
        # Exact match
        if key in test_index:
            t = test_index[key]
            proj['avg_score'] = t.get('avg_score', 0)
            proj['expert_count'] = t.get('expert_count', 0)
            proj['evaluations'] = t.get('evaluations', [])
            enriched_scores += 1
        else:
            # Fuzzy match
            best_match = None
            best_score = 0
            for tt, test_data in test_index.items():
                score = similarity(key, tt)
                if score > best_score and score > 0.65:
                    best_score = score
                    best_match = test_data

            if best_match:
                proj['avg_score'] = best_match.get('avg_score', 0)
                proj['expert_count'] = best_match.get('expert_count', 0)
                proj['evaluations'] = best_match.get('evaluations', [])
                enriched_scores += 1
            else:
                proj['avg_score'] = 0
                proj['expert_count'] = 0
                proj['evaluations'] = []

    print(f"   {enriched_scores} enriched with scores")

    # 8. Enrich with student data
    print("\n8. Enriching with student data...")
    enriched_students = 0
    for key, proj in projects.items():
        if key in students_index:
            s = students_index[key]
            proj['track'] = s.get('track', '')
            proj['course'] = s.get('course', '')
            proj['tech_areas'] = s.get('tech_areas', [])
            proj['mentor_involvement'] = s.get('mentor_involvement')
            enriched_students += 1
        else:
            # Try fuzzy
            best_match = None
            best_score = 0
            for st, stud_data in students_index.items():
                score = similarity(key, st)
                if score > best_score and score > 0.65:
                    best_score = score
                    best_match = stud_data

            if best_match:
                proj['track'] = best_match.get('track', '')
                proj['course'] = best_match.get('course', '')
                proj['tech_areas'] = best_match.get('tech_areas', [])
                proj['mentor_involvement'] = best_match.get('mentor_involvement')
                enriched_students += 1
            else:
                proj['track'] = ''
                proj['course'] = ''
                proj['tech_areas'] = []
                proj['mentor_involvement'] = None

    print(f"   {enriched_students} enriched with student data")

    # 9. Build final list
    print("\n9. Building final list...")
    final = []
    for key, proj in projects.items():
        # Calculate criterion scores
        scores_by_criterion = {}
        comments = []
        for ev in proj.get('evaluations', []):
            for criterion, score in ev.get('scores', {}).items():
                if criterion not in scores_by_criterion:
                    scores_by_criterion[criterion] = []
                scores_by_criterion[criterion].append(score)
            if ev.get('comment'):
                comments.append(ev['comment'])

        avg_criterion_scores = {}
        for c, vals in scores_by_criterion.items():
            avg_criterion_scores[c] = round(sum(vals) / len(vals), 2) if vals else 0

        entry = {
            'title': proj['title'],
            'team': proj['team'],
            'track': proj.get('track') or '',
            'course': proj.get('course') or '',
            'rooms': '; '.join(proj['rooms']),
            'days': '; '.join(proj['days']),
            'times': '; '.join(proj['times']),
            'room_theme': proj['room_theme'],
            'format': proj['format'],
            'tags': proj['tags'],
            'tech_areas': '; '.join(proj.get('tech_areas', [])),
            'description': proj.get('description', ''),
            'expected_result': proj.get('expected_result', ''),
            'author': proj.get('author', ''),
            'telegram': proj.get('telegram', ''),
            'links': '; '.join(proj.get('links', [])),
            'avg_score': proj.get('avg_score', 0),
            'expert_count': proj.get('expert_count', 0),
            'mentor_involvement': proj.get('mentor_involvement') or '',
            'score_актуальность': avg_criterion_scores.get('актуальность', ''),
            'score_практ_значимость': avg_criterion_scores.get('практ_значимость', ''),
            'score_новизна': avg_criterion_scores.get('новизна', ''),
            'score_импакт': avg_criterion_scores.get('импакт', ''),
            'score_rd_сложность': avg_criterion_scores.get('rd_сложность', ''),
            'score_масштабирование': avg_criterion_scores.get('масштабирование', ''),
            'score_критерий_7': avg_criterion_scores.get('критерий_7', ''),
            'expert_comments': ' | '.join(comments),
        }
        final.append(entry)

    # Sort by day, time, title
    final.sort(key=lambda x: (x['days'], x['times'], x['title']))

    # 10. Save
    print("\n10. Saving files...")

    # JSON
    json_path = DATA_DIR / "projects_final.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    print(f"   JSON: {json_path}")

    # CSV
    csv_path = DATA_DIR / "projects_final.csv"
    fieldnames = list(final[0].keys())
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final)
    print(f"   CSV: {csv_path}")

    # Stats
    print("\n" + "=" * 60)
    print("FINAL STATS")
    print("=" * 60)
    print(f"Total projects: {len(final)}")
    print(f"With description: {sum(1 for p in final if p['description'])}")
    print(f"With scores: {sum(1 for p in final if p['avg_score'] > 0)}")
    print(f"With links: {sum(1 for p in final if p['links'])}")
    print(f"With track: {sum(1 for p in final if p['track'])}")

    # By day
    print("\nBy day:")
    by_day = {}
    for p in final:
        day = p['days'] or 'Unknown'
        by_day[day] = by_day.get(day, 0) + 1
    for day, count in sorted(by_day.items()):
        print(f"  {day}: {count}")

    # By room theme
    print("\nBy room theme:")
    by_theme = {}
    for p in final:
        theme = p['room_theme'] or 'Unknown'
        by_theme[theme] = by_theme.get(theme, 0) + 1
    for theme, count in sorted(by_theme.items(), key=lambda x: -x[1]):
        print(f"  {theme}: {count}")


if __name__ == '__main__':
    main()
