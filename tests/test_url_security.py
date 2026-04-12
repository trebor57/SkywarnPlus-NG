"""Tests for webhook URL validation."""

import pytest

from skywarnplus_ng.utils.url_security import validate_public_https_webhook_url


@pytest.mark.parametrize(
    "url,ok",
    [
        ("", True),
        ("  ", True),
        ("https://example.com/hook", True),
        ("http://example.com/hook", False),
        ("https://127.0.0.1/x", False),
        ("https://localhost/x", False),
        ("https://192.168.1.1/x", False),
    ],
)
def test_validate_public_https_webhook_url(url, ok):
    valid, msg = validate_public_https_webhook_url(url)
    assert valid is ok, msg
