"""Абстракция TTS-клиентов: Yandex SpeechKit v3 / ElevenLabs / OpenAI."""
from __future__ import annotations

import abc
import asyncio
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LOGGER = logging.getLogger("ru_tts.client")


class TTSClient(abc.ABC):
    """Единый интерфейс синтеза. Вход — SSML или plain (зависит от supports_ssml)."""

    name: str = "base"
    supports_ssml: bool = False

    @abc.abstractmethod
    async def synthesize(self, text_or_ssml: str, out_path: Path) -> Path:
        """Синтез в MP3/OGG → out_path. Возвращает путь к файлу."""

    async def synthesize_many(self, items: list[tuple[str, Path]]) -> list[Path]:
        sem = asyncio.Semaphore(int(os.getenv("RU_TTS_CONCURRENCY", "3")))

        async def _one(text: str, path: Path) -> Path:
            async with sem:
                return await self.synthesize(text, path)

        return list(await asyncio.gather(*[_one(t, p) for t, p in items]))


class YandexSpeechKitV3Client(TTSClient):
    """Yandex SpeechKit: пробуем v3 JSON, иначе v1 form (текущий Empire).

    Сеть через stdlib urllib (без обязательного aiohttp).
    """

    name = "yandex_v3"
    supports_ssml = True
    URL_V3 = "https://tts.api.cloud.yandex.net/tts/v3/utteranceSynthesis"
    URL_V1 = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        folder_id: str | None = None,
        voice: str = "filipp",
        role: str = "neutral",
        speed: float = 1.0,
        prefer_v3: bool | None = None,
    ) -> None:
        self.api_key = (
            api_key or os.getenv("YANDEX_API_KEY") or os.getenv("SPEECHKIT_API_KEY") or ""
        ).strip()
        self.folder_id = (
            folder_id or os.getenv("YANDEX_FOLDER_ID") or os.getenv("YC_FOLDER_ID") or ""
        ).strip()
        self.voice = voice or os.getenv("PDF_AUDIO_YANDEX_VOICE", "filipp")
        self.role = role
        self.speed = speed
        if prefer_v3 is None:
            prefer_v3 = (os.getenv("RU_TTS_YANDEX_V3") or "0").strip().lower() not in (
                "0",
                "false",
                "no",
                "off",
            )
        self.prefer_v3 = prefer_v3
        if not self.api_key:
            LOGGER.warning("YandexSpeechKitV3Client: нет YANDEX_API_KEY")

    async def synthesize(self, text_or_ssml: str, out_path: Path) -> Path:
        return await asyncio.to_thread(self._synthesize_sync, text_or_ssml, out_path)

    def _synthesize_sync(self, text_or_ssml: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if self.prefer_v3:
            try:
                return self._synth_v3(text_or_ssml, out_path)
            except Exception as exc:
                LOGGER.warning("yandex v3 failed (%s) — fallback v1", exc)
        return self._synth_v1(text_or_ssml, out_path)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Api-Key {self.api_key}"}

    def _synth_v3(self, text_or_ssml: str, out_path: Path) -> Path:
        payload: dict = {
            "model": "general",
            "voice": self.voice,
            "role": self.role,
            "speed": self.speed,
            "loudnessNormalization": True,
        }
        if text_or_ssml.lstrip().lower().startswith("<speak"):
            payload["ssml"] = text_or_ssml
        else:
            payload["text"] = text_or_ssml
        if self.folder_id:
            payload["folderId"] = self.folder_id
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.URL_V3,
            data=body,
            headers={**self._headers(), "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        if data[:4] == b"ID3" or data[:2] == b"\xff\xfb" or data[:4] == b"OggS":
            out_path.write_bytes(data)
            LOGGER.info("yandex v3 wrote %s (%s bytes)", out_path, len(data))
            return out_path
        raise RuntimeError(f"yandex v3 unexpected payload ({len(data)} bytes)")

    def _synth_v1(self, text_or_ssml: str, out_path: Path) -> Path:
        text = _ssml_to_yandex_v1_text(text_or_ssml)
        form = {
            "text": text,
            "lang": "ru-RU",
            "voice": self.voice,
            "format": "mp3",
            "speed": str(self.speed),
        }
        if self.folder_id:
            form["folderId"] = self.folder_id
        body = urllib.parse.urlencode(form).encode("utf-8")
        req = urllib.request.Request(
            self.URL_V1,
            data=body,
            headers={
                **self._headers(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
        if len(data) < 500:
            raise RuntimeError(f"yandex v1 too short audio: {len(data)} bytes")
        out_path.write_bytes(data)
        LOGGER.info("yandex v1 wrote %s (%s bytes)", out_path, len(data))
        return out_path


class ElevenLabsClient(TTSClient):
    name = "elevenlabs"
    supports_ssml = False
    URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        voice_id: str | None = None,
        model_id: str = "eleven_multilingual_v2",
    ) -> None:
        self.api_key = (api_key or os.getenv("ELEVENLABS_API_KEY") or "").strip()
        self.voice_id = (voice_id or os.getenv("ELEVENLABS_VOICE_ID") or "").strip()
        self.model_id = model_id

    async def synthesize(self, text_or_ssml: str, out_path: Path) -> Path:
        return await asyncio.to_thread(self._synthesize_sync, text_or_ssml, out_path)

    def _synthesize_sync(self, text_or_ssml: str, out_path: Path) -> Path:
        if not self.api_key or not self.voice_id:
            raise RuntimeError("ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID не заданы")
        text = _strip_ssml(text_or_ssml)
        url = self.URL.format(voice_id=self.voice_id)
        payload = json.dumps(
            {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {"stability": 0.4, "similarity_boost": 0.75},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(req, timeout=120) as resp:
            out_path.write_bytes(resp.read())
        LOGGER.info("elevenlabs wrote %s", out_path)
        return out_path


class OpenAITTSClient(TTSClient):
    name = "openai"
    supports_ssml = False
    URL = "https://api.openai.com/v1/audio/speech"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "gpt-4o-mini-tts",
        voice: str = "alloy",
    ) -> None:
        self.api_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        self.model = model
        self.voice = voice

    async def synthesize(self, text_or_ssml: str, out_path: Path) -> Path:
        return await asyncio.to_thread(self._synthesize_sync, text_or_ssml, out_path)

    def _synthesize_sync(self, text_or_ssml: str, out_path: Path) -> Path:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY не задан")
        text = _strip_ssml(text_or_ssml)
        payload = json.dumps(
            {"model": self.model, "voice": self.voice, "input": text, "format": "mp3"}
        ).encode("utf-8")
        req = urllib.request.Request(
            self.URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(req, timeout=120) as resp:
            out_path.write_bytes(resp.read())
        LOGGER.info("openai tts wrote %s", out_path)
        return out_path


def build_tts_client(provider: str | None = None) -> TTSClient:
    name = (provider or os.getenv("RU_TTS_PROVIDER") or "yandex").strip().lower()
    if name in ("yandex", "yandex_v3", "speechkit"):
        return YandexSpeechKitV3Client()
    if name in ("eleven", "elevenlabs"):
        return ElevenLabsClient()
    if name in ("openai", "oai"):
        return OpenAITTSClient()
    raise ValueError(f"Unknown RU_TTS_PROVIDER: {name}")


def _strip_ssml(text: str) -> str:
    import re

    t = re.sub(r"<[^>]+>", " ", text)
    t = t.replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


# Известные IPA → Yandex v1 [[…]] (как в tts_pronunciation_dict.txt).
_IPA_TO_YANDEX_V1 = {
    "ˈmnogə": "[[m n ɔ g ʌ]]",
    "mnogə": "[[m n ɔ g ʌ]]",
    "nʲɪˈmnogə": "[[nʲ ɪ m n ɔ g ʌ]]",
    "nʲɪmnogə": "[[nʲ ɪ m n ɔ g ʌ]]",
}


def _ssml_to_yandex_v1_text(text: str) -> str:
    """SSML → текст/паузы для v1 (sil<[ms]>). IPA phoneme → [[…]] по таблице."""
    import re

    t = text
    # паркуем break до вырезания тегов, иначе <[500]> съест общий cleaner
    t = re.sub(
        r'<break\s+time="(\d+)ms"\s*/>',
        lambda m: f" §SIL{m.group(1)}§ ",
        t,
        flags=re.I,
    )

    def _phoneme(m: re.Match[str]) -> str:
        ph = m.group(1).strip()
        word = m.group(2).strip()
        mapped = _IPA_TO_YANDEX_V1.get(ph) or _IPA_TO_YANDEX_V1.get(
            ph.replace("ˈ", "").replace("ˌ", "")
        )
        return mapped if mapped else word

    # вложенные phoneme — снимаем снаружи внутрь
    for _ in range(4):
        newt = re.sub(
            r'<phoneme[^>]*\bph="([^"]+)"[^>]*>([^<]+)</phoneme>',
            _phoneme,
            t,
            flags=re.I,
        )
        if newt == t:
            break
        t = newt
    t = re.sub(
        r'<sub\s+alias="([^"]+)">[^<]*</sub>',
        lambda m: m.group(1),
        t,
        flags=re.I,
    )
    t = re.sub(r"</?speak>", "", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"§SIL(\d+)§", r"sil<[\1]>", t)
    t = t.replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()
