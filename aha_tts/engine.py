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

import audioop
import io
import re
import wave
from pathlib import Path

import requests
from piper import PiperVoice

# مدل‌های صوتی: فارسی از MahtaFetrat/Mana-Persian-Piper (صدای زن، دیتاست Mana-TTS)
# انگلیسی از مخزن رسمی rhasspy/piper-voices
VOICE_SOURCES = {
    "fa": {
        "onnx_url": "https://huggingface.co/MahtaFetrat/Mana-Persian-Piper/resolve/main/fa_IR-mana-medium.onnx",
        "json_url": "https://huggingface.co/MahtaFetrat/Mana-Persian-Piper/resolve/main/fa_IR-mana-medium.onnx.json",
        "filename": "fa_IR-mana-medium",
    },
    "en": {
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
        "filename": "en_US-lessac-medium",
    },
}

MODELS_DIR = Path(__file__).parent / "models"

# فرمت خروجی نهایی — با آنچه پروژه دستیار هوشمند شما انتظار دارد یکی است
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
TARGET_SAMPWIDTH = 2  # 16-bit


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
        source = VOICE_SOURCES[lang]
        name = source["filename"]
        onnx_path = MODELS_DIR / f"{name}.onnx"
        json_path = MODELS_DIR / f"{name}.onnx.json"

        if not onnx_path.exists():
            self._download(source["onnx_url"], onnx_path)
        if not json_path.exists():
            self._download(source["json_url"], json_path)

        return onnx_path

    def _load(self, lang: str) -> PiperVoice:
        if lang not in VOICE_SOURCES:
            raise ValueError(
                f"زبان '{lang}' پشتیبانی نمی‌شود. زبان‌های مجاز: {list(VOICE_SOURCES.keys())}"
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

    @staticmethod
    def _standardize_wav(wav_bytes: bytes) -> bytes:
        """تبدیل هر WAV ورودی به ۱۶kHz / مونو / ۱۶-بیت (فرمت مورد انتظار Worker)."""
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf_in:
            n_channels = wf_in.getnchannels()
            sampwidth = wf_in.getsampwidth()
            framerate = wf_in.getframerate()
            frames = wf_in.readframes(wf_in.getnframes())

        # تبدیل به مونو در صورت استریو بودن
        if n_channels == 2 and TARGET_CHANNELS == 1:
            frames = audioop.tomono(frames, sampwidth, 0.5, 0.5)
            n_channels = 1

        # یکسان‌سازی عمق بیت (بیشتر مدل‌های Piper خودشون 16-bit می‌دن)
        if sampwidth != TARGET_SAMPWIDTH:
            frames = audioop.lin2lin(frames, sampwidth, TARGET_SAMPWIDTH)
            sampwidth = TARGET_SAMPWIDTH

        # تغییر نرخ نمونه‌برداری (مثلاً از 22050 به 16000)
        if framerate != TARGET_SAMPLE_RATE:
            frames, _ = audioop.ratecv(
                frames, sampwidth, n_channels, framerate, TARGET_SAMPLE_RATE, None
            )
            framerate = TARGET_SAMPLE_RATE

        out_buf = io.BytesIO()
        with wave.open(out_buf, "wb") as wf_out:
            wf_out.setnchannels(n_channels)
            wf_out.setsampwidth(sampwidth)
            wf_out.setframerate(framerate)
            wf_out.writeframes(frames)
        out_buf.seek(0)
        return out_buf.read()

    def synthesize_to_bytes(self, text: str, lang: str = None) -> bytes:
        """تولید صدا و برگرداندن آن به‌صورت bytes یک فایل WAV (16kHz/مونو/16-bit)."""
        if not text or not text.strip():
            raise ValueError("متن ورودی خالی است.")

        lang = lang or self.detect_language(text)
        voice = self._load(lang)

        raw_buf = io.BytesIO()
        with wave.open(raw_buf, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        raw_buf.seek(0)

        return self._standardize_wav(raw_buf.read())

    def synthesize_to_file(self, text: str, out_path: str, lang: str = None) -> str:
        """تولید صدا و ذخیره مستقیم در فایل (16kHz/مونو/16-bit)."""
        wav_bytes = self.synthesize_to_bytes(text, lang=lang)
        with open(out_path, "wb") as f:
            f.write(wav_bytes)
        return out_path


if __name__ == "__main__":
    engine = AhaTTSEngine()
    engine.synthesize_to_file("سلام، این یک تست است.", "test_fa.wav", lang="fa")
    print("فایل تست ساخته شد: test_fa.wav")
