from validators.pii_validator import PIIValidator


def test_detects_email():
    validator = PIIValidator()
    result = validator.validate("Contact me at test@example.com")
    assert result.has_pii
    assert "email" in result.pii_types
    assert not result.safe_to_send


def test_sanitizes_credit_card():
    validator = PIIValidator()
    text = "Use card 4242 4242 4242 4242 for payment"
    sanitized = validator.sanitize(text)
    assert "[CARD_REDACTED]" in sanitized


def test_sanitizes_phone():
    validator = PIIValidator()
    text = "Call me at (415) 555-1212"
    sanitized = validator.sanitize(text)
    assert "[PHONE_REDACTED]" in sanitized
