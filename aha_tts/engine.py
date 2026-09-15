"""
AHA TTS Engine — نسخه سبک (مبتنی بر Piper)
--------------------------------------------
تولید صدا کاملاً محلی و آفلاین، بدون وابستگی به هیچ API ابری.

چرا Piper به‌جای torch/transformers؟
    نسخه‌ی قبلی (MMS/VITS از طریق transformers) روی هاست رایگان با ۵۱۲
    مگابایت رم OOM می‌داد. Piper یک موتور TTS بسیار سبک (مبتنی بر ONNX
    Runtime) است که اصلاً برای اجرا روی سخت‌افزار کم‌منبع (حتی Raspberry
    Pi) طراحی شده و مصرف حافظه‌اش بسیار کمتر است.

نصب پیش‌نیازها:
    pip install piper-tts requests fastapi uvicorn
    (روی Debian/Ubuntu ممکن است به espeak-ng هم نیاز باشد: apt-get install espeak-ng)
"""

import io
import re
import wave
from pathlib import Path

import requests
from piper import PiperVoice

# مدل‌های رسمی Piper برای فارسی و انگلیسی (از مخزن عمومی rhasspy/piper-voices)
MODEL_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

VOICE_PATHS = {
    "fa": "fa/fa_IR/gyro/medium/fa_IR-gyro-medium",
    "en": "en/en_US/lessac/medium/en_US-lessac-medium",
}

MODELS_DIR = Path(__file__).parent / "models"


class AhaTTSEngine:
    """موتور اصلی AHA TTS. یک بار ساخته می‌شود و برای چندین درخواست قابل استفاده مجدد است."""

    def __init__(self, preload=("fa",)):
        self._voices = {}
        MODELS_DIR.mkdir(exist_ok=True)
        for lang in preload:
            self._load(lang)

    @staticmethod
    def _download(url: str, dest: Path):
        resp = requests.get(url, stream=True, timeout=180)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)

    def _ensure_model_files(self, lang: str) -> Path:
        rel = VOICE_PATHS[lang]
        name = rel.split("/")[-1]
        onnx_path = MODELS_DIR / f"{name}.onnx"
        json_path = MODELS_DIR / f"{name}.onnx.json"

        if not onnx_path.exists():
            self._download(f"{MODEL_BASE_URL}/{rel}.onnx", onnx_path)
        if not json_path.exists():
            self._download(f"{MODEL_BASE_URL}/{rel}.onnx.json", json_path)

        return onnx_path

    def _load(self, lang: str) -> PiperVoice:
        if lang not in VOICE_PATHS:
            raise ValueError(
                f"زبان '{lang}' پشتیبانی نمی‌شود. زبان‌های مجاز: {list(VOICE_PATHS.keys())}"
            )
        if lang not in self._voices:
            onnx_path = self._ensure_model_files(lang)
            self._voices[lang] = PiperVoice.load(str(onnx_path))
        return self._voices[lang]

    @staticmethod
    def detect_language(text: str) -> str:
        """تشخیص ساده زبان بر اساس وجود حروف فارسی/عربی در متن."""
        if re.search(r"[\u0600-\u06FF]", text):
            return "fa"
        return "en"

    def synthesize_to_bytes(self, text: str, lang: str = None) -> bytes:
        """تولید صدا و برگرداندن آن به‌صورت bytes یک فایل WAV."""
        if not text or not text.strip():
            raise ValueError("متن ورودی خالی است.")

        lang = lang or self.detect_language(text)
        voice = self._load(lang)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        buf.seek(0)
        return buf.read()

    def synthesize_to_file(self, text: str, out_path: str, lang: str = None) -> str:
        """تولید صدا و ذخیره مستقیم در فایل."""
        if not text or not text.strip():
            raise ValueError("متن ورودی خالی است.")

        lang = lang or self.detect_language(text)
        voice = self._load(lang)

        with wave.open(out_path, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        return out_path


if __name__ == "__main__":
    engine = AhaTTSEngine()
    engine.synthesize_to_file("سلام، این یک تست است.", "test_fa.wav", lang="fa")
    print("فایل تست ساخته شد: test_fa.wav")
