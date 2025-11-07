# azure_asr_tts.py
import azure.cognitiveservices.speech as speechsdk
import os
import asyncio

class AzureSpeechClient:
    def __init__(self):
        self.speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.region = os.getenv("AZURE_SPEECH_REGION")

        if not self.speech_key or not self.region:
            raise Exception("Azure Speech: Missing AZURE_SPEECH_KEY or AZURE_SPEECH_REGION in .env")

        # Speech Config
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.region
        )
        self.speech_config.speech_recognition_language = "en-US"

        # Voice for TTS
        self.speech_config.speech_synthesis_voice_name = os.getenv(
            "AZURE_TTS_VOICE",
            "en-US-JennyNeural"
        )

        # Audio output
        self.audio_output = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

    # ----------------------------------------------------------------------
    # SYNTHESIZE SPEECH
    # ----------------------------------------------------------------------
    async def speak(self, text: str):
        """Speak text out loud using Azure TTS."""
        try:
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=self.audio_output
            )
            print(f"[TTS] {text}")
            result = synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
            else:
                print("[TTS ERROR]", result)
                return False

        except Exception as e:
            print("\n[SPEAK ERROR]\n", e)
            return False

    # ----------------------------------------------------------------------
    # CAPTURE USER SPEECH
    # ----------------------------------------------------------------------
    async def listen_once(self, timeout_seconds=8):
        """
        Listen for one utterance of speech.
        Returns text or "" on failure.
        """

        try:
            # Microphone input
            audio_in = speechsdk.audio.AudioConfig(use_default_microphone=True)

            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_in
            )

            print("[ASR] Listening...")

            # Run async recognition in a thread
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, recognizer.recognize_once)

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print("[ASR RESULT]", result.text)
                return result.text.strip()

            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("[ASR] No speech recognized")
                return ""

            elif result.reason == speechsdk.ResultReason.Canceled:
                print("[ASR] Canceled:", result.cancellation_details)
                return ""

            return ""

        except Exception as e:
            print("\n[ASR ERROR]\n", e)
            return ""
