# ivr_agent.py
import re
from conversation_logger import ConversationLogger

LOGGER = ConversationLogger()

def detect_intent(text: str):
    txt = (text or "").lower()
    if any(k in txt for k in ["benefit", "eligible", "eligibility", "coverage"]):
        return "benefit_eligibility"
    if any(k in txt for k in ["doctor", "appointment", "schedule", "book"]):
        return "doctor_schedule"
    if any(k in txt for k in ["password", "reset", "sign in", "login"]):
        return "password_reset"
    return "general"

async def handle_intent_and_respond(intent: str, user_record: dict, speech_client):
    if intent == "benefit_eligibility":
        plan = user_record.get("plan", "your plan")
        reply = f"Your {plan} plan is active. You have outpatient and prescription coverage. Would you like me to send details to your email?"
        await speech_client.speak(reply)
        LOGGER.append_response(user_record.get("phone"), reply)
        return

    if intent == "doctor_schedule":
        await speech_client.speak("Sure — what specialty do you need, or do you want a primary care physician?")
        specialty = await speech_client.listen_once()
        if not specialty:
            await speech_client.speak("I didn't catch that.")
            return
        await speech_client.speak(f"I found two available primary care appointments next week. Do you want me to book the first one?")
        confirmation = await speech_client.listen_once()
        if "yes" in (confirmation or "").lower():
            await speech_client.speak("Done. Your appointment is booked. You will receive a confirmation via email.")
            LOGGER.append_response(user_record.get("phone"), "Booked appointment (simulated).")
        else:
            await speech_client.speak("Okay, no appointment booked.")
        return

    if intent == "password_reset":
        await speech_client.speak("I can help reset your password. I will send a reset link to your registered email address. Would you like me to proceed?")
        confirm = await speech_client.listen_once()
        if confirm and "yes" in confirm.lower():
            await speech_client.speak("A password reset link has been sent. Please check your email.")
            LOGGER.append_response(user_record.get("phone"), "Password reset initiated.")
        else:
            await speech_client.speak("Okay, no reset initiated.")
        return

    await speech_client.speak("I can help with checking benefits, scheduling doctors, or resetting passwords.")
    return
