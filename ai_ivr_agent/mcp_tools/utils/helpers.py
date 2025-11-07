import os
import datetime
import logging

# ------------------------------------------------------------
# Logging Setup
# ------------------------------------------------------------
logger = logging.getLogger("mcp_helpers")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ------------------------------------------------------------
# Environment Helpers
# ------------------------------------------------------------
def safe_env(key: str, default=None):
    """
    Read an environment variable safely.
    """
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value


# ------------------------------------------------------------
# Time / Formatting Helpers
# ------------------------------------------------------------
def iso_to_human(iso_dt: str):
    """
    Convert ISO datetime to readable form.
    Example: '2025-01-01T09:30:00Z' -> 'Jan 1, 2025 09:30'
    """
    if not iso_dt:
        return "Unknown"

    try:
        dt = datetime.datetime.fromisoformat(iso_dt.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return iso_dt


def format_slot_readable(slot_obj: dict):
    """
    Format a FHIR Slot entry into human-readable text.
    Handles both STU3 and R4 formats.
    """
    try:
        start = slot_obj.get("start")
        end = slot_obj.get("end")
        status = slot_obj.get("status", "UNKNOWN")

        start_h = iso_to_human(start)
        end_h = iso_to_human(end)

        return f"{start_h} → {end_h} ({status})"
    except Exception as e:
        logger.error(f"Failed to format slot: {e}")
        return "Unavailable slot"


# ------------------------------------------------------------
# Misc Helpers
# ------------------------------------------------------------
def mask(value: str, show_last=4):
    """
    Mask sensitive strings.
    Example: 123456789 -> *****6789
    """
    if not value:
        return ""
    return "*" * max(0, len(value) - show_last) + value[-show_last:]


def debug_dump(obj, label="DEBUG"):
    """
    Pretty-print dicts or objects for debugging.
    """
    logger.info(f"[{label}] {obj}")
