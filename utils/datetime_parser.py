"""
Natural language date/time parsing utilities.
Converts human-friendly time expressions to structured datetime objects.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import re
import pytz


class DateTimeParser:
    """Parses natural language date/time expressions."""

    def __init__(self, timezone: str = 'UTC'):
        self.tz = pytz.timezone(timezone)

    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parses natural language date/time string into structured format.

        Args:
            text: Natural language time expression (e.g., "tomorrow at 3pm")

        Returns:
            Dict containing parsed datetime information, or None if parsing fails

        Examples:
            >>> parser = DateTimeParser()
            >>> parser.parse("tomorrow at 3pm")
            {'start': datetime(...), 'duration_minutes': 60}
        """
        text = text.lower().strip()
        now = datetime.now(self.tz)

        # Patterns for relative dates
        if 'tomorrow' in text:
            base_date = now + timedelta(days=1)
        elif 'next week' in text:
            base_date = now + timedelta(weeks=1)
        elif 'next month' in text:
            base_date = now + timedelta(days=30)
        elif 'today' in text or 'this' in text:
            base_date = now
        else:
            base_date = now

        # Extract time
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            meridiem = time_match.group(3)

            if meridiem == 'pm' and hour < 12:
                hour += 12
            elif meridiem == 'am' and hour == 12:
                hour = 0

            start_time = base_date.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )
        else:
            # Default to current time or 9am if date is in future
            if base_date.date() > now.date():
                start_time = base_date.replace(hour=9, minute=0, second=0, microsecond=0)
            else:
                start_time = base_date

        # Extract duration
        duration_minutes = 60  # Default duration
        duration_match = re.search(r'(\d+)\s*(hour|hr|minute|min)', text)
        if duration_match:
            value = int(duration_match.group(1))
            unit = duration_match.group(2)
            if 'hour' in unit or 'hr' in unit:
                duration_minutes = value * 60
            else:
                duration_minutes = value

        return {
            'start': start_time,
            'end': start_time + timedelta(minutes=duration_minutes),
            'duration_minutes': duration_minutes,
            'timezone': str(self.tz)
        }

    def parse_date(self, text: str) -> Optional[datetime]:
        """
        Extracts just the date from a natural language string.

        Args:
            text: Natural language date expression

        Returns:
            datetime object or None if parsing fails
        """
        result = self.parse(text)
        return result['start'] if result else None

    def format_for_calendar(self, dt: datetime) -> str:
        """
        Formats datetime for Google Calendar API.

        Args:
            dt: datetime object

        Returns:
            RFC3339 formatted string
        """
        return dt.isoformat()
