"""Tag normalization mapping and utilities."""

# Canonical tags (17 total)
CANONICAL_TAGS = [
    "NLP",
    "CV",
    "LLM",
    "Agents",
    "RecSys",
    "RL",
    "ASR",
    "TTS",
    "Audio",
    "EdTech",
    "FinTech",
    "MedTech",
    "Security",
    "Industrial",
    "TimeSeries",
    "MLOps",
    "Science",
]

# Mapping: variant -> canonical
TAG_MAPPING = {
    # NLP
    "nlp": "NLP",
    "natural language processing": "NLP",

    # CV
    "cv": "CV",
    "computer vision": "CV",
    "cv (computer vision)": "CV",
    "сomputer vision": "CV",  # с латинской С

    # LLM
    "llm": "LLM",
    "llm/vlm": "LLM",
    "llm и vlm": "LLM",
    "rag": "LLM",
    "rag и llm": "LLM",
    "llm-агенты в области информационной безопасности": "LLM",

    # Agents
    "agents": "Agents",
    "автономные агенты": "Agents",
    "агентные системы": "Agents",
    "автономные модели": "Agents",
    "marl": "Agents",
    "мульти-агентные системы": "Agents",
    "mcp": "Agents",

    # RecSys
    "recsys": "RecSys",
    "recsys / предиктивная аналитика": "RecSys",

    # RL
    "rl": "RL",
    "обучение с подкреплением": "RL",
    "reinforcement learning": "RL",

    # ASR
    "asr": "ASR",
    "распознавание речи": "ASR",
    "распознавание речи (automated speech recognition (asr) / speech-to-text (stt))": "ASR",
    "speech recognition": "ASR",

    # TTS
    "tts": "TTS",
    "синтез речи": "TTS",
    "синтез речи (speech synthesis / text-to-speech (tts))": "TTS",

    # Audio
    "audio": "Audio",
    "ии в музыке (сепарация": "Audio",
    "транскрибация)": "Audio",
    "распознавание и синтез речи": "Audio",

    # EdTech
    "edtech": "EdTech",

    # FinTech
    "fintech": "FinTech",
    "ml в fintech": "FinTech",
    "финтех": "FinTech",
    "regtech": "FinTech",

    # MedTech
    "medtech": "MedTech",

    # Security
    "security": "Security",
    "mlsec": "Security",
    "red teaming": "Security",
    "информационная безопасность (iam) + llm": "Security",

    # Industrial
    "industrial": "Industrial",
    "ml в промышленности": "Industrial",
    "dl в промышленности": "Industrial",
    "агротех": "Industrial",

    # TimeSeries
    "timeseries": "TimeSeries",
    "временные ряды": "TimeSeries",

    # MLOps
    "mlops": "MLOps",

    # Science
    "science": "Science",
    "естественные науки + ml": "Science",
    "geoml": "Science",

    # Generic ML - map to closest or skip
    "ml": None,  # too generic, skip
    "classic ml + ab-тесты": None,
    "data": None,
    "backend": None,
    "parsing": None,
    "процессы": None,
    "ai-сервисы": None,
    "ocr": "CV",  # OCR is CV-related

    # Garbage - skip
    "описание": None,
    "описание проекта": None,
}


def normalize_tag(tag: str) -> str | None:
    """Normalize a single tag. Returns None if tag should be skipped."""
    tag_lower = tag.lower().strip()

    # Direct mapping
    if tag_lower in TAG_MAPPING:
        return TAG_MAPPING[tag_lower]

    # Check if already canonical
    for canonical in CANONICAL_TAGS:
        if tag_lower == canonical.lower():
            return canonical

    # Try partial match for compound tags like "NLP        Автономные агенты"
    found_tags = []
    for canonical in CANONICAL_TAGS:
        if canonical.lower() in tag_lower:
            found_tags.append(canonical)

    if found_tags:
        return found_tags[0]  # Return first match

    # Unknown tag - return as-is for manual review
    return tag


def normalize_tags(tags: list[str]) -> list[str]:
    """Normalize a list of tags, removing duplicates and None values."""
    result = []
    seen = set()

    for tag in tags:
        normalized = normalize_tag(tag)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)

    return result


if __name__ == "__main__":
    # Test
    test_tags = [
        "NLP",
        "nlp",
        "Автономные агенты",
        "CV (Computer Vision)",
        "описание",
        "ML в промышленности",
        "NLP        Автономные агенты",
    ]

    for tag in test_tags:
        print(f"  '{tag}' -> '{normalize_tag(tag)}'")

    print(f"\nNormalized list: {normalize_tags(test_tags)}")
