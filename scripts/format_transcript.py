"""Format raw ElevenLabs transcript JSON into readable markdown."""
import json

INPUT = "docs/01-discovery/interview-raw-botov.json"
OUTPUT = "docs/01-discovery/interview-transcript-botov.md"

SPEAKER_MAP = {
    "speaker_0": "Дмитрий Ботов",
    "speaker_1": "Интервьюер",
    "speaker_2": "Участник 3",
}

with open(INPUT, "r", encoding="utf-8") as f:
    data = json.load(f)

# Build segments by speaker
segments = []
current_speaker = None
current_text = []

for w in data["words"]:
    sp = w.get("speaker_id", "unknown")
    if sp != current_speaker:
        if current_text:
            segments.append((current_speaker, " ".join(current_text)))
        current_speaker = sp
        current_text = [w["text"]]
    else:
        current_text.append(w["text"])

if current_text:
    segments.append((current_speaker, " ".join(current_text)))

lines = []
lines.append("# Интервью #5: Дмитрий Ботов (автор идеи)")
lines.append("")
lines.append("| Параметр | Значение |")
lines.append("|----------|----------|")
lines.append("| Респондент | Дмитрий Ботов (@dmbotov) — автор идеи проекта, организатор Demo Day |")
lines.append("| Дата | 02.02.2026 |")
lines.append("| Файл | Ботов Дмитрий (1).aac |")
lines.append("| Сервис | ElevenLabs Scribe v1, язык: русский, диаризация: 3 спикера |")
lines.append(f"| Сегменты | {len(segments)} |")
lines.append(f"| Слов | {len(data['words'])} |")
lines.append("")
lines.append("---")
lines.append("")

import re

for speaker, text in segments:
    name = SPEAKER_MAP.get(speaker, speaker)
    # Normalize multiple spaces to single
    clean = re.sub(r" {2,}", " ", text.strip())
    lines.append(f"**{name}:** {clean}")
    lines.append("")

output = "\n".join(lines)
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(output)

print(f"Written {len(output)} chars, {len(segments)} segments")
