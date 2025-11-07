# main.py
import asyncio
import os
import subprocess
import sys
from flask import Flask, request, jsonify

from azure_asr_tts import AzureSpeechClient
from customer_data import generate_customers, validate_customer
from ivr_agent import detect_intent, handle_intent_and_respond

app = Flask(__name__)

# --- Ensure customers exist ---
generate_customers()

# --- Initialize Azure Speech client once ---
speech_client = AzureSpeechClient()


# --- Async handler to simulate a call flow ---
async def simulate_call_flow():
    await speech_client.speak("Incoming call. Connecting now.")
    user = await authenticate_user()
    if not user:
        return "Authentication failed."

    await speech_client.speak("How can I help you today?")
    utterance = await speech_client.listen_once()
    intent = detect_intent(utterance)
    await handle_intent_and_respond(intent, user, speech_client)
    await speech_client.speak("Goodbye.")
    return "Call completed."


# --- Authentication loop ---
async def authenticate_user():
    await speech_client.speak("Please say your registered phone number.")
    phone = await speech_client.listen_once()

    await speech_client.speak("Say the last four digits of your SSN.")
    ssn = await speech_client.listen_once()

    await speech_client.speak("Say your date of birth in MM slash DD slash YYYY format.")
    dob = await speech_client.listen_once()

    user = validate_customer(phone, ssn, dob)
    if user:
        await speech_client.speak(f"Welcome {user.get('first_name', '')}.")
        return user

    await speech_client.speak("Authentication failed.")
    return None


# --- Flask Route ---
@app.route("/start_call", methods=["GET", "POST"])
def start_call():
    if request.method == "GET":
        return jsonify({
            "message": "✅ AI IVR endpoint is live!",
            "usage": "Send a POST request to /start_call to simulate a call."
        }), 200

    try:
        asyncio.run(simulate_call_flow())
        return jsonify({"status": "Call simulation completed successfully ✅"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Helper: find the lt (localtunnel) command ---
def find_localtunnel_exe():
    """Find localtunnel executable even if npm global path is not in system PATH."""
    # Common npm global install paths on Windows
    candidates = [
        os.path.expanduser("~\\AppData\\Roaming\\npm\\lt.cmd"),
        os.path.expanduser("~\\AppData\\Roaming\\npm\\lt"),
        "lt",  # If it's already in PATH
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


# --- Run Flask + LocalTunnel ---
if __name__ == "__main__":
    port = 5000
    print("🚀 Starting Flask server and creating LocalTunnel public URL...")

    lt_exe = find_localtunnel_exe()
    if not lt_exe:
        print("❌ Could not find LocalTunnel executable.")
        print("👉 Please run this command first:\n   npm install -g localtunnel")
        print("Then re-run this script.")
        sys.exit(1)

    # Optional: you can fix your subdomain here (change None to your desired subdomain)
    subdomain = "aiivrbot"  # change to your preferred name or set to None

    try:
        # Build LocalTunnel command
        cmd = [lt_exe, "--port", str(port)]
        if subdomain:
            cmd.extend(["--subdomain", subdomain])

        lt_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        public_url = None
        for line in lt_process.stdout:
            if "your url is:" in line.lower() or "https://" in line:
                public_url = line.strip().split()[-1]
                break

        if public_url:
            local_url = f"http://127.0.0.1:{port}"
            print("\n✅ Flask server started successfully!")
            print("────────────────────────────────────────────")
            print(f"🌐 Local URL   → {local_url}/start_call")
            print(f"☁️  Tunnel URL  → {public_url}/start_call")
            print("────────────────────────────────────────────")
            print("\n💡 Use the TUNNEL URL for EPIC or Twilio webhooks.")
            print("💡 You can test locally using the LOCAL URL (e.g., with Postman).")
            print("\nPress CTRL+C to stop.\n")

        else:
            print("❌ Failed to retrieve LocalTunnel URL. Check your Node.js or lt installation.")

    except Exception as e:
        print(f"❌ Error starting LocalTunnel: {e}")

    # Start Flask
    app.run(port=port)
