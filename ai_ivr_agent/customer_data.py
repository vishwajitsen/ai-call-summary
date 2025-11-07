# customer_data.py
from pathlib import Path
import pandas as pd
import random
from faker import Faker
import re

DATA_PATH = Path("data/customers.xlsx")

def generate_customers(n=1000, path=DATA_PATH):
    """
    Generates sample customer data for testing. Creates an Excel file with
    random customer information if it doesn't already exist.
    
    :param n: Number of sample customers to generate (default: 1000)
    :param path: Path to save the customer data file
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        print(f"Customer data file exists: {path}")
        return
    fake = Faker()
    rows = []
    for i in range(n):
        phone = f"{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}"
        ssn = ''.join(random.choices("0123456789", k=9))
        dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%m/%d/%Y")
        rows.append({
            "customer_id": i+1,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "phone": phone,
            "last4ssn": ssn[-4:],
            "dob": dob,
            "zip_code": fake.zipcode(),
            "plan": random.choice(["Basic", "Gold", "Premium"]),
            "status": random.choice(["Bronze", "Silver", "Gold", "Diamond"]),
            "email": fake.email()
        })
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False)
    print(f"{n} sample customers created at {path}")

def _normalize_digits(s: str):
    """
    Utility to extract digits from any input string (e.g., spoken input)
    """
    if not s:
        return ""
    return re.sub(r"\D", "", s)

def validate_customer(phone_spoken: str, last4_spoken: str, dob_spoken: str, path=DATA_PATH):
    """
    Validates a customer using spoken phone number, last 4 of SSN, and DOB.
    
    :param phone_spoken: Full phone number spoken by user (may include text or formats)
    :param last4_spoken: Spoken last 4 of SSN (may include noise)
    :param dob_spoken: Spoken date of birth (e.g., "11 slash 10 slash 1986")
    :param path: Path to the customer data file
    :return: Matching customer record as a dict or None
    """
    if not path.exists():
        return None

    # Normalize inputs
    phone_digits = _normalize_digits(phone_spoken)
    last4 = _normalize_digits(last4_spoken)[-4:]
    dob_norm = dob_spoken.strip()

    # Normalize DOB if written as digits (e.g., "11101986" → "11/10/1986")
    raw_digits = re.sub(r"\D", "", dob_norm)
    if len(raw_digits) == 8:
        dob_norm = f"{raw_digits[0:2]}/{raw_digits[2:4]}/{raw_digits[4:8]}"

    # Load data
    df = pd.read_excel(path, dtype=str)
    df['phone_norm'] = df['phone'].astype(str).str.replace(r"\D", "", regex=True).str[-10:]

    # Filter data by phone, last4ssn, and dob
    match = df[
        (df['phone_norm'].str.endswith(phone_digits[-10:])) &
        (df['last4ssn'] == last4) &
        (df['dob'] == dob_norm)
    ]

    if not match.empty:
        return match.iloc[0].to_dict()
    return None
