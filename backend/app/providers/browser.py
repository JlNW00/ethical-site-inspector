from __future__ import annotations

import itertools
import time
from abc import ABC, abstractmethod
from typing import Callable
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.extractors.playwright_extractors import (
    capture_screenshot,
    extract_button_labels,
    extract_checkbox_states,
    extract_dom_excerpt,
    extract_prices,
    extract_text_snippets,
    guess_friction,
)
from app.providers.storage import StorageProvider
from app.schemas.runtime import BrowserRunResult, JourneyObservation, ObservationEvidence


ProgressCallback = Callable[[str, str, int, str, dict], None]


class BrowserAuditProvider(ABC):
    @abstractmethod
    def run_audit(
        self,
        audit_id: str,
        target_url: str,
        scenarios: list[str],
        personas: list[str],
        progress: ProgressCallback,
    ) -> BrowserRunResult:
        raise NotImplementedError


class MockBrowserAuditProvider(BrowserAuditProvider):
    def __init__(self, storage: StorageProvider):
        self.storage = storage

    def run_audit(
        self,
        audit_id: str,
        target_url: str,
        scenarios: list[str],
        personas: list[str],
        progress: ProgressCallback,
    ) -> BrowserRunResult:
        observations: list[JourneyObservation] = []
        combinations = list(itertools.product(scenarios, personas))
        total = max(1, len(combinations))
        for index, (scenario, persona) in enumerate(combinations, start=1):
            base_progress = 8 + int((index - 1) / total * 42)
            progress(
                "browser",
                f"Simulating {scenario.replace('_', ' ')} for {persona.replace('_', ' ')}",
                base_progress,
                "running",
                {"scenario": scenario, "persona": persona},
            )
            time.sleep(0.2)
            observation = self._build_observation(audit_id, target_url, scenario, persona)
            observations.append(observation)
            progress(
                "evidence",
                f"Captured evidence bundle for {scenario.replace('_', ' ')} / {persona.replace('_', ' ')}",
                min(base_progress + 8, 58),
                "running",
                {
                    "scenario": scenario,
                    "persona": persona,
                    "image_url": next(iter(observation.evidence.screenshot_urls), None),
                    "buttons": observation.evidence.button_labels[:3],
                },
            )
            time.sleep(0.1)

        return BrowserRunResult(
            observations=observations,
            summary={
                "mode": "mock",
                "observation_count": len(observations),
                "scenarios": scenarios,
                "personas": personas,
            },
        )

    def _build_observation(self, audit_id: str, target_url: str, scenario: str, persona: str) -> JourneyObservation:
        host = urlparse(target_url).netloc or "site"
        evidence = self._scenario_evidence(scenario, persona)
        screenshot_urls: list[str] = []
        screenshot_paths: list[str] = []
        for image_index, note in enumerate(evidence["image_notes"], start=1):
            svg = self._render_mock_screenshot(
                host=host,
                scenario=scenario,
                persona=persona,
                note=note,
                accent=evidence["accent"],
            )
            saved = self.storage.save_text(
                f"screenshots/{audit_id}/{scenario}_{persona}_{image_index}.svg",
                svg,
                "image/svg+xml",
            )
            screenshot_urls.append(saved.public_url)
            if saved.absolute_path:
                screenshot_paths.append(saved.absolute_path)

        return JourneyObservation(
            scenario=scenario,
            persona=persona,
            target_url=target_url,
            final_url=f"{target_url.rstrip('/')}/{scenario.replace('_', '-')}",
            evidence=ObservationEvidence(
                screenshot_urls=screenshot_urls,
                screenshot_paths=screenshot_paths,
                button_labels=evidence["button_labels"],
                checkbox_states=evidence["checkbox_states"],
                price_points=evidence["price_points"],
                text_snippets=evidence["text_snippets"],
                dom_excerpt=evidence["dom_excerpt"],
                step_count=evidence["step_count"],
                friction_indicators=evidence["friction_indicators"],
                activity_log=evidence["activity_log"],
                metadata={"source": "mock"},
            ),
        )

    def _scenario_evidence(self, scenario: str, persona: str) -> dict:
        catalog: dict[tuple[str, str], dict] = {
            ("cookie_consent", "privacy_sensitive"): {
                "accent": "#d9485f",
                "button_labels": ["Accept all", "Manage settings", "Continue with recommended choice"],
                "checkbox_states": {"Personalized ads": True, "Performance cookies": True},
                "price_points": [],
                "text_snippets": [
                    "Improve your experience by saying yes to personalized tracking. Continuing without acceptance may reduce site quality.",
                    "The reject path is buried under a secondary link while the accept action receives the primary visual treatment.",
                ],
                "dom_excerpt": "<div class='banner'><button>Accept all</button><a>Manage settings</a></div>",
                "step_count": 3,
                "friction_indicators": ["Reject option hidden behind secondary link", "Retention copy guilting the user"],
                "activity_log": ["Cookie banner detected", "Secondary preferences panel opened", "Pre-selected consent toggles found"],
                "image_notes": ["Consent banner uses a dominant approval CTA", "Preferences modal shows pre-selected toggles"],
            },
            ("cookie_consent", "cost_sensitive"): {
                "accent": "#d97706",
                "button_labels": ["Accept & save 10%", "Essential only", "See partners"],
                "checkbox_states": {"Savings newsletter": False},
                "price_points": [{"label": "Coupon offer", "value": 10.0}],
                "text_snippets": [
                    "Accept tracking to unlock an instant 10 percent discount. Essential only is available but visually minimized.",
                ],
                "dom_excerpt": "<div class='cookie-offer'>Accept & save 10%</div>",
                "step_count": 2,
                "friction_indicators": ["Discount incentive tied to tracking acceptance"],
                "activity_log": ["Discount-linked consent variant surfaced", "Essential-only action located below the fold"],
                "image_notes": ["Discount incentive attached to consent", "Essential-only path is visually de-emphasized"],
            },
            ("cookie_consent", "exit_intent"): {
                "accent": "#9f1239",
                "button_labels": ["Stay on personalized experience", "Dismiss", "Manage settings"],
                "checkbox_states": {"Ad personalization": True},
                "price_points": [],
                "text_snippets": [
                    "Before you go, keep the tailored experience turned on. Choosing otherwise may limit recommendations.",
                ],
                "dom_excerpt": "<div class='modal'>Stay on personalized experience</div>",
                "step_count": 3,
                "friction_indicators": ["Exit-intent modal re-prompts consent choice"],
                "activity_log": ["Exit-intent layer triggered", "Dismiss action requires secondary styling click"],
                "image_notes": ["Exit modal re-asks for consent", "Dismiss action appears as tertiary text"],
            },
            ("checkout_flow", "privacy_sensitive"): {
                "accent": "#0f766e",
                "button_labels": ["Continue to secure checkout", "Add protection plan", "Save details for faster checkout"],
                "checkbox_states": {"Save card for future use": True, "Protection plan": False},
                "price_points": [{"label": "Product page", "value": 49.99}, {"label": "Checkout", "value": 57.98}],
                "text_snippets": [
                    "Secure checkout highlights convenience but defaults to saving payment details for future use.",
                    "A protection plan is introduced within the checkout step rather than on the product page.",
                ],
                "dom_excerpt": "<form><input type='checkbox' checked name='save-card' /></form>",
                "step_count": 4,
                "friction_indicators": ["Stored-payment default enabled"],
                "activity_log": ["Checkout CTA clicked", "Saved-payment checkbox detected", "Total price increased at checkout"],
                "image_notes": ["Checkout total exceeds product page total", "Stored-card preference pre-selected"],
            },
            ("checkout_flow", "cost_sensitive"): {
                "accent": "#1d4ed8",
                "button_labels": ["Buy now", "Add shipping protection", "Only 2 left at this price"],
                "checkbox_states": {"Shipping protection": True},
                "price_points": [{"label": "Product page", "value": 24.99}, {"label": "Review order", "value": 38.47}],
                "text_snippets": [
                    "Only 2 left at this price. Shipping protection is already selected and taxes and fees appear later in the flow.",
                    "The total jumps at review order after the user already committed to the path.",
                ],
                "dom_excerpt": "<aside>Only 2 left at this price</aside>",
                "step_count": 5,
                "friction_indicators": ["Only X left / countdown copy", "Extra preference step present"],
                "activity_log": ["Urgency banner captured", "Protection add-on preselected", "Review order reveals higher total"],
                "image_notes": ["Urgency banner adjacent to checkout CTA", "Review order includes late-stage fee increase"],
            },
            ("checkout_flow", "exit_intent"): {
                "accent": "#7c3aed",
                "button_labels": ["Complete order", "Apply flash deal", "Keep my limited-time bundle"],
                "checkbox_states": {"Limited-time bundle": True},
                "price_points": [{"label": "Cart", "value": 89.0}, {"label": "Final step", "value": 99.0}],
                "text_snippets": [
                    "Keep my limited-time bundle before it disappears. Exit-intent behavior triggers another bundled offer.",
                ],
                "dom_excerpt": "<div class='bundle'>Keep my limited-time bundle</div>",
                "step_count": 5,
                "friction_indicators": ["Only X left / countdown copy", "Retention copy guilting the user"],
                "activity_log": ["Bundle upsell surfaced on exit", "Final price increased after bundle insertion"],
                "image_notes": ["Exit-intent upsell overlays checkout", "Bundled upsell increases final amount"],
            },
            ("cancellation_flow", "privacy_sensitive"): {
                "accent": "#be123c",
                "button_labels": ["Pause instead", "Talk to support", "Continue to cancellation"],
                "checkbox_states": {"Keep product updates": True},
                "price_points": [],
                "text_snippets": [
                    "Before cancellation, users are prompted to pause, contact support, or accept a retention offer.",
                    "The direct cancellation path is present but visually secondary and multiple detours appear first.",
                ],
                "dom_excerpt": "<section class='retention'>Talk to support</section>",
                "step_count": 7,
                "friction_indicators": ["Support detour likely required", "Retention copy guilting the user", "Extra step present"],
                "activity_log": ["Account settings reached", "Pause plan option prioritized", "Support detour inserted before final cancellation"],
                "image_notes": ["Retention screen appears before cancellation", "Support detour blocks direct cancel action"],
            },
            ("cancellation_flow", "cost_sensitive"): {
                "accent": "#b45309",
                "button_labels": ["Keep my discount", "Cancel anyway", "Chat with billing"],
                "checkbox_states": {"Resume later reminders": True},
                "price_points": [],
                "text_snippets": [
                    "Keep my discount and save your plan. Cancel anyway appears after a discount-focused retention card and billing chat prompt.",
                ],
                "dom_excerpt": "<div class='discount-retention'>Keep my discount</div>",
                "step_count": 6,
                "friction_indicators": ["Retention copy guilting the user", "Support detour likely required"],
                "activity_log": ["Discount retention card inserted", "Billing chat callout shown before final exit"],
                "image_notes": ["Retention discount prioritizes staying", "Billing chat detour adds more friction"],
            },
            ("cancellation_flow", "exit_intent"): {
                "accent": "#4338ca",
                "button_labels": ["Stay enrolled", "No thanks, lose my benefits", "Pause plan"],
                "checkbox_states": {"Email me a comeback offer": True},
                "price_points": [],
                "text_snippets": [
                    "No thanks, lose my benefits is used as the decline label in the cancellation retention step.",
                ],
                "dom_excerpt": "<button>No thanks, lose my benefits</button>",
                "step_count": 7,
                "friction_indicators": ["Retention copy guilting the user", "Extra step present"],
                "activity_log": ["Confirmshaming copy observed", "Pause option repeated after user chose cancel"],
                "image_notes": ["Confirmshaming label used for cancellation", "Pause plan offered again after opt-out"],
            },
        }
        return catalog[(scenario, persona)]

    @staticmethod
    def _render_mock_screenshot(host: str, scenario: str, persona: str, note: str, accent: str) -> str:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="900" viewBox="0 0 1440 900">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b1020"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
  </defs>
  <rect width="1440" height="900" fill="url(#bg)"/>
  <rect x="80" y="90" width="1280" height="720" rx="32" fill="#f8fafc"/>
  <rect x="80" y="90" width="1280" height="84" rx="32" fill="{accent}"/>
  <text x="128" y="142" fill="#f8fafc" font-family="Segoe UI, Arial" font-size="28" font-weight="700">EthicalSiteInspector Mock Capture</text>
  <text x="128" y="245" fill="#0f172a" font-family="Segoe UI, Arial" font-size="48" font-weight="700">{scenario.replace('_', ' ').title()}</text>
  <text x="128" y="302" fill="#334155" font-family="Segoe UI, Arial" font-size="28">{persona.replace('_', ' ').title()} persona on {host}</text>
  <rect x="128" y="360" width="1184" height="220" rx="24" fill="#e2e8f0"/>
  <text x="164" y="430" fill="#0f172a" font-family="Segoe UI, Arial" font-size="34" font-weight="700">Captured signal</text>
  <text x="164" y="486" fill="#334155" font-family="Segoe UI, Arial" font-size="26">{note}</text>
  <rect x="128" y="628" width="280" height="72" rx="18" fill="{accent}"/>
  <text x="176" y="672" fill="#f8fafc" font-family="Segoe UI, Arial" font-size="28" font-weight="700">Primary CTA</text>
  <rect x="438" y="628" width="280" height="72" rx="18" fill="#cbd5e1"/>
  <text x="506" y="672" fill="#0f172a" font-family="Segoe UI, Arial" font-size="28" font-weight="700">Secondary action</text>
</svg>"""


class PlaywrightAuditProvider(BrowserAuditProvider):
    def __init__(self, storage: StorageProvider):
        self.storage = storage

    def run_audit(
        self,
        audit_id: str,
        target_url: str,
        scenarios: list[str],
        personas: list[str],
        progress: ProgressCallback,
    ) -> BrowserRunResult:
        observations: list[JourneyObservation] = []
        combinations = list(itertools.product(scenarios, personas))
        total = max(1, len(combinations))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for index, (scenario, persona) in enumerate(combinations, start=1):
                    progress(
                        "browser",
                        f"Running live browser audit for {scenario.replace('_', ' ')} / {persona.replace('_', ' ')}",
                        6 + int((index - 1) / total * 40),
                        "running",
                        {"scenario": scenario, "persona": persona},
                    )
                    context = browser.new_context(**self._context_options(persona))
                    page = context.new_page()
                    observation = self._run_scenario(audit_id, target_url, scenario, persona, page)
                    observations.append(observation)
                    progress(
                        "evidence",
                        f"Captured browser evidence for {scenario.replace('_', ' ')} / {persona.replace('_', ' ')}",
                        12 + int(index / total * 44),
                        "running",
                        {
                            "scenario": scenario,
                            "persona": persona,
                            "image_url": next(iter(observation.evidence.screenshot_urls), None),
                            "buttons": observation.evidence.button_labels[:3],
                        },
                    )
                    context.close()
            finally:
                browser.close()

        return BrowserRunResult(
            observations=observations,
            summary={
                "mode": "playwright",
                "observation_count": len(observations),
                "scenarios": scenarios,
                "personas": personas,
            },
        )

    def _run_scenario(self, audit_id: str, target_url: str, scenario: str, persona: str, page) -> JourneyObservation:
        page.goto(target_url, wait_until="domcontentloaded", timeout=25_000)
        page.wait_for_timeout(1_000)
        step_count = 1
        activity_log = ["Loaded target URL"]
        self._attempt_scenario_actions(page, scenario, activity_log)
        step_count += max(0, len(activity_log) - 1)

        first_path, first_url = capture_screenshot(
            page,
            self.storage,
            f"screenshots/{audit_id}/{scenario}_{persona}_live_1.png",
        )
        page.wait_for_timeout(500)
        second_path, second_url = capture_screenshot(
            page,
            self.storage,
            f"screenshots/{audit_id}/{scenario}_{persona}_live_2.png",
        )

        button_labels = extract_button_labels(page)
        checkbox_states = extract_checkbox_states(page)
        price_points = extract_prices(page)
        text_snippets = extract_text_snippets(page)
        friction_indicators = guess_friction(text_snippets, button_labels)
        dom_excerpt = extract_dom_excerpt(page)

        return JourneyObservation(
            scenario=scenario,
            persona=persona,
            target_url=target_url,
            final_url=page.url,
            evidence=ObservationEvidence(
                screenshot_urls=[item for item in [first_url, second_url] if item],
                screenshot_paths=[item for item in [first_path, second_path] if item],
                button_labels=button_labels,
                checkbox_states=checkbox_states,
                price_points=price_points,
                text_snippets=text_snippets,
                dom_excerpt=dom_excerpt,
                step_count=step_count,
                friction_indicators=friction_indicators,
                activity_log=activity_log,
                metadata={"source": "playwright"},
            ),
        )

    def _attempt_scenario_actions(self, page, scenario: str, activity_log: list[str]) -> None:
        scenario_map = {
            "cookie_consent": ["accept", "allow", "reject", "essential", "settings", "preferences"],
            "checkout_flow": ["add to cart", "checkout", "buy now", "continue", "review order"],
            "cancellation_flow": ["cancel", "unsubscribe", "account", "billing", "manage", "pause"],
        }
        keywords = scenario_map.get(scenario, [])
        try:
            for keyword in keywords:
                locator = page.get_by_role("button", name=lambda text: keyword in text.lower())
                if locator.count():
                    locator.first.click(timeout=4_000)
                    page.wait_for_timeout(800)
                    activity_log.append(f"Clicked button matching '{keyword}'")
                    break
        except PlaywrightTimeoutError:
            activity_log.append(f"Timed out while trying '{scenario}' interaction")
        except Exception as exc:
            activity_log.append(f"Scenario interaction degraded gracefully: {exc.__class__.__name__}")

    @staticmethod
    def _context_options(persona: str) -> dict:
        base = {
            "viewport": {"width": 1440, "height": 960},
            "locale": "en-US",
            "color_scheme": "light",
        }
        if persona == "privacy_sensitive":
            base["extra_http_headers"] = {"DNT": "1", "Sec-GPC": "1"}
        if persona == "exit_intent":
            base["reduced_motion"] = "reduce"
        return base
