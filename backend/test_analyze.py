#!/usr/bin/env python3
"""
Тестовый скрипт для анализа видео через Replicate Gemini 3.5 Flash.

Использование:
    python test_analyze.py /path/to/video.mp4
"""

import base64
import json
import mimetypes
import os
import sys
import re
import time

import replicate

from app.services.analysis_prompts import VIDEO_ANALYSIS_PROMPT

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
REPLICATE_MODEL = "google/gemini-3.5-flash"
ANALYSIS_PROMPT = VIDEO_ANALYSIS_PROMPT


RISK_LABELS = {
    "drugs": "Наркотики",
    "weapons": "Оружие",
    "violence": "Насилие",
    "sexual_content": "Сексуальный контент",
    "profanity": "Нецензурная лексика",
    "illegal_actions": "Незаконные действия",
    "alcohol": "Алкоголь",
    "smoking": "Курение",
    "animal_cruelty": "Жестокое обращение с животными",
    "forbidden_symbols": "Запрещённая символика",
    "text_in_frame": "Текст в кадре",
    "discreditation_values": "Дискредитация ценностей",
    "propaganda": "Пропаганда",
    "crime_glorification": "Героизация преступлений",
    "excessive_cruelty": "Чрезмерная жестокость",
}

LEVEL_LABELS = {
    "critical": "КРИТИЧНО",
    "warning": "ПРЕДУПРЕЖДЕНИЕ",
    "info": "ИНФОРМАЦИЯ",
}

REC_LABELS = {
    "remove": "Удалить",
    "shorten": "Сократить",
    "mute": "Заглушить",
    "blur": "Заблюрить",
    "info": "Информирование",
    "mark": "Маркировка",
}


def parse_response(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if json_match:
        cleaned = json_match.group(1).strip()

    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        if start != -1:
            cleaned = cleaned[start:]

    if not cleaned.endswith("}"):
        end = cleaned.rfind("}")
        if end != -1:
            cleaned = cleaned[: end + 1]

    return json.loads(cleaned)


def main():
    if len(sys.argv) < 2:
        print("Использование: python test_analyze.py /path/to/video.mp4")
        sys.exit(1)

    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"Файл не найден: {video_path}")
        sys.exit(1)

    size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"Файл: {os.path.basename(video_path)} ({size_mb:.1f} МБ)")
    print(f"Модель: {REPLICATE_MODEL}")
    print("=" * 60)
    print("Отправка видео на анализ...")
    print()

    if not REPLICATE_API_TOKEN:
        print("Задайте REPLICATE_API_TOKEN в окружении или в backend/.env")
        sys.exit(1)

    content_type = mimetypes.guess_type(video_path)[0] or "video/mp4"
    with open(video_path, "rb") as f:
        raw = f.read()
    video_uri = f"data:{content_type};base64,{base64.b64encode(raw).decode('ascii')}"

    client = replicate.Client(api_token=REPLICATE_API_TOKEN)
    start_time = time.time()

    output = client.run(
        REPLICATE_MODEL,
        input={
            "prompt": ANALYSIS_PROMPT,
            "videos": [video_uri],
            "video_fps": 2,
            "max_output_tokens": 65535,
            "temperature": 0.2,
            "thinking_level": "high",
        },
    )

    if isinstance(output, list):
        raw_response = "".join(str(chunk) for chunk in output)
    else:
        raw_response = str(output)

    elapsed = time.time() - start_time
    print(f"Ответ получен за {elapsed:.1f} секунд ({len(raw_response)} символов)")
    print("=" * 60)

    # Save raw response
    raw_path = video_path + ".raw_response.txt"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_response)
    print(f"Сырой ответ сохранён: {raw_path}")

    try:
        data = parse_response(raw_response)
    except json.JSONDecodeError as e:
        print(f"\nОшибка парсинга JSON: {e}")
        print("Сырой ответ (первые 2000 символов):")
        print(raw_response[:2000])
        sys.exit(1)

    # Save parsed JSON
    json_path = video_path + ".analysis.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON результат сохранён: {json_path}")
    print()

    # Print summary
    print("=" * 60)
    print(f"ВИДЕО: {data.get('video_title', 'N/A')}")
    print(f"ДЛИТЕЛЬНОСТЬ: {data.get('duration', 'N/A')}")
    print("=" * 60)

    scenes = data.get("scenes", [])
    risky = [s for s in scenes if s.get("risks")]
    total_risks = sum(len(s.get("risks", [])) for s in scenes)

    print(f"Всего сцен: {len(scenes)}")
    print(f"Сцен с рисками: {len(risky)}")
    print(f"Всего нарушений: {total_risks}")
    print()

    if risky:
        print("ОБНАРУЖЕННЫЕ НАРУШЕНИЯ:")
        print("-" * 60)
        for scene in risky:
            for risk in scene.get("risks", []):
                level = LEVEL_LABELS.get(risk.get("risk_level", ""), risk.get("risk_level", ""))
                category = RISK_LABELS.get(risk.get("risk", ""), risk.get("risk", ""))
                prob = risk.get("probability", 0)
                rec = REC_LABELS.get(risk.get("recommendation", ""), risk.get("recommendation", ""))

                print(f"\n  [{level}] Сцена {scene.get('scene_number')}: {scene.get('start_time')} - {scene.get('end_time')}")
                print(f"  Категория: {category}")
                print(f"  Вероятность: {prob:.0%}")
                print(f"  Причина: {risk.get('reason', '-')}")
                if risk.get("quote"):
                    print(f"  Цитата: {risk['quote']}")
                if risk.get("text_in_frame"):
                    print(f"  Текст в кадре: {risk['text_in_frame']}")
                print(f"  Рекомендация: {rec}")
                print(f"  Описание сцены: {scene.get('description', '-')}")
                print("-" * 40)
    else:
        print("Нарушений не обнаружено.")

    print()
    print("Готово!")


if __name__ == "__main__":
    main()
