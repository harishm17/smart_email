"""
Gmail API tools for email operations.
Provides functions for searching, reading, and sending emails.
"""
import base64
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from googleapiclient.errors import HttpError

from utils.auth import get_auth_manager


class GmailTools:
    """Tools for interacting with Gmail API."""

    def __init__(self):
        self.service = get_auth_manager().get_gmail_service()

    def search_emails(
        self,
        query: str,
        max_results: int = 10,
        include_body: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Searches for emails matching the query.

        Args:
            query: Gmail search query (e.g., "from:john@example.com")
            max_results: Maximum number of results to return
            include_body: Whether to include email body in results

        Returns:
            List of email dictionaries with metadata and optionally body

        Example:
            >>> gmail = GmailTools()
            >>> emails = gmail.search_emails("subject:meeting", max_results=5)
        """
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            email_list = []

            for message in messages:
                email_data = self.get_email(message['id'], include_body=include_body)
                if email_data:
                    email_list.append(email_data)

            return email_list

        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def get_email(self, message_id: str, include_body: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific email by ID.

        Args:
            message_id: Gmail message ID
            include_body: Whether to include email body

        Returns:
            Dictionary with email data or None if error
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = {
                header['name']: header['value']
                for header in message['payload']['headers']
            }

            email_data = {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'from': headers.get('From', ''),
                'to': headers.get('To', ''),
                'subject': headers.get('Subject', ''),
                'date': headers.get('Date', ''),
                'snippet': message.get('snippet', '')
            }

            if include_body:
                email_data['body'] = self._extract_body(message['payload'])

            return email_data

        except HttpError as error:
            print(f'An error occurred: {error}')
            return None

    def _extract_body(self, payload: Dict) -> str:
        """Extracts email body from payload."""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        return base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                elif 'parts' in part:
                    # Recursively search nested parts
                    body = self._extract_body(part)
                    if body:
                        return body
        elif 'body' in payload and 'data' in payload['body']:
            return base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8')
        return ''

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> bool:
        """
        Sends an email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipients (comma-separated)
            bcc: BCC recipients (comma-separated)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject

            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc

            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            return True

        except HttpError as error:
            print(f'An error occurred: {error}')
            return False

    def get_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all messages in a thread.

        Args:
            thread_id: Gmail thread ID

        Returns:
            List of email dictionaries in the thread
        """
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()

            messages = thread.get('messages', [])
            return [self.get_email(msg['id']) for msg in messages]

        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def list_recent_emails(self, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Lists recent emails from inbox.

        Args:
            max_results: Maximum number of emails to retrieve

        Returns:
            List of email dictionaries
        """
        return self.search_emails('in:inbox', max_results=max_results)
