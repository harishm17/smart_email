"""
Drafter Agent: Generates context-aware email drafts with appropriate tone.
Uses retrieved context and plan to create polished email content.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from config import GEMINI_API_KEY, LLM_MODEL, LLM_TEMPERATURE
from validators.pii_validator import get_pii_validator


class EmailDraft(BaseModel):
    """Structured email draft."""
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body content")
    tone: str = Field(description="Tone used (professional, casual, formal)")
    signature: Optional[str] = Field(default=None, description="Email signature if applicable")
    has_pii: bool = Field(default=False, description="Whether PII was detected")
    is_safe: bool = Field(default=True, description="Whether email is safe to send")


class DrafterAgent:
    """
    Generates context-aware email drafts with PII protection.
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=LLM_TEMPERATURE
        )

        self.parser = PydanticOutputParser(pydantic_object=EmailDraft)
        self.pii_validator = get_pii_validator()

        self.prompt = ChatPromptTemplate.from_template(
            """You are an expert email writer. Craft a professional, context-aware email based on the information provided.

User Request: {request}

Plan:
- Intent: {intent}
- Tone: {tone}
- Recipients: {recipients}
- Key Points: {key_points}

{context_section}

Instructions:
1. Write a clear, well-structured email body
2. Use appropriate tone: {tone}
3. Include all key points naturally
4. Be concise but complete
5. Add appropriate opening and closing
6. Do NOT include any personally identifiable information (PII) like:
   - Phone numbers
   - Social security numbers
   - Credit card numbers
   - Personal addresses
   - Unless explicitly mentioned in key points

{format_instructions}

Email Draft:"""
        )

    def draft(
        self,
        user_request: str,
        plan: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> EmailDraft:
        """
        Generates an email draft based on plan and context.

        Args:
            user_request: Original user request
            plan: EmailPlan from PlannerAgent
            context: Optional context from RetrieverAgent

        Returns:
            EmailDraft with subject, body, and safety validation

        Example:
            >>> drafter = DrafterAgent()
            >>> draft = drafter.draft(
            ...     "Reply to John about the project deadline",
            ...     plan={'intent': 'reply', 'tone': 'professional'},
            ...     context={'emails': [...]}
            ... )
        """
        # Prepare context section
        context_section = ""
        if context and context.get('emails'):
            context_section = f"""
Context from Previous Emails:
{context.get('summary', 'No summary available')}
"""

        # Prepare plan values
        intent = plan.get('intent', 'compose')
        tone = plan.get('tone', 'professional')
        recipients = ', '.join(plan.get('recipients', ['recipient']))
        key_points = '\n- '.join(plan.get('key_points', [user_request]))

        # Pre-LLM PII scrubbing (configurable)
        if self.pii_validator.enabled:
            user_request = self.pii_validator.sanitize(user_request)
            key_points = self.pii_validator.sanitize(key_points)
            context_section = self.pii_validator.sanitize(context_section)

        # Generate draft
        chain = self.prompt | self.llm | self.parser

        try:
            draft = chain.invoke({
                "request": user_request,
                "intent": intent,
                "tone": tone,
                "recipients": recipients,
                "key_points": key_points,
                "context_section": context_section,
                "format_instructions": self.parser.get_format_instructions()
            })

            # Validate for PII
            pii_result = self.pii_validator.validate(draft.body)
            draft.has_pii = pii_result.has_pii
            draft.is_safe = pii_result.safe_to_send

            if not draft.is_safe:
                print(f"⚠️  PII detected: {pii_result.pii_types}")
                print(f"Details: {pii_result.details}")
                # Sanitize the draft
                draft.body = self.pii_validator.sanitize(draft.body)

            return draft

        except Exception as e:
            print(f"Drafting error: {e}")
            # Fallback to basic draft
            return EmailDraft(
                subject=plan.get('subject', 'No subject'),
                body=f"Hello,\n\n{user_request}\n\nBest regards,",
                tone=tone,
                is_safe=True
            )

    def generate_reply(
        self,
        original_email: Dict[str, Any],
        reply_intent: str,
        tone: str = "professional"
    ) -> EmailDraft:
        """
        Generates a reply to an existing email.

        Args:
            original_email: Dictionary with original email data
            reply_intent: What the reply should accomplish
            tone: Desired tone for reply

        Returns:
            EmailDraft for the reply
        """
        context = {
            'emails': [original_email],
            'summary': f"""Original email:
From: {original_email.get('from')}
Subject: {original_email.get('subject')}
Body: {original_email.get('body', original_email.get('snippet', ''))}
"""
        }

        plan = {
            'intent': 'reply',
            'tone': tone,
            'recipients': [original_email.get('from')],
            'subject': f"Re: {original_email.get('subject', '')}",
            'key_points': [reply_intent]
        }

        return self.draft(reply_intent, plan, context)

    def compose_new(
        self,
        to: str,
        subject: str,
        message: str,
        tone: str = "professional"
    ) -> EmailDraft:
        """
        Composes a new email from scratch.

        Args:
            to: Recipient email address
            subject: Email subject
            message: Core message to convey
            tone: Desired tone

        Returns:
            EmailDraft for new email
        """
        plan = {
            'intent': 'compose',
            'tone': tone,
            'recipients': [to],
            'subject': subject,
            'key_points': [message]
        }

        return self.draft(message, plan, context=None)
