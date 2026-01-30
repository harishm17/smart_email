"""
Retriever Agent: Searches email history and contacts for relevant context.
Provides context to the Drafter Agent for more informed email composition.
"""
from typing import List, Dict, Any
from tools.gmail_tools import GmailTools
from config import MAX_SEARCH_RESULTS


class RetrieverAgent:
    """
    Retrieves relevant context from email history and contacts.
    """

    def __init__(self):
        self.gmail_tools = GmailTools()

    def retrieve_context(
        self,
        query: str,
        max_results: int = MAX_SEARCH_RESULTS
    ) -> Dict[str, Any]:
        """
        Retrieves relevant emails based on search query.

        Args:
            query: Search query for finding relevant emails
            max_results: Maximum number of emails to retrieve

        Returns:
            Dictionary with retrieved context

        Example:
            >>> retriever = RetrieverAgent()
            >>> context = retriever.retrieve_context("from:john@example.com subject:project")
        """
        emails = self.gmail_tools.search_emails(
            query=query,
            max_results=max_results,
            include_body=True
        )

        return {
            'query': query,
            'emails_found': len(emails),
            'emails': emails,
            'summary': self._summarize_emails(emails)
        }

    def _summarize_emails(self, emails: List[Dict[str, Any]]) -> str:
        """
        Creates a brief summary of retrieved emails.

        Args:
            emails: List of email dictionaries

        Returns:
            Summary string
        """
        if not emails:
            return "No relevant emails found."

        summaries = []
        for email in emails[:5]:  # Summarize top 5
            summary = (
                f"From: {email.get('from', 'Unknown')}\n"
                f"Subject: {email.get('subject', 'No subject')}\n"
                f"Snippet: {email.get('snippet', '')[:100]}...\n"
            )
            summaries.append(summary)

        return "\n---\n".join(summaries)

    def get_thread_context(self, thread_id: str) -> Dict[str, Any]:
        """
        Retrieves full context of an email thread.

        Args:
            thread_id: Gmail thread ID

        Returns:
            Dictionary with thread context
        """
        thread_emails = self.gmail_tools.get_thread(thread_id)

        return {
            'thread_id': thread_id,
            'email_count': len(thread_emails),
            'emails': thread_emails,
            'summary': self._summarize_thread(thread_emails)
        }

    def _summarize_thread(self, emails: List[Dict[str, Any]]) -> str:
        """
        Creates a chronological summary of email thread.

        Args:
            emails: List of emails in thread

        Returns:
            Thread summary string
        """
        if not emails:
            return "Empty thread."

        summary_parts = [f"Thread with {len(emails)} messages:\n"]

        for i, email in enumerate(emails, 1):
            summary_parts.append(
                f"{i}. {email.get('from', 'Unknown')} -> {email.get('to', 'Unknown')}: "
                f"{email.get('subject', 'No subject')}"
            )

        return "\n".join(summary_parts)

    def search_by_sender(self, sender: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Retrieves recent emails from a specific sender.

        Args:
            sender: Email address or name of sender
            max_results: Maximum results to return

        Returns:
            Dictionary with emails from sender
        """
        query = f"from:{sender}"
        return self.retrieve_context(query, max_results)

    def search_by_subject(self, subject: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Retrieves emails with matching subject.

        Args:
            subject: Subject keywords to search for
            max_results: Maximum results to return

        Returns:
            Dictionary with matching emails
        """
        query = f"subject:{subject}"
        return self.retrieve_context(query, max_results)

    def get_recent_conversation(self, contact: str) -> Dict[str, Any]:
        """
        Gets recent conversation history with a contact.

        Args:
            contact: Email address or name

        Returns:
            Dictionary with conversation context
        """
        # Search for emails to or from the contact
        query = f"(from:{contact} OR to:{contact})"
        return self.retrieve_context(query, max_results=20)
