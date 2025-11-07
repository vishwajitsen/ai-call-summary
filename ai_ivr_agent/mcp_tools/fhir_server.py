import logging
from .helpers import debug_dump
from .epic_server import EpicOAuthPKCE

logger = logging.getLogger("fhir_server")
logger.setLevel(logging.INFO)


class FHIRService:
    """
    A thin wrapper around EpicOAuthPKCE to provide high-level FHIR operations:
    ✅ Search for slots (availability)
    ✅ Get patient data
    ✅ Book appointment
    ✅ Generic GET/POST wrappers
    """

    def __init__(self):
        self.epic = EpicOAuthPKCE()
        logger.info("FHIRService initialized.")

    # ------------------------------------------------------------
    # Search for available appointment slots for a provider
    # ------------------------------------------------------------
    def search_slots(self, access_token: str, provider_id: str):
        """
        Uses FHIR Slot search:
        GET /Slot?schedule.actor=ProviderId&status=free
        """

        endpoint = f"Slot?schedule.actor={provider_id}&status=free"

        logger.info(f"Searching slots for provider {provider_id}")

        result = self.epic.fhir_get(endpoint, access_token)

        debug_dump(result, "FHIR_SLOT_SEARCH")

        return result

    # ------------------------------------------------------------
    # Get patient demographic info
    # ------------------------------------------------------------
    def get_patient(self, access_token: str, patient_id: str):
        """
        GET /Patient/{id}
        """

        endpoint = f"Patient/{patient_id}"

        logger.info(f"Fetching Patient {patient_id}")

        result = self.epic.fhir_get(endpoint, access_token)

        debug_dump(result, "FHIR_GET_PATIENT")

        return result

    # ------------------------------------------------------------
    # Book Appointment using STU3 / Appointment resource
    # ------------------------------------------------------------
    def book_appointment(self, access_token: str, patient_id: str, slot_id: str, provider_id: str):
        """
        POST /Appointment
        """

        appointment_body = {
            "resourceType": "Appointment",
            "status": "booked",
            "participant": [
                {
                    "actor": {
                        "reference": f"Patient/{patient_id}"
                    },
                    "status": "accepted"
                },
                {
                    "actor": {
                        "reference": f"Practitioner/{provider_id}"
                    },
                    "status": "accepted"
                }
            ],
            "slot": [
                {
                    "reference": f"Slot/{slot_id}"
                }
            ],
            "description": "IVR AI auto-booked appointment"
        }

        debug_dump(appointment_body, "FHIR_APPOINTMENT_BODY")

        logger.info(f"Booking Appointment → P:{patient_id} S:{slot_id}")

        result = self.epic.fhir_post("Appointment", access_token, appointment_body)

        debug_dump(result, "FHIR_APPOINTMENT_RESPONSE")

        return result

    # ------------------------------------------------------------
    # Generic FHIR delegations
    # ------------------------------------------------------------
    def fhir_get(self, endpoint: str, access_token: str):
        return self.epic.fhir_get(endpoint, access_token)

    def fhir_post(self, endpoint: str, access_token: str, body: dict):
        return self.epic.fhir_post(endpoint, access_token, body)

