# epic_oauth.py
"""
Epic OAuth helper (STU3 usage)
- Builds authorize URL (PKCE optional)
- Exchanges code for tokens (supports confidential or public clients)
- Refreshes tokens
- Extracts patient FHIR id from id_token or token response
"""
import os
import time
import base64
import json
import secrets
import hashlib
from urllib.parse import urlencode
import requests

# Read environment (set these in your .env):
# EPIC_CLIENT_ID, EPIC_CLIENT_SECRET (optional), EPIC_AUTH_BASE (oauth base), EPIC_FHIR_BASE (FHIR base - STU3),
# EPIC_REDIRECT_URI, EPIC_SCOPE
EPIC_CLIENT_ID = os.getenv("EPIC_CLIENT_ID")
EPIC_CLIENT_SECRET = os.getenv("EPIC_CLIENT_SECRET")  # may be empty for public clients
EPIC_AUTH_BASE = os.getenv("EPIC_AUTH_BASE", "https://fhir.epic.com/interconnect-fhir-oauth/oauth2")
EPIC_TOKEN_URL = EPIC_AUTH_BASE.rstrip("/") + "/token"
EPIC_AUTHORIZE_URL = EPIC_AUTH_BASE.rstrip("/") + "/authorize"
EPIC_FHIR_BASE = os.getenv("EPIC_FHIR_BASE")  # e.g. https://fhir.epic.com/interconnect-fhir-stu3/api/FHIR/STU3
REDIRECT_URI = os.getenv("EPIC_REDIRECT_URI")
SCOPE = os.getenv("EPIC_SCOPE", "launch/patient patient/Appointment.write patient/Slot.read openid fhirUser offline_access")

# in-memory session store: session_id -> token info + pkce verifier + fhir patient id
_SESSIONS = {}

# ---------------- PKCE helpers ----------------
def _make_pkce_pair():
    # RFC7636 PKCE pair
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge

def _safe_b64_json_decode(b64_str):
    try:
        padded = b64_str + "=" * ((4 - len(b64_str) % 4) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        return json.loads(decoded)
    except Exception:
        return {}

# ---------------- EpicOAuthClient ----------------
class EpicOAuthClient:
    def __init__(self):
        self.sessions = _SESSIONS

        # sanity checks
        if not EPIC_CLIENT_ID or not REDIRECT_URI or not EPIC_FHIR_BASE:
            print("WARNING: EPIC_CLIENT_ID, EPIC_REDIRECT_URI and EPIC_FHIR_BASE must be set in environment")

    # create session bucket
    def create_session(self, session_id: str):
        self.sessions[session_id] = {
            "created_at": time.time(),
            "pkce_verifier": None,
            "token": None,
            "fhir_patient_id": None
        }

    # build authorize URL (includes PKCE code challenge)
    def build_authorize_url(self, session_id: str):
        verifier, challenge = _make_pkce_pair()
        self.sessions.setdefault(session_id, {})["pkce_verifier"] = verifier

        params = {
            "client_id": EPIC_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "state": session_id,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "aud": EPIC_FHIR_BASE
        }
        return EPIC_AUTHORIZE_URL + "?" + urlencode(params)

    # exchange code for tokens
    def redeem_code_for_token(self, code: str, session_id: str):
        sess = self.sessions.get(session_id)
        if not sess:
            raise RuntimeError("Unknown session")

        verifier = sess.get("pkce_verifier")
        if not verifier:
            raise RuntimeError("PKCE verifier missing for session")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": EPIC_CLIENT_ID,
            "code_verifier": verifier,
            "aud": EPIC_FHIR_BASE
        }

        # If client secret present, some apps use Basic auth or client_secret in body.
        headers = {}
        if EPIC_CLIENT_SECRET:
            # Use basic auth header (Epic accepts this for confidential apps)
            basic = base64.b64encode(f"{EPIC_CLIENT_ID}:{EPIC_CLIENT_SECRET}".encode()).decode()
            headers["Authorization"] = f"Basic {basic}"

        r = requests.post(EPIC_TOKEN_URL, data=data, headers=headers, timeout=30)
        r.raise_for_status()
        tok = r.json()

        # store token + expiry
        tok["expires_at"] = time.time() + int(tok.get("expires_in", 3600))
        sess["token"] = tok

        # attempt to derive patient id
        fhir_patient = None

        # Epic sometimes returns a patient key in tok (non-standard)
        if "__epic.dstu2.patient" in tok:
            fhir_patient = tok.get("__epic.dstu2.patient")
        if not fhir_patient and "patient" in tok:
            fhir_patient = tok.get("patient")

        # id_token may include fhirUser -> "Patient/{id}" or "Practitioner/..."
        id_token = tok.get("id_token")
        if not fhir_patient and id_token:
            claims = _safe_b64_json_decode(id_token.split(".")[1]) if "." in id_token else {}
            fhir_user = claims.get("fhirUser")
            if fhir_user and "/Patient/" in fhir_user:
                fhir_patient = fhir_user.split("/Patient/")[-1]

        if fhir_patient:
            sess["fhir_patient_id"] = fhir_patient

        return tok

    # check presence of token (does not ensure fresh)
    def has_token(self, session_id: str):
        sess = self.sessions.get(session_id, {})
        tok = sess.get("token")
        return bool(tok and tok.get("access_token"))

    # return access token, refreshing if necessary
    def get_valid_access_token(self, session_id: str):
        sess = self.sessions.get(session_id)
        if not sess or not sess.get("token"):
            return None
        tok = sess["token"]
        # still valid
        if time.time() < tok.get("expires_at", 0) - 10:
            return tok.get("access_token")
        # attempt refresh
        refresh = tok.get("refresh_token")
        if not refresh:
            return None

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": EPIC_CLIENT_ID,
            "aud": EPIC_FHIR_BASE
        }
        headers = {}
        if EPIC_CLIENT_SECRET:
            basic = base64.b64encode(f"{EPIC_CLIENT_ID}:{EPIC_CLIENT_SECRET}".encode()).decode()
            headers["Authorization"] = f"Basic {basic}"

        r = requests.post(EPIC_TOKEN_URL, data=data, headers=headers, timeout=30)
        r.raise_for_status()
        newtok = r.json()
        newtok["expires_at"] = time.time() + int(newtok.get("expires_in", 3600))
        sess["token"] = newtok
        # try re-extract patient id again
        id_token = newtok.get("id_token")
        if id_token:
            claims = _safe_b64_json_decode(id_token.split(".")[1]) if "." in id_token else {}
            fhir_user = claims.get("fhirUser")
            if fhir_user and "/Patient/" in fhir_user:
                sess["fhir_patient_id"] = fhir_user.split("/Patient/")[-1]
        return newtok.get("access_token")

    def get_fhir_patient_id(self, session_id: str):
        sess = self.sessions.get(session_id, {})
        pid = sess.get("fhir_patient_id")
        # debug print
        # print("DEBUG: fhir_patient_id:", pid)
        return pid
