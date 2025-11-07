import os
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("email_server")
logger.setLevel(logging.INFO)


class EmailServer:
    """
    Outlook SMTP email sender.
    
    ✅ Uses your Outlook account (with App Password or Microsoft 365)
    ✅ Sends plaintext or HTML
    ✅ Handles appointment confirmation emails
    """

    def __init__(self):
        self.smtp_host = os.getenv("EMAIL_HOST", "smtp.office365.com")
        self.smtp_port = int(os.getenv("EMAIL_PORT", 587))
        self.username = os.getenv("EMAIL_HOST_USER")
        self.password = os.getenv("EMAIL_HOST_PASSWORD")  # MUST be an Outlook App Password

        if not self.username or not self.password:
            raise ValueError("Missing EMAIL_HOST_USER or EMAIL_HOST_PASSWORD in .env")

    # -----------------------------------------------------------
    # Generic send email
    # -----------------------------------------------------------
    def send_email(self, to_email: str, subject: str, body: str, html_body: str = None):
        msg = EmailMessage()
        msg["From"] = self.username
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        if html_body:
            msg.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"✅ Email sent to {to_email}")

        except Exception as e:
            logger.error(f"❌ Email failed: {e}")
            raise

    # -----------------------------------------------------------
    # Appointment confirmation
    # -----------------------------------------------------------
    def send_appointment_confirmation(self, to_email, patient_name, appointment, summary_text=None):
        appt_id = appointment.get("id", "Unknown")
        start = appointment.get("start", "Unknown")
        practitioner = appointment.get("practitioner_display", "Doctor")

        subject = f"Appointment Confirmation – {patient_name}"

        text_body = (
            f"Hello {patient_name},\n\n"
            f"Your appointment has been successfully scheduled.\n"
            f"• Appointment ID: {appt_id}\n"
            f"• Provider: {practitioner}\n"
            f"• Time: {start}\n\n"
        )

        if summary_text:
            text_body += f"Conversation summary:\n{summary_text}\n\n"

        text_body += "Thank you.\n"

        html_body = f"""
        <html>
        <body>
            <h2>Appointment Confirmation</h2>
            <p>Hello <b>{patient_name}</b>,</p>
            <p>Your appointment has been scheduled successfully.</p>
            <ul>
                <li><b>Appointment ID:</b> {appt_id}</li>
                <li><b>Provider:</b> {practitioner}</li>
                <li><b>Time:</b> {start}</li>
            </ul>
            {f"<p><b>Conversation Summary:</b><br>{summary_text}</p>" if summary_text else ""}
            <p>Thank you.</p>
        </body>
        </html>
        """

        self.send_email(to_email, subject, text_body, html_body=html_body)
