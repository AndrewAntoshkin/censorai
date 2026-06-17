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
from app.services.analysis_coverage import (
    FULL_ANALYSIS_MAX_OUTPUT_TOKENS,
    full_coverage_prompt_suffix,
)
from app.services.analysis_prompts import VIDEO_ANALYSIS_PROMPT
from app.services.replicate_media import build_replicate_media_url
from app.services.video_media import effective_size_bytes
from app.schemas.analysis import GeminiAnalysisResult

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = VIDEO_ANALYSIS_PROMPT

# This is a content-moderation tool: it must inspect explicit/violent material,
# so Gemini's default safety filters (which would return empty candidates with
# block_reason) must be disabled. String form is accepted by google-generativeai.
GEMINI_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]


def _is_transient_replicate_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in ("interrupted", "code: pa", "timeout", "temporarily unavailable", "rate limit")
    )


class GeminiService:
    def __init__(self) -> None:
        token = settings.REPLICATE_API_TOKEN
        # Long timeout for create/wait paths; status polls must stay short on serverless.
        self._client = replicate.Client(
            api_token=token,
            timeout=httpx.Timeout(300, connect=30),
        )
        self._poll_client = replicate.Client(
            api_token=token,
            timeout=httpx.Timeout(45, connect=15),
        )
        self._semaphore = asyncio.Semaphore(settings.GEMINI_MAX_CONCURRENT)

    async def analyze_video(
        self,
        video_path: str,
        *,
        file_id: str | None = None,
        file_size: int | None = None,
    ) -> GeminiAnalysisResult:
        async with self._semaphore:
            return await asyncio.to_thread(
                self._analyze_sync, video_path, file_id=file_id, file_size=file_size
            )

    def _analyze_sync(
        self,
        video_path: str,
        max_retries: int = 5,
        *,
        file_id: str | None = None,
        file_size: int | None = None,
    ) -> GeminiAnalysisResult:
        last_error: Exception | None = None
        video_uri = self.resolve_video_uri(
            video_path, file_id=file_id, file_size=file_size
        )

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
                if attempt < max_retries and _is_transient_replicate_error(e):
                    wait = min(10 * attempt, 60)
                    logger.info("Transient Replicate error, waiting %ds before retry...", wait)
                    time.sleep(wait)
                elif attempt < max_retries:
                    wait = min(5 * attempt, 30)
                    logger.info("Waiting %ds before retry...", wait)
                    time.sleep(wait)

        raise RuntimeError(f"Analysis failed after {max_retries} retries") from last_error

    def _read_video_bytes(self, video_path: str) -> tuple[bytes, str]:
        if video_path.startswith(("http://", "https://")):
            import httpx

            with httpx.Client(timeout=300, follow_redirects=True) as client:
                response = client.get(video_path)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";")[0].strip()
            if not content_type or content_type == "application/octet-stream":
                content_type = mimetypes.guess_type(video_path.split("?")[0])[0] or "video/mp4"
            return response.content, content_type

        content_type = mimetypes.guess_type(video_path)[0] or "video/mp4"
        with open(video_path, "rb") as video_file:
            return video_file.read(), content_type

    def resolve_video_uri(
        self,
        storage_path: str,
        *,
        file_id: str | None = None,
        file_size: int | None = None,
    ) -> str:
        """Pick inline base64 (small files) or signed HTTPS URL (large files)."""
        if storage_path.startswith(("http://", "https://")):
            return storage_path

        if storage_path.startswith("chunk-session:"):
            if not file_id:
                raise RuntimeError(
                    "chunk-session storage requires file_id for replicate-media URL"
                )
            return build_replicate_media_url(file_id)

        if storage_path.startswith("s3://"):
            from app.services.object_storage import presigned_get_url

            url = presigned_get_url(storage_path)
            logger.info("Using presigned S3 URL for model input")
            return url

        from pathlib import Path

        path = Path(storage_path)
        if not path.exists():
            raise FileNotFoundError(f"Video not found: {storage_path}")

        size_bytes = effective_size_bytes(storage_path, file_size)
        if size_bytes <= 0 and path.exists():
            size_bytes = path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        if size_mb <= settings.INLINE_VIDEO_MAX_MB:
            logger.info("Using inline video payload (%.1f MB)", size_mb)
            return self._video_to_data_uri(storage_path)

        if not file_id:
            raise RuntimeError(
                f"Видео {size_mb:.0f} МБ — нужен signed URL, но file_id не передан"
            )

        url = build_replicate_media_url(file_id)
        logger.info("Using signed URL for Replicate (%.1f MB): %s", size_mb, url)
        return url

    def _video_input_uri(self, video_path: str) -> str:
        """Backward-compatible helper for callers that only have a path."""
        return self.resolve_video_uri(video_path)

    def _video_to_data_uri(self, video_path: str) -> str:
        """Encode the video as a base64 data URI passed inline to the model."""
        raw, content_type = self._read_video_bytes(video_path)

        size_mb = len(raw) / (1024 * 1024)
        if size_mb > settings.INLINE_VIDEO_MAX_MB:
            raise RuntimeError(
                f"Видео слишком большое для встроенной передачи: {size_mb:.0f} МБ "
                f"(максимум {settings.INLINE_VIDEO_MAX_MB} МБ). Загрузите более короткий фрагмент."
            )
        encoded = base64.b64encode(raw).decode("ascii")
        return f"data:{content_type};base64,{encoded}"

    def _build_analysis_prompt(
        self,
        *,
        expected_duration_seconds: int | None = None,
        extra_prompt_suffix: str = "",
    ) -> str:
        return (
            ANALYSIS_PROMPT
            + full_coverage_prompt_suffix(expected_duration_seconds)
            + (extra_prompt_suffix or "")
        )

    def analyze_video_direct(
        self,
        storage_path: str,
        *,
        file_id: str | None = None,
        file_size: int | None = None,
        expected_duration_seconds: int | None = None,
        extra_prompt_suffix: str = "",
        model_name: str | None = None,
        prompt_override: str | None = None,
    ) -> GeminiAnalysisResult:
        """Run analysis via Google AI Studio (bypasses Replicate)."""
        import google.generativeai as genai

        api_key = settings.GEMINI_API_KEY.strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        genai.configure(api_key=api_key)
        model_slugs = self._fallback_model_slugs(model_name)
        prompt = (prompt_override or "").strip() or self._build_analysis_prompt(
            expected_duration_seconds=expected_duration_seconds,
            extra_prompt_suffix=extra_prompt_suffix,
        )

        video_uri = self.resolve_video_uri(
            storage_path, file_id=file_id, file_size=file_size
        )
        if video_uri.startswith("data:"):
            import tempfile
            from pathlib import Path

            from app.services.video_segmentation import sweep_stale_temp_media

            sweep_stale_temp_media()
            header, encoded = video_uri.split(",", 1)
            mime = header.split(":")[1].split(";")[0]
            tmp = Path(tempfile.gettempdir()) / f"gemini_direct_{file_id or 'inline'}.mp4"
            try:
                tmp.write_bytes(base64.b64decode(encoded))
                return self._direct_generate_from_path(str(tmp), prompt, model_slugs, mime=mime)
            finally:
                tmp.unlink(missing_ok=True)

        if video_uri.startswith(("http://", "https://")):
            import tempfile
            from pathlib import Path

            from app.services.video_segmentation import (
                ensure_tmp_space,
                sweep_stale_temp_media,
            )

            # Clear leaked temps from killed/concurrent runs before we write a
            # 100+ MB download, otherwise /tmp (~512 MB on Vercel) overflows.
            sweep_stale_temp_media()
            # Refuse to start (transient → auto-retry) if /tmp can't hold the file.
            ensure_tmp_space(file_size)
            tmp = Path(tempfile.gettempdir()) / f"gemini_direct_{file_id or 'remote'}.mp4"
            content_type = "video/mp4"
            try:
                with httpx.Client(
                    timeout=httpx.Timeout(600.0, connect=60.0), follow_redirects=True
                ) as client, client.stream("GET", video_uri) as resp:
                    resp.raise_for_status()
                    content_type = (
                        resp.headers.get("content-type", "").split(";")[0].strip()
                        or "video/mp4"
                    )
                    with open(tmp, "wb") as out:
                        for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                            out.write(chunk)
                return self._direct_generate_from_path(
                    str(tmp), prompt, model_slugs, mime=content_type
                )
            finally:
                tmp.unlink(missing_ok=True)

        return self._direct_generate_from_path(video_uri, prompt, model_slugs)

    def analyze_local_file_direct(
        self,
        local_path: str,
        *,
        expected_duration_seconds: int | None = None,
        extra_prompt_suffix: str = "",
        model_name: str | None = None,
    ) -> GeminiAnalysisResult:
        """Run direct Gemini on an already-local file (e.g. a cut segment).

        Unlike ``analyze_video_direct`` this never goes through
        ``resolve_video_uri`` — the path is uploaded to Gemini as-is, so it is
        safe for segment temp files that are larger than the inline limit.
        """
        if not settings.GEMINI_API_KEY.strip():
            raise RuntimeError("GEMINI_API_KEY is not configured")
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY.strip())
        prompt = self._build_analysis_prompt(
            expected_duration_seconds=expected_duration_seconds,
            extra_prompt_suffix=extra_prompt_suffix,
        )
        mime = mimetypes.guess_type(local_path)[0] or "video/mp4"
        return self._direct_generate_from_path(
            local_path, prompt, self._fallback_model_slugs(model_name), mime=mime
        )

    def _fallback_model_slugs(self, model_name: str | None = None) -> list[str]:
        """Model chain: explicit override, else Flash then (different) Pro."""
        if model_name and model_name.strip():
            return [model_name.strip()]
        flash = (settings.GEMINI_MODEL or "gemini-2.5-flash").strip()
        slugs = [flash]
        pro = (settings.GEMINI_PRO_MODEL or "").strip()
        if pro and pro != flash:
            slugs.append(pro)
        return slugs

    def _direct_generate_from_path(
        self,
        local_path: str,
        prompt: str,
        model_slugs: str | list[str],
        *,
        mime: str | None = None,
    ) -> GeminiAnalysisResult:
        """Upload once, then try each model in order; a content block falls
        through to the next model, other errors propagate immediately."""
        import google.generativeai as genai

        from app.services.analysis_errors import ContentBlockedError

        slugs = [model_slugs] if isinstance(model_slugs, str) else list(model_slugs)
        if not slugs:
            slugs = [(settings.GEMINI_MODEL or "gemini-2.5-flash").strip()]

        if mime:
            uploaded = genai.upload_file(local_path, mime_type=mime)
        else:
            uploaded = genai.upload_file(local_path)
        try:
            deadline = time.time() + 600
            while uploaded.state.name == "PROCESSING":
                if time.time() > deadline:
                    raise TimeoutError("Gemini file processing timed out")
                time.sleep(3)
                uploaded = genai.get_file(uploaded.name)

            if uploaded.state.name != "ACTIVE":
                raise RuntimeError(f"Gemini file state: {uploaded.state.name}")

            last_block: ContentBlockedError | None = None
            for index, slug in enumerate(slugs):
                try:
                    return self._generate_with_model(genai, uploaded, prompt, slug)
                except ContentBlockedError as blocked:
                    last_block = blocked
                    if index + 1 < len(slugs):
                        logger.warning(
                            "Model %s blocked content (%s); falling back to %s",
                            slug,
                            blocked.block_reason,
                            slugs[index + 1],
                        )
                        continue
            raise last_block or ContentBlockedError(message="Content blocked by model")
        finally:
            try:
                genai.delete_file(uploaded.name)
            except Exception:
                logger.debug("Failed to delete Gemini uploaded file", exc_info=True)

    def _generate_with_model(
        self, genai, uploaded, prompt: str, model_slug: str
    ) -> GeminiAnalysisResult:
        from app.services.analysis_errors import ContentBlockedError

        model = genai.GenerativeModel(model_slug)
        response = model.generate_content(
            [uploaded, prompt],
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=min(FULL_ANALYSIS_MAX_OUTPUT_TOKENS, 65535),
                response_mime_type="application/json",
            ),
            safety_settings=GEMINI_SAFETY_SETTINGS,
            request_options={"timeout": 600},
        )
        feedback = getattr(response, "prompt_feedback", None)
        block_reason = getattr(feedback, "block_reason", None)
        if block_reason:
            raise ContentBlockedError(block_reason)

        # Some blocks surface as an empty candidate list / non-STOP finish reason
        # rather than prompt_feedback; treat those as content blocks too.
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            raise ContentBlockedError(message="No candidates returned (content blocked)")
        finish = str(getattr(candidates[0], "finish_reason", "")).upper()
        if any(tok in finish for tok in ("SAFETY", "RECITATION", "PROHIBITED", "BLOCK")):
            raise ContentBlockedError(message=f"finish_reason={finish}")

        try:
            raw = (response.text or "").strip()
        except (ValueError, AttributeError) as exc:
            raise ContentBlockedError(message=f"No usable text ({exc})") from exc
        if not raw:
            raise RuntimeError("Empty response from direct Gemini API")
        logger.info("Direct Gemini response from %s (%d chars)", model_slug, len(raw))
        return self._parse_response(raw)

    def _model_input(
        self,
        video_url: str,
        *,
        expected_duration_seconds: int | None = None,
        extra_prompt_suffix: str = "",
    ) -> dict:
        prompt = self._build_analysis_prompt(
            expected_duration_seconds=expected_duration_seconds,
            extra_prompt_suffix=extra_prompt_suffix,
        )
        payload = {
            "prompt": prompt,
            "videos": [video_url],
            "video_fps": settings.REPLICATE_VIDEO_FPS,
            "max_output_tokens": FULL_ANALYSIS_MAX_OUTPUT_TOKENS,
            "temperature": 0.2,
        }
        if settings.REPLICATE_THINKING_LEVEL and settings.REPLICATE_THINKING_LEVEL != "none":
            payload["thinking_level"] = settings.REPLICATE_THINKING_LEVEL
        return payload

    def start_analysis(
        self,
        storage_path: str,
        *,
        file_id: str | None = None,
        file_size: int | None = None,
        expected_duration_seconds: int | None = None,
        extra_prompt_suffix: str = "",
    ) -> str:
        """Start Replicate prediction without blocking (for serverless)."""
        video_uri = self.resolve_video_uri(
            storage_path, file_id=file_id, file_size=file_size
        )
        prediction = self._client.predictions.create(
            model=settings.REPLICATE_MODEL,
            input=self._model_input(
                video_uri,
                expected_duration_seconds=expected_duration_seconds,
                extra_prompt_suffix=extra_prompt_suffix,
            ),
        )
        return prediction.id

    def poll_prediction(self, prediction_id: str) -> tuple[str, GeminiAnalysisResult | None]:
        """Poll once. Returns (status, result) where result is set when succeeded."""
        prediction = self._poll_client.predictions.get(prediction_id)
        status = prediction.status

        if status in {"starting", "processing"}:
            return status, None

        if status != "succeeded":
            raise RuntimeError(prediction.error or f"Prediction ended with status {status}")

        raw = self._extract_output_text(prediction.output)
        logger.info("Replicate output received (%d chars)", len(raw))
        try:
            return status, self._parse_response(raw)
        except Exception as e:
            logger.error("Failed to parse Replicate output (first 800 chars): %s", raw[:800])
            raise RuntimeError(f"Failed to parse model response: {e}") from e

    def _extract_output_text(self, output) -> str:
        if output is None:
            raise ValueError("Empty Replicate output")

        if isinstance(output, dict):
            if "scenes" in output:
                return json.dumps(output, ensure_ascii=False)
            for key in ("text", "output", "content", "response"):
                if key in output and output[key]:
                    return str(output[key])
            return json.dumps(output, ensure_ascii=False)

        if isinstance(output, list):
            chunks: list[str] = []
            for item in output:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict):
                    item_type = str(item.get("type", "")).lower()
                    if "thought" in item_type or item_type in {"reasoning", "signature"}:
                        continue
                    text = item.get("text") or item.get("content") or item.get("output")
                    if text:
                        chunks.append(str(text))
                elif item is not None:
                    text = str(item)
                    if text.startswith("{") or text.startswith("[") or "scene" in text.lower():
                        chunks.append(text)
            raw = "".join(chunks).strip()
            if raw:
                return raw
            raise ValueError("Replicate returned no text output")

        if isinstance(output, str):
            if output.startswith("http://") or output.startswith("https://"):
                with httpx.Client(timeout=120, follow_redirects=True) as client:
                    response = client.get(output)
                response.raise_for_status()
                return response.text
            return output

        return str(output)

    def _normalize_parsed_data(self, data: dict) -> dict:
        scenes = data.get("scenes") or []
        normalized_scenes = []
        for index, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                continue
            scene_copy = dict(scene)
            if "scene_number" not in scene_copy:
                scene_copy["scene_number"] = index + 1
            risks = scene_copy.get("risks")
            if risks is None:
                scene_copy["risks"] = []
            elif isinstance(risks, dict):
                scene_copy["risks"] = [risks]
            normalized_scenes.append(scene_copy)
        data["scenes"] = normalized_scenes
        return data

    def _run_model(self, video_url: str) -> str:
        prediction = self._client.predictions.create(
            model=settings.REPLICATE_MODEL,
            input=self._model_input(video_url),
        )

        deadline = time.time() + 1800
        while prediction.status not in {"succeeded", "failed", "canceled"}:
            if time.time() > deadline:
                raise TimeoutError("Replicate prediction polling timed out after 30 minutes")
            time.sleep(5)
            prediction.reload()

        if prediction.status != "succeeded":
            error = prediction.error or f"Prediction ended with status {prediction.status}"
            raise RuntimeError(error)

        return self._extract_output_text(prediction.output)

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

        if isinstance(data, dict):
            data = self._normalize_parsed_data(data)
            data["scenes"] = [
                scene
                for scene in data.get("scenes", [])
                if isinstance(scene, dict) and scene.get("risks")
            ]

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
