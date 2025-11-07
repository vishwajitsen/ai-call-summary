# email_utils.py
import os
import smtplib
from email.message import EmailMessage

class EmailClient:
    """
    Sends appointment confirmations and general notifications.
    Works with Outlook, Gmail, or any SMTP provider.
    """

    def __init__(self):
        self.host = os.getenv("EMAIL_HOST")
        self.port = int(os.getenv("EMAIL_PORT", "587"))
        self.user = os.getenv("EMAIL_HOST_USER")
        self.password = os.getenv("EMAIL_HOST_PASSWORD")

        if not all([self.host, self.port, self.user, self.password]):
            print("⚠️ EmailClient missing SMTP environment variables")

    # ------------------------------------------------------------------
    # INTERNAL HELPER
    # ------------------------------------------------------------------
    def _send(self, to_email: str, subject: str, body: str):
        msg = EmailMessage()
        msg["From"] = self.user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)

    # ------------------------------------------------------------------
    # SEND APPOINTMENT CONFIRMATION
    # ------------------------------------------------------------------
    def send_appointment_confirmation(self, to_email: str, patient_name: str, appointment: dict, summary: str):
        if not to_email:
            print("⚠️ No email available for patient, skipping confirmation.")
            return

        subject = f"Appointment Confirmation for {patient_name}"

        appt_time = appointment.get("start")
        appt_provider = appointment.get("provider", "Your Provider")
        appt_location = appointment.get("location", "Clinic")

        body = f"""
Hello {patient_name},

Your appointment has been successfully booked.

📅 **Date & Time:** {appt_time}
👨‍⚕️ **Provider:** {appt_provider}
📍 **Location:** {appt_location}

------------------------------
📘 **Call Summary**
{summary}
------------------------------

Thank you,
AI Virtual Assistant
"""

        try:
            self._send(to_email, subject, body)
            print(f"✅ Email sent to {to_email}")
        except Exception as e:
            print("❌ Email send error:", e)

    # ------------------------------------------------------------------
    # GENERIC EMAIL (OPTIONAL)
    # ------------------------------------------------------------------
    def send_generic(self, to_email: str, subject: str, body: str):
        try:
            self._send(to_email, subject, body)
            print(f"✅ Generic email sent to {to_email}")
        except Exception as e:
            print("❌ Error sending generic email:", e)
