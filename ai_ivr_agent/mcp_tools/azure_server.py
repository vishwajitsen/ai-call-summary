import os
import asyncio
import logging
import base64
from pathlib import Path
import uuid
import requests

logger = logging.getLogger("azure_speech")
logger.setLevel(logging.INFO)


class AzureSpeechClient:
    """
    Unified Azure Speech client for:
    ✅ Speech-to-Text (ASR)
    ✅ Text-to-Speech (TTS)
    """

    def __init__(self):
        self.speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        self.voice = os.getenv("AZURE_TTS_VOICE", "en-US-AriaNeural")

        if not self.speech_key:
            raise ValueError("AZURE_SPEECH_KEY missing in .env")

        self.asr_url = f"https://{self.region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
        self.tts_url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"

    # ------------------------------------------------------------------
    # TEXT → SPEECH (TTS)
    # ------------------------------------------------------------------
    async def speak(self, text: str, out_path: str = None) -> str:
        """
        Converts text → speech (MP3).
        Returns the path of the MP3 file.
        """

        if not text:
            return None

        logger.info(f"[TTS] Speaking: {text}")

        if not out_path:
            out_path = f"data/audio/tts_{uuid.uuid4().hex}.mp3"
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        xml_body = f"""
            <speak version='1.0' xml:lang='en-US'>
                <voice name='{self.voice}'>{text}</voice>
            </speak>
        """

        headers = {
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-48khz-192kbitrate-mono-mp3",
            "Ocp-Apim-Subscription-Key": self.speech_key,
        }

        r = requests.post(self.tts_url, data=xml_body.encode("utf-8"), headers=headers)
        if r.status_code != 200:
            logger.error(f"TTS error: {r.status_code} {r.text}")
            return None

        with open(out_path, "wb") as f:
            f.write(r.content)

        return out_path

    # ------------------------------------------------------------------
    # SPEECH → TEXT (STT)
    # ------------------------------------------------------------------
    async def transcribe(self, audio_path: str) -> str:
        """
        Transcribes an audio file (wav, mp3).
        """

        if not Path(audio_path).exists():
            logger.error(f"ASR input missing: {audio_path}")
            return ""

        headers = {
            "Ocp-Apim-Subscription-Key": self.speech_key,
            "Content-Type": "audio/wav" if audio_path.endswith(".wav") else "audio/mpeg",
        }

        with open(audio_path, "rb") as audio:
            r = requests.post(self.asr_url, data=audio, headers=headers)

        if r.status_code != 200:
            logger.error(f"ASR error: {r.status_code} {r.text}")
            return ""

        try:
            result = r.json()
            return result.get("DisplayText", "")
        except Exception as e:
            logger.error(f"ASR parse error: {e}")
            return ""

    # ------------------------------------------------------------------
    # CONVERSATION LISTEN ONCE → returns text
    # ------------------------------------------------------------------
    async def listen_once(self) -> str:
        """
        Placeholder — real IVR systems record microphone/telephony audio.

        For local testing, we simulate by input().
        Replace this later when connecting RingCentral, Twilio, or SIP trunk.
        """

        try:
            text = input("🎤 You (simulate microphone): ")
            return text.strip()
        except Exception:
            return ""
