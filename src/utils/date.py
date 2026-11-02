from datetime import datetime

def parse_date(date_str: str) -> datetime | None:
    """Safely parses an ISO 8601 date string."""
    if not date_str:
        return None
    try:
        # Handle different precisions, e.g., with or without milliseconds
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        logger.warning(f"Could not parse date: {date_str}. Returning None as fallback.")
        return None
