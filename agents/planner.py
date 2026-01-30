"""
Planner Agent: Analyzes user requests and determines required actions.
First agent in the multi-agent workflow.
"""
from typing import Dict, List, Any
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from config import GEMINI_API_KEY, LLM_MODEL, LLM_TEMPERATURE


class EmailPlan(BaseModel):
    """Structured plan for email operations."""
    intent: str = Field(description="Primary intent (compose, reply, schedule_meeting, etc.)")
    requires_context: bool = Field(description="Whether email history context is needed")
    context_query: str = Field(default="", description="Search query for retrieving context")
    recipients: List[str] = Field(default_factory=list, description="Email recipients")
    subject: str = Field(default="", description="Email subject")
    key_points: List[str] = Field(default_factory=list, description="Key points to include")
    tone: str = Field(default="professional", description="Desired tone (professional, casual, formal)")
    requires_calendar: bool = Field(description="Whether calendar operations are needed")
    meeting_details: Dict[str, Any] = Field(default_factory=dict, description="Meeting scheduling details if applicable")


class PlannerAgent:
    """
    Analyzes user requests and creates structured plans for email operations.
    """

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=LLM_TEMPERATURE
        )

        self.parser = PydanticOutputParser(pydantic_object=EmailPlan)

        self.prompt = ChatPromptTemplate.from_template(
            """You are an intelligent email planning assistant. Analyze the user's request and create a structured plan.

User Request: {request}

Create a detailed plan that includes:
1. The primary intent (compose new email, reply to existing, schedule meeting, etc.)
2. Whether context from email history is needed
3. If context is needed, what search query to use
4. Recipients if mentioned
5. Subject line if applicable
6. Key points to include in the email
7. Appropriate tone based on context
8. Whether calendar operations are needed
9. Meeting details if scheduling is involved

{format_instructions}

Plan:"""
        )

    def plan(self, user_request: str) -> EmailPlan:
        """
        Creates a structured plan from user request.

        Args:
            user_request: Natural language request from user

        Returns:
            EmailPlan object with structured plan

        Example:
            >>> planner = PlannerAgent()
            >>> plan = planner.plan("Reply to John's email about the project meeting")
        """
        chain = self.prompt | self.llm | self.parser

        try:
            result = chain.invoke({
                "request": user_request,
                "format_instructions": self.parser.get_format_instructions()
            })
            return result
        except Exception as e:
            print(f"Planning error: {e}")
            # Fallback to basic plan
            return EmailPlan(
                intent="compose",
                requires_context=False,
                tone="professional",
                requires_calendar=False,
                key_points=[user_request]
            )

    def analyze_intent(self, user_request: str) -> str:
        """
        Quickly analyzes user intent without full planning.

        Args:
            user_request: User's natural language request

        Returns:
            Intent string (compose, reply, forward, schedule, search)
        """
        request_lower = user_request.lower()

        if any(word in request_lower for word in ['reply', 'respond', 'answer']):
            return 'reply'
        elif any(word in request_lower for word in ['meeting', 'schedule', 'calendar']):
            return 'schedule_meeting'
        elif any(word in request_lower for word in ['forward', 'fwd']):
            return 'forward'
        elif any(word in request_lower for word in ['search', 'find', 'look for']):
            return 'search'
        else:
            return 'compose'

    def extract_recipients(self, user_request: str) -> List[str]:
        """
        Extracts email recipients from request.

        Args:
            user_request: User's request

        Returns:
            List of email addresses
        """
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, user_request)
