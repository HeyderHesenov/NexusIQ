"""validate_runtime() fail-closed qapıları."""
from __future__ import annotations

import pytest

from app.core import config


def test_email_verify_flag_blocks_boot(monkeypatch):
    # Verify axını tam olmadan bayraq açılsa → boot dayanmalıdır (footgun qorusu).
    monkeypatch.setattr(config.settings, "email_verification_required", True)
    with pytest.raises(RuntimeError, match="EMAIL_VERIFICATION_REQUIRED"):
        config.validate_runtime()


def test_dev_defaults_boot_ok(monkeypatch):
    # Bayraq bağlı + dev → raise yox (yalnız xəbərdarlıqlar).
    monkeypatch.setattr(config.settings, "email_verification_required", False)
    monkeypatch.setattr(config.settings, "environment", "development")
    config.validate_runtime()  # raise etməməlidir
