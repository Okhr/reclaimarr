from pprint import pp
import requests
from typing import Any
from ..config import JELLYFIN_URL, JELLYFIN_API_KEY
from ..utils.logger import setup_logger
from ..utils.date import parse_date

# Initialize logger
logger = setup_logger()


class JellyfinClient:
    """
    A client for interacting with the Jellyfin API.
    """

    def __init__(self, base_url: str = JELLYFIN_URL, api_key: str = JELLYFIN_API_KEY):
        """
        Initializes the JellyfinClient.

        Args:
            base_url (str): The base URL of the Jellyfin server.
            api_key (str): The API key for authentication.
        """
        if not base_url or not api_key:
            raise ValueError("Jellyfin URL and API key must be provided.")

        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "Authorization": f'MediaBrowser Token="{self.api_key}"',
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any | None:
        """
        Performs a GET request to a Jellyfin API endpoint.

        Args:
            endpoint (str): The API endpoint to call.
            params (dict[str, Any] | None): Query parameters for the request.

        Returns:
            Any | None: The JSON response from the API, or None if an error occurs.
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Jellyfin API endpoint {endpoint}: {e}")
            return None

    def get_all_movies(self) -> list[dict[str, Any]]:
        """
        Fetches all movies from the Jellyfin server.

        Returns:
            list[dict[str, Any]]: A list of movie items.
        """
        logger.info("Fetching all movies from Jellyfin...")
        params = {"IncludeItemTypes": "Movie", "Recursive": "true", "Fields": "ProviderIds"}
        data = self._get("/Items", params)
        movies = data.get("Items", []) if data else []
        logger.info(f"Found {len(movies)} movies in Jellyfin.")
        return movies

    def get_all_shows(self) -> list[dict[str, Any]]:
        """
        Fetches all TV shows (series) from the Jellyfin server.

        Returns:
            list[dict[str, Any]]: A list of TV show items.
        """
        logger.info("Fetching all TV shows from Jellyfin...")
        params = {"IncludeItemTypes": "Series", "Recursive": "true", "Fields": "ProviderIds"}
        data = self._get("/Items", params)
        shows = data.get("Items", []) if data else []
        logger.info(f"Found {len(shows)} TV shows in Jellyfin.")
        return shows

    def get_item_details(self, item_id: str) -> dict[str, Any] | None:
        """
        Gets detailed information for a specific media item.

        Args:
            item_id (str): The ID of the Jellyfin item.

        Returns:
            dict[str, Any] | None: Detailed information about the item.
        """
        logger.debug(f"Fetching details for item ID: {item_id}")
        return self._get(f"/Items/{item_id}")

    def get_episodes_for_show(self, show_id: str) -> list[dict[str, Any]]:
        """
        Gets all episodes for a given TV show.

        Args:
            show_id (str): The ID of the Jellyfin TV show (series).

        Returns:
            list[dict[str, Any]]: A list of episode items for the show.
        """
        logger.debug(f"Fetching episodes for show ID: {show_id}")
        data = self._get(f"/Shows/{show_id}/Episodes")
        episodes = data.get("Items", []) if data else []
        logger.debug(f"Found {len(episodes)} episodes for show ID: {show_id}")
        return episodes

    def get_playback_history(self) -> list[dict[str, Any]]:
        users = self._get("/Users")
        playback_events = {}

        for user in users:
            user_id = user.get("Id")
            user_name = user.get("Name")

            # Configure parameters to pull movie data specific to this user context
            params = {
                "Recursive": "true",
                "Fields": "ProviderIds",
                "userId": user_id,
                "enableUserData": "true"
            }

            # Query items for the current iteration's user
            response = self._get("/Items", params)
            items = response.get("Items", [])

            # Parse the results for the current user
            for item in items:
                user_data = item.get("UserData", {})
                last_played = user_data.get("LastPlayedDate")

                # Only append items that actually have a last played timestamp
                if last_played:
                    item_id = item.get("Id")

                    # Only store the most recent playback date per item
                    if (item_id in playback_events and
                        parse_date(playback_events[item_id].get("ActivityDateInserted")) >= parse_date(last_played)):
                        continue

                    playback_events[item_id] = {
                        "ItemId": item_id,
                        "ActivityDateInserted": last_played,
                        "PlaybackDuration": 600,
                        "UserId": user_id,
                        "UserName": user_name,
                        "Played": user_data.get("Played", False)
                    }

        logger.debug(f"Found {len(playback_events)} playback events")
        return list(playback_events.values())


if __name__ == '__main__':
    # Example usage for testing the client
    # Note: This requires a running Jellyfin instance and a valid .env file.

    logger = setup_logger(verbose=True)

    try:
        client = JellyfinClient()

        # Test fetching movies
        movies = client.get_all_movies()
        pp(movies[0])

        # Test fetching shows
        shows = client.get_all_shows()
        pp(shows[0])
        if shows:
            logger.info(f"Successfully fetched {len(shows)} shows.")
            # Log episodes of the first show if available
            first_show_id = shows[0].get("Id")
            if first_show_id:
                episodes = client.get_episodes_for_show(first_show_id)
                pp(episodes)
                if episodes:
                    logger.info(f"Found {len(episodes)} episodes for the first show.")

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during testing: {e}")
