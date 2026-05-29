import asyncio
import json
import logging
import re
import time

import httpx
import replicate
from PyPDF2 import PdfReader

from app.core.config import settings
from app.schemas.analysis import GeminiAnalysisResult

logger = logging.getLogger(__name__)

TEXT_ANALYSIS_PROMPT = """Ты — профессиональный цензор текстового контента (книги, документы). Проанализируй данный текст на наличие контента, который может нарушать законодательство РФ или требовать маркировки.

Разбей текст на фрагменты (главы, разделы или логические блоки). Для каждого фрагмента:
1. Укажи номер фрагмента
2. Укажи начальную и конечную страницу (или примерное расположение в тексте)
3. Подробно опиши содержание фрагмента
4. Оцени наличие рисков из следующих категорий:

КАТЕГОРИИ РИСКОВ:
- drugs — наркотики и наркотические средства (описание употребления, пропаганда)
- weapons — оружие (детальное описание изготовления, применения)
- violence — насилие (сцены насилия, жестокости)
- sexual_content — сексуальный контент (откровенные сцены)
- profanity — нецензурная лексика (мат, грубые выражения)
- illegal_actions — незаконные действия (инструкции, призывы)
- alcohol — алкоголь (пропаганда употребления)
- smoking — курение (пропаганда)
- animal_cruelty — жестокое обращение с животными
- forbidden_symbols — запрещённая символика
- extremism — экстремизм (разжигание ненависти, призывы)
- discreditation_values — дискредитация традиционных ценностей
- propaganda — пропаганда запрещённого контента
- crime_glorification — героизация преступлений
- excessive_cruelty — чрезмерная жестокость (натуралистические описания)
- suicide — суицид (описание способов, романтизация)
- minor_content — вовлечение несовершеннолетних в опасные действия

Для КАЖДОГО фрагмента с обнаруженным риском средней или высокой вероятности укажи:
- risk: категория риска (из списка выше)
- risk_level: уровень ("critical", "warning" или "info")
- probability: вероятность от 0.0 до 1.0
- reason: подробная причина на русском языке
- quote: точная цитата из текста (до 200 символов)
- text_in_frame: null
- recommendation: рекомендация ("remove" — удалить фрагмент, "edit" — отредактировать, "mark" — добавить маркировку возрастного ограничения)

Отмечай только риски со средней и высокой вероятностью (probability >= 0.5).
Если во фрагменте несколько рисков — укажи каждый отдельно в массиве risks.
Если рисков нет — оставь массив risks пустым.

Верни результат СТРОГО в формате JSON (без markdown-блоков, без пояснений, только чистый JSON):
{
  "video_title": "Название книги или документа",
  "duration": "Количество страниц",
  "scenes": [
    {
      "scene_number": 1,
      "start_time": "стр. 1",
      "end_time": "стр. 15",
      "description": "Описание содержания фрагмента",
      "risks": [
        {
          "risk": "категория",
          "risk_level": "critical",
          "probability": 0.85,
          "reason": "Причина",
          "quote": "Точная цитата из текста",
          "text_in_frame": null,
          "recommendation": "remove"
        }
      ]
    }
  ]
}

ТЕКСТ ДЛЯ АНАЛИЗА:
"""

MAX_PROMPT_CHARS = 900_000


class TextAnalysisService:
    def __init__(self) -> None:
        self._client = replicate.Client(
            api_token=settings.REPLICATE_API_TOKEN,
            timeout=httpx.Timeout(300, connect=30),
        )
        self._semaphore = asyncio.Semaphore(settings.GEMINI_MAX_CONCURRENT)

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        reader = PdfReader(pdf_path)
        pages: list[str] = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"--- Страница {i} ---\n{text}")
        return "\n\n".join(pages)

    async def analyze_text(self, file_path: str) -> GeminiAnalysisResult:
        async with self._semaphore:
            return await asyncio.to_thread(self._analyze_sync, file_path)

    def _analyze_sync(self, file_path: str, max_retries: int = 5) -> GeminiAnalysisResult:
        text = self.extract_text_from_pdf(file_path)
        if not text.strip():
            raise ValueError("Could not extract any text from the PDF")

        logger.info("Extracted %d characters from PDF", len(text))

        if len(text) > MAX_PROMPT_CHARS:
            logger.warning(
                "Text too long (%d chars), truncating to %d",
                len(text), MAX_PROMPT_CHARS,
            )
            text = text[:MAX_PROMPT_CHARS]

        full_prompt = TEXT_ANALYSIS_PROMPT + text
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Sending text to Replicate Gemini (attempt %d/%d, %d chars)",
                    attempt, max_retries, len(full_prompt),
                )
                raw_response = self._run_model(full_prompt)
                logger.info("Received response (%d chars)", len(raw_response))
                return self._parse_response(raw_response)
            except Exception as e:
                last_error = e
                logger.warning("Attempt %d failed: %s", attempt, e)
                if attempt < max_retries:
                    wait = min(5 * attempt, 30)
                    logger.info("Waiting %ds before retry...", wait)
                    time.sleep(wait)

        raise RuntimeError(f"Text analysis failed after {max_retries} retries") from last_error

    def _run_model(self, prompt: str) -> str:
        prediction = self._client.predictions.create(
            model=settings.REPLICATE_MODEL,
            input={
                "prompt": prompt,
                "max_output_tokens": 65535,
                "temperature": 0.3,
            },
        )

        deadline = time.time() + 1800
        while prediction.status not in {"succeeded", "failed", "canceled"}:
            if time.time() > deadline:
                raise TimeoutError("Replicate prediction polling timed out after 30 minutes")
            time.sleep(5)
            prediction.reload()

        if prediction.status != "succeeded":
            raise RuntimeError(prediction.error or f"Prediction ended with status {prediction.status}")

        output = prediction.output
        if isinstance(output, list):
            return "".join(str(chunk) for chunk in output)
        return str(output)

    def _parse_response(self, raw_text: str) -> GeminiAnalysisResult:
        cleaned = raw_text.strip()
        if not cleaned:
            raise ValueError("Empty response from model")

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

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Direct JSON parse failed, trying to repair truncated JSON...")
            data = self._repair_truncated_json(cleaned)

        return GeminiAnalysisResult.model_validate(data)

    def _repair_truncated_json(self, text: str) -> dict:
        scenes_match = re.search(r'"scenes"\s*:\s*\[', text)
        if not scenes_match:
            raise ValueError("Cannot find 'scenes' array in response")

        last_complete = text.rfind("},")
        if last_complete == -1:
            last_complete = text.rfind("}")

        if last_complete == -1:
            raise ValueError("No complete scene objects found")

        truncated = text[: last_complete + 1]
        open_brackets = truncated.count("[") - truncated.count("]")
        open_braces = truncated.count("{") - truncated.count("}")
        truncated += "]" * max(0, open_brackets)
        truncated += "}" * max(0, open_braces)

        try:
            data = json.loads(truncated)
            logger.info("Repaired truncated JSON successfully (%d scenes)", len(data.get("scenes", [])))
            return data
        except json.JSONDecodeError as e:
            logger.error("JSON repair failed: %s", e)
            raise ValueError(f"Cannot repair JSON: {e}") from e


text_analysis_service = TextAnalysisService()
