"""
Google OAuth 2.0 authentication utilities.
Handles token storage, refresh, and authentication flow.
"""
import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from typing import Optional

from config import (
    GOOGLE_SCOPES,
    TOKEN_PATH,
    CREDENTIALS_PATH
)


class GoogleAuthManager:
    """Manages Google OAuth 2.0 authentication and credential storage."""

    def __init__(self):
        self.creds: Optional[Credentials] = None
        self.token_path = TOKEN_PATH
        self.credentials_path = CREDENTIALS_PATH

    def authenticate(self) -> Credentials:
        """
        Authenticates with Google using OAuth 2.0.

        Returns:
            Credentials: Valid Google OAuth credentials

        Raises:
            FileNotFoundError: If credentials.json is not found
        """
        # Load existing credentials if available
        if self.token_path.exists():
            self.creds = Credentials.from_authorized_user_file(
                str(self.token_path),
                GOOGLE_SCOPES
            )

        # Refresh or obtain new credentials
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # Refresh expired credentials
                self.creds.refresh(Request())
            else:
                # Run OAuth flow for new credentials
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found at {self.credentials_path}. "
                        "Please download it from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path),
                    GOOGLE_SCOPES
                )
                self.creds = flow.run_local_server(port=8080)

            # Save credentials for future use
            self._save_credentials()

        return self.creds

    def _save_credentials(self):
        """Saves credentials to token.json file."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, 'w') as token_file:
            token_file.write(self.creds.to_json())

    def get_gmail_service(self):
        """
        Returns authenticated Gmail API service.

        Returns:
            Resource: Gmail API service object
        """
        if not self.creds:
            self.authenticate()
        return build('gmail', 'v1', credentials=self.creds)

    def get_calendar_service(self):
        """
        Returns authenticated Google Calendar API service.

        Returns:
            Resource: Calendar API service object
        """
        if not self.creds:
            self.authenticate()
        return build('calendar', 'v3', credentials=self.creds)

    def get_contacts_service(self):
        """
        Returns authenticated Google People (Contacts) API service.

        Returns:
            Resource: People API service object
        """
        if not self.creds:
            self.authenticate()
        return build('people', 'v1', credentials=self.creds)

    def revoke_credentials(self):
        """Revokes and deletes stored credentials."""
        if self.token_path.exists():
            self.token_path.unlink()
        self.creds = None


# Singleton instance
_auth_manager = None

def get_auth_manager() -> GoogleAuthManager:
    """Returns singleton GoogleAuthManager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = GoogleAuthManager()
    return _auth_manager
