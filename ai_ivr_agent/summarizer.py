# summarizer.py
import os
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
You are a medical call-summary generator for an AI IVR system.
You will receive a raw transcript (JSON entries). Produce a clean structured summary.

RULES:
- Short, clear, clinic-friendly.
- No hallucination: Only infer if obvious.
- Extract patient info if present.
- Always include “intent”, “action_required”, and “confidence”.

Output format (MUST FOLLOW):

{
  "summary": "...",
  "patient": {
      "name": "...", 
      "dob": "...",
      "phone": "...",
      "mrn": "..."
  },
  "intent": "...",
  "requested_appointment_date": "...",
  "action_required": "...",
  "confidence": 0.0
}
"""


class Summarizer:
    def __init__(self):
        pass

    # ----------------------------------------------------------------------
    # BUILD PROMPT
    # ----------------------------------------------------------------------
    def build_prompt(self, transcript_json):
        lines = []
        for item in transcript_json:
            ts = item.get("timestamp", "")
            role = item.get("role", "")
            msg = item.get("message", "")
            lines.append(f"[{ts}] {role.upper()}: {msg}")

        return "\n".join(lines)

    # ----------------------------------------------------------------------
    # RUN SUMMARY
    # ----------------------------------------------------------------------
    def summarize(self, transcript_json):
        prompt = self.build_prompt(transcript_json)

        completion = client.chat.completions.create(
            model="gpt-5",
            temperature=0.0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )

        try:
            raw = completion.choices[0].message["content"]
            return raw
        except:
            return '{"error": "summary_generation_failed"}'


# Optional shared instance
summarizer = Summarizer()
