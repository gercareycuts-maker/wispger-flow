"""Groq Whisper API client and audio recording."""

import array
import io
import math
import threading
import wave

import requests
import sounddevice as sd

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3-turbo"
WHISPER_PROMPT = "Hello, how are you? I'm doing well. Yes, that sounds great! Let me think about it. Okay, I'll do that."


class AudioRecorder:
    """Thread-safe audio recorder using sounddevice."""
    RATE = 16000

    def __init__(self):
        self._chunks, self._stream, self._lock, self.level = [], None, threading.Lock(), 0.0

    def start(self):
        with self._lock:
            self._chunks.clear()
        self.level = 0.0
        self._stream = sd.RawInputStream(
            samplerate=self.RATE, channels=1, dtype="int16",
            blocksize=self.RATE // 10, callback=self._cb,
        )
        self._stream.start()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.level = 0.0
        with self._lock:
            data = b"".join(self._chunks)
            self._chunks.clear()
            return data

    def _cb(self, indata, *_):
        raw = bytes(indata)
        with self._lock:
            self._chunks.append(raw)
        s = array.array("h", raw)
        if s:
            self.level = math.sqrt(sum(v * v for v in s[::8]) / max(len(s) // 8, 1)) / 32768.0

    def to_wav(self, pcm):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.RATE)
            w.writeframes(pcm)
        return buf.getvalue()


def send_transcription(api_key, wav_bytes, language, prompt):
    """POST audio to Groq Whisper API. Returns raw text or raises on error."""
    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        data={
            "model": GROQ_MODEL,
            "language": language,
            "response_format": "json",
            "prompt": prompt,
        },
        timeout=15,
    )
    if resp.status_code == 401:
        raise PermissionError("Invalid API key")
    resp.raise_for_status()
    return resp.json().get("text", "").strip()
