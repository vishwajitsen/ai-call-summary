import pandas as pd
from pathlib import Path
import re
import logging
from .helpers import debug_dump

logger = logging.getLogger("customer_server")
logger.setLevel(logging.INFO)

DATA_PATH = Path("data/customers.xlsx")


class CustomerDataService:
    """
    Lightweight internal “customer lookup” service.
    Used for IVR identity verification before using Epic OAuth.

    ✅ Loads customers.xlsx
    ✅ Normalizes spoken phone, SSN last4, DOB
    ✅ Returns matching customer dict
    """

    def __init__(self, data_path: Path = DATA_PATH):
        self.data_path = data_path
        self.data = None
        self._load_data()

    # ------------------------------------------------------------
    # Load Excel data into memory
    # ------------------------------------------------------------
    def _load_data(self):
        if not self.data_path.exists():
            logger.warning(f"Customer data file missing at: {self.data_path}")
            self.data = None
            return

        self.data = pd.read_excel(self.data_path, dtype=str)

        # Normalize phone into a separate column
        self.data["phone_norm"] = (
            self.data["phone"]
            .astype(str)
            .str.replace(r"\D", "", regex=True)
            .str[-10:]
        )

        logger.info(f"Loaded {len(self.data)} customers from {self.data_path}")

    # ------------------------------------------------------------
    # Utility normalizer
    # ------------------------------------------------------------
    @staticmethod
    def normalize_digits(text: str):
        if not text:
            return ""
        return re.sub(r"\D", "", text or "")

    # ------------------------------------------------------------
    # Optional DOB formatter: if user speaks digits → convert to mm/dd/yyyy
    # ------------------------------------------------------------
    @staticmethod
    def normalize_dob(text: str):
        if not text:
            return ""

        text = text.strip()
        only_digits = re.sub(r"\D", "", text)

        # If exactly 8 digits → mmddyyyy → mm/dd/yyyy
        if len(only_digits) == 8:
            return f"{only_digits[0:2]}/{only_digits[2:4]}/{only_digits[4:8]}"

        return text

    # ------------------------------------------------------------
    # Main lookup: phone + last4 + DOB must match
    # ------------------------------------------------------------
    def validate_customer(self, phone: str, last4: str, dob: str):
        if self.data is None:
            return None

        phone_digits = self.normalize_digits(phone)[-10:]
        last4_digits = self.normalize_digits(last4)[-4:]
        dob_norm = self.normalize_dob(dob)

        debug_dump(
            {
                "input_phone": phone,
                "normalized_phone": phone_digits,
                "input_last4": last4,
                "normalized_last4": last4_digits,
                "input_dob": dob,
                "normalized_dob": dob_norm,
            },
            tag="CUSTOMER_LOOKUP_INPUTS",
        )

        match = self.data[
            (self.data["phone_norm"].str.endswith(phone_digits))
            & (self.data["last4ssn"] == last4_digits)
            & (self.data["dob"] == dob_norm)
        ]

        if match.empty:
            logger.info("No matching customer found.")
            return None

        customer = match.iloc[0].to_dict()

        debug_dump(customer, "CUSTOMER_LOOKUP_MATCH")

        return customer
