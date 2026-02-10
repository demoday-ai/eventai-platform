#!/usr/bin/env python3
"""
Prepare test data files from checkpoint12_anon.xlsx in the correct format for import.
"""
import openpyxl
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "data" / "test"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "import_ready"
OUTPUT_DIR.mkdir(exist_ok=True)

# Read checkpoint12
checkpoint_file = DATA_DIR / "checkpoint12_anon.xlsx"
wb_checkpoint = openpyxl.load_workbook(checkpoint_file)
ws_checkpoint = wb_checkpoint.active

# Extract projects data
projects = []
students_set = set()

for row_idx in range(2, ws_checkpoint.max_row + 1):
    row = ws_checkpoint[row_idx]

    # Columns: ID, Время, ФИО, Телеграм, Курс, Трек, Название, ...
    fio = row[2].value
    telegram = row[3].value
    track = row[5].value
    title = row[6].value
    plan = row[12].value
    team = row[14].value

    if not title or not fio:
        continue

    # Clean telegram
    if telegram:
        telegram = str(telegram).strip()
        if not telegram.startswith('@'):
            telegram = f'@{telegram}'

    # Use plan as description, limit to 200 chars
    description = str(plan)[:200] if plan else f"Проект {title}"

    # Normalize track to Russian canonical names
    track_map = {
        "Education": "Образовательный",
        "EdTech": "Образовательный",
        "Startup": "Стартап",
        "Industrial": "Индустриальный",
        "Research": "Научный",
    }
    track_normalized = track_map.get(track, None) if track else None

    # Tags from track if available
    tags = track if track else ""

    projects.append({
        'title': title,
        'description': description,
        'author': fio,
        'telegram_contact': telegram or "",
        'tags': tags,
        'track': track_normalized,
    })

    # Collect students
    if fio and telegram:
        students_set.add((fio, telegram))

    # Add team members to students
    if team:
        members = str(team).split(',')
        for member in members:
            member = member.strip()
            if member and member != fio:
                students_set.add((member, ""))

print(f"Extracted {len(projects)} projects")
print(f"Extracted {len(students_set)} unique students")

# Create projects.xlsx
wb_projects = openpyxl.Workbook()
ws_projects = wb_projects.active
ws_projects.title = "Projects"

# Header
ws_projects.append(['title *', 'description *', 'author *', 'telegram_contact', 'tags', 'track'])

# Data
for p in projects[:50]:  # Limit to 50 for testing
    ws_projects.append([
        p['title'],
        p['description'],
        p['author'],
        p['telegram_contact'],
        p['tags'],
        p['track'],
    ])

projects_file = OUTPUT_DIR / "projects.xlsx"
wb_projects.save(projects_file)
print(f"Created {projects_file}")

# Create students.xlsx
wb_students = openpyxl.Workbook()
ws_students = wb_students.active
ws_students.title = "Students"

# Header
ws_students.append(['name', 'telegram'])

# Data
for name, telegram in sorted(students_set)[:100]:  # Limit to 100
    ws_students.append([name, telegram])

students_file = OUTPUT_DIR / "students.xlsx"
wb_students.save(students_file)
print(f"Created {students_file}")

# Create experts.xlsx (mock data)
wb_experts = openpyxl.Workbook()
ws_experts = wb_experts.active
ws_experts.title = "Experts"

# Header
ws_experts.append(['name *', 'telegram', 'position', 'expertise_tags'])

# Mock experts with relevant tags
experts_data = [
    ('Алексей Иванов', '@expert_ai', 'Senior ML Engineer', 'NLP, CV, ML'),
    ('Мария Петрова', '@expert_nlp', 'Head of AI Research', 'NLP, Research, Education'),
    ('Дмитрий Сидоров', '@expert_cv', 'Computer Vision Lead', 'CV, Deep Learning'),
    ('Анна Козлова', '@expert_fintech', 'FinTech Product Manager', 'Finance, Product'),
    ('Сергей Морозов', '@expert_edu', 'EdTech Founder', 'Education, Startups'),
    ('Елена Новикова', '@expert_ml', 'ML Team Lead', 'ML, Data Science'),
    ('Игорь Волков', '@expert_web', 'Senior Frontend Dev', 'Web, UI/UX'),
    ('Ольга Смирнова', '@expert_mobile', 'Mobile Dev Lead', 'Mobile, iOS, Android'),
    ('Павел Федоров', '@expert_backend', 'Backend Architect', 'Backend, Databases, API'),
    ('Наталья Егорова', '@expert_ds', 'Data Scientist', 'Data Science, Analytics, ML'),
]

for expert in experts_data:
    ws_experts.append(expert)

experts_file = OUTPUT_DIR / "experts.xlsx"
wb_experts.save(experts_file)
print(f"Created {experts_file}")

# Create partners.xlsx (mock data)
wb_partners = openpyxl.Workbook()
ws_partners = wb_partners.active
ws_partners.title = "Partners"

# Header
ws_partners.append(['name', 'telegram'])

# Mock partners
partners_data = [
    ('Иван Соколов', '@partner_tech'),
    ('Татьяна Лебедева', '@partner_invest'),
    ('Максим Орлов', '@partner_hr'),
    ('Виктория Белова', '@partner_business'),
    ('Андрей Козлов', '@partner_corp'),
]

for partner in partners_data:
    ws_partners.append(partner)

partners_file = OUTPUT_DIR / "partners.xlsx"
wb_partners.save(partners_file)
print(f"Created {partners_file}")

print(f"\nAll files saved to: {OUTPUT_DIR}")
print("Ready to import!")
