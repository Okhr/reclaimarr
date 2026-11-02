import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigError(Exception):
    """Custom exception for missing configuration."""
    pass


def get_env_variable(var_name: str, default: str | None = None, required: bool | None = True, options: list | None = None) -> str:
    """Get an environment variable or return a default value."""
    value = os.getenv(var_name)
    if value is None:
        if not required or default is not None:
            return default
        raise ConfigError(f"Required environment variable '{var_name}' not found. Please set it in your .env file.")

    if options is not None:
        if not value in options:
            raise ConfigError(f"Environment variable '{var_name}' has an invalid value. Please set the variable to one of these: {options}")

    return value


# --- Jellyfin Configuration ---
JELLYFIN_URL = get_env_variable("JELLYFIN_URL")
JELLYFIN_API_KEY = get_env_variable("JELLYFIN_API_KEY")

# --- Jellystat Configuration ---
JELLYSTAT_URL = get_env_variable("JELLYSTAT_URL", required=False)
JELLYSTAT_API_KEY = get_env_variable("JELLYSTAT_API_KEY", required=False)

# --- Jellyseerr Configuration ---
JELLYSEERR_URL = get_env_variable("JELLYSEERR_URL")
JELLYSEERR_API_KEY = get_env_variable("JELLYSEERR_API_KEY")
JELLYSEERR_DELETE_REQUESTS = get_env_variable("JELLYSEERR_DELETE_REQUESTS", "false").lower() in ('true', '1', 'yes')

# --- Radarr Configuration ---
RADARR_URL = get_env_variable("RADARR_URL")
RADARR_API_KEY = get_env_variable("RADARR_API_KEY")

# --- Sonarr Configuration ---
SONARR_URL = get_env_variable("SONARR_URL")
SONARR_API_KEY = get_env_variable("SONARR_API_KEY")

# --- Media Path ---
MEDIA_PATH = get_env_variable("MEDIA_PATH")

# --- Deletion Settings ---
TARGET_USAGE = int(get_env_variable("TARGET_USAGE", "80"))
MIN_AGE_DAYS = int(get_env_variable("MIN_AGE_DAYS", "90"))
DRY_RUN = get_env_variable("DRY_RUN", "true").lower() in ('true', '1', 'yes')
VERBOSE = get_env_variable("VERBOSE", "false").lower() in ('true', '1', 'yes')
STRATEGY = get_env_variable("STRATEGY", "PRESERVE_WATCHED", options=["PRESERVE_WATCHED", "MERGE_LAST_WATCHED_DATE_ADDED"])

# --- Scheduler Settings ---
# A cron-style string to schedule runs (e.g., "0 3 * * *" for 3 AM daily).
# If not set, the script will run only once.
CRON_SCHEDULE = get_env_variable("CRON_SCHEDULE", required=False)


if __name__ == '__main__':
    # A simple check to print the loaded configuration for verification
    print("--- Configuration Loaded ---")
    print(f"JELLYFIN_URL: {JELLYFIN_URL}")
    print(f"JELLYSTAT_URL: {JELLYSTAT_URL}")
    print(f"JELLYSEERR_URL: {JELLYSEERR_URL}")
    print(f"RADARR_URL: {RADARR_URL}")
    print(f"SONARR_URL: {SONARR_URL}")
    print(f"MEDIA_PATH: {MEDIA_PATH or 'Not Set'}")
    print("--- Deletion Settings ---")
    print(f"TARGET_USAGE: {TARGET_USAGE}%")
    print(f"MIN_AGE_DAYS: {MIN_AGE_DAYS}")
    print(f"DRY_RUN: {DRY_RUN}")
    print(f"VERBOSE: {VERBOSE}")
    print("--- Scheduler Settings ---")
    print(f"CRON_SCHEDULE: {CRON_SCHEDULE or 'Not Set'}")
    print("--------------------------")
