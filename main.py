"""
Smart Email Assistant - Main Entry Point
Multi-agent system for automated email drafting with PII protection.
"""
import sys
from typing import Optional

from agents.planner import PlannerAgent
from agents.retriever import RetrieverAgent
from agents.drafter import DrafterAgent
from tools.gmail_tools import GmailTools
from utils.auth import get_auth_manager


class SmartEmailAssistant:
    """
    Orchestrates the multi-agent email assistant workflow.
    """

    def __init__(self):
        print("🚀 Initializing Smart Email Assistant...")

        # Authenticate with Google
        try:
            self.auth_manager = get_auth_manager()
            self.auth_manager.authenticate()
            print("✅ Authentication successful")
        except FileNotFoundError as e:
            print(f"❌ {e}")
            print("\nPlease set up Google OAuth credentials:")
            print("1. Go to Google Cloud Console")
            print("2. Create OAuth 2.0 credentials")
            print("3. Download as 'credentials.json'")
            print("4. Place in 'credentials/' directory")
            sys.exit(1)

        # Initialize agents
        self.planner = PlannerAgent()
        self.retriever = RetrieverAgent()
        self.drafter = DrafterAgent()
        self.gmail = GmailTools()

        print("✅ All agents initialized\n")

    def process_request(self, user_request: str, auto_send: bool = False) -> dict:
        """
        Processes a user request through the multi-agent workflow.

        Args:
            user_request: Natural language request from user
            auto_send: Whether to automatically send the draft (default: False)

        Returns:
            Dictionary with draft and metadata

        Example:
            >>> assistant = SmartEmailAssistant()
            >>> result = assistant.process_request(
            ...     "Reply to John's email about the project meeting"
            ... )
        """
        print(f"📝 User Request: {user_request}\n")

        # Step 1: Plan
        print("🧠 Step 1: Planning...")
        plan = self.planner.plan(user_request)
        print(f"   Intent: {plan.intent}")
        print(f"   Tone: {plan.tone}")
        print(f"   Requires Context: {plan.requires_context}\n")

        # Step 2: Retrieve Context (if needed)
        context = None
        if plan.requires_context and plan.context_query:
            print(f"🔍 Step 2: Retrieving context with query: '{plan.context_query}'")
            context = self.retriever.retrieve_context(plan.context_query)
            print(f"   Found {context['emails_found']} relevant emails\n")
        else:
            print("⏭️  Step 2: No context needed\n")

        # Step 3: Draft Email
        print("✍️  Step 3: Drafting email...")
        draft = self.drafter.draft(
            user_request,
            plan.dict(),
            context
        )

        print(f"   Subject: {draft.subject}")
        print(f"   Tone: {draft.tone}")
        print(f"   Safe to send: {'✅ Yes' if draft.is_safe else '⚠️  No (PII detected)'}\n")

        # Display draft
        self._display_draft(draft)

        # Step 4: Send (if auto_send and safe)
        if auto_send and draft.is_safe:
            if plan.recipients:
                self._send_draft(draft, plan.recipients[0])
            else:
                print("❌ Cannot auto-send: No recipient specified")

        return {
            'plan': plan.dict(),
            'context': context,
            'draft': draft.dict(),
            'sent': auto_send and draft.is_safe
        }

    def _display_draft(self, draft):
        """Displays the draft email in a formatted way."""
        print("=" * 60)
        print(f"SUBJECT: {draft.subject}")
        print("=" * 60)
        print(draft.body)
        print("=" * 60)
        if draft.has_pii:
            print("⚠️  WARNING: PII detected and sanitized")
        print()

    def _send_draft(self, draft, recipient: str):
        """Sends the draft email."""
        print(f"📤 Sending email to {recipient}...")
        success = self.gmail.send_email(
            to=recipient,
            subject=draft.subject,
            body=draft.body
        )
        if success:
            print("✅ Email sent successfully!")
        else:
            print("❌ Failed to send email")

    def interactive_mode(self):
        """Starts interactive mode for multiple requests."""
        print("🤖 Smart Email Assistant - Interactive Mode")
        print("=" * 60)
        print("Commands:")
        print("  - Type your request to draft an email")
        print("  - 'search <query>' to search your emails")
        print("  - 'recent' to see recent emails")
        print("  - 'quit' to exit")
        print("=" * 60)
        print()

        while True:
            try:
                user_input = input("📧 You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() == 'quit':
                    print("👋 Goodbye!")
                    break

                elif user_input.lower().startswith('search '):
                    query = user_input[7:]
                    print(f"\n🔍 Searching for: {query}")
                    context = self.retriever.retrieve_context(query, max_results=5)
                    print(f"\nFound {context['emails_found']} emails:")
                    print(context['summary'])
                    print()

                elif user_input.lower() == 'recent':
                    print("\n📬 Fetching recent emails...")
                    emails = self.gmail.list_recent_emails(max_results=10)
                    for i, email in enumerate(emails, 1):
                        print(f"{i}. From: {email['from']}")
                        print(f"   Subject: {email['subject']}")
                        print(f"   Snippet: {email['snippet'][:80]}...")
                        print()

                else:
                    # Process as email request
                    self.process_request(user_input, auto_send=False)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Smart Email Assistant')
    parser.add_argument(
        '--request',
        type=str,
        help='Email request to process'
    )
    parser.add_argument(
        '--auto-send',
        action='store_true',
        help='Automatically send the drafted email'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Start interactive mode'
    )

    args = parser.parse_args()

    try:
        assistant = SmartEmailAssistant()

        if args.interactive or not args.request:
            assistant.interactive_mode()
        else:
            assistant.process_request(args.request, auto_send=args.auto_send)

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
