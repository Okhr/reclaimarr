from pprint import pp
import requests
from typing import Any
from ..config import JELLYSEERR_URL, JELLYSEERR_API_KEY
from ..utils.logger import setup_logger

# Initialize logger
logger = setup_logger()


class JellyseerrClient:
    """
    A client for interacting with the Jellyseerr API.
    """

    def __init__(self, base_url: str = JELLYSEERR_URL, api_key: str = JELLYSEERR_API_KEY):
        """
        Initializes the JellyseerrClient.

        Args:
            base_url (str): The base URL of the Jellyseerr server.
            api_key (str): The API key for authentication.
        """
        if not base_url or not api_key:
            raise ValueError("Jellyseerr URL and API key must be provided.")

        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any | None:
        """
        Performs a GET request to a Jellyseerr API endpoint.

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
            logger.error(f"Error calling Jellyseerr API endpoint GET {endpoint}: {e}")
            return None

    def _delete(self, endpoint: str, params: dict[str, Any] | None = None) -> bool:
        """
        Performs a DELETE request to a Jellyseerr API endpoint.

        Args:
            endpoint (str): The API endpoint to call.
            params (dict[str, Any] | None): Query parameters for the request.

        Returns:
            Any | None: The JSON response from the API, or None if an error occurs.
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.delete(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Jellyseerr API endpoint DELETE {endpoint}: {e}")
            return False

    def get_all_requests(self) -> list[dict[str, Any]]:
        """
        Fetches all media requests from the Jellyseerr server.

        Returns:
            list[dict[str, Any]]: A list of media request records.
        """
        logger.info("Fetching all media requests from Jellyseerr...")
        # The endpoint from the swagger is /api/v1/request
        # Jellyseerr API might require pagination. For now, we fetch without it.
        # A `take` parameter might be needed for larger libraries.
        params = {"take": 1000}  # A reasonable limit to start with
        data = self._get("/api/v1/request", params=params)

        # The response is expected to have a 'results' key.
        requests = data.get("results", []) if data else []

        logger.info(f"Found {len(requests)} media requests in Jellyseerr.")
        return requests

    def delete_request(self, request_id: str) -> bool:
        """
        Deletes a media requests from the Jellyseerr server.

        Returns:
            bool: The success state of the request
        """
        logger.info(f"Deleting media requests {request_id} from Jellyseerr...")
        return self._delete(f"/api/v1/request/{request_id}", params={})


if __name__ == '__main__':
    # Example usage for testing the client
    # Note: This requires a running Jellyseerr instance and a valid .env file.

    logger = setup_logger(verbose=True)

    try:
        client = JellyseerrClient()

        # Test fetching media requests
        all_requests = client.get_all_requests()
        if all_requests:
            logger.info(f"Successfully fetched {len(all_requests)} media requests.")
            # Log the first request if available
            logger.debug(f"First media request: {all_requests[0]}")
            pp(all_requests)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during testing: {e}")
