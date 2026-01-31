"""Tests for natural language date parsing."""
import pytest
from datetime import datetime, timedelta
import pytz
from utils.datetime_parser import DateTimeParser


class TestDateTimeParser:
    """Test datetime parsing functionality."""

    @pytest.fixture
    def parser(self):
        """Create parser instance with UTC timezone."""
        return DateTimeParser(timezone='UTC')

    @pytest.fixture
    def parser_pst(self):
        """Create parser instance with PST timezone."""
        return DateTimeParser(timezone='US/Pacific')

    def test_parse_tomorrow(self, parser):
        """Should parse 'tomorrow' correctly."""
        result = parser.parse("tomorrow at 3pm")

        assert result is not None
        expected = datetime.now(parser.tz) + timedelta(days=1)

        # Check date matches
        assert result['start'].date() == expected.date()
        # Check time is 3pm (15:00)
        assert result['start'].hour == 15
        assert result['start'].minute == 0

    def test_parse_today(self, parser):
        """Should parse 'today' correctly."""
        result = parser.parse("today at 10am")

        assert result is not None
        now = datetime.now(parser.tz)

        assert result['start'].date() == now.date()
        assert result['start'].hour == 10
        assert result['start'].minute == 0

    def test_parse_next_week(self, parser):
        """Should parse 'next week' correctly."""
        result = parser.parse("next week at 2pm")

        assert result is not None
        expected = datetime.now(parser.tz) + timedelta(weeks=1)

        # Date should be approximately 7 days from now
        days_diff = (result['start'].date() - datetime.now(parser.tz).date()).days
        assert 6 <= days_diff <= 8

    def test_parse_next_month(self, parser):
        """Should parse 'next month' correctly."""
        result = parser.parse("next month at 9am")

        assert result is not None
        expected = datetime.now(parser.tz) + timedelta(days=30)

        # Date should be approximately 30 days from now
        days_diff = (result['start'].date() - datetime.now(parser.tz).date()).days
        assert 28 <= days_diff <= 32

    def test_parse_am_time(self, parser):
        """Should parse AM times correctly."""
        result = parser.parse("tomorrow at 9am")

        assert result['start'].hour == 9
        assert result['start'].minute == 0

    def test_parse_pm_time(self, parser):
        """Should parse PM times correctly."""
        result = parser.parse("tomorrow at 3pm")

        assert result['start'].hour == 15  # 3pm = 15:00

    def test_parse_time_with_minutes(self, parser):
        """Should parse time with minutes."""
        result = parser.parse("tomorrow at 2:30pm")

        assert result['start'].hour == 14  # 2pm = 14:00
        assert result['start'].minute == 30

    def test_parse_midnight(self, parser):
        """Should parse midnight (12am) correctly."""
        result = parser.parse("tomorrow at 12am")

        assert result['start'].hour == 0
        assert result['start'].minute == 0

    def test_parse_noon(self, parser):
        """Should parse noon (12pm) correctly."""
        result = parser.parse("tomorrow at 12pm")

        assert result['start'].hour == 12
        assert result['start'].minute == 0

    def test_parse_duration_hours(self, parser):
        """Should parse duration in hours."""
        result = parser.parse("tomorrow at 2pm for 2 hours")

        assert result['duration_minutes'] == 120

    def test_parse_duration_minutes(self, parser):
        """Should parse duration in minutes."""
        result = parser.parse("tomorrow at 2pm for 30 minutes")

        assert result['duration_minutes'] == 30

    def test_parse_duration_hour_singular(self, parser):
        """Should parse singular 'hour'."""
        result = parser.parse("tomorrow at 2pm for 1 hour")

        assert result['duration_minutes'] == 60

    def test_parse_duration_hr_abbreviation(self, parser):
        """Should parse 'hr' abbreviation."""
        result = parser.parse("tomorrow at 2pm for 3 hr")

        assert result['duration_minutes'] == 180

    def test_default_duration(self, parser):
        """Should use default duration when not specified."""
        result = parser.parse("tomorrow at 2pm")

        # Default is 60 minutes
        assert result['duration_minutes'] == 60

    def test_end_time_calculation(self, parser):
        """Should calculate end time correctly."""
        result = parser.parse("tomorrow at 2pm for 90 minutes")

        duration = result['end'] - result['start']
        assert duration.total_seconds() == 90 * 60

    def test_parse_without_time_defaults_to_9am(self, parser):
        """Should default to 9am when no time specified for future date."""
        result = parser.parse("tomorrow")

        # Should default to 9am for future dates
        assert result['start'].hour == 9
        assert result['start'].minute == 0

    def test_timezone_preservation(self, parser):
        """Should preserve timezone information."""
        result = parser.parse("tomorrow at 3pm")

        assert result['timezone'] == 'UTC'
        assert result['start'].tzinfo == parser.tz

    def test_timezone_pst(self, parser_pst):
        """Should handle PST timezone."""
        result = parser_pst.parse("tomorrow at 3pm")

        assert result['timezone'] == 'US/Pacific'
        assert result['start'].tzinfo == parser_pst.tz

    def test_parse_date_method(self, parser):
        """parse_date should return just the datetime."""
        dt = parser.parse_date("tomorrow at 3pm")

        assert isinstance(dt, datetime)
        assert dt.hour == 15

    def test_parse_date_returns_none_on_failure(self, parser):
        """parse_date should return None if parsing fails."""
        # Mock parse to return None
        with pytest.MonkeyPatch.context() as m:
            m.setattr(parser, 'parse', lambda x: None)
            dt = parser.parse_date("invalid")
            assert dt is None

    def test_format_for_calendar(self, parser):
        """Should format datetime for Google Calendar API."""
        dt = datetime(2026, 2, 15, 14, 30, 0, tzinfo=parser.tz)
        formatted = parser.format_for_calendar(dt)

        # Should be ISO format
        assert isinstance(formatted, str)
        assert '2026-02-15' in formatted
        assert '14:30:00' in formatted

    def test_case_insensitive_parsing(self, parser):
        """Parsing should be case insensitive."""
        results = [
            parser.parse("TOMORROW at 3PM"),
            parser.parse("Tomorrow at 3pm"),
            parser.parse("tomorrow at 3PM")
        ]

        for result in results:
            assert result['start'].hour == 15

    def test_whitespace_handling(self, parser):
        """Should handle extra whitespace."""
        result = parser.parse("  tomorrow   at   3pm  ")

        assert result is not None
        assert result['start'].hour == 15

    def test_parse_this_afternoon(self, parser):
        """Should parse 'this afternoon'."""
        result = parser.parse("this afternoon at 2pm")

        now = datetime.now(parser.tz)
        assert result['start'].date() == now.date()
        assert result['start'].hour == 14

    def test_multiple_time_mentions_uses_first(self, parser):
        """Should use first time mentioned if multiple present."""
        result = parser.parse("tomorrow at 2pm or 3pm")

        # Should parse first time (2pm)
        assert result['start'].hour == 14


class TestDateTimeParserEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return DateTimeParser(timezone='UTC')

    def test_empty_string(self, parser):
        """Should handle empty string."""
        result = parser.parse("")

        # Should return a result (likely current time)
        assert result is not None

    def test_no_time_specified_today(self, parser):
        """Should handle no time for 'today'."""
        result = parser.parse("today")

        assert result is not None
        # Should use current time or default

    def test_24_hour_time_format(self, parser):
        """Should handle 24-hour time format."""
        result = parser.parse("tomorrow at 14:30")

        assert result['start'].hour == 14
        assert result['start'].minute == 30

    def test_invalid_time_format(self, parser):
        """Should handle invalid time gracefully."""
        result = parser.parse("tomorrow at 25:00")

        # Should still return a result with sensible defaults
        assert result is not None

    def test_ambiguous_text(self, parser):
        """Should handle ambiguous text."""
        result = parser.parse("sometime soon")

        # Should return a result with defaults
        assert result is not None

    def test_duration_with_multiple_units(self, parser):
        """Should handle complex duration expressions."""
        # This may or may not be supported depending on implementation
        result = parser.parse("tomorrow at 2pm for 1 hour and 30 minutes")

        # Should parse at least one duration unit
        assert result['duration_minutes'] > 0


class TestTimezoneHandling:
    """Test timezone-specific behavior."""

    def test_different_timezones(self):
        """Should handle different timezones correctly."""
        parser_utc = DateTimeParser(timezone='UTC')
        parser_est = DateTimeParser(timezone='US/Eastern')
        parser_pst = DateTimeParser(timezone='US/Pacific')

        text = "tomorrow at 3pm"

        result_utc = parser_utc.parse(text)
        result_est = parser_est.parse(text)
        result_pst = parser_pst.parse(text)

        # All should parse to 3pm in their respective timezones
        assert result_utc['start'].hour == 15
        assert result_est['start'].hour == 15
        assert result_pst['start'].hour == 15

        # But the UTC times should be different
        # (Not comparing actual UTC values as it depends on DST)

    def test_timezone_in_result(self):
        """Result should include timezone information."""
        parser = DateTimeParser(timezone='US/Eastern')
        result = parser.parse("tomorrow at 3pm")

        assert 'timezone' in result
        assert result['timezone'] == 'US/Eastern'


class TestRFC3339Formatting:
    """Test RFC3339 formatting for calendar APIs."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return DateTimeParser(timezone='UTC')

    def test_format_includes_timezone(self, parser):
        """Formatted string should include timezone."""
        dt = datetime(2026, 2, 15, 14, 30, 0, tzinfo=pytz.UTC)
        formatted = parser.format_for_calendar(dt)

        # ISO format includes timezone
        assert '+00:00' in formatted or 'Z' in formatted or '+0000' in formatted

    def test_format_is_iso_compliant(self, parser):
        """Formatted string should be ISO 8601 compliant."""
        dt = datetime(2026, 2, 15, 14, 30, 0, tzinfo=pytz.UTC)
        formatted = parser.format_for_calendar(dt)

        # Should be able to parse it back
        parsed = datetime.fromisoformat(formatted.replace('Z', '+00:00'))
        assert parsed.year == 2026
        assert parsed.month == 2
        assert parsed.day == 15
