from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from app.providers.storage import StorageProvider


PRICE_RE = re.compile(r"(?:[$€£]|USD\s?|EUR\s?|GBP\s?)(\d{1,4}(?:[.,]\d{2})?)")
TRUST_KEYWORDS = (
    "cookie",
    "consent",
    "accept",
    "reject",
    "decline",
    "essential",
    "preference",
    "tracking",
    "save",
    "discount",
    "fee",
    "tax",
    "reserve",
    "book",
    "pay",
    "continue",
    "cancel",
    "unsubscribe",
    "support",
    "offer",
    "only",
    "left",
    "deal",
    "bundle",
)

SCENARIO_KEYWORDS = {
    "cookie_consent": ("cookie", "consent", "privacy", "tracking", "preferences", "accept", "reject", "decline", "essential"),
    "checkout_flow": (
        "price",
        "availability",
        "reserve",
        "reservation",
        "room",
        "night",
        "taxes",
        "fee",
        "fees",
        "deal",
        "offer",
        "book",
        "checkout",
        "select",
        "pay",
    ),
    "cancellation_flow": ("cancel", "unsubscribe", "manage", "billing", "support", "help", "pause", "retention", "leave"),
}


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _safe_text(locator: Locator, *, timeout: int = 3_000) -> str:
    try:
        text = locator.inner_text(timeout=timeout)
    except Exception:
        text = ""
    return _normalize_text(text)


def _contains_keyword(text: str, keyword: str) -> bool:
    lower_text = text.lower()
    lower_keyword = keyword.lower()
    if " " in lower_keyword:
        return lower_keyword in lower_text
    return re.search(rf"\b{re.escape(lower_keyword)}\b", lower_text) is not None


def _visible_text_lines(page: Page, limit: int = 180) -> list[str]:
    body_text = page.locator("body").inner_text(timeout=8_000)
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in body_text.splitlines():
        line = _normalize_text(raw_line)
        if len(line) < 3 or line in seen:
            continue
        seen.add(line)
        lines.append(line[:240])
        if len(lines) >= limit:
            break
    return lines


def extract_page_title(page: Page) -> str:
    try:
        return _normalize_text(page.title())
    except Exception:
        return ""


def extract_headings(page: Page, limit: int = 6) -> list[str]:
    headings: list[str] = []
    seen: set[str] = set()
    locator = page.locator("h1, h2, h3, [role='heading']")
    total = min(locator.count(), 16)
    for index in range(total):
        heading = _safe_text(locator.nth(index))
        if len(heading) < 3 or heading in seen:
            continue
        seen.add(heading)
        headings.append(heading[:160])
        if len(headings) >= limit:
            break
    return headings


def extract_button_labels(page: Page, limit: int = 16) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    locator = page.locator("button, [role='button'], input[type='submit'], input[type='button'], a")
    total = min(locator.count(), 80)
    for index in range(total):
        element = locator.nth(index)
        label = _safe_text(element)
        if not label:
            label = _normalize_text(element.get_attribute("value") or "")
        if len(label) < 2 or label in seen:
            continue
        seen.add(label)
        labels.append(label[:120])
        if len(labels) >= limit:
            break
    return labels


def extract_checkbox_states(page: Page) -> dict[str, bool]:
    states: dict[str, bool] = {}
    checkboxes = page.locator("input[type='checkbox']")
    total = min(checkboxes.count(), 8)
    for index in range(total):
        checkbox = checkboxes.nth(index)
        checkbox_id = checkbox.get_attribute("id")
        label = ""
        if checkbox_id:
            label = _safe_text(page.locator(f"label[for='{checkbox_id}']").first)
        if not label:
            try:
                parent_label = checkbox.locator("xpath=ancestor::label[1]").first
                label = _safe_text(parent_label)
            except Exception:
                label = ""
        if not label:
            label = checkbox.get_attribute("aria-label") or checkbox.get_attribute("name") or f"checkbox_{index + 1}"
        states[_normalize_text(label)[:100]] = checkbox.is_checked()
    return states


def extract_prices(page: Page, limit: int = 8) -> list[dict[str, float | str]]:
    prices: list[dict[str, float | str]] = []
    seen: set[tuple[str, float]] = set()
    for line in _visible_text_lines(page):
        for match in PRICE_RE.finditer(line):
            value = float(match.group(1).replace(",", ""))
            key = (line, value)
            if key in seen:
                continue
            seen.add(key)
            prices.append(
                {
                    "label": line[:180],
                    "value": value,
                    "raw": match.group(0),
                }
            )
            if len(prices) >= limit:
                return prices
    return prices


def extract_prices_from_text(text: str, limit: int = 4) -> list[dict[str, float | str]]:
    prices: list[dict[str, float | str]] = []
    seen: set[tuple[str, float]] = set()
    normalized = _normalize_text(text)
    for match in PRICE_RE.finditer(normalized):
        value = float(match.group(1).replace(",", ""))
        key = (normalized, value)
        if key in seen:
            continue
        seen.add(key)
        prices.append(
            {
                "label": normalized[:180],
                "value": value,
                "raw": match.group(0),
            }
        )
        if len(prices) >= limit:
            break
    return prices


def extract_text_snippets(page: Page, limit: int = 6) -> list[str]:
    lines = _visible_text_lines(page)
    prioritized = [line for line in lines if any(_contains_keyword(line, keyword) for keyword in TRUST_KEYWORDS)]
    selected: list[str] = []
    seen: set[str] = set()
    for line in prioritized + lines:
        if line in seen:
            continue
        seen.add(line)
        selected.append(line[:240])
        if len(selected) >= limit:
            break
    return selected


def extract_lines_matching_keywords(page: Page, keywords: tuple[str, ...], limit: int = 8) -> list[str]:
    matched: list[str] = []
    seen: set[str] = set()
    for line in _visible_text_lines(page):
        if not any(_contains_keyword(line, keyword) for keyword in keywords):
            continue
        if line in seen:
            continue
        seen.add(line)
        matched.append(line[:240])
        if len(matched) >= limit:
            break
    return matched


def extract_controls_matching_keywords(page: Page, keywords: tuple[str, ...], limit: int = 10) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    locator = page.locator("button, [role='button'], input[type='submit'], input[type='button'], a")
    total = min(locator.count(), 120)
    for index in range(total):
        element = locator.nth(index)
        label = _safe_text(element)
        if not label:
            label = _normalize_text(element.get_attribute("value") or "")
        if len(label) < 2 or label in seen:
            continue
        if not any(_contains_keyword(label, keyword) for keyword in keywords):
            continue
        seen.add(label)
        labels.append(label[:120])
        if len(labels) >= limit:
            break
    return labels


def extract_headings_matching_keywords(page: Page, keywords: tuple[str, ...], limit: int = 6) -> list[str]:
    headings: list[str] = []
    seen: set[str] = set()
    locator = page.locator("h1, h2, h3, [role='heading']")
    total = min(locator.count(), 24)
    for index in range(total):
        heading = _safe_text(locator.nth(index))
        if len(heading) < 3 or heading in seen:
            continue
        if not any(_contains_keyword(heading, keyword) for keyword in keywords):
            continue
        seen.add(heading)
        headings.append(heading[:160])
        if len(headings) >= limit:
            break
    return headings


def scenario_keywords(scenario: str) -> tuple[str, ...]:
    return SCENARIO_KEYWORDS.get(scenario, ())


def extract_dom_excerpt(page: Page, limit: int = 3_500) -> str:
    html = page.locator("body").inner_html(timeout=8_000)
    compact = re.sub(r"\s+", " ", html).strip()
    return compact[:limit]


def capture_screenshot(page: Page, storage: StorageProvider, relative_key: str, full_page: bool = True) -> tuple[str | None, str]:
    payload = page.screenshot(full_page=full_page, type="png")
    saved = storage.save_bytes(relative_key, payload, "image/png")
    return saved.absolute_path, saved.public_url


def guess_friction(text_snippets: list[str], buttons: list[str], headings: list[str] | None = None) -> list[str]:
    haystack = " ".join(text_snippets + buttons + (headings or [])).lower()
    flags: list[str] = []
    trigger_map = {
        "Only X left / countdown copy": ("only", "left", "deal ends", "limited time", "last chance"),
        "Retention copy guilting the user": ("no thanks", "lose", "miss out", "stay", "keep"),
        "Extra preference step present": ("manage settings", "preferences", "options", "review"),
        "Support detour likely required": ("contact support", "support", "chat", "call us", "help centre"),
    }
    for label, terms in trigger_map.items():
        if any(term in haystack for term in terms):
            flags.append(label)
    return flags
