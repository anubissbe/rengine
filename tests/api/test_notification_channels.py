"""A channel's stored URL is masked on the way out and checked on the way in."""

from __future__ import annotations

import pytest

from app.services.notification_channel import _mask_url
from shared.services.scan_resolve import MASK
from shared.utils.net import validate_public_https_url

pytestmark = pytest.mark.api


@pytest.mark.parametrize(
    "url",
    [
        "https://hooks.example.com/services/abc",
        "https://hooks.example.com:8443/services/abc",
        "https://hooks.example.com:99999/services/abc",
        "https://hooks.example.com:8o80/services/abc",
        "https://[2001:db8::1]:8443/hook",
    ],
)
def test_masking_a_url_never_raises_on_the_port(url):
    masked = _mask_url(url)
    assert MASK in masked
    assert "abc" not in masked


def test_a_port_that_is_not_a_number_is_refused_before_it_is_stored():
    with pytest.raises(ValueError, match="not a port number"):
        validate_public_https_url(
            "https://hooks.example.com:99999/x", label="Webhook URL"
        )
