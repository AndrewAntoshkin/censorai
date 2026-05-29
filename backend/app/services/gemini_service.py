import asyncio
import base64
import json
import logging
import mimetypes
import re
import time

import httpx
import replicate

from app.core.config import settings
from app.schemas.analysis import GeminiAnalysisResult

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Ты — профессиональный цензор видеоконтента. Проанализируй данное видео последовательно от начала до конца.

Разбей видео на сцены. Для каждой сцены:
1. Укажи номер сцены, время начала и конца (формат MM:SS или HH:MM:SS)
2. Подробно опиши происходящее в сцене
3. Оцени наличие рисков из следующих категорий:

КАТЕГОРИИ РИСКОВ:
- drugs — наркотики и наркотические средства
- weapons — оружие
- violence — насилие
- sexual_content — сексуальный контент
- profanity — нецензурная лексика
- illegal_actions — незаконные действия
- alcohol — алкоголь
- smoking — курение
- animal_cruelty — жестокое обращение с животными
- forbidden_symbols — запрещённая символика
- text_in_frame — опасный/запрещённый текст в кадре
- discreditation_values — дискредитация ценностей
- propaganda — пропаганда
- crime_glorification — героизация преступлений
- excessive_cruelty — чрезмерная жестокость

Для КАЖДОЙ сцены с обнаруженным риском средней или высокой вероятности укажи:
- risk: категория риска (из списка выше)
- risk_level: уровень ("critical", "warning" или "info")
- probability: вероятность от 0.0 до 1.0
- reason: подробная причина на русском языке
- quote: цитата или описание конкретного момента
- text_in_frame: если есть текст в кадре — укажи его
- recommendation: рекомендация ("remove" — удалить, "shorten" — сократить, "mute" — заглушить звук, "blur" — заблюрить)

Отмечай только риски со средней и высокой вероятностью (probability >= 0.5).
Если в сцене несколько рисков — укажи каждый отдельно в массиве risks.
Если рисков нет — оставь массив risks пустым.

Верни результат СТРОГО в формате JSON (без markdown-блоков, без пояснений, только чистый JSON):
{
  "video_title": "название или описание видео",
  "duration": "общая длительность видео",
  "scenes": [
    {
      "scene_number": 1,
      "start_time": "00:00",
      "end_time": "00:30",
      "description": "Описание сцены",
      "risks": [
        {
          "risk": "категория",
          "risk_level": "critical",
          "probability": 0.85,
          "reason": "Причина",
          "quote": "Цитата или описание момента",
          "text_in_frame": null,
          "recommendation": "remove"
        }
      ]
    }
  ]
}"""


class GeminiService:
    def __init__(self) -> None:
        self._client = replicate.Client(
            api_token=settings.REPLICATE_API_TOKEN,
            timeout=httpx.Timeout(300, connect=30),
        )
        self._semaphore = asyncio.Semaphore(settings.GEMINI_MAX_CONCURRENT)

    async def analyze_video(self, video_path: str) -> GeminiAnalysisResult:
        async with self._semaphore:
            return await asyncio.to_thread(self._analyze_sync, video_path)

    def _analyze_sync(self, video_path: str, max_retries: int = 5) -> GeminiAnalysisResult:
        last_error: Exception | None = None

        video_uri = self._video_to_data_uri(video_path)
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Sending video to Replicate Gemini (attempt %d/%d)",
                    attempt,
                    max_retries,
                )
                raw_response = self._run_model(video_uri)
                logger.info("Received response (%d chars)", len(raw_response))
                return self._parse_response(raw_response)
            except Exception as e:
                last_error = e
                logger.warning("Attempt %d failed: %s", attempt, e)
                if attempt < max_retries:
                    wait = min(5 * attempt, 30)
                    logger.info("Waiting %ds before retry...", wait)
                    time.sleep(wait)

        raise RuntimeError(f"Analysis failed after {max_retries} retries") from last_error

    def _video_to_data_uri(self, video_path: str) -> str:
        """Encode the video as a base64 data URI passed inline to the model.

        Passing the bytes inline (with an explicit mime type) is what the
        Gemini-on-Replicate model reliably accepts — external URLs failed with
        "Could not determine the mimetype". Inline payloads keep the file on our
        own infrastructure (no third-party public host)."""
        content_type = mimetypes.guess_type(video_path)[0] or "video/mp4"
        with open(video_path, "rb") as video_file:
            raw = video_file.read()

        size_mb = len(raw) / (1024 * 1024)
        if size_mb > settings.INLINE_VIDEO_MAX_MB:
            raise RuntimeError(
                f"Видео слишком большое для встроенной передачи: {size_mb:.0f} МБ "
                f"(максимум {settings.INLINE_VIDEO_MAX_MB} МБ). Загрузите более короткий фрагмент."
            )
        encoded = base64.b64encode(raw).decode("ascii")
        return f"data:{content_type};base64,{encoded}"

    def _run_model(self, video_url: str) -> str:
        prediction = self._client.predictions.create(
            model=settings.REPLICATE_MODEL,
            input={
                "prompt": ANALYSIS_PROMPT,
                "videos": [video_url],
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
        """Try to repair truncated JSON by closing open brackets."""
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
            logger.debug("Truncated text (last 500 chars): %s", truncated[-500:])
            raise ValueError(f"Cannot repair JSON: {e}") from e


gemini_service = GeminiService()
