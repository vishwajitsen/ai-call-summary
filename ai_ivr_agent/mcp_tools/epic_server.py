import os
import json
import base64
import hashlib
import logging
import requests
from urllib.parse import urlencode
from .helpers import safe_env, debug_dump

logger = logging.getLogger("epic_server")
logger.setLevel(logging.INFO)


# ------------------------------------------------------------
# EPIC OAuth2 PKCE Client – Corrected for STU3
# ------------------------------------------------------------

class EpicOAuthPKCE:
    """
    Handles Epic OAuth2 PKCE workflow for STU3 FHIR.
    Fully corrected for:
    - Proper STU3 audience
    - No SMART launch scopes
    - Correct authorize + token endpoints
    """

    def __init__(self):
        # Load from environment
        self.client_id = safe_env("EPIC_CLIENT_ID")
        self.redirect_uri = safe_env("EPIC_REDIRECT_URI")

        # ✅ Correct patient-facing scopes (NO launch/patient)
        self.scope = safe_env(
            "EPIC_SCOPE",
            "openid fhirUser patient/Appointment.read patient/Appointment.write patient/Slot.read offline_access"
        )

        # ✅ Correct default EPIC STU3 Base URL
        self.epic_base_url = safe_env(
            "EPIC_BASE_URL",
            "https://fhir.epic.com/interconnect-fhir-stu3/api/FHIR/STU3"
        )

        # ✅ Correct OAuth endpoints
        self.auth_url = safe_env(
            "EPIC_AUTH_URL",
            "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize"
        )
        self.token_url = safe_env(
            "EPIC_TOKEN_URL",
            "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
        )

        # ✅ Correct STU3 audience needed by Epic
        self.audience = safe_env(
            "EPIC_FHIR_AUDIENCE",
            "https://fhir.epic.com/interconnect-fhir-stu3/api/FHIR/STU3"
        )

        if not self.client_id or not self.redirect_uri:
            raise Exception("Missing EPIC_CLIENT_ID or EPIC_REDIRECT_URI in environment")

        logger.info(f"✅ Epic OAuth PKCE initialized for Client ID: {self.client_id}")

    # ------------------------------------------------------------
    # PKCE Challenge Generator
    # ------------------------------------------------------------
    @staticmethod
    def generate_pkce_pair():
        verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("utf-8")
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("utf-8")).digest()
        ).rstrip(b"=").decode("utf-8")

        return verifier, challenge

    # ------------------------------------------------------------
    # Step 1 — Build Authorization URL (Corrected)
    # ------------------------------------------------------------
    def generate_auth_url(self):
        """
        Returns the full authorization URL with PKCE and correct Epic parameters.
        """

        code_verifier, code_challenge = self.generate_pkce_pair()

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "aud": self.audience,   # ✅ CRITICAL FIX
        }

        url = f"{self.auth_url}?{urlencode(params)}"

        logger.info(f"✅ Generated EPIC Authorization URL:\n{url}")

        return {
            "auth_url": url,
            "code_verifier": code_verifier
        }

    # ------------------------------------------------------------
    # Step 2 — Exchange code for access token (PKCE)
    # ------------------------------------------------------------
    def exchange_code_for_token(self, code: str, code_verifier: str):
        """
        Exchanges the auth code + PKCE verifier for access token.
        """

        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": code_verifier
        }

        logger.info("🔄 Sending Epic token request...")

        resp = requests.post(self.token_url, data=payload, timeout=30)

        if resp.status_code != 200:
            logger.error(f"❌ Epic token request failed: {resp.text}")
            raise Exception(f"Epic token exchange failed: {resp.text}")

        token_json = resp.json()
        debug_dump(token_json, "EPIC_TOKEN_RESPONSE")

        logger.info("✅ Epic token retrieved successfully")

        return token_json

    # ------------------------------------------------------------
    # Step 3 — Generic FHIR GET
    # ------------------------------------------------------------
    def fhir_get(self, endpoint: str, access_token: str):
        """
        Performs GET on Epic FHIR endpoint.
        """

        url = f"{self.epic_base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        logger.info(f"➡️ Epic GET: {url}")

        resp = requests.get(url, headers=headers, timeout=30)

        if resp.status_code not in (200, 201):
            logger.error(f"❌ FHIR GET failed: {resp.status_code} {resp.text}")
            raise Exception(f"Epic GET error {resp.status_code}: {resp.text}")

        return resp.json()

    # ------------------------------------------------------------
    # Step 4 — Generic FHIR POST (Appointment)
    # ------------------------------------------------------------
    def fhir_post(self, endpoint: str, access_token: str, json_body: dict):
        """
        Performs POST on Epic FHIR endpoint.
        """

        url = f"{self.epic_base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        logger.info(f"➡️ Epic POST: {url}")

        resp = requests.post(url, headers=headers, json=json_body, timeout=30)

        if resp.status_code not in (200, 201):
            logger.error(f"❌ FHIR POST failed: {resp.status_code} {resp.text}")
            raise Exception(f"Epic POST error {resp.status_code}: {resp.text}")

        return resp.json()
