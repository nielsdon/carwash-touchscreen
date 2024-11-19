import time
import os
import requests
from cryptography.fernet import Fernet


class AuthClient:
    def __init__(self, api_path, api_token, api_secret):
        self.api_path = api_path
        self.api_token = api_token
        self.api_secret = api_secret
        self.jwt_token = None
        self.encryption_key = self.load_encryption_key()
        self.refresh_token = self.load_refresh_token()  # Load refresh token if available
        self.token_expiry_time = 0  # Track token expiration

        # Authenticate or refresh token if needed
        if not self.refresh_token:
            print("No refresh token found. Performing full authentication.")
            self.authenticate()
        elif self.is_token_expired():
            print("Access token expired. Refreshing token.")
            self.refresh_access_token()

    def load_encryption_key(self):
        """Load or generate an encryption key for secure storage."""
        key_path = "secret.key"
        if os.path.exists(key_path):
            print('Reading encryption key')
            with open(key_path, "rb") as key_file:
                return key_file.read()
        else:
            print('Creating encryption key')
            key = Fernet.generate_key()
            with open(key_path, "wb") as key_file:
                key_file.write(key)
            return key

    def save_refresh_token(self, token):
        """Encrypt and save the refresh token."""
        print('Saving refresh token...')
        cipher = Fernet(self.encryption_key)
        encrypted_token = cipher.encrypt(token.encode())
        with open("refresh_token.enc", "wb") as token_file:
            token_file.write(encrypted_token)

    def load_refresh_token(self):
        """Load and decrypt the refresh token if it exists."""
        print('Loading refresh token...')
        if os.path.exists("refresh_token.enc"):
            cipher = Fernet(self.encryption_key)
            with open("refresh_token.enc", "rb") as token_file:
                encrypted_token = token_file.read()
            return cipher.decrypt(encrypted_token).decode()
        return None

    def is_token_expired(self):
        # Check if the token is expired (considering a buffer for safety)
        return time.time() > self.token_expiry_time - 60  # Refresh 60 seconds before expiry

    def authenticate(self):
        """Initial authentication to obtain access and refresh tokens."""
        print('Authenticating with username/password...')
        url = f'https://api.washterminalpro.nl/{self.api_path}/auth/login/'
        response = requests.post(url, json={
            "username": self.api_token,
            "password": self.api_secret
        }, timeout=10)
        response.raise_for_status()

        responseData = response.json()
        self.jwt_token = responseData["jwt"]
        self.refresh_token = responseData.get("refreshToken")
        self.token_expiry_time = time.time() + responseData.get("expires_in", 3600)

        # Save the refresh token securely
        if self.refresh_token:
            self.save_refresh_token(self.refresh_token)

    def refresh_access_token(self):
        """Refresh the JWT token if it's expired using the refresh token."""
        print('Refreshing access token...')
        url = f'https://api.washterminalpro.nl/{self.api_path}/auth/refresh/'
        response = requests.post(url, json={
            "token": self.refresh_token
        }, timeout=10)

        # If refresh token is invalid, re-authenticate
        if response.status_code == 403:
            print("Refresh token expired or invalid, re-authenticating.")
            self.authenticate()
        else:
            response.raise_for_status()
            responseData = response.json()
            self.jwt_token = responseData["jwt"]
            self.token_expiry_time = time.time() + responseData.get("expires_in", 3600)

    def get_authorization_header(self):
        """Get the Authorization header with a valid token, refreshing it if necessary."""
        print('Retrieving the auth header...')
        if time.time() > self.token_expiry_time:
            self.refresh_access_token()
        return {"Authorization": f'Bearer {self.jwt_token}'}
