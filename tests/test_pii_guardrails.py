import pytest
from qa_pipeline.pii_guardrails import PIIGuardrails


def test_detect_no_pii():
    guardrails = PIIGuardrails()
    content = "This is a clean requirement text without any personal data."
    result = guardrails.detect_pii(content)
    assert result.has_pii is False
    assert result.pii_count == 0


def test_detect_and_mask_email():
    guardrails = PIIGuardrails()
    content = "Please contact test.user@example.com for registration issues."
    result = guardrails.mask_pii(content)
    
    assert result.has_pii is True
    assert "test.user@example.com" not in result.masked_content
    # Проверяем, что начало и конец сохранены, а середина замаскирована
    assert result.masked_content.startswith("Please contact te")
    assert result.masked_content.endswith("om for registration issues.")
    assert "*" in result.masked_content


def test_detect_and_mask_passport():
    guardrails = PIIGuardrails()
    content = "User passport number is 45 12 123456."
    result = guardrails.mask_pii(content)
    
    assert result.has_pii is True
    assert "45 12 123456" not in result.masked_content


def test_generate_pii_report():
    guardrails = PIIGuardrails()
    content = "My email is admin@site.com and phone is +7 (999) 123-45-67"
    result = guardrails.mask_pii(content)
    report = guardrails.generate_pii_report(result)
    
    assert report["has_pii"] is True
    assert report["total_pii_count"] >= 2
    assert "email" in report["pii_categories"]
    assert "phone" in report["pii_categories"]
