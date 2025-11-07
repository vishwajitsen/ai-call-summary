import os
import argparse
import librosa
import numpy as np
import torch
import pandas as pd
from pathlib import Path
from transformers import (
    WhisperProcessor, WhisperForConditionalGeneration,
    Wav2Vec2ForCTC, Wav2Vec2Processor,
    PegasusTokenizer, PegasusForConditionalGeneration,
    T5Tokenizer, T5ForConditionalGeneration,
    pipeline
)
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu
import sounddevice as sd
import scipy.io.wavfile as wav
import time

# ============ CONFIG ============
SAMPLE_RATE = 16000
RECORD_SECONDS = 30
os.makedirs("outputs", exist_ok=True)

# ============ HELPER FUNCTIONS ============
def record_audio(duration=RECORD_SECONDS, sr=SAMPLE_RATE):
    print(f"\n🎙️ Recording for {duration} seconds ...")
    audio = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype="float32")
    sd.wait()
    print("✅ Recording complete!\n")
    return audio.flatten()

def save_audio(audio, path, sr=SAMPLE_RATE):
    wav.write(path, sr, (audio * 32767).astype(np.int16))

def load_model_asr():
    print("⏳ Loading ASR models...")
    whisper_processor = WhisperProcessor.from_pretrained("openai/whisper-small")
    whisper_model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-small")

    wav2vec_processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-large-960h-lv60")
    wav2vec_model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-large-960h-lv60")

    return (whisper_processor, whisper_model), (wav2vec_processor, wav2vec_model)

def load_model_summarizers():
    print("⏳ Loading summarization models...")
    pegasus_tokenizer = PegasusTokenizer.from_pretrained("google/pegasus-cnn_dailymail")
    pegasus_model = PegasusForConditionalGeneration.from_pretrained("google/pegasus-cnn_dailymail")

    t5_tokenizer = T5Tokenizer.from_pretrained("t5-base")
    t5_model = T5ForConditionalGeneration.from_pretrained("t5-base")

    return (pegasus_tokenizer, pegasus_model), (t5_tokenizer, t5_model)

def transcribe_whisper(processor, model, audio):
    inputs = processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
    with torch.no_grad():
        generated_ids = model.generate(inputs["input_features"])
    transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return transcription

def transcribe_wav2vec(processor, model, audio):
    inputs = processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = model(inputs.input_values).logits
    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = processor.batch_decode(predicted_ids)[0]
    return transcription.lower()

def summarize_pegasus(tokenizer, model, text):
    tokens = tokenizer(text, truncation=True, padding="longest", return_tensors="pt")
    summary_ids = model.generate(**tokens, max_length=120, min_length=25, num_beams=4)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

def summarize_t5(tokenizer, model, text):
    input_text = "summarize: " + text
    tokens = tokenizer(input_text, return_tensors="pt", truncation=True, padding=True)
    summary_ids = model.generate(**tokens, max_length=120, min_length=25, num_beams=4)
    return tokenizer.decode(summary_ids[0], skip_special_tokens=True)

def evaluate_summary(reference, generated):
    scorer = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)
    rouge = scorer.score(reference, generated)
    bleu = sentence_bleu([reference.split()], generated.split())
    return rouge, bleu

# ============ MAIN PIPELINE ============
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["live", "file"], default="live")
    parser.add_argument("--input_file", type=str, help="Optional .wav file for 'file' mode")
    parser.add_argument("--output_dir", default="outputs")
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(exist_ok=True)

    (whisper_proc, whisper_model), (wav2vec_proc, wav2vec_model) = load_model_asr()
    (pegasus_tok, pegasus_model), (t5_tok, t5_model) = load_model_summarizers()

    if args.mode == "live":
        audio = record_audio()
        audio_path = out / "recorded_audio.wav"
        save_audio(audio, audio_path)
    else:
        if not args.input_file or not Path(args.input_file).exists():
            print("❌ Please provide valid --input_file for mode=file")
            return
        audio_path = args.input_file
        audio, _ = librosa.load(audio_path, sr=SAMPLE_RATE)

    print("🎧 Transcribing audio...")
    whisper_text = transcribe_whisper(whisper_proc, whisper_model, audio)
    wav2vec_text = transcribe_wav2vec(wav2vec_proc, wav2vec_model, audio)

    print("\n📝 Generating summaries...")
    pegasus_summary = summarize_pegasus(pegasus_tok, pegasus_model, whisper_text)
    t5_summary = summarize_t5(t5_tok, t5_model, whisper_text)

    # ============ SAVE CSV ============
    csv_data = pd.DataFrame([
        {
            "ASR Model": "Whisper",
            "Transcription": whisper_text,
            "Summarizer": "Pegasus",
            "Summary": pegasus_summary
        },
        {
            "ASR Model": "Wav2Vec2",
            "Transcription": wav2vec_text,
            "Summarizer": "T5",
            "Summary": t5_summary
        }
    ])
    csv_path = out / "transcription_summary.csv"
    csv_data.to_csv(csv_path, index=False)
    print(f"✅ CSV saved to: {csv_path}")

    # ============ SAVE METRICS ============
    print("\n📊 Evaluating summaries...")
    metrics = []
    for _, row in csv_data.iterrows():
        rouge, bleu = evaluate_summary(row["Transcription"], row["Summary"])
        metrics.append({
            "ASR Model": row["ASR Model"],
            "Summarizer": row["Summarizer"],
            "ROUGE-1": rouge["rouge1"].fmeasure,
            "ROUGE-L": rouge["rougeL"].fmeasure,
            "BLEU": bleu
        })
    df_metrics = pd.DataFrame(metrics)
    xlsx_path = out / "evaluation_metrics.xlsx"
    df_metrics.to_excel(xlsx_path, index=False)
    print(f"✅ Metrics saved to: {xlsx_path}")

    print("\n🏁 Pipeline complete!\n")
    print(csv_data)
    print(df_metrics)


if __name__ == "__main__":
    main()
