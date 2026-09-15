"""
AHA TTS API Server
-------------------
یک سرور ساده که موتور TTS را از طریق HTTP در دسترس پروژه‌های دیگر
(مثل دستیار هوشمند شما) قرار می‌دهد.

اجرا:
    pip install fastapi uvicorn
    uvicorn aha_tts.server:app --host 0.0.0.0 --port 8000

سپس هر پروژه دیگری (حتی نوشته‌شده با زبان دیگر) می‌تواند با یک
درخواست POST به /tts صدا بگیرد.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from .engine import AhaTTSEngine

app = FastAPI(title="AHA TTS Engine", version="0.1.0")

# موتور را عمداً این‌جا نمی‌سازیم: ساخت آن مدل سنگین را بارگذاری می‌کند و
# ممکن است چند ثانیه طول بکشد. اگر این کار را همین ابتدا (قبل از باز شدن
# پورت) انجام بدیم، Render قبل از این‌که سرویس پورت را باز کند تایم‌اوت
# می‌کند. به‌جایش، موتور در اولین درخواست واقعی ساخته می‌شود (lazy load).
_engine: AhaTTSEngine | None = None


def get_engine() -> AhaTTSEngine:
    global _engine
    if _engine is None:
        _engine = AhaTTSEngine()
    return _engine


class TTSRequest(BaseModel):
    text: str
    lang: str | None = None  # "fa" یا "en"؛ اگر خالی باشد خودکار تشخیص داده می‌شود


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tts")
def tts(req: TTSRequest):
    try:
        audio_bytes = get_engine().synthesize_to_bytes(req.text, lang=req.lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(content=audio_bytes, media_type="audio/wav")
