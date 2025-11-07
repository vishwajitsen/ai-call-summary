# AI_IVR.py  (Cloudflare Tunnel Version – LocalTunnel Removed Completely)

import asyncio
import os
import sys
import secrets
from flask import Flask, request, jsonify
from dotenv import load_dotenv
load_dotenv()

# Core modules
from azure_asr_tts import AzureSpeechClient
from customer_data import generate_customers, validate_customer
from ivr_agent import detect_intent, handle_intent_and_respond

from epic_oauth import EpicOAuthClient
from fhir_appointments import FHIRAppointmentClient
from conversation_logger import ConversationLogger
from summarizer import Summarizer
from email_utils import EmailClient


# -----------------------------------------------------------
# Flask App Init
# -----------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

# -----------------------------------------------------------
# Initialize Components
# -----------------------------------------------------------
generate_customers()
speech_client = AzureSpeechClient()
EPIC = EpicOAuthClient()
FHIR = FHIRAppointmentClient(EPIC)
LOGGER = ConversationLogger()
SUMMARIZER = Summarizer()
EMAIL = EmailClient()


# -----------------------------------------------------------
# Fallback MCP Router (simple local version)
# -----------------------------------------------------------
class MCPRouterFallback:
    def __init__(self):
        self.epic = EPIC
        self.fhir = FHIR
        self.logger = LOGGER
        self.summarizer = SUMMARIZER
        self.email = EMAIL

    # EPIC OAuth start
    def epic_start(self, session_id: str):
        self.epic.create_session(session_id)
        return self.epic.build_authorize_url(session_id)

    def epic_redeem(self, code: str, session_id: str):
        return self.epic.redeem_code_for_token(code, session_id)

    def epic_has_token(self, session_id: str):
        return self.epic.has_valid_token(session_id)

    def epic_get_access_token(self, session_id: str):
        return self.epic.get_valid_access_token(session_id)

    def epic_get_patient_id(self, session_id: str):
        return self.epic.get_fhir_patient_id(session_id)

    # FHIR
    def find_slots(self, specialty, token, days_ahead=14):
        return self.fhir.search_available_slots(specialty, token, days_ahead)

    def book_slot(self, patient_id, slot, token):
        return self.fhir.book_appointment(patient_id, slot, token)

    # Logging
    def log_utterance(self, phone, text, speaker="user"):
        return self.logger.append_utterance(phone, text, speaker)

    def log_response(self, phone, text, speaker="agent"):
        return self.logger.append_response(phone, text, speaker)

    def get_conversation(self, phone):
        return self.logger.get_recent_conversation(phone)

    # Summary
    def summarize(self, convo):
        return self.summarizer.generate_summary(convo)

    # Email
    def send_email_confirmation(self, to_email, patient_name, appointment, summary):
        return self.email.send_appointment_confirmation(
            to_email, patient_name, appointment, summary
        )


# Create MCP instance
try:
    import mcp_router as m
    MCP = m.MCPRouter()
except:
    MCP = MCPRouterFallback()


# -----------------------------------------------------------
# Full IVR Call Flow
# -----------------------------------------------------------
async def simulate_call_flow():
    await speech_client.speak("Incoming call. Connecting now.")
    user = await authenticate_user()

    if not user:
        return "Authentication failed."

    await speech_client.speak("If you want me to connect to your Epic record, say connect. Otherwise say manual.")

    choice = (await speech_client.listen_once() or "").lower()

    # EPIC MODE
    if "epic" in choice:
        session_id = secrets.token_urlsafe(12)
        auth_url = MCP.epic_start(session_id)

        print(f"[DEBUG] EPIC LOGIN URL for testing:\n{auth_url}\n")

        await speech_client.speak(
            "I sent a secure Epic login link to my console. "
            "Open the link, login, and say done when finished."
        )

        for _ in range(24):  # poll 2 minutes
            await asyncio.sleep(5)
            if MCP.epic_has_token(session_id):
                await speech_client.speak("Epic authentication completed.")
                await speech_client.speak("How can I help you today?")
                utterance = await speech_client.listen_once()
                intent = detect_intent(utterance)
                await handle_intent_with_epic(intent, user, session_id)
                await speech_client.speak("Goodbye.")
                return "Call completed (Epic Mode)."

        await speech_client.speak("Login not detected. Continuing without Epic.")

    # MANUAL MODE
    await speech_client.speak("How can I help you?")
    utterance = await speech_client.listen_once()
    intent = detect_intent(utterance)
    await handle_intent_and_respond(intent, user, speech_client)
    await speech_client.speak("Goodbye.")

    return "Call completed (Manual Mode)."


# -----------------------------------------------------------
# Epic Intent Handler
# -----------------------------------------------------------
async def handle_intent_with_epic(intent, user, session_id):
    phone = user["phone"]
    MCP.log_utterance(phone, f"intent:{intent}")

    if intent != "doctor_schedule":
        return await handle_intent_and_respond(intent, user, speech_client)

    await speech_client.speak("Which specialty do you need?")
    specialty = await speech_client.listen_once()

    token = MCP.epic_get_access_token(session_id)
    patient_id = MCP.epic_get_patient_id(session_id)

    # Search slots
    try:
        slots = MCP.find_slots(specialty, token)
    except Exception:
        await speech_client.speak("I couldn't find any appointments.")
        return

    if not slots:
        await speech_client.speak("No slots available.")
        return

    # Present first 3
    for i, s in enumerate(slots[:3], start=1):
        await speech_client.speak(
            f"Option {i}: {s.get('start_human','Unknown time')} "
            f"with {s.get('practitioner_display','the provider')}."
        )

    await speech_client.speak("Say the option number to book.")
    choice = (await speech_client.listen_once() or "").lower()

    selected = None
    if "1" in choice or "one" in choice:
        selected = slots[0]
    elif "2" in choice and len(slots) > 1:
        selected = slots[1]
    elif "3" in choice and len(slots) > 2:
        selected = slots[2]

    if not selected:
        await speech_client.speak("No appointment booked.")
        return

    # BOOK
    try:
        appointment = MCP.book_slot(patient_id, selected, token)
    except Exception:
        await speech_client.speak("Error booking the appointment.")
        return

    await speech_client.speak("Your appointment is booked.")

    # Summary + email
    convo = MCP.get_conversation(phone)
    summary = MCP.summarize(convo)
    LOGGER.append_summary(phone, summary)

    if user.get("email"):
        try:
            MCP.send_email_confirmation(
                user["email"],
                f"{user['first_name']} {user['last_name']}",
                appointment,
                summary
            )
            await speech_client.speak("Confirmation email sent.")
        except:
            await speech_client.speak("Email sending failed.")

    await speech_client.speak("Anything else?")


# -----------------------------------------------------------
# User Authentication
# -----------------------------------------------------------
async def authenticate_user():
    await speech_client.speak("Please say your registered phone number.")
    phone = await speech_client.listen_once()

    await speech_client.speak("Say the last four digits of your SSN.")
    ssn = await speech_client.listen_once()

    await speech_client.speak("Say your date of birth in MM slash DD slash YYYY.")
    dob = await speech_client.listen_once()

    user = validate_customer(phone, ssn, dob)
    if not user:
        await speech_client.speak("Authentication failed.")
        return None

    await speech_client.speak(f"Welcome {user['first_name']}.")
    return user


# -----------------------------------------------------------
# HTTP Routes
# -----------------------------------------------------------
@app.route("/start_call", methods=["GET", "POST"])
def start_call():
    if request.method == "GET":
        return jsonify({"message": "✅ AI IVR is live!"})
    try:
        asyncio.run(simulate_call_flow())
        return jsonify({"status": "Call finished"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/start_epic_login", methods=["GET"])
def start_epic_login():
    session_id = secrets.token_urlsafe(12)
    url = MCP.epic_start(session_id)
    return jsonify({"session_id": session_id, "auth_url": url})


@app.route("/epic_callback", methods=["GET"])
def epic_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state:
        return "Missing parameters", 400

    try:
        MCP.epic_redeem(code, state)
        return "<h3>Epic login complete. You may return to the call.</h3>"
    except Exception as e:
        return f"Error: {e}", 500


@app.route("/poll_auth", methods=["GET"])
def poll_auth():
    session = request.args.get("session")
    ok = MCP.epic_has_token(session)
    return jsonify({"authenticated": bool(ok)})


# -----------------------------------------------------------
# MAIN (NO LOCAL TUNNEL)
# -----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("✅ Flask server running.")
    print("🌐 Local URL → http://127.0.0.1:5000/start_call")
    print("☁️ For public access: Run Cloudflare tunnel:")
    print("   cloudflared tunnel --url http://localhost:5000\n")
    print("⚠️ LocalTunnel removed permanently.\n")

    app.run(host="0.0.0.0", port=port)
