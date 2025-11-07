# fhir_appointments.py
"""
STU3 Appointment helpers for Epic sandbox.
Implements:
 - Appointment/$find (POST) -> returns list of proposed appointment resources (Bundle)
 - Appointment/$book (POST) -> books selected appointment returned by $find

Usage: instantiate with EpicOAuthClient instance (to obtain token when needed).
"""

import os
import requests
from datetime import datetime, timedelta
import json

EPIC_FHIR_BASE = os.getenv("EPIC_FHIR_BASE", "https://fhir.epic.com/interconnect-fhir-stu3/api/FHIR/STU3")
EPIC_FHIR_BASE = EPIC_FHIR_BASE.rstrip("/")

class FHIRAppointmentClient:
    def __init__(self, epic_client):
        """
        epic_client: instance of EpicOAuthClient (used only to fetch access token externally)
        """
        self.epic = epic_client
        self.base = EPIC_FHIR_BASE

    def _headers(self, access_token):
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json"
        }

    # -------------------- Appointment.$find --------------------
    def find_slots(self, patient_id: str, access_token: str,
                   start_dt: datetime = None, end_dt: datetime = None,
                   service_code: dict = None, specialty_text: str = None):
        """
        Call Appointment/$find with Parameters resource.
        - patient_id: FHIR Patient id (from Epic OAuth session)
        - start_dt, end_dt: datetime window (defaults: now .. now+14 days)
        - service_code: optional dict for serviceType coding e.g.
            {"system":"urn:oid:1.2.840.114350.1.13.861.1.7.2.808267","code":"10770","display":"Office Visit"}
        - returns list of appointment "resources" (simplified entries)
        """
        if not access_token:
            raise RuntimeError("access_token required")

        if start_dt is None:
            start_dt = datetime.utcnow()
        if end_dt is None:
            end_dt = start_dt + timedelta(days=14)

        # Build Parameters body as described by Epic STU3 docs:
        # parameter: patient (resource Patient), startTime, endTime, serviceType (valueCodeableConcept)
        params_body = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "patient",
                    "resource": {
                        "resourceType": "Patient",
                        "id": patient_id
                    }
                },
                {
                    "name": "startTime",
                    "valueDateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                },
                {
                    "name": "endTime",
                    "valueDateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            ]
        }

        if service_code:
            params_body["parameter"].append({
                "name": "serviceType",
                "valueCodeableConcept": {"coding": [service_code]}
            })

        # Optional specialty text passed as a free-text param (some orgs accept it)
        if specialty_text:
            params_body["parameter"].append({
                "name": "specialty",
                "valueString": specialty_text
            })

        url = f"{self.base}/Appointment/$find"
        r = requests.post(url, headers=self._headers(access_token), json=params_body, timeout=30)
        r.raise_for_status()
        bundle = r.json()

        # Parse returned Bundle entries into a simplified list
        results = []
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {}) or entry.get("resource")
            # Appointment resource in STU3 may contain contained Slot or a Slot reference
            appt_id = resource.get("id")
            start = resource.get("start") or (resource.get("contained") and resource.get("contained")[0].get("start") if resource.get("contained") else None)
            end = resource.get("end") or (resource.get("contained") and resource.get("contained")[0].get("end") if resource.get("contained") else None)
            # try to display provider/location
            practitioner_display = None
            participants = resource.get("participant", [])
            for p in participants:
                actor = p.get("actor", {})
                if actor and actor.get("display"):
                    practitioner_display = actor.get("display")
                    break
            results.append({
                "appointment_id": appt_id,
                "resource": resource,
                "start": start,
                "end": end,
                "start_human": start.replace("T", " ").replace("Z", " UTC") if start else "unknown",
                "practitioner_display": practitioner_display
            })

        return results

    # -------------------- Appointment.$book --------------------
    def book_appointment(self, patient_id: str, appointment_id: str, access_token: str, reason: str = None):
        """
        Book an appointment selected from a prior $find result.
        - appointment_id: the Appointment id returned by $find (the "proposed" appointment)
        - patient_id: FHIR Patient id
        - returns server response JSON
        Per Epic STU3 docs the body is a Parameters with 'id' and 'patient' resource.
        """
        if not access_token:
            raise RuntimeError("access_token required")

        params = {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "id", "valueString": appointment_id},
                {"name": "patient", "resource": {"resourceType": "Patient", "id": patient_id}}
            ]
        }

        if reason:
            params["parameter"].append({"name": "comment", "valueString": reason})

        url = f"{self.base}/Appointment/$book"
        r = requests.post(url, headers=self._headers(access_token), json=params, timeout=30)
        r.raise_for_status()
        return r.json()

    # -------------------- Convenience: read appointment by id --------------------
    def read_appointment(self, appointment_id: str, access_token: str):
        url = f"{self.base}/Appointment/{appointment_id}"
        r = requests.get(url, headers=self._headers(access_token), timeout=30)
        r.raise_for_status()
        return r.json()
