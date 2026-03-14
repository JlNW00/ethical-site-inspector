from __future__ import annotations

import contextlib
import itertools
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from urllib.parse import urljoin, urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.extractors.playwright_extractors import (
    capture_screenshot,
    extract_checkbox_states,
    extract_controls_matching_keywords,
    extract_dom_excerpt,
    extract_headings_matching_keywords,
    extract_lines_matching_keywords,
    extract_locator_label,
    extract_page_title,
    extract_prices,
    extract_prices_from_text,
    guess_friction,
    scenario_keywords,
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
    # Minimal valid WebM file bytes (EBML header + minimal content)
    # This is a tiny placeholder webm file that validates as real WebM
    MOCK_WEBM_BYTES: bytes = bytes([
        0x1A, 0x45, 0xDF, 0xA3,  # EBML ID
        0x9F,  # Size (31 bytes following)
        0x42, 0x86, 0x81, 0x01,  # EBMLVersion = 1
        0x42, 0xF7, 0x81, 0x01,  # EBMLReadVersion = 1
        0x42, 0xF2, 0x81, 0x04,  # EBMLMaxIDLength = 4
        0x42, 0xF3, 0x81, 0x08,  # EBMLMaxSizeLength = 8
        0x42, 0x82, 0x88, 0x77, 0x65, 0x62, 0x6D, 0x00,  # DocType = "webm"
        0x42, 0x87, 0x81, 0x04,  # DocTypeVersion = 4
        0x42, 0x85, 0x81, 0x02,  # DocTypeReadVersion = 2
    ])

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
        video_urls: dict[str, str] = {}
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

            # Generate and save mock video for this scenario-persona
            video_key = f"videos/{audit_id}/{scenario}_{persona}.webm"
            saved_video = self.storage.save_bytes(
                video_key,
                self.MOCK_WEBM_BYTES,
                "video/webm",
            )
            video_key_id = f"{scenario}_{persona}"
            video_urls[video_key_id] = saved_video.public_url

            progress(
                "video",
                f"Recorded session video for {scenario.replace('_', ' ')} / {persona.replace('_', ' ')}",
                min(base_progress + 8, 58),
                "running",
                {
                    "scenario": scenario,
                    "persona": persona,
                    "image_url": next(iter(observation.evidence.screenshot_urls), None),
                    "video_url": saved_video.public_url,
                    "buttons": observation.evidence.button_labels[:3],
                },
            )
            time.sleep(0.1)

        return BrowserRunResult(
            observations=observations,
            summary={
                "mode": "mock",
                "evidence_origin": "simulated",
                "evidence_origin_label": "Simulated",
                "observation_count": len(observations),
                "scenarios": scenarios,
                "personas": personas,
            },
            video_urls=video_urls,
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
                headings=evidence.get(
                    "headings", [scenario.replace("_", " ").title(), persona.replace("_", " ").title()]
                ),
                page_title=evidence.get("page_title", f"{host} {scenario.replace('_', ' ').title()}"),
                dom_excerpt=evidence["dom_excerpt"],
                step_count=evidence["step_count"],
                friction_indicators=evidence["friction_indicators"],
                activity_log=evidence["activity_log"],
                metadata={
                    "source": "mock",
                    "source_label": "Simulated",
                    "site_host": host,
                    "page_url": f"{target_url.rstrip('/')}/{scenario.replace('_', '-')}",
                    "interacted_controls": evidence.get("button_labels", [])[:2],
                },
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
                "headings": ["Cookie preferences", "Recommended privacy setting"],
                "page_title": "Cookie preferences",
                "dom_excerpt": "<div class='banner'><button>Accept all</button><a>Manage settings</a></div>",
                "step_count": 3,
                "friction_indicators": [
                    "Reject option hidden behind secondary link",
                    "Retention copy guilting the user",
                ],
                "activity_log": [
                    "Cookie banner detected",
                    "Secondary preferences panel opened",
                    "Pre-selected consent toggles found",
                ],
                "image_notes": [
                    "Consent banner uses a dominant approval CTA",
                    "Preferences modal shows pre-selected toggles",
                ],
            },
            ("cookie_consent", "cost_sensitive"): {
                "accent": "#d97706",
                "button_labels": ["Accept & save 10%", "Essential only", "See partners"],
                "checkbox_states": {"Savings newsletter": False},
                "price_points": [{"label": "Coupon offer", "value": 10.0}],
                "text_snippets": [
                    "Accept tracking to unlock an instant 10 percent discount. Essential only is available but visually minimized.",
                ],
                "headings": ["Tracking choices", "Discount unlock prompt"],
                "page_title": "Discount-linked consent prompt",
                "dom_excerpt": "<div class='cookie-offer'>Accept & save 10%</div>",
                "step_count": 2,
                "friction_indicators": ["Discount incentive tied to tracking acceptance"],
                "activity_log": [
                    "Discount-linked consent variant surfaced",
                    "Essential-only action located below the fold",
                ],
                "image_notes": [
                    "Discount incentive attached to consent",
                    "Essential-only path is visually de-emphasized",
                ],
            },
            ("cookie_consent", "exit_intent"): {
                "accent": "#9f1239",
                "button_labels": ["Stay on personalized experience", "Dismiss", "Manage settings"],
                "checkbox_states": {"Ad personalization": True},
                "price_points": [],
                "text_snippets": [
                    "Before you go, keep the tailored experience turned on. Choosing otherwise may limit recommendations.",
                ],
                "headings": ["Before you go", "Personalized experience"],
                "page_title": "Exit-intent consent prompt",
                "dom_excerpt": "<div class='modal'>Stay on personalized experience</div>",
                "step_count": 3,
                "friction_indicators": ["Exit-intent modal re-prompts consent choice"],
                "activity_log": ["Exit-intent layer triggered", "Dismiss action requires secondary styling click"],
                "image_notes": ["Exit modal re-asks for consent", "Dismiss action appears as tertiary text"],
            },
            ("checkout_flow", "privacy_sensitive"): {
                "accent": "#0f766e",
                "button_labels": [
                    "Continue to secure checkout",
                    "Add protection plan",
                    "Save details for faster checkout",
                ],
                "checkbox_states": {"Save card for future use": True, "Protection plan": False},
                "price_points": [{"label": "Product page", "value": 49.99}, {"label": "Checkout", "value": 57.98}],
                "text_snippets": [
                    "Secure checkout highlights convenience but defaults to saving payment details for future use.",
                    "A protection plan is introduced within the checkout step rather than on the product page.",
                ],
                "headings": ["Secure checkout", "Saved details"],
                "page_title": "Secure checkout",
                "dom_excerpt": "<form><input type='checkbox' checked name='save-card' /></form>",
                "step_count": 4,
                "friction_indicators": ["Stored-payment default enabled"],
                "activity_log": [
                    "Checkout CTA clicked",
                    "Saved-payment checkbox detected",
                    "Total price increased at checkout",
                ],
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
                "headings": ["Review order", "Only 2 left at this price"],
                "page_title": "Review order",
                "dom_excerpt": "<aside>Only 2 left at this price</aside>",
                "step_count": 5,
                "friction_indicators": ["Only X left / countdown copy", "Extra preference step present"],
                "activity_log": [
                    "Urgency banner captured",
                    "Protection add-on preselected",
                    "Review order reveals higher total",
                ],
                "image_notes": [
                    "Urgency banner adjacent to checkout CTA",
                    "Review order includes late-stage fee increase",
                ],
            },
            ("checkout_flow", "exit_intent"): {
                "accent": "#7c3aed",
                "button_labels": ["Complete order", "Apply flash deal", "Keep my limited-time bundle"],
                "checkbox_states": {"Limited-time bundle": True},
                "price_points": [{"label": "Cart", "value": 89.0}, {"label": "Final step", "value": 99.0}],
                "text_snippets": [
                    "Keep my limited-time bundle before it disappears. Exit-intent behavior triggers another bundled offer.",
                ],
                "headings": ["Limited-time bundle", "Complete order"],
                "page_title": "Bundle upsell",
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
                "headings": ["Keep your plan", "Talk to support"],
                "page_title": "Cancellation flow",
                "dom_excerpt": "<section class='retention'>Talk to support</section>",
                "step_count": 7,
                "friction_indicators": [
                    "Support detour likely required",
                    "Retention copy guilting the user",
                    "Extra step present",
                ],
                "activity_log": [
                    "Account settings reached",
                    "Pause plan option prioritized",
                    "Support detour inserted before final cancellation",
                ],
                "image_notes": [
                    "Retention screen appears before cancellation",
                    "Support detour blocks direct cancel action",
                ],
            },
            ("cancellation_flow", "cost_sensitive"): {
                "accent": "#b45309",
                "button_labels": ["Keep my discount", "Cancel anyway", "Chat with billing"],
                "checkbox_states": {"Resume later reminders": True},
                "price_points": [],
                "text_snippets": [
                    "Keep my discount and save your plan. Cancel anyway appears after a discount-focused retention card and billing chat prompt.",
                ],
                "headings": ["Keep my discount", "Billing support"],
                "page_title": "Retention offer",
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
                "headings": ["Stay enrolled", "Pause plan"],
                "page_title": "Cancellation retention prompt",
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
  <text x="128" y="245" fill="#0f172a" font-family="Segoe UI, Arial" font-size="48" font-weight="700">{scenario.replace("_", " ").title()}</text>
  <text x="128" y="302" fill="#334155" font-family="Segoe UI, Arial" font-size="28">{persona.replace("_", " ").title()} persona on {host}</text>
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
                "evidence_origin": "captured",
                "evidence_origin_label": "Captured from site",
                "observation_count": len(observations),
                "scenarios": scenarios,
                "personas": personas,
            },
        )

    def _run_scenario(self, audit_id: str, target_url: str, scenario: str, persona: str, page) -> JourneyObservation:
        page.goto(target_url, wait_until="domcontentloaded", timeout=25_000)
        page.wait_for_timeout(1_000)
        activity_log = ["Loaded target URL"]
        self._dismiss_irrelevant_dialogs(page, scenario, activity_log)
        page.wait_for_timeout(700)
        self._dismiss_irrelevant_dialogs(page, scenario, activity_log)
        state_snapshots = [self._snapshot_state(page, scenario=scenario, label="initial")]

        first_path, first_url = capture_screenshot(
            page,
            self.storage,
            f"screenshots/{audit_id}/{scenario}_{persona}_live_1.png",
        )
        interacted_controls = self._attempt_scenario_actions(page, scenario, persona, activity_log, state_snapshots)
        page.wait_for_timeout(700)
        second_path, second_url = capture_screenshot(
            page,
            self.storage,
            f"screenshots/{audit_id}/{scenario}_{persona}_live_2.png",
        )
        state_snapshots.append(self._snapshot_state(page, scenario=scenario, label="final"))

        scenario_states = [state for state in state_snapshots if state["grounded"]]
        effective_states = scenario_states or state_snapshots[-1:]
        headings = self._merge_unique_from_states(effective_states, "headings", limit=6)
        button_labels = self._merge_unique_from_states(effective_states, "buttons", limit=8)
        text_snippets = self._merge_unique_from_states(effective_states, "texts", limit=8)
        checkbox_states = self._merge_checkbox_states(effective_states)
        price_points = self._scenario_price_points(scenario_states)
        friction_indicators = self._scenario_friction(
            scenario=scenario,
            states=effective_states,
            interacted_controls=interacted_controls,
            text_snippets=text_snippets,
            button_labels=button_labels,
            headings=headings,
        )
        dom_excerpt = extract_dom_excerpt(page)
        step_count = max(1, len(interacted_controls))
        host = urlparse(target_url).netloc or page.url
        page_title = effective_states[-1]["page_title"] if effective_states else extract_page_title(page)
        if page_title:
            activity_log.append(f"Observed page title: {page_title}")
        scenario_state_found = bool(scenario_states)
        if scenario_state_found:
            activity_log.append(f"Scenario-grounded state captured for {scenario.replace('_', ' ')}.")
        else:
            activity_log.append(f"No scenario-grounded UI state was confirmed for {scenario.replace('_', ' ')}.")

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
                headings=headings,
                page_title=page_title,
                dom_excerpt=dom_excerpt,
                step_count=step_count,
                friction_indicators=friction_indicators,
                activity_log=activity_log,
                metadata={
                    "source": "playwright",
                    "source_label": "Captured from site",
                    "site_host": host,
                    "page_url": page.url,
                    "interacted_controls": interacted_controls,
                    "scenario_state_found": scenario_state_found,
                    "scenario_state_count": len(scenario_states),
                    "state_snapshots": state_snapshots,
                    "action_count": len(interacted_controls),
                    "observed_price_delta": self._observed_price_delta(price_points),
                },
            ),
        )

    def _attempt_scenario_actions(
        self, page, scenario: str, persona: str, activity_log: list[str], state_snapshots: list[dict]
    ) -> list[str]:
        if scenario == "checkout_flow":
            return self._attempt_checkout_actions(page, persona, activity_log, state_snapshots)
        if scenario == "cookie_consent":
            return self._attempt_cookie_actions(page, persona, activity_log, state_snapshots)
        return self._attempt_plan_actions(page, scenario, persona, activity_log, state_snapshots)

    def _attempt_plan_actions(
        self, page, scenario: str, persona: str, activity_log: list[str], state_snapshots: list[dict]
    ) -> list[str]:
        interactions: list[str] = []
        plan = self._scenario_action_plan(scenario, persona)
        try:
            for step in plan:
                label = self._click_first_matching(page, step["keywords"], step.get("require_keywords"))
                if not label:
                    continue
                interactions.append(label)
                activity_log.append(f'Interacted with control "{label}" while testing {scenario.replace("_", " ")}')
                page.wait_for_timeout(900)
                state_snapshots.append(self._snapshot_state(page, scenario=scenario, label=step["label"]))
        except PlaywrightTimeoutError:
            activity_log.append(f"Timed out while trying '{scenario}' interaction")
        except Exception as exc:
            activity_log.append(f"Scenario interaction degraded gracefully: {exc.__class__.__name__}")
        return interactions

    def _attempt_cookie_actions(
        self, page, persona: str, activity_log: list[str], state_snapshots: list[dict]
    ) -> list[str]:
        current_buttons = state_snapshots[-1].get("buttons", []) if state_snapshots else []
        direct_cookie_controls = any(
            term in label.lower()
            for label in current_buttons
            for term in (
                "accept",
                "reject",
                "decline",
                "allow",
                "agree",
                "essential",
                "necessary",
                "preferences",
                "settings",
            )
        )
        interactions = (
            self._attempt_plan_actions(page, "cookie_consent", persona, activity_log, state_snapshots)
            if direct_cookie_controls
            else []
        )
        if interactions or any(state.get("grounded") for state in state_snapshots):
            return interactions

        for scroll_ratio in (0.0, 0.45, 0.8, 1.0):
            try:
                page.evaluate("(ratio) => window.scrollTo(0, document.body.scrollHeight * ratio)", scroll_ratio)
                page.wait_for_timeout(500)
            except Exception:
                pass
            label = self._click_first_matching(
                page,
                ["cookie", "cookies", "consent", "privacy", "preferences"],
                selector="a, button, [role='button'], input[type='submit'], input[type='button']",
            )
            if not label:
                continue
            interactions.append(label)
            activity_log.append(f'Opened privacy or cookie entry point "{label}".')
            page.wait_for_timeout(900)
            state_snapshots.append(self._snapshot_state(page, scenario="cookie_consent", label="consent_entry"))
            return interactions
        activity_log.append(
            "No visible cookie or privacy entry point was captured after dismissing unrelated blockers."
        )
        return interactions

    def _attempt_checkout_actions(
        self, page, persona: str, activity_log: list[str], state_snapshots: list[dict]
    ) -> list[str]:
        interactions: list[str] = []
        try:
            offer = self._choose_checkout_offer(page, persona)
            if not offer:
                activity_log.append("No visible offer or destination result could be grounded for checkout.")
                return interactions

            offer_label = offer["text"]
            self._append_checkout_offer_state(page, offer, state_snapshots)
            interactions.append(f'Selected offer "{offer_label[:80]}"')
            activity_log.append(f'Observed and selected offer "{offer_label[:120]}" from the site.')

            if self._navigate_to_href(page, offer["href"]):
                page.wait_for_timeout(1_400)
                result_label = "result_page" if offer["kind"] == "destination" else "offer_result"
                state_snapshots.append(self._snapshot_state(page, scenario="checkout_flow", label=result_label))

            needs_detail = "/hotel/" not in page.url
            if needs_detail:
                hotel = self._choose_hotel_detail_link(page, persona)
                if hotel and self._navigate_to_href(page, hotel["href"]):
                    self._append_checkout_hotel_state(page, hotel, state_snapshots)
                    interactions.append(f'Opened hotel detail "{hotel["text"][:80]}"')
                    activity_log.append(f'Opened hotel detail "{hotel["text"][:120]}" for checkout review.')
                    page.wait_for_timeout(1_400)
                    state_snapshots.append(self._snapshot_state(page, scenario="checkout_flow", label="detail_page"))

            follow_up = self._checkout_follow_up(page, persona)
            for action in follow_up:
                label = self._click_first_matching(
                    page,
                    action["keywords"],
                    selector=action.get("selector")
                    or "button, a, [role='button'], input[type='submit'], input[type='button']",
                )
                if not label:
                    continue
                interactions.append(label)
                activity_log.append(f'Interacted with checkout control "{label}".')
                page.wait_for_timeout(900)
                state_snapshots.append(self._snapshot_state(page, scenario="checkout_flow", label=action["label"]))
        except PlaywrightTimeoutError:
            activity_log.append("Timed out while trying checkout-specific navigation.")
        except Exception as exc:
            activity_log.append(f"Checkout interaction degraded gracefully: {exc.__class__.__name__}")
        return interactions

    def _click_first_matching(
        self,
        page,
        keywords: list[str],
        require_keywords: list[str] | None = None,
        *,
        selector: str = "button, a, [role='button'], input[type='submit'], input[type='button']",
    ) -> str | None:
        for frame in self._candidate_frames(page):
            label = self._click_first_matching_in_scope(frame, keywords, require_keywords, selector=selector)
            if label:
                return label
        return None

    @staticmethod
    def _element_label(element) -> str:
        return extract_locator_label(element)

    @staticmethod
    def _candidate_frames(page) -> list:
        frames: list = []
        for frame in page.frames:
            try:
                if frame.is_detached():
                    continue
            except Exception:
                continue
            frames.append(frame)
        return frames or [page]

    def _click_first_matching_in_scope(
        self,
        scope,
        keywords: list[str],
        require_keywords: list[str] | None = None,
        *,
        selector: str,
    ) -> str | None:
        locator = scope.locator(selector)
        try:
            total = min(locator.count(), 360)
        except Exception:
            return None
        for index in range(total):
            element = locator.nth(index)
            try:
                if not element.is_visible():
                    continue
                label = self._element_label(element)
                lower_label = label.lower()
                if not label or not any(keyword in lower_label for keyword in keywords):
                    continue
                if require_keywords and not any(keyword in lower_label for keyword in require_keywords):
                    continue
                with contextlib.suppress(Exception):
                    element.scroll_into_view_if_needed(timeout=1_000)
                try:
                    element.click(timeout=2_000)
                except Exception:
                    try:
                        element.click(timeout=2_000, force=True)
                    except Exception:
                        element.evaluate("(node) => node.click()")
                return label
            except Exception:
                continue
        return None

    def _dismiss_irrelevant_dialogs(self, page, scenario: str, activity_log: list[str]) -> None:
        dialogs = page.locator("[role='dialog'], dialog, [aria-modal='true']")
        total = min(dialogs.count(), 4)
        for index in range(total):
            dialog = dialogs.nth(index)
            try:
                if not dialog.is_visible():
                    continue
                dialog_text = " ".join(dialog.inner_text(timeout=1_500).split()).strip().lower()
                if any(term in dialog_text for term in scenario_keywords(scenario)):
                    continue
                label = self._click_first_matching_in_scope(
                    dialog,
                    ["dismiss", "close", "not now", "maybe later", "no thanks", "skip"],
                    selector="button, [role='button'], input[type='submit'], input[type='button'], a",
                )
                if not label:
                    continue
                activity_log.append(f'Dismissed unrelated dialog via "{label}".')
                page.wait_for_timeout(500)
            except Exception:
                continue

    def _snapshot_state(self, page, *, scenario: str, label: str) -> dict:
        keywords = scenario_keywords(scenario)
        headings = extract_headings_matching_keywords(page, keywords, limit=6)
        texts = extract_lines_matching_keywords(page, keywords, limit=10)
        buttons = extract_controls_matching_keywords(page, keywords, limit=10)
        all_prices = extract_prices(page, limit=12)
        prices = [
            item for item in all_prices if self._price_is_scenario_grounded(scenario, item, texts, headings, buttons)
        ]
        page_title = extract_page_title(page)
        state_type = self._state_type(
            page, scenario=scenario, label=label, headings=headings, texts=texts, buttons=buttons
        )
        grounded = self._state_is_grounded(
            scenario,
            label=label,
            page_url=page.url,
            state_type=state_type,
            headings=headings,
            texts=texts,
            buttons=buttons,
            prices=prices,
        )
        return {
            "label": label,
            "state_type": state_type,
            "page_title": page_title,
            "page_url": page.url,
            "headings": headings,
            "texts": texts,
            "buttons": buttons,
            "prices": prices,
            "primary_price": self._representative_price(prices),
            "checkbox_states": extract_checkbox_states(page),
            "grounded": grounded,
        }

    def _scenario_action_plan(self, scenario: str, persona: str) -> list[dict]:
        plans = {
            "cookie_consent": {
                "privacy_sensitive": [
                    {
                        "type": "click",
                        "keywords": ["reject", "decline", "necessary", "essential"],
                        "label": "consent_decline",
                    },
                    {"type": "click", "keywords": ["settings", "preferences"], "label": "consent_settings"},
                ],
                "cost_sensitive": [
                    {"type": "click", "keywords": ["accept", "allow", "agree"], "label": "consent_accept"},
                    {"type": "click", "keywords": ["continue"], "label": "consent_continue"},
                ],
                "exit_intent": [
                    {"type": "click", "keywords": ["settings", "preferences"], "label": "consent_settings"},
                    {"type": "click", "keywords": ["dismiss", "close", "continue"], "label": "consent_dismiss"},
                ],
            },
            "checkout_flow": {
                "privacy_sensitive": [
                    {
                        "type": "click",
                        "keywords": ["reject", "decline", "necessary", "essential"],
                        "label": "checkout_privacy_guard",
                    },
                ],
                "cost_sensitive": [
                    {"type": "click", "keywords": ["reserve", "book", "select"], "label": "reserve_step"},
                ],
                "exit_intent": [
                    {"type": "click", "keywords": ["reserve", "book", "select"], "label": "reserve_step"},
                    {"type": "click", "keywords": ["details", "policies", "cancellation"], "label": "exit_review"},
                ],
            },
            "cancellation_flow": {
                "privacy_sensitive": [
                    {"type": "click", "keywords": ["manage", "account", "support"], "label": "account_entry"},
                    {"type": "click", "keywords": ["cancel", "unsubscribe"], "label": "cancel_entry"},
                ],
                "cost_sensitive": [
                    {"type": "click", "keywords": ["billing", "manage", "help"], "label": "billing_entry"},
                    {"type": "click", "keywords": ["cancel", "unsubscribe"], "label": "cancel_entry"},
                ],
                "exit_intent": [
                    {"type": "click", "keywords": ["cancel", "unsubscribe", "manage"], "label": "cancel_entry"},
                    {"type": "click", "keywords": ["pause", "keep", "stay"], "label": "retention_state"},
                ],
            },
        }
        return plans.get(scenario, {}).get(persona, [])

    def _state_type(
        self, page, *, scenario: str, label: str, headings: list[str], texts: list[str], buttons: list[str]
    ) -> str:
        if scenario != "checkout_flow":
            return label
        combined = " ".join(headings + texts + buttons).lower()
        if label == "offer_selection":
            return "offer"
        if label in {"reserve_state", "availability_panel"}:
            return "reserve"
        if label == "policy_review":
            return "policy"
        if "/hotel/" in page.url:
            return "detail"
        if "/city/" in page.url or "searchresults.html" in page.url:
            return "results"
        if any(term in combined for term in ("current price", "original price", "2 nights", "deal")):
            return "offer"
        return "landing"

    @staticmethod
    def _state_is_grounded(
        scenario: str,
        *,
        label: str,
        page_url: str,
        state_type: str,
        headings: list[str],
        texts: list[str],
        buttons: list[str],
        prices: list[dict],
    ) -> bool:
        combined = " ".join(texts + headings + buttons).lower()
        if scenario == "cookie_consent":
            return bool(
                buttons
                or any(term in combined for term in ("cookie", "consent", "privacy", "tracking", "accept", "reject"))
            )
        if scenario == "checkout_flow":
            if label == "initial" or state_type == "landing":
                return False
            if state_type == "offer":
                return bool(
                    prices
                    or any(term in combined for term in ("deal", "price", "current price", "original price", "night"))
                )
            if state_type == "results":
                return bool(
                    any(
                        term in combined
                        for term in ("hotels and places to stay", "check availability", "availability", "hotel")
                    )
                    or "/city/" in page_url
                    or "searchresults.html" in page_url
                )
            if state_type in {"detail", "reserve", "policy"}:
                return bool(
                    any(
                        term in combined
                        for term in ("reserve", "availability", "room", "charges may apply", "damage deposit", "policy")
                    )
                )
            return False
        if scenario == "cancellation_flow":
            return label != "initial" and bool(
                buttons
                or any(term in combined for term in ("cancel", "unsubscribe", "manage", "pause", "billing", "support"))
            )
        return False

    @staticmethod
    def _price_is_scenario_grounded(
        scenario: str, price_point: dict, texts: list[str], headings: list[str], buttons: list[str]
    ) -> bool:
        if scenario != "checkout_flow":
            return False
        context = " ".join(texts + headings + buttons + [str(price_point.get("label", ""))]).lower()
        return any(
            term in context
            for term in (
                "price",
                "current price",
                "original price",
                "tax",
                "fee",
                "night",
                "reserve",
                "room",
                "deal",
                "availability",
                "book",
                "charges may apply",
            )
        )

    def _merge_unique_from_states(self, states: list[dict], key: str, limit: int) -> list[str]:
        values: list[str] = []
        seen: set[str] = set()
        for state in states:
            for item in state.get(key, []):
                if not item or item in seen:
                    continue
                seen.add(item)
                values.append(item)
                if len(values) >= limit:
                    return values
        return values

    @staticmethod
    def _merge_checkbox_states(states: list[dict]) -> dict[str, bool]:
        merged: dict[str, bool] = {}
        for state in states:
            merged.update(state.get("checkbox_states", {}))
        return merged

    def _scenario_price_points(self, states: list[dict]) -> list[dict]:
        if len(states) < 2:
            return []
        selected_points: list[dict] = []
        seen_states: set[str] = set()
        eligible_labels = {"detail_page", "availability_panel", "reserve_state", "policy_review", "final"}
        for state in states:
            state_label = state.get("label", "")
            state_type = state.get("state_type", "")
            primary_price = state.get("primary_price")
            if not primary_price or state_label in seen_states:
                continue
            if state_type not in {"offer", "results", "detail", "reserve"}:
                continue
            if state_label not in eligible_labels:
                continue
            seen_states.add(state_label)
            selected_points.append({**primary_price, "state_label": state_label, "page_url": state.get("page_url", "")})
        if len(selected_points) < 2:
            return []
        unique_values = {float(item.get("value", 0)) for item in selected_points}
        unique_states = {item.get("state_label") for item in selected_points}
        return selected_points if len(unique_values) >= 2 and len(unique_states) >= 2 else []

    def _scenario_friction(
        self,
        *,
        scenario: str,
        states: list[dict],
        interacted_controls: list[str],
        text_snippets: list[str],
        button_labels: list[str],
        headings: list[str],
    ) -> list[str]:
        indicators: list[str] = []
        if scenario == "checkout_flow":
            if len(interacted_controls) >= 2:
                indicators.append("Multiple commerce steps observed")
            if any(
                term in " ".join(text_snippets + headings).lower()
                for term in ("charges may apply", "damage deposit", "availability")
            ):
                indicators.append("Checkout details surfaced deeper in the journey")
        elif scenario == "cancellation_flow":
            indicators.extend(guess_friction(text_snippets, button_labels, headings))
            if any("support" in control.lower() for control in interacted_controls):
                indicators.append("Support detour likely required")
        elif scenario == "cookie_consent":
            if any(
                "settings" in control.lower() or "preferences" in control.lower() for control in interacted_controls
            ):
                indicators.append("Preference layer required before decision")
        deduped: list[str] = []
        for item in indicators:
            if item not in deduped:
                deduped.append(item)
        return deduped

    @staticmethod
    def _observed_price_delta(price_points: list[dict]) -> float:
        if len(price_points) < 2:
            return 0.0
        values = [float(item["value"]) for item in price_points]
        return round(values[-1] - values[0], 2)

    def _append_checkout_offer_state(self, page, offer: dict, state_snapshots: list[dict]) -> None:
        offer_prices = extract_prices_from_text(offer["text"], limit=4)
        offer_state = {
            "label": "offer_selection",
            "state_type": "offer",
            "page_title": extract_page_title(page),
            "page_url": page.url,
            "headings": [],
            "texts": [offer["text"][:240]],
            "buttons": [offer["text"][:120]],
            "prices": offer_prices,
            "primary_price": self._representative_price(offer_prices),
            "checkbox_states": {},
            "grounded": True,
        }
        state_snapshots.append(offer_state)

    def _append_checkout_hotel_state(self, page, hotel: dict, state_snapshots: list[dict]) -> None:
        hotel_state = {
            "label": "detail_selection",
            "state_type": "detail",
            "page_title": extract_page_title(page),
            "page_url": hotel["href"],
            "headings": [],
            "texts": [hotel["text"][:240]],
            "buttons": [hotel["text"][:120]],
            "prices": [],
            "primary_price": None,
            "checkbox_states": {},
            "grounded": True,
        }
        state_snapshots.append(hotel_state)

    def _choose_checkout_offer(self, page, persona: str) -> dict | None:
        candidates = self._extract_checkout_candidates(page)
        if not candidates:
            return None
        ranked = sorted(candidates, key=lambda item: self._checkout_offer_score(item, persona), reverse=True)
        return ranked[0]

    def _extract_checkout_candidates(self, page) -> list[dict]:
        candidates: list[dict] = []
        locator = page.locator("a[href]")
        total = min(locator.count(), 160)
        for index in range(total):
            element = locator.nth(index)
            try:
                if not element.is_visible():
                    continue
                text = self._element_label(element)
                href = element.get_attribute("href") or ""
                if not text or not href:
                    continue
                absolute_href = urljoin(page.url, href)
                lower_href = absolute_href.lower()
                lower_text = text.lower()
                if "searchresults.html" in lower_href and "dest_type=hotel" in lower_href:
                    kind = "hotel_offer"
                elif "searchresults.html" in lower_href and "dest_type=city" in lower_href:
                    kind = "destination"
                elif "/hotel/" in lower_href:
                    kind = "hotel_detail"
                else:
                    continue
                prices = extract_prices_from_text(text, limit=4)
                current_price = prices[-1]["value"] if prices else None
                discount = 0.0
                if len(prices) >= 2:
                    discount = max(0.0, float(prices[0]["value"]) - float(prices[-1]["value"]))
                candidates.append(
                    {
                        "kind": kind,
                        "text": text,
                        "href": absolute_href,
                        "current_price": current_price,
                        "discount": discount,
                        "contains_deal": "deal" in lower_text or "current price" in lower_text,
                    }
                )
            except Exception:
                continue
        return candidates

    def _checkout_offer_score(self, candidate: dict, persona: str) -> float:
        text = candidate["text"].lower()
        kind = candidate["kind"]
        current_price = float(candidate["current_price"] or 9999.0)
        discount = float(candidate["discount"] or 0.0)
        score = 0.0
        if persona == "privacy_sensitive":
            if kind == "destination":
                score += 80
            if kind == "hotel_offer":
                score += 20
            if "deal" in text or "only" in text:
                score -= 10
            if "pay at the property" in text or "free cancellation" in text:
                score += 12
        elif persona == "cost_sensitive":
            if kind == "hotel_offer":
                score += 80
            score += max(0.0, 600.0 - current_price) / 10
            score += discount / 5
            if candidate["contains_deal"]:
                score += 10
        else:
            if kind in {"hotel_offer", "hotel_detail"}:
                score += 70
            if "cancellation" in text or "policy" in text:
                score += 15
            if candidate["contains_deal"]:
                score += 8
            score += discount / 8
        return score

    def _choose_hotel_detail_link(self, page, persona: str) -> dict | None:
        locator = page.locator("a[href*='/hotel/']")
        candidates: list[dict] = []
        total = min(locator.count(), 80)
        excluded_labels = {"hotels", "apartments", "resorts", "villas", "cabins", "cottages"}
        for index in range(total):
            element = locator.nth(index)
            try:
                if not element.is_visible():
                    continue
                text = self._element_label(element)
                href = element.get_attribute("href") or ""
                if not text or not href:
                    continue
                absolute_href = urljoin(page.url, href)
                lower_text = text.lower()
                if lower_text in excluded_labels or absolute_href.endswith("/hotel/index.html"):
                    continue
                score = 0.0
                if persona == "exit_intent" and ("suite" in lower_text or "downtown" in lower_text):
                    score += 6
                if persona == "privacy_sensitive" and "airport" in lower_text:
                    score -= 4
                if "hotel in" in lower_text or len(text.split()) >= 3:
                    score += 4
                candidates.append({"text": text, "href": absolute_href, "score": score})
            except Exception:
                continue
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: item["score"], reverse=True)[0]

    def _checkout_follow_up(self, page, persona: str) -> list[dict]:
        if "/hotel/" not in page.url:
            return []
        if persona == "privacy_sensitive":
            return [
                {"keywords": ["see availability", "availability"], "label": "availability_panel"},
            ]
        if persona == "cost_sensitive":
            return [
                {"keywords": ["reserve", "see availability", "availability"], "label": "reserve_state"},
            ]
        return [
            {"keywords": ["reserve", "see availability", "availability"], "label": "reserve_state"},
            {
                "keywords": ["house rules", "policies", "policy", "cancellation"],
                "label": "policy_review",
                "selector": "button, a, [role='button'], summary",
            },
        ]

    @staticmethod
    def _navigate_to_href(page, href: str) -> bool:
        if not href:
            return False
        try:
            page.goto(href, wait_until="domcontentloaded", timeout=25_000)
            return True
        except Exception:
            return False

    @staticmethod
    def _representative_price(prices: list[dict]) -> dict | None:
        preferred_terms = ("current price", "price $", "from $", "total", "you'll pay", "pay")
        for price in prices:
            label = str(price.get("label", "")).lower()
            if any(term in label for term in preferred_terms):
                return price
        return None

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
