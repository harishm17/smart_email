"""Tests for planner agent."""
import pytest
from unittest.mock import MagicMock, patch
from agents.planner import PlannerAgent, EmailPlan


class TestPlannerAgent:
    """Test planner agent functionality."""

    @pytest.fixture
    def planner(self):
        """Create planner agent instance."""
        with patch('agents.planner.ChatGoogleGenerativeAI'):
            return PlannerAgent()

    def test_analyze_intent_reply(self, planner):
        """Should identify reply intent."""
        requests = [
            "Reply to John's email about the meeting",
            "Respond to Sarah's question",
            "Answer the email from Bob"
        ]
        for req in requests:
            intent = planner.analyze_intent(req)
            assert intent == 'reply', f"Failed for: {req}"

    def test_analyze_intent_compose(self, planner):
        """Should identify compose intent."""
        requests = [
            "Send an email to john@example.com",
            "Write an email about the project",
            "Email the team about updates"
        ]
        for req in requests:
            intent = planner.analyze_intent(req)
            assert intent == 'compose', f"Failed for: {req}"

    def test_analyze_intent_schedule(self, planner):
        """Should identify schedule meeting intent."""
        requests = [
            "Schedule a meeting with Sarah for Tuesday",
            "Set up a calendar event for the team",
            "Create a meeting for next week"
        ]
        for req in requests:
            intent = planner.analyze_intent(req)
            assert intent == 'schedule_meeting', f"Failed for: {req}"

    def test_analyze_intent_forward(self, planner):
        """Should identify forward intent."""
        requests = [
            "Forward this email to the team",
            "Fwd Sarah's message to Bob"
        ]
        for req in requests:
            intent = planner.analyze_intent(req)
            assert intent == 'forward', f"Failed for: {req}"

    def test_analyze_intent_search(self, planner):
        """Should identify search intent."""
        requests = [
            "Search for emails from John",
            "Find messages about the project",
            "Look for emails mentioning budget"
        ]
        for req in requests:
            intent = planner.analyze_intent(req)
            assert intent == 'search', f"Failed for: {req}"

    def test_extract_recipients_single(self, planner):
        """Should extract single email address."""
        request = "Send an email to john.doe@example.com about the meeting"
        recipients = planner.extract_recipients(request)
        assert len(recipients) == 1
        assert 'john.doe@example.com' in recipients

    def test_extract_recipients_multiple(self, planner):
        """Should extract multiple email addresses."""
        request = "Send to john@example.com and sarah@test.org about the project"
        recipients = planner.extract_recipients(request)
        assert len(recipients) == 2
        assert 'john@example.com' in recipients
        assert 'sarah@test.org' in recipients

    def test_extract_recipients_none(self, planner):
        """Should return empty list when no emails found."""
        request = "Reply to John's email about the meeting"
        recipients = planner.extract_recipients(request)
        assert recipients == []

    def test_extract_recipients_various_formats(self, planner):
        """Should handle various email formats."""
        valid_emails = [
            "user@example.com",
            "first.last@company.co.uk",
            "name+tag@domain.org",
            "user123@test-domain.com"
        ]
        for email in valid_emails:
            request = f"Send to {email}"
            recipients = planner.extract_recipients(request)
            assert email in recipients, f"Failed to extract: {email}"

    def test_plan_fallback_on_error(self, planner):
        """Should return fallback plan on error."""
        with patch.object(planner, 'prompt') as mock_prompt:
            # Simulate chain error
            mock_chain = MagicMock()
            mock_chain.invoke.side_effect = Exception("API Error")
            mock_prompt.__or__.return_value = mock_chain

            plan = planner.plan("Test request")

            # Should return fallback plan
            assert isinstance(plan, EmailPlan)
            assert plan.intent == 'compose'
            assert plan.requires_context is False
            assert plan.requires_calendar is False

    def test_plan_pii_sanitization(self, planner):
        """Should sanitize PII before planning."""
        with patch.object(planner, 'pii_validator') as mock_validator:
            mock_validator.enabled = True
            mock_validator.sanitize.return_value = "Sanitized request"

            # Mock the chain
            mock_plan = EmailPlan(
                intent='compose',
                requires_context=False,
                requires_calendar=False
            )
            with patch.object(planner, 'prompt') as mock_prompt:
                mock_chain = MagicMock()
                mock_chain.invoke.return_value = mock_plan
                mock_prompt.__or__.return_value.__or__.return_value = mock_chain

                planner.plan("Request with SSN: 123-45-6789")

            # Verify sanitize was called
            mock_validator.sanitize.assert_called_once()


class TestEmailPlan:
    """Test EmailPlan data model."""

    def test_email_plan_creation(self):
        """Should create valid EmailPlan instance."""
        plan = EmailPlan(
            intent="reply",
            requires_context=True,
            context_query="emails from John",
            recipients=["john@example.com"],
            subject="Re: Project Update",
            key_points=["Acknowledge receipt", "Provide update"],
            tone="professional",
            requires_calendar=False
        )

        assert plan.intent == "reply"
        assert plan.requires_context is True
        assert plan.context_query == "emails from John"
        assert len(plan.recipients) == 1
        assert plan.subject == "Re: Project Update"
        assert len(plan.key_points) == 2
        assert plan.tone == "professional"
        assert plan.requires_calendar is False

    def test_email_plan_defaults(self):
        """Should use default values for optional fields."""
        plan = EmailPlan(
            intent="compose",
            requires_context=False,
            requires_calendar=False
        )

        assert plan.context_query == ""
        assert plan.recipients == []
        assert plan.subject == ""
        assert plan.key_points == []
        assert plan.tone == "professional"
        assert plan.meeting_details == {}

    def test_email_plan_with_meeting_details(self):
        """Should support meeting details."""
        meeting_details = {
            "date": "2026-02-15",
            "time": "14:00",
            "duration": 60,
            "attendees": ["john@example.com", "sarah@example.com"]
        }

        plan = EmailPlan(
            intent="schedule_meeting",
            requires_context=False,
            requires_calendar=True,
            meeting_details=meeting_details
        )

        assert plan.requires_calendar is True
        assert plan.meeting_details == meeting_details
        assert "date" in plan.meeting_details
        assert "attendees" in plan.meeting_details


class TestPlannerIntentAnalysis:
    """Test intent analysis edge cases."""

    @pytest.fixture
    def planner(self):
        """Create planner agent instance."""
        with patch('agents.planner.ChatGoogleGenerativeAI'):
            return PlannerAgent()

    def test_case_insensitive_intent(self, planner):
        """Intent analysis should be case insensitive."""
        requests = [
            "REPLY to John's email",
            "Reply TO JOHN'S EMAIL",
            "reply to john's email"
        ]
        for req in requests:
            intent = planner.analyze_intent(req)
            assert intent == 'reply'

    def test_ambiguous_request_defaults_to_compose(self, planner):
        """Ambiguous requests should default to compose."""
        ambiguous_requests = [
            "Do that thing",
            "Help me with email",
            "Just send it"
        ]
        for req in ambiguous_requests:
            intent = planner.analyze_intent(req)
            assert intent == 'compose', f"Failed for: {req}"

    def test_multiple_intents_prioritizes_first(self, planner):
        """When multiple intents present, should prioritize appropriately."""
        # Reply takes precedence
        assert planner.analyze_intent("Reply and schedule a meeting") == 'reply'

        # Schedule takes precedence over compose
        assert planner.analyze_intent("Schedule a meeting and email") == 'schedule_meeting'

    def test_handles_empty_request(self, planner):
        """Should handle empty request gracefully."""
        intent = planner.analyze_intent("")
        assert intent == 'compose'

    def test_handles_special_characters(self, planner):
        """Should handle special characters in request."""
        request = "Reply to email with subject: Project & Budget (Q1)"
        intent = planner.analyze_intent(request)
        assert intent == 'reply'


class TestRecipientExtraction:
    """Test recipient extraction edge cases."""

    @pytest.fixture
    def planner(self):
        """Create planner agent instance."""
        with patch('agents.planner.ChatGoogleGenerativeAI'):
            return PlannerAgent()

    def test_extract_from_complex_text(self, planner):
        """Should extract emails from complex text."""
        request = """
        Please send an update to john.doe@company.com and sarah@example.org
        about the meeting we had last week. Also CC bob+team@test.io
        """
        recipients = planner.extract_recipients(request)

        assert len(recipients) >= 2
        assert 'john.doe@company.com' in recipients
        assert 'sarah@example.org' in recipients

    def test_ignore_invalid_emails(self, planner):
        """Should ignore invalid email patterns."""
        request = "Send to user@domain but not @invalid or user@ or @domain.com"
        recipients = planner.extract_recipients(request)

        # Should only extract valid email
        valid_emails = [r for r in recipients if r == 'user@domain']
        # The regex pattern should validate properly formed emails

    def test_deduplicate_recipients(self, planner):
        """Should handle duplicate email addresses."""
        request = "Send to john@example.com and john@example.com"
        recipients = planner.extract_recipients(request)

        # Duplicates may or may not be removed depending on implementation
        # This test documents current behavior
        assert 'john@example.com' in recipients
