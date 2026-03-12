from __future__ import annotations

import re

from playwright.sync_api import Page

from app.providers.storage import StorageProvider


PRICE_RE = re.compile(r"(?:\$|USD\s?)(\d{1,4}(?:[.,]\d{2})?)")


def extract_button_labels(page: Page) -> list[str]:
    raw_labels = page.locator("button, [role='button'], input[type='submit'], a").all_inner_texts()
    labels: list[str] = []
    for label in raw_labels:
        normalized = " ".join(label.split())
        if normalized and normalized not in labels:
            labels.append(normalized[:100])
        if len(labels) >= 12:
            break
    return labels


def extract_checkbox_states(page: Page) -> dict[str, bool]:
    states: dict[str, bool] = {}
    checkboxes = page.locator("input[type='checkbox']")
    total = min(checkboxes.count(), 8)
    for index in range(total):
        checkbox = checkboxes.nth(index)
        label = checkbox.get_attribute("aria-label") or checkbox.get_attribute("name") or f"checkbox_{index + 1}"
        states[label[:80]] = checkbox.is_checked()
    return states


def extract_prices(page: Page) -> list[dict[str, float | str]]:
    text = page.locator("body").inner_text(timeout=8_000)
    prices: list[dict[str, float | str]] = []
    for match in PRICE_RE.finditer(text):
        value = float(match.group(1).replace(",", ""))
        prices.append({"label": "Detected price", "value": value})
        if len(prices) >= 6:
            break
    return prices


def extract_text_snippets(page: Page, limit: int = 5) -> list[str]:
    text = " ".join(page.locator("body").inner_text(timeout=8_000).split())
    if not text:
        return []
    snippets = []
    chunk_size = max(180, min(320, len(text)))
    for index in range(0, len(text), chunk_size):
        snippet = text[index : index + chunk_size].strip()
        if snippet:
            snippets.append(snippet)
        if len(snippets) >= limit:
            break
    return snippets


def extract_dom_excerpt(page: Page, limit: int = 3_500) -> str:
    html = page.locator("body").inner_html(timeout=8_000)
    compact = re.sub(r"\s+", " ", html).strip()
    return compact[:limit]


def capture_screenshot(page: Page, storage: StorageProvider, relative_key: str, full_page: bool = True) -> tuple[str | None, str]:
    payload = page.screenshot(full_page=full_page, type="png")
    saved = storage.save_bytes(relative_key, payload, "image/png")
    return saved.absolute_path, saved.public_url


def guess_friction(text_snippets: list[str], buttons: list[str]) -> list[str]:
    haystack = " ".join(text_snippets + buttons).lower()
    flags: list[str] = []
    trigger_map = {
        "Only X left / countdown copy": ["only", "left", "timer", "offer ends", "minutes"],
        "Retention copy guilting the user": ["no thanks", "stay subscribed", "don't leave", "miss out"],
        "Extra preference step present": ["manage settings", "preferences", "review options"],
        "Support detour likely required": ["contact support", "chat", "call us", "speak to us"],
    }
    for label, terms in trigger_map.items():
        if all(term in haystack for term in terms[:2]) or any(term in haystack for term in terms[2:]):
            flags.append(label)
    return flags
