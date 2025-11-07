import os
import sys
import time
import sounddevice as sd
from scipy.io.wavfile import write
from dotenv import load_dotenv
import pandas as pd
import azure.cognitiveservices.speech as speechsdk
from openai import AzureOpenAI

# ----------------- Load environment -----------------
load_dotenv()

AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION")

DATA_PATH = os.getenv(
    "DATA_PATH",
    os.path.join(os.getcwd(), "customers_us.xlsx")
)

# ----------------- Validations -----------------
if not SPEECH_KEY or not SPEECH_REGION:
    print("❌ Missing SPEECH_KEY or SPEECH_REGION in .env")
    sys.exit(1)
if not AZURE_OPENAI_KEY or not AZURE_OPENAI_ENDPOINT:
    print("❌ Missing AZURE_OPENAI_KEY or AZURE_OPENAI_ENDPOINT in .env")
    sys.exit(1)
if not os.path.exists(DATA_PATH):
    print(f"❌ Customer data file not found at: {DATA_PATH}")
    sys.exit(1)

# ----------------- Initialize Clients -----------------
speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
speech_config.speech_recognition_language = "en-US"

try:
    openai_client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version="2024-08-01-preview"
    )
except Exception as e:
    print("⚠️ Could not initialize Azure OpenAI client:", e)
    openai_client = None


# ----------------- RECORD AUDIO -----------------
def record_audio(filename="input.wav", duration=8, fs=16000):
    print(f"\n🎤 Recording for {duration} seconds — speak now!")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="int16")
    sd.wait()
    write(filename, fs, audio)
    print(f"✅ Saved audio as: {filename}")
    return filename


# ----------------- TRANSCRIBE AUDIO -----------------
def transcribe_audio(filename):
    try:
        audio_config = speechsdk.AudioConfig(filename=filename)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        print("🎧 Transcribing your speech...")
        result = recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print("🗣️ Transcript:", result.text)
            return result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("⚠️ No speech recognized.")
        elif result.reason == speechsdk.ResultReason.Canceled:
            cd = result.cancellation_details
            print("⚠️ Transcription canceled:", cd.reason)
            if cd.reason == speechsdk.CancellationReason.Error:
                print("Error details:", cd.error_details)
        return None
    except Exception as e:
        print("❌ Transcription error:", e)
        return None


# ----------------- VALIDATE CUSTOMER -----------------
def validate_customer_by_phone(phone_input: str):
    try:
        df = pd.read_excel(DATA_PATH, dtype=str)
    except Exception as e:
        print("❌ Failed to read customer file:", e)
        return None

    df.columns = [c.strip().lower() for c in df.columns]
    phone_col = next((c for c in df.columns if "phone" in c), None)

    if not phone_col:
        print("❌ No phone column found in customer data.")
        return None

    df[phone_col] = df[phone_col].astype(str).str.replace(r"[\s\-\(\)]", "", regex=True)
    normalized_input = phone_input.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    match = df[df[phone_col].str.endswith(normalized_input[-10:])]
    if match.empty:
        print("❌ Customer not found.")
        return None

    rec = match.iloc[0].to_dict()
    first = rec.get("first_name") or rec.get("firstname") or ""
    last = rec.get("last_name") or rec.get("lastname") or ""
    print(f"✅ Found customer: {first} {last} (id={rec.get('customer_id')})")
    return rec


# ----------------- GENERATE GPT REPLY -----------------
def generate_gpt_reply(transcript: str, customer: dict | None):
    if openai_client is None:
        return "Assistant unavailable at the moment."

    system_prompt = "You are a warm, concise healthcare IVR assistant. Avoid diagnosis. Encourage professional medical consultation."
    if customer:
        first = customer.get("first_name") or ""
        last = customer.get("last_name") or ""
        system_prompt += f" The verified customer is {first} {last}."

    try:
        response = openai_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript},
            ],
            max_tokens=400,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ GPT error:", e)
        return "Sorry, I couldn't generate a reply."


# ----------------- SPEAK RESPONSE -----------------
def speak_text(text: str, voice: str = "en-US-AvaMultilingualNeural"):
    """
    Speak text using Azure TTS via AvaMultilingualNeural voice.
    Ensures playback on system default speakers.
    """
    try:
        tts_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
        tts_config.speech_synthesis_voice_name = voice

        # Explicitly output to default speaker
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=tts_config, audio_config=audio_config
        )

        print("🔊 Speaking response...")
        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print("✅ Speech completed.")
        elif result.reason == speechsdk.ResultReason.Canceled:
            cd = result.cancellation_details
            print("⚠️ Speech synthesis canceled:", cd.reason)
            if cd.reason == speechsdk.CancellationReason.Error:
                print("Error details:", cd.error_details)
    except Exception as e:
        print("❌ TTS error:", e)


# ----------------- MAIN FLOW -----------------
def main():
    print("------------------------------------------------------")
    print("🤖 AI Healthcare Voice Agent — Local Test")
    print("------------------------------------------------------")

    # Record
    filename = record_audio(duration=10)

    # Transcribe
    transcript = transcribe_audio(filename)
    if not transcript:
        speak_text("I could not hear you clearly. Please try again.")
        return

    # Validate customer
    phone = input("\n📞 Enter caller phone (e.g., +12025550123): ").strip()
    customer = validate_customer_by_phone(phone)

    if customer:
        first = customer.get("first_name") or ""
        speak_text(f"Hello {first}, your identity is verified.")
    else:
        speak_text("Sorry, your number is not recognized.")
        return

    # GPT response
    reply = generate_gpt_reply(transcript, customer)
    print("\n🤖 Assistant reply:\n", reply)

    # Speak GPT response
    speak_text(reply)

    print("\n✅ Done. Re-run to test another caller.")


# ----------------- ENTRY POINT -----------------
if __name__ == "__main__":
    main()
