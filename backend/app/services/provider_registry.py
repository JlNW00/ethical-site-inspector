from __future__ import annotations

from app.core.config import Settings, get_settings
from app.providers.browser import BrowserAuditProvider, MockBrowserAuditProvider, PlaywrightAuditProvider
from app.providers.classifier import ClassifierProvider, LiveNovaClassifierProvider, MockClassifierProvider
from app.providers.nova_act_browser import NovaActAuditProvider, NOVA_ACT_AVAILABLE
from app.providers.storage import LocalStorageProvider, S3StorageProvider, StorageProvider


def is_playwright_ready() -> bool:
    try:
        import playwright  # noqa: F401
    except Exception:
        return False
    return True


def get_storage_provider(settings: Settings | None = None) -> StorageProvider:
    config = settings or get_settings()
    if config.s3_ready:
        return S3StorageProvider(config)
    return LocalStorageProvider(config.local_storage_root)


def get_browser_provider(mode: str | None = None, settings: Settings | None = None) -> BrowserAuditProvider:
    config = settings or get_settings()
    effective_mode = mode or config.effective_mode
    storage = get_storage_provider(config)
    if effective_mode == "live":
        if NOVA_ACT_AVAILABLE:
            return NovaActAuditProvider(storage)
        # Fallback to mock if NovaAct is not available in live mode
        return MockBrowserAuditProvider(storage)
    if effective_mode == "hybrid":
        return PlaywrightAuditProvider(storage)
    return MockBrowserAuditProvider(storage)


def get_fallback_browser_provider(settings: Settings | None = None) -> BrowserAuditProvider:
    storage = get_storage_provider(settings or get_settings())
    return MockBrowserAuditProvider(storage)


def get_classifier_provider(mode: str | None = None, settings: Settings | None = None) -> ClassifierProvider:
    config = settings or get_settings()
    effective_mode = mode or config.effective_mode
    if effective_mode == "live" and config.nova_ready:
        return LiveNovaClassifierProvider(config)
    return MockClassifierProvider()
