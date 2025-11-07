import smtplib, os
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

msg = MIMEText("Hello from your AI IVR Outlook configuration!")
msg["Subject"] = "IVR Email Test"
msg["From"] = os.getenv("EMAIL_HOST_USER")
msg["To"] = "vishu1009@gmail.com"

with smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT"))) as server:
    server.starttls()
    server.login(os.getenv("EMAIL_HOST_USER"), os.getenv("EMAIL_HOST_PASSWORD"))
    server.send_message(msg)

print("✅ Test email sent successfully!")
