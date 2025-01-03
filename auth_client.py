from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
import logging
import requests
import time
logging.getLogger("requests_oauthlib").setLevel(logging.WARNING)


class AuthClient:
    def __init__(self, client_id, client_secret, token_url):
        """
        Initialize the OAuth2 session with client credentials.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.scope = "machine_scope"
        client = BackendApplicationClient(client_id=self.client_id)
        self.oauth = OAuth2Session(client=client)

    def fetch_access_token(self):
        """
        Fetch a new access token and store it in the session.
        """
        try:
            token = self.oauth.fetch_token(
                token_url=self.token_url,
                client_id=self.client_id,
                client_secret=self.client_secret,
                include_client_id=True
            )
            logging.debug("Access token fetched successfully.")
            return token
        except requests.exceptions.RequestException as e:
            logging.error("Error fetching access token: %s", e)
            raise

    def make_authenticated_request(self, url, method="GET", data=None):
        """
        Make an authenticated API request using the OAuth2 session.
        """
        try:
            # Ensure the token is valid or fetch a new one if needed
            if not self.oauth.token or self.oauth.token.get("expires_at", 0) < time.time():
                self.fetch_access_token()

            # Perform the authenticated request
            response = self.oauth.request(method, url, json=data)

            # Handle 200, 460, and 462 responses gracefully
            if response.status_code not in [200, 460, 462]:
                response.raise_for_status()  # Raise an error for 4xx/5xx responses

            # Handle the response
            return response.status_code, response.json()
        except requests.exceptions.RequestException as e:
            logging.error("Error making API request: %s", e)
            raise

    def get_token(self):
        """
        Returns the current token for debugging purposes.
        """
        return self.oauth.token
