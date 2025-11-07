import time
import logging
from pathlib import Path
from .helpers import debug_dump

logger = logging.getLogger("auth_server")
logger.setLevel(logging.INFO)


class AuthTokenCache:
    """
    Simple in-memory + disk snapshot token cache.

    ✅ Stores Epic OAuth access_token + refresh_token
    ✅ Persists to disk (auth_token.json)
    ✅ Auto-expiration handling
    """

    def __init__(self, path: Path = Path("data/auth_token.json")):
        self.path = path
        self.token = None
        self._load()

    # ------------------------------------------------------------
    # Load saved token
    # ------------------------------------------------------------
    def _load(self):
        if not self.path.exists():
            return

        try:
            import json

            with open(self.path, "r") as f:
                self.token = json.load(f)
                logger.info(f"Loaded cached Epic token from {self.path}")

        except Exception as e:
            logger.error(f"Failed loading token cache: {e}")

    # ------------------------------------------------------------
    # Save token to disk
    # ------------------------------------------------------------
    def _save(self):
        try:
            import json

            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.token, f, indent=2)
        except Exception as e:
            logger.error(f"Failed saving token cache: {e}")

    # ------------------------------------------------------------
    # Set token + expiration
    # ------------------------------------------------------------
    def set_token(self, access_token, refresh_token, expires_in):
        now = int(time.time())
        self.token = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": now + int(expires_in),
        }

        debug_dump(self.token, tag="SET_EPIC_TOKEN")
        self._save()

    # ------------------------------------------------------------
    # Retrieve active token
    # ------------------------------------------------------------
    def get_token(self):
        if not self.token:
            return None

        expires_at = self.token.get("expires_at", 0)
        now = int(time.time())

        if now >= expires_at:
            logger.info("Cached Epic token expired.")
            return None

        return self.token["access_token"]

    # ------------------------------------------------------------
    # Retrieve refresh_token
    # ------------------------------------------------------------
    def get_refresh_token(self):
        if not self.token:
            return None
        return self.token.get("refresh_token")
