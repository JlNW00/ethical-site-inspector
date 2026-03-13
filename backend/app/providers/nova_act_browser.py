"""
Nova Act Browser Provider - AI-driven browser automation for dark pattern detection.

Implements BrowserAuditProvider ABC using Amazon Nova Act SDK.
Uses act() for navigation and act_get() with Pydantic schemas for structured extraction.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, ClassVar
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.core.taxonomy import (
    AUDIT_SCENARIOS,
    PERSONA_DEFINITIONS,
    PersonaType,
    ScenarioType,
)
from app.providers.browser import BrowserAuditProvider, ProgressCallback
from app.providers.storage import StorageProvider
from app.schemas.runtime import BrowserRunResult, JourneyObservation, ObservationEvidence

logger = logging.getLogger(__name__)

# Try to import Nova Act, but allow it to fail gracefully
try:
    from nova_act import BOOL_SCHEMA, STRING_SCHEMA, NovaAct

    NOVA_ACT_AVAILABLE = True
except ImportError:
    NOVA_ACT_AVAILABLE = False
    NovaAct = None  # type: ignore[misc,assignment]
    BOOL_SCHEMA = {"type": "boolean"}
    STRING_SCHEMA = {"type": "string"}


# =============================================================================
# Pydantic Schemas for Nova Act Structured Extraction
# =============================================================================


class CookieConsentObservation(BaseModel):
    """Structured observation for cookie consent scenario."""

    banner_present: bool = Field(description="Whether a cookie consent banner is visible")
    accept_button_text: str = Field(description="Text on the accept/all cookies button")
    reject_button_text: str | None = Field(description="Text on the reject/decline button, if present")
    reject_button_visible: bool = Field(description="Whether reject option is immediately visible")
    accept_clicks_required: int = Field(description="Number of clicks to accept cookies")
    reject_clicks_required: int = Field(description="Number of clicks to reject/decline cookies")
    asymmetry_detected: bool = Field(description="Whether accept is easier than reject")
    deceptive_language: list[str] = Field(default_factory=list, description="List of manipulative phrases found")
    pre_selected_options: list[str] = Field(default_factory=list, description="List of pre-selected tracking options")
    has_essential_only_option: bool = Field(description="Whether 'essential only' or 'necessary only' option exists")


class CheckoutObservation(BaseModel):
    """Structured observation for checkout flow scenario."""

    page_reached: bool = Field(description="Whether a checkout/review page was reached")
    prices_seen: list[dict[str, Any]] = Field(default_factory=list, description="List of prices observed with labels")
    hidden_fees: list[str] = Field(default_factory=list, description="List of unexpected fees found")
    price_delta: float = Field(default=0.0, description="Difference between initial and final price")
    urgency_tactics: list[str] = Field(default_factory=list, description="Urgency language like 'only X left'")
    pre_selected_addons: list[str] = Field(default_factory=list, description="Add-ons that were pre-selected")
    required_steps: int = Field(default=0, description="Number of steps to complete checkout")
    unexpected_obstacles: list[str] = Field(default_factory=list, description="Unexpected barriers encountered")


class SubscriptionCancellationObservation(BaseModel):
    """Structured observation for subscription cancellation scenario."""

    cancellation_flow_found: bool = Field(description="Whether a cancellation flow was found")
    clicks_to_cancel: int = Field(default=0, description="Number of clicks to reach cancellation")
    detours_encountered: list[str] = Field(
        default_factory=list, description="Retention offers, support chat prompts, etc."
    )
    confirmshaming_detected: bool = Field(description="Whether guilt-tripping language was used")
    confirmshaming_phrases: list[str] = Field(default_factory=list, description="Specific guilt-tripping phrases")
    pause_offered: bool = Field(description="Whether 'pause instead of cancel' was offered")
    alternative_options: list[str] = Field(default_factory=list, description="Alternative options presented")
    final_cancel_difficult: bool = Field(description="Whether final cancellation was difficult to complete")


class AccountDeletionObservation(BaseModel):
    """Structured observation for account deletion scenario."""

    deletion_flow_found: bool = Field(description="Whether account deletion flow was found")
    clicks_to_delete: int = Field(default=0, description="Number of clicks to reach deletion")
    obstacles_encountered: list[str] = Field(default_factory=list, description="Steps that obstruct deletion")
    requires_contact_support: bool = Field(description="Whether deletion requires contacting support")
    confirmation_required: bool = Field(description="Whether extra confirmation steps are needed")
    data_retention_warning: str | None = Field(description="Warning about data retention, if any")
    alternatives_offered: list[str] = Field(default_factory=list, description="Alternatives to deletion offered")
    flow_completed: bool = Field(description="Whether deletion flow could be completed to final step")


class NewsletterSignupObservation(BaseModel):
    """Structured observation for newsletter signup scenario."""

    signup_form_found: bool = Field(description="Whether newsletter signup form was found")
    pre_checked_boxes: list[str] = Field(default_factory=list, description="Pre-checked consent boxes")
    confusing_opt_in: bool = Field(description="Whether opt-in language is confusing/unclear")
    confusing_language_examples: list[str] = Field(default_factory=list, description="Examples of confusing language")
    dark_enrollment_detected: bool = Field(description="Whether sneaky enrollment patterns detected")
    bundled_with_other_services: bool = Field(description="Whether newsletter bundled with other services")
    unsubscription_difficulty: str | None = Field(description="How difficult it appears to unsubscribe later")
    consent_separated: bool = Field(description="Whether marketing consent is clearly separated from other consent")


class PricingComparisonObservation(BaseModel):
    """Structured observation for pricing comparison scenario."""

    prices_found: list[dict[str, Any]] = Field(default_factory=list, description="Prices found with context")
    price_variations_detected: bool = Field(description="Whether different prices shown for same item")
    bait_and_switch_suspected: bool = Field(description="Whether bait-and-switch pattern detected")
    persona_specific_offers: list[str] = Field(default_factory=list, description="Offers that appear persona-specific")
    hidden_discounts: list[str] = Field(default_factory=list, description="Discounts not immediately visible")
    loyalty_program_pressure: bool = Field(description="Whether loyalty program pushed to access prices")
    dynamic_pricing_indicators: list[str] = Field(
        default_factory=list, description="Signs of dynamic/discriminatory pricing"
    )


class ScreenshotEvidence(BaseModel):
    """Evidence captured at a journey step."""

    step_name: str = Field(description="Name of the journey step")
    screenshot_bytes: bytes = Field(description="PNG screenshot data")
    url_at_step: str = Field(description="URL at this step")
    action_taken: str | None = Field(description="Action taken to reach this state")


# =============================================================================
# Nova Act Audit Provider
# =============================================================================


class NovaActAuditProvider(BrowserAuditProvider):
    """
    AI-driven browser audit provider using Amazon Nova Act SDK.

    Uses natural language prompts to navigate sites and Pydantic schemas
    for structured evidence extraction. Supports parallel persona testing
    via ThreadPoolExecutor.
    """

    # Default timeout per scenario (in seconds)
    DEFAULT_SCENARIO_TIMEOUT: int = 120

    # Per-scenario timeout overrides (can be customized)
    SCENARIO_TIMEOUTS: ClassVar[dict[str, int]] = {
        "cookie_consent": 120,
        "checkout_flow": 180,  # Checkout can take longer
        "subscription_cancellation": 120,
        "account_deletion": 120,
        "newsletter_signup": 90,  # Usually quicker
        "pricing_comparison": 120,
    }

    def __init__(
        self,
        storage: StorageProvider,
        headless: bool = True,
        tty: bool = False,
        timeout: int = 120,
        max_workers: int = 3,
        scenario_timeouts: dict[str, int] | None = None,
    ):
        self.storage = storage
        self.headless = headless
        self.tty = tty
        self.timeout = timeout
        self.max_workers = max_workers
        # Allow custom scenario timeouts to override defaults
        if scenario_timeouts:
            self.scenario_timeouts = {**self.SCENARIO_TIMEOUTS, **scenario_timeouts}
        else:
            self.scenario_timeouts = self.SCENARIO_TIMEOUTS.copy()
        if not NOVA_ACT_AVAILABLE:
            logger.warning("Nova Act SDK not available. Provider will run in degraded mode.")

    def _get_scenario_timeout(self, scenario: str) -> int:
        """Get the timeout for a specific scenario."""
        return self.scenario_timeouts.get(scenario, self.DEFAULT_SCENARIO_TIMEOUT)

    def _ensure_nova_act(self) -> Any:
        """Ensure Nova Act SDK is available."""
        if not NOVA_ACT_AVAILABLE or NovaAct is None:
            raise RuntimeError("Nova Act SDK is required but not installed. Run: pip install nova-act")
        return type(
            "NovaActModule",
            (),
            {
                "NovaAct": NovaAct,
                "BOOL_SCHEMA": BOOL_SCHEMA,
                "STRING_SCHEMA": STRING_SCHEMA,
            },
        )()

    def run_audit(
        self,
        audit_id: str,
        target_url: str,
        scenarios: list[str],
        personas: list[str],
        progress: ProgressCallback,
    ) -> BrowserRunResult:
        """
        Run audit scenarios against target URL using Nova Act.

        Args:
            audit_id: Unique identifier for this audit
            target_url: Starting URL for the audit
            scenarios: List of scenario types to run
            personas: List of persona types to test
            progress: Callback for reporting progress

        Returns:
            BrowserRunResult with all observations and summary
        """
        nova_act = self._ensure_nova_act()
        observations: list[JourneyObservation] = []

        # Validate scenarios against taxonomy
        valid_scenarios = [s for s in scenarios if s in AUDIT_SCENARIOS]
        valid_personas = [p for p in personas if p in PERSONA_DEFINITIONS]

        if not valid_scenarios:
            logger.warning(f"No valid scenarios provided: {scenarios}")
            return self._empty_result(target_url, scenarios, personas, "No valid scenarios")

        if not valid_personas:
            logger.warning(f"No valid personas provided: {personas}")
            return self._empty_result(target_url, scenarios, personas, "No valid personas")

        total_combinations = len(valid_scenarios) * len(valid_personas)
        completed = 0
        failed_scenarios: list[str] = []
        successful_observations: list[JourneyObservation] = []

        for scenario in valid_scenarios:
            scenario_observations = self._run_scenario_with_personas(
                audit_id=audit_id,
                target_url=target_url,
                scenario=scenario,  # type: ignore[arg-type]
                personas=valid_personas,  # type: ignore[arg-type]
                nova_act=nova_act,
                progress=progress,
                base_progress=int((completed / total_combinations) * 50),
            )

            # Check if this scenario had any successful observations (not error observations)
            scenario_success_count = sum(1 for obs in scenario_observations if not obs.evidence.metadata.get("error"))
            scenario_failed_count = len(scenario_observations) - scenario_success_count

            if scenario_success_count == 0 and scenario_failed_count > 0:
                # All personas for this scenario failed
                failed_scenarios.append(scenario)
                logger.error(f"Scenario {scenario} failed for all {len(valid_personas)} personas")
            else:
                successful_observations.extend(scenario_observations)

            observations.extend(scenario_observations)
            completed += len(valid_personas)

        # Determine overall success based on partial completion rules:
        # - If ALL scenarios fail -> mark as failed
        # - If some succeed -> mark as completed (partial results)
        all_scenarios_failed = len(failed_scenarios) == len(valid_scenarios)
        some_scenarios_succeeded = len(failed_scenarios) < len(valid_scenarios)

        summary: dict[str, Any] = {
            "mode": "nova_act",
            "evidence_origin": "nova_act",
            "evidence_origin_label": "Nova Act AI-driven browser automation",
            "observation_count": len(observations),
            "scenarios": valid_scenarios,
            "personas": valid_personas,
            "failed_scenarios": failed_scenarios,
            "successful_observation_count": len(successful_observations),
        }

        if all_scenarios_failed:
            summary["status"] = "failed"
            summary["error"] = f"All scenarios failed: {', '.join(failed_scenarios)}"
            logger.error(f"Audit {audit_id}: All scenarios failed ({', '.join(failed_scenarios)})")
        elif some_scenarios_succeeded and failed_scenarios:
            summary["status"] = "completed"
            summary["partial_failure"] = True
            summary["warning"] = f"Partial completion: {len(failed_scenarios)} scenario(s) failed"
            logger.warning(
                f"Audit {audit_id}: Partial completion - {len(failed_scenarios)}/{len(valid_scenarios)} scenarios failed"
            )
        else:
            summary["status"] = "completed"

        return BrowserRunResult(
            observations=observations,
            summary=summary,
        )

    def _run_scenario_with_personas(
        self,
        audit_id: str,
        target_url: str,
        scenario: ScenarioType,
        personas: list[PersonaType],
        nova_act: Any,
        progress: ProgressCallback,
        base_progress: int,
    ) -> list[JourneyObservation]:
        """Run a single scenario across multiple personas in parallel with per-scenario timeouts."""
        observations: list[JourneyObservation] = []
        total = len(personas)
        scenario_timeout = self._get_scenario_timeout(scenario)
        failed_personas: list[str] = []

        # Use ThreadPoolExecutor for parallel persona testing
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(personas))) as executor:
            future_to_persona = {
                executor.submit(
                    self._run_single_persona,
                    audit_id,
                    target_url,
                    scenario,
                    persona,
                    nova_act,
                ): persona
                for persona in personas
            }

            for index, future in enumerate(as_completed(future_to_persona), start=1):
                persona = future_to_persona[future]
                try:
                    progress(
                        "browser",
                        f"Running Nova Act {scenario.replace('_', ' ')} for {persona.replace('_', ' ')}",
                        base_progress + int((index / total) * 40),
                        "running",
                        {"scenario": scenario, "persona": persona},
                    )

                    # Use scenario-specific timeout
                    observation = future.result(timeout=scenario_timeout)
                    observations.append(observation)

                    progress(
                        "evidence",
                        f"Captured Nova Act evidence for {scenario.replace('_', ' ')} / {persona.replace('_', ' ')}",
                        base_progress + int((index / total) * 50),
                        "running",
                        {
                            "scenario": scenario,
                            "persona": persona,
                            "image_url": next(iter(observation.evidence.screenshot_urls), None),
                            "buttons": observation.evidence.button_labels[:3],
                        },
                    )
                except TimeoutError as te:
                    logger.error(f"Timeout in {scenario}/{persona} after {scenario_timeout}s: {te}")
                    failed_personas.append(persona)
                    # Create a fallback observation with timeout info
                    observations.append(
                        self._error_observation(
                            target_url, scenario, persona, f"Scenario timed out after {scenario_timeout} seconds"
                        )
                    )
                    progress(
                        "browser",
                        f"Timeout for {scenario.replace('_', ' ')} / {persona.replace('_', ' ')} - skipping",
                        base_progress + int((index / total) * 50),
                        "warning",
                        {"scenario": scenario, "persona": persona, "timeout_seconds": scenario_timeout},
                    )
                except Exception as e:
                    logger.error(f"Error in {scenario}/{persona}: {e}")
                    failed_personas.append(persona)
                    # Create a fallback observation with error info
                    observations.append(self._error_observation(target_url, scenario, persona, str(e)))

        # Log summary of failures for this scenario
        if failed_personas:
            logger.warning(
                f"Scenario {scenario}: {len(failed_personas)}/{total} personas failed ({', '.join(failed_personas)})"
            )

        return observations

    def _run_single_persona(
        self,
        audit_id: str,
        target_url: str,
        scenario: ScenarioType,
        persona: PersonaType,
        nova_act: Any,
    ) -> JourneyObservation:
        """Run a single scenario for a single persona using Nova Act."""
        scenario_method = getattr(self, f"_run_{scenario}_scenario", None)
        if scenario_method is None:
            raise ValueError(f"Unknown scenario: {scenario}")

        return scenario_method(audit_id, target_url, persona, nova_act)

    def _run_cookie_consent_scenario(
        self,
        audit_id: str,
        target_url: str,
        persona: PersonaType,
        nova_act: Any,
    ) -> JourneyObservation:
        """Run cookie consent scenario with Nova Act."""
        # NovaAct is imported at module level
        nova_act_class = NovaAct  # Use module-level import
        if nova_act_class is None:
            raise RuntimeError("Nova Act SDK not available")

        activity_log: list[str] = []
        state_snapshots: list[dict] = []
        screenshot_paths: list[str] = []
        screenshot_urls: list[str] = []
        interacted_controls: list[str] = []

        with NovaAct(
            starting_page=target_url,
            headless=self.headless,
            tty=self.tty,
            go_to_url_timeout=self.timeout,
        ) as nova:
            # Initial screenshot
            self._capture_screenshot(
                audit_id, nova, "cookie_consent", persona, "initial", screenshot_paths, screenshot_urls
            )
            activity_log.append(f"Loaded {target_url}")
            state_snapshots.append({"url": target_url, "step": "initial", "action": "page_load"})

            # Check for cookie banner using act_get with schema
            bool_schema = nova_act.BOOL_SCHEMA if nova_act else {"type": "boolean"}
            result = nova.act_get(
                "Is there a cookie consent banner, popup, or dialog visible? Look for terms like 'cookies', 'consent', 'privacy', 'accept', 'reject'.",
                schema=bool_schema,
            )
            has_banner = result.parsed_response if hasattr(result, "parsed_response") else False

            if not has_banner:
                activity_log.append("No cookie banner detected")
                # Try scrolling to find it
                nova.act("Scroll down to look for a cookie consent banner or footer notice")
                result = nova.act_get(
                    "Is there now a cookie consent banner, popup, or dialog visible?",
                    schema=nova_act.BOOL_SCHEMA,
                )
                has_banner = result.parsed_response if hasattr(result, "parsed_response") else False

            if has_banner:
                activity_log.append("Cookie banner detected")
                self._capture_screenshot(
                    audit_id, nova, "cookie_consent", persona, "banner_found", screenshot_paths, screenshot_urls
                )

                # Extract structured observations
                observation_result = nova.act_get(
                    "Analyze the cookie consent banner. What are the button labels for accepting vs rejecting? "
                    "Is the reject option hidden or less prominent? Are there pre-selected checkboxes? "
                    "What manipulative language is used?",
                    schema=CookieConsentObservation.model_json_schema(),
                )

                try:
                    consent_data = CookieConsentObservation.model_validate(
                        observation_result.parsed_response if hasattr(observation_result, "parsed_response") else {}
                    )
                except Exception:
                    consent_data = CookieConsentObservation(
                        banner_present=True,
                        accept_button_text="",
                        reject_button_text=None,
                        reject_button_visible=False,
                        accept_clicks_required=0,
                        reject_clicks_required=0,
                        asymmetry_detected=False,
                        has_essential_only_option=False,
                    )

                # Try to interact based on persona
                if persona == "privacy_sensitive":
                    nova.act(
                        "Try to reject all cookies or select only necessary/essential cookies. "
                        "Click through any settings/preferences if needed to find the minimal option.",
                        max_steps=15,
                    )
                    interacted_controls.append("reject_all_attempt")
                    activity_log.append("Attempted to reject cookies (privacy-sensitive persona)")
                elif persona == "cost_sensitive":
                    nova.act(
                        "Look for any discount or savings tied to accepting cookies. "
                        "If found, note it. Then try to accept cookies if it's the only way to see prices.",
                        max_steps=10,
                    )
                    interacted_controls.append("price_check_attempt")
                    activity_log.append("Checked for price-linked cookie acceptance")
                else:  # exit_intent
                    nova.act(
                        "Try to dismiss the cookie banner without making a choice, or find a 'manage preferences' option.",
                        max_steps=8,
                    )
                    interacted_controls.append("dismiss_or_manage_attempt")
                    activity_log.append("Attempted to dismiss or manage cookie preferences")

                # Post-interaction screenshot
                self._capture_screenshot(
                    audit_id, nova, "cookie_consent", persona, "after_interaction", screenshot_paths, screenshot_urls
                )
                state_snapshots.append(
                    {
                        "url": nova.page.url if hasattr(nova, "page") else target_url,
                        "step": "after_interaction",
                        "action": interacted_controls[-1] if interacted_controls else "none",
                    }
                )

                # Re-extract observations after interaction
                post_result = nova.act_get(
                    "After attempting to interact with the cookie banner, describe what happened. "
                    "How many clicks were needed? Was it easy or difficult? Any deceptive patterns observed?",
                    schema=CookieConsentObservation.model_json_schema(),
                )
                try:
                    post_consent_data = CookieConsentObservation.model_validate(
                        post_result.parsed_response if hasattr(post_result, "parsed_response") else {}
                    )
                    consent_data = post_consent_data  # Use post-interaction data
                except Exception:
                    pass

                # Build observation evidence
                evidence = ObservationEvidence(
                    screenshot_urls=screenshot_urls,
                    screenshot_paths=screenshot_paths,
                    button_labels=[consent_data.accept_button_text, consent_data.reject_button_text]
                    if consent_data.reject_button_text
                    else [consent_data.accept_button_text],
                    checkbox_states=dict.fromkeys(consent_data.pre_selected_options, True),
                    price_points=[],
                    text_snippets=consent_data.deceptive_language,
                    headings=["Cookie Consent"] if consent_data.banner_present else [],
                    page_title="Cookie Consent Analysis",
                    dom_excerpt=f"Banner present: {consent_data.banner_present}, Asymmetry: {consent_data.asymmetry_detected}",
                    step_count=len(interacted_controls) + 1,
                    friction_indicators=["Preference layer required"]
                    if consent_data.reject_clicks_required > consent_data.accept_clicks_required
                    else [],
                    activity_log=activity_log,
                    metadata={
                        "source": "nova_act",
                        "source_label": "Nova Act AI-driven browser automation",
                        "site_host": urlparse(target_url).netloc,
                        "page_url": nova.page.url if hasattr(nova, "page") else target_url,
                        "interacted_controls": interacted_controls,
                        "scenario_state_found": consent_data.banner_present,
                        "action_count": len(interacted_controls),
                        "observed_price_delta": 0.0,
                        "state_snapshots": state_snapshots,
                    },
                )

                return JourneyObservation(
                    scenario="cookie_consent",
                    persona=persona,
                    target_url=target_url,
                    final_url=nova.page.url if hasattr(nova, "page") else target_url,
                    evidence=evidence,
                )

            else:
                # No banner found
                activity_log.append("No cookie consent banner found on page")
                evidence = ObservationEvidence(
                    screenshot_urls=screenshot_urls,
                    screenshot_paths=screenshot_paths,
                    button_labels=[],
                    checkbox_states={},
                    price_points=[],
                    text_snippets=["No cookie banner detected"],
                    headings=[],
                    page_title="No Cookie Consent",
                    dom_excerpt="No cookie banner detected",
                    step_count=1,
                    friction_indicators=[],
                    activity_log=activity_log,
                    metadata={
                        "source": "nova_act",
                        "source_label": "Nova Act AI-driven browser automation",
                        "site_host": urlparse(target_url).netloc,
                        "page_url": nova.page.url if hasattr(nova, "page") else target_url,
                        "interacted_controls": [],
                        "scenario_state_found": False,
                        "action_count": 0,
                        "observed_price_delta": 0.0,
                        "state_snapshots": state_snapshots,
                    },
                )

                return JourneyObservation(
                    scenario="cookie_consent",
                    persona=persona,
                    target_url=target_url,
                    final_url=nova.page.url if hasattr(nova, "page") else target_url,
                    evidence=evidence,
                )

    def _run_checkout_flow_scenario(
        self,
        audit_id: str,
        target_url: str,
        persona: PersonaType,
        nova_act: Any,
    ) -> JourneyObservation:
        """Run checkout flow scenario with Nova Act."""

        activity_log: list[str] = []
        state_snapshots: list[dict] = []
        screenshot_paths: list[str] = []
        screenshot_urls: list[str] = []
        interacted_controls: list[str] = []

        with NovaAct(
            starting_page=target_url,
            headless=self.headless,
            tty=self.tty,
            go_to_url_timeout=self.timeout,
        ) as nova:
            # Initial state
            self._capture_screenshot(
                audit_id, nova, "checkout_flow", persona, "initial", screenshot_paths, screenshot_urls
            )
            activity_log.append(f"Loaded {target_url}")
            state_snapshots.append({"url": target_url, "step": "initial", "action": "page_load"})

            # Navigate to find products/offers based on persona
            if persona == "cost_sensitive":
                nova.act(
                    "Look for deals, discounts, or lowest-priced items. Click on a product or offer that shows a price.",
                    max_steps=8,
                )
                interacted_controls.append("select_offer")
                activity_log.append("Selected an offer/product (cost-sensitive persona)")
            elif persona == "privacy_sensitive":
                nova.act(
                    "Look for products but avoid anything requiring account creation. Try to find 'guest checkout' or 'pay at property' options.",
                    max_steps=8,
                )
                interacted_controls.append("privacy_aware_navigation")
                activity_log.append("Navigated with privacy preferences")
            else:  # exit_intent
                nova.act(
                    "Browse products but act hesitant. Look at details without committing to purchase.", max_steps=5
                )
                interacted_controls.append("browse_hesitant")
                activity_log.append("Browsed with exit-intent behavior")

            self._capture_screenshot(
                audit_id, nova, "checkout_flow", persona, "product_selected", screenshot_paths, screenshot_urls
            )

            # Extract checkout observations
            checkout_result = nova.act_get(
                "Analyze the current checkout or product page. What prices are displayed? "
                "Are there any unexpected fees, taxes, or charges not initially shown? "
                "Is there urgency language like 'only X left' or 'limited time'? "
                "Are there pre-selected add-ons or insurance options?",
                schema=CheckoutObservation.model_json_schema(),
            )

            try:
                checkout_data = CheckoutObservation.model_validate(
                    checkout_result.parsed_response if hasattr(checkout_result, "parsed_response") else {}
                )
            except Exception:
                checkout_data = CheckoutObservation(page_reached=True)

            # Try to proceed through checkout flow
            nova.act(
                "Try to proceed toward checkout or reservation. Click buttons like 'Reserve', 'Book', 'Continue', or 'Checkout'. "
                "Navigate through the flow and stop at the final review/payment page.",
                max_steps=15,
            )
            interacted_controls.append("proceed_checkout")
            activity_log.append("Attempted to proceed through checkout flow")

            self._capture_screenshot(
                audit_id, nova, "checkout_flow", persona, "checkout_progress", screenshot_paths, screenshot_urls
            )

            # Extract final checkout observations
            final_checkout_result = nova.act_get(
                "At the current checkout/review page, extract: final price, any hidden fees, price changes from earlier, "
                "urgency tactics, and number of steps taken. Is the final price higher than initially shown?",
                schema=CheckoutObservation.model_json_schema(),
            )

            try:
                final_checkout_data = CheckoutObservation.model_validate(
                    final_checkout_result.parsed_response if hasattr(final_checkout_result, "parsed_response") else {}
                )
                checkout_data = final_checkout_data
            except Exception:
                pass

            state_snapshots.append(
                {
                    "url": nova.page.url if hasattr(nova, "page") else target_url,
                    "step": "checkout_review",
                    "action": "review_checkout",
                    "prices": checkout_data.prices_seen,
                }
            )

            # Build observation evidence
            evidence = ObservationEvidence(
                screenshot_urls=screenshot_urls,
                screenshot_paths=screenshot_paths,
                button_labels=[],
                checkbox_states=dict.fromkeys(checkout_data.pre_selected_addons, True),
                price_points=checkout_data.prices_seen,
                text_snippets=checkout_data.urgency_tactics + checkout_data.hidden_fees,
                headings=["Checkout"] if checkout_data.page_reached else [],
                page_title="Checkout Analysis",
                dom_excerpt=f"Page reached: {checkout_data.page_reached}, Price delta: {checkout_data.price_delta}",
                step_count=len(interacted_controls) + checkout_data.required_steps,
                friction_indicators=["Hidden fees detected"] if checkout_data.hidden_fees else [],
                activity_log=activity_log,
                metadata={
                    "source": "nova_act",
                    "source_label": "Nova Act AI-driven browser automation",
                    "site_host": urlparse(target_url).netloc,
                    "page_url": nova.page.url if hasattr(nova, "page") else target_url,
                    "interacted_controls": interacted_controls,
                    "scenario_state_found": checkout_data.page_reached,
                    "action_count": len(interacted_controls),
                    "observed_price_delta": checkout_data.price_delta,
                    "state_snapshots": state_snapshots,
                },
            )

            return JourneyObservation(
                scenario="checkout_flow",
                persona=persona,
                target_url=target_url,
                final_url=nova.page.url if hasattr(nova, "page") else target_url,
                evidence=evidence,
            )

    def _run_subscription_cancellation_scenario(
        self,
        audit_id: str,
        target_url: str,
        persona: PersonaType,
        nova_act: Any,
    ) -> JourneyObservation:
        """Run subscription cancellation scenario with Nova Act."""

        activity_log: list[str] = []
        state_snapshots: list[dict] = []
        screenshot_paths: list[str] = []
        screenshot_urls: list[str] = []
        interacted_controls: list[str] = []

        with NovaAct(
            starting_page=target_url,
            headless=self.headless,
            tty=self.tty,
            go_to_url_timeout=self.timeout,
        ) as nova:
            # Initial state
            self._capture_screenshot(
                audit_id, nova, "subscription_cancellation", persona, "initial", screenshot_paths, screenshot_urls
            )
            activity_log.append(f"Loaded {target_url}")
            state_snapshots.append({"url": target_url, "step": "initial", "action": "page_load"})

            # Look for account/subscription management
            nova.act(
                "Look for account settings, subscription management, billing, or plan settings. "
                "Try to navigate to where subscription cancellation would be managed. "
                "Click on relevant links like 'Account', 'Subscription', 'Billing', 'Manage Plan'.",
                max_steps=12,
            )
            interacted_controls.append("find_account_settings")
            activity_log.append("Attempted to find account/subscription settings")

            self._capture_screenshot(
                audit_id, nova, "subscription_cancellation", persona, "account_area", screenshot_paths, screenshot_urls
            )

            # Check for cancellation flow
            cancel_result = nova.act_get(
                "Is there a cancellation, unsubscribe, or 'cancel plan' option visible? "
                "Look for buttons or links mentioning 'cancel', 'unsubscribe', 'end subscription', 'close account'. "
                "Are there retention offers, support chat prompts, or alternatives offered instead?",
                schema=SubscriptionCancellationObservation.model_json_schema(),
            )

            try:
                cancel_data = SubscriptionCancellationObservation.model_validate(
                    cancel_result.parsed_response if hasattr(cancel_result, "parsed_response") else {}
                )
            except Exception:
                cancel_data = SubscriptionCancellationObservation(
                    cancellation_flow_found=False,
                    confirmshaming_detected=False,
                    pause_offered=False,
                    final_cancel_difficult=False,
                )

            # If cancellation option exists, try to navigate through it
            if cancel_data.cancellation_flow_found:
                nova.act(
                    "Click on the cancellation or unsubscribe option. Navigate through any retention screens, "
                    "confirmshaming messages, or alternative offers. Try to reach the final cancellation confirmation.",
                    max_steps=15,
                )
                interacted_controls.append("initiate_cancellation")
                activity_log.append("Initiated cancellation flow")

                self._capture_screenshot(
                    audit_id,
                    nova,
                    "subscription_cancellation",
                    persona,
                    "cancel_flow",
                    screenshot_paths,
                    screenshot_urls,
                )

                # Extract observations from cancellation flow
                flow_result = nova.act_get(
                    "Analyze the cancellation flow. How many clicks/steps to cancel? "
                    "What detours were encountered (retention offers, support prompts)? "
                    "Was there confirmshaming (guilt-tripping language)? "
                    "Was 'pause instead' offered? Could you complete the cancellation?",
                    schema=SubscriptionCancellationObservation.model_json_schema(),
                )

                try:
                    flow_data = SubscriptionCancellationObservation.model_validate(
                        flow_result.parsed_response if hasattr(flow_result, "parsed_response") else {}
                    )
                    cancel_data = flow_data
                except Exception:
                    pass

                state_snapshots.append(
                    {
                        "url": nova.page.url if hasattr(nova, "page") else target_url,
                        "step": "cancellation_attempted",
                        "action": "cancel_flow",
                        "detours": cancel_data.detours_encountered,
                    }
                )

            # Build observation evidence
            friction_indicators: list[str] = []
            if cancel_data.confirmshaming_detected:
                friction_indicators.append("Confirmshaming detected")
            if cancel_data.pause_offered:
                friction_indicators.append("Pause offered as alternative")
            if cancel_data.detours_encountered:
                friction_indicators.append("Support detour likely required")

            evidence = ObservationEvidence(
                screenshot_urls=screenshot_urls,
                screenshot_paths=screenshot_paths,
                button_labels=cancel_data.alternative_options
                + (cancel_data.confirmshaming_phrases if cancel_data.confirmshaming_detected else []),
                checkbox_states={},
                price_points=[],
                text_snippets=cancel_data.confirmshaming_phrases if cancel_data.confirmshaming_detected else [],
                headings=["Cancellation"] if cancel_data.cancellation_flow_found else [],
                page_title="Subscription Cancellation Analysis",
                dom_excerpt=f"Flow found: {cancel_data.cancellation_flow_found}, Clicks: {cancel_data.clicks_to_cancel}",
                step_count=len(interacted_controls) + cancel_data.clicks_to_cancel,
                friction_indicators=friction_indicators,
                activity_log=activity_log,
                metadata={
                    "source": "nova_act",
                    "source_label": "Nova Act AI-driven browser automation",
                    "site_host": urlparse(target_url).netloc,
                    "page_url": nova.page.url if hasattr(nova, "page") else target_url,
                    "interacted_controls": interacted_controls,
                    "scenario_state_found": cancel_data.cancellation_flow_found,
                    "action_count": len(interacted_controls),
                    "observed_price_delta": 0.0,
                    "state_snapshots": state_snapshots,
                },
            )

            return JourneyObservation(
                scenario="subscription_cancellation",
                persona=persona,
                target_url=target_url,
                final_url=nova.page.url if hasattr(nova, "page") else target_url,
                evidence=evidence,
            )

    def _run_account_deletion_scenario(
        self,
        audit_id: str,
        target_url: str,
        persona: PersonaType,
        nova_act: Any,
    ) -> JourneyObservation:
        """Run account deletion scenario with Nova Act."""

        activity_log: list[str] = []
        state_snapshots: list[dict] = []
        screenshot_paths: list[str] = []
        screenshot_urls: list[str] = []
        interacted_controls: list[str] = []

        with NovaAct(
            starting_page=target_url,
            headless=self.headless,
            tty=self.tty,
            go_to_url_timeout=self.timeout,
        ) as nova:
            # Initial state
            self._capture_screenshot(
                audit_id, nova, "account_deletion", persona, "initial", screenshot_paths, screenshot_urls
            )
            activity_log.append(f"Loaded {target_url}")
            state_snapshots.append({"url": target_url, "step": "initial", "action": "page_load"})

            # Look for account settings
            nova.act(
                "Look for account settings, profile settings, privacy settings, or data management. "
                "Try to find where account deletion would be managed. "
                "Click on links like 'Account', 'Profile', 'Settings', 'Privacy', 'Data & Privacy'.",
                max_steps=10,
            )
            interacted_controls.append("find_privacy_settings")
            activity_log.append("Attempted to find privacy/account settings")

            self._capture_screenshot(
                audit_id, nova, "account_deletion", persona, "settings_area", screenshot_paths, screenshot_urls
            )

            # Check for deletion option
            deletion_result = nova.act_get(
                "Is there an account deletion, 'delete my account', 'close account', or 'data deletion' option? "
                "Look in advanced settings or privacy sections. "
                "Are there obstacles like requiring contact support, multi-step confirmations, or warnings?",
                schema=AccountDeletionObservation.model_json_schema(),
            )

            try:
                deletion_data = AccountDeletionObservation.model_validate(
                    deletion_result.parsed_response if hasattr(deletion_result, "parsed_response") else {}
                )
            except Exception:
                deletion_data = AccountDeletionObservation(
                    deletion_flow_found=False,
                    requires_contact_support=False,
                    confirmation_required=False,
                    data_retention_warning=None,
                    flow_completed=False,
                )

            # If deletion option exists, try to navigate through it
            if deletion_data.deletion_flow_found:
                nova.act(
                    "Click on the account deletion option. Navigate through any confirmation steps, "
                    "warnings, or alternative offers. Try to reach the final deletion confirmation.",
                    max_steps=12,
                )
                interacted_controls.append("initiate_deletion")
                activity_log.append("Initiated account deletion flow")

                self._capture_screenshot(
                    audit_id, nova, "account_deletion", persona, "deletion_flow", screenshot_paths, screenshot_urls
                )

                # Extract observations from deletion flow
                flow_result = nova.act_get(
                    "Analyze the account deletion flow. How many clicks/steps? "
                    "What obstacles encountered? Is contact support required? "
                    "Are there confirmation requirements? Data retention warnings? "
                    "Could the flow be completed to final step?",
                    schema=AccountDeletionObservation.model_json_schema(),
                )

                try:
                    flow_data = AccountDeletionObservation.model_validate(
                        flow_result.parsed_response if hasattr(flow_result, "parsed_response") else {}
                    )
                    deletion_data = flow_data
                except Exception:
                    pass

                state_snapshots.append(
                    {
                        "url": nova.page.url if hasattr(nova, "page") else target_url,
                        "step": "deletion_attempted",
                        "action": "deletion_flow",
                        "obstacles": deletion_data.obstacles_encountered,
                    }
                )

            # Build observation evidence
            friction_indicators: list[str] = []
            if deletion_data.requires_contact_support:
                friction_indicators.append("Support contact required")
            if deletion_data.confirmation_required:
                friction_indicators.append("Extra confirmation steps")
            if deletion_data.obstacles_encountered:
                friction_indicators.extend(deletion_data.obstacles_encountered[:3])

            evidence = ObservationEvidence(
                screenshot_urls=screenshot_urls,
                screenshot_paths=screenshot_paths,
                button_labels=deletion_data.alternatives_offered,
                checkbox_states={},
                price_points=[],
                text_snippets=[deletion_data.data_retention_warning] if deletion_data.data_retention_warning else [],
                headings=["Account Deletion"] if deletion_data.deletion_flow_found else [],
                page_title="Account Deletion Analysis",
                dom_excerpt=f"Flow found: {deletion_data.deletion_flow_found}, Clicks: {deletion_data.clicks_to_delete}",
                step_count=len(interacted_controls) + deletion_data.clicks_to_delete,
                friction_indicators=friction_indicators,
                activity_log=activity_log,
                metadata={
                    "source": "nova_act",
                    "source_label": "Nova Act AI-driven browser automation",
                    "site_host": urlparse(target_url).netloc,
                    "page_url": nova.page.url if hasattr(nova, "page") else target_url,
                    "interacted_controls": interacted_controls,
                    "scenario_state_found": deletion_data.deletion_flow_found,
                    "action_count": len(interacted_controls),
                    "observed_price_delta": 0.0,
                    "state_snapshots": state_snapshots,
                },
            )

            return JourneyObservation(
                scenario="account_deletion",
                persona=persona,
                target_url=target_url,
                final_url=nova.page.url if hasattr(nova, "page") else target_url,
                evidence=evidence,
            )

    def _run_newsletter_signup_scenario(
        self,
        audit_id: str,
        target_url: str,
        persona: PersonaType,
        nova_act: Any,
    ) -> JourneyObservation:
        """Run newsletter signup scenario with Nova Act."""

        activity_log: list[str] = []
        state_snapshots: list[dict] = []
        screenshot_paths: list[str] = []
        screenshot_urls: list[str] = []
        interacted_controls: list[str] = []

        with NovaAct(
            starting_page=target_url,
            headless=self.headless,
            tty=self.tty,
            go_to_url_timeout=self.timeout,
        ) as nova:
            # Initial state
            self._capture_screenshot(
                audit_id, nova, "newsletter_signup", persona, "initial", screenshot_paths, screenshot_urls
            )
            activity_log.append(f"Loaded {target_url}")
            state_snapshots.append({"url": target_url, "step": "initial", "action": "page_load"})

            # Look for newsletter signup forms
            nova.act(
                "Look for newsletter signup forms, email subscription forms, or marketing consent checkboxes. "
                "Check footer, checkout pages, account creation forms, and settings. "
                "Scroll down to find any subscription elements.",
                max_steps=10,
            )
            interacted_controls.append("find_newsletter_elements")
            activity_log.append("Searched for newsletter signup elements")

            self._capture_screenshot(
                audit_id, nova, "newsletter_signup", persona, "search_complete", screenshot_paths, screenshot_urls
            )

            # Extract newsletter observations
            newsletter_result = nova.act_get(
                "Analyze any newsletter/email signup forms or consent checkboxes found. "
                "Are there pre-checked boxes? Is the opt-in language confusing? "
                "Is consent bundled with other services? How difficult does unsubscription appear? "
                "Are marketing consents clearly separated from necessary communications?",
                schema=NewsletterSignupObservation.model_json_schema(),
            )

            try:
                newsletter_data = NewsletterSignupObservation.model_validate(
                    newsletter_result.parsed_response if hasattr(newsletter_result, "parsed_response") else {}
                )
            except Exception:
                newsletter_data = NewsletterSignupObservation(
                    signup_form_found=False,
                    confusing_opt_in=False,
                    dark_enrollment_detected=False,
                    bundled_with_other_services=False,
                    unsubscription_difficulty=None,
                    consent_separated=False,
                )

            # If form found, try to interact based on persona
            if newsletter_data.signup_form_found:
                if persona == "privacy_sensitive":
                    nova.act(
                        "Look for unchecked newsletter options or ways to opt out. "
                        "Note any pre-checked boxes and try to uncheck them.",
                        max_steps=5,
                    )
                    interacted_controls.append("opt_out_attempt")
                    activity_log.append("Attempted to opt out of newsletters (privacy persona)")
                elif persona == "exit_intent":
                    nova.act(
                        "Look for newsletter signup prompts that appear when trying to leave or navigate away. "
                        "Note any popups or exit-intent modals.",
                        max_steps=5,
                    )
                    interacted_controls.append("check_exit_intent_popups")
                    activity_log.append("Checked for exit-intent newsletter prompts")

                self._capture_screenshot(
                    audit_id,
                    nova,
                    "newsletter_signup",
                    persona,
                    "interaction_complete",
                    screenshot_paths,
                    screenshot_urls,
                )

            # Build observation evidence
            friction_indicators: list[str] = []
            if newsletter_data.pre_checked_boxes:
                friction_indicators.append("Pre-checked consent boxes")
            if newsletter_data.confusing_opt_in:
                friction_indicators.append("Confusing opt-in language")
            if newsletter_data.dark_enrollment_detected:
                friction_indicators.append("Dark enrollment pattern")

            evidence = ObservationEvidence(
                screenshot_urls=screenshot_urls,
                screenshot_paths=screenshot_paths,
                button_labels=[],
                checkbox_states=dict.fromkeys(newsletter_data.pre_checked_boxes, True),
                price_points=[],
                text_snippets=newsletter_data.confusing_language_examples,
                headings=["Newsletter Signup"] if newsletter_data.signup_form_found else [],
                page_title="Newsletter Signup Analysis",
                dom_excerpt=f"Form found: {newsletter_data.signup_form_found}, Pre-checked: {len(newsletter_data.pre_checked_boxes)}",
                step_count=len(interacted_controls),
                friction_indicators=friction_indicators,
                activity_log=activity_log,
                metadata={
                    "source": "nova_act",
                    "source_label": "Nova Act AI-driven browser automation",
                    "site_host": urlparse(target_url).netloc,
                    "page_url": nova.page.url if hasattr(nova, "page") else target_url,
                    "interacted_controls": interacted_controls,
                    "scenario_state_found": newsletter_data.signup_form_found,
                    "action_count": len(interacted_controls),
                    "observed_price_delta": 0.0,
                    "state_snapshots": state_snapshots,
                },
            )

            return JourneyObservation(
                scenario="newsletter_signup",
                persona=persona,
                target_url=target_url,
                final_url=nova.page.url if hasattr(nova, "page") else target_url,
                evidence=evidence,
            )

    def _run_pricing_comparison_scenario(
        self,
        audit_id: str,
        target_url: str,
        persona: PersonaType,
        nova_act: Any,
    ) -> JourneyObservation:
        """Run pricing comparison scenario with Nova Act."""

        activity_log: list[str] = []
        state_snapshots: list[dict] = []
        screenshot_paths: list[str] = []
        screenshot_urls: list[str] = []
        interacted_controls: list[str] = []

        with NovaAct(
            starting_page=target_url,
            headless=self.headless,
            tty=self.tty,
            go_to_url_timeout=self.timeout,
        ) as nova:
            # Initial state
            self._capture_screenshot(
                audit_id, nova, "pricing_comparison", persona, "initial", screenshot_paths, screenshot_urls
            )
            activity_log.append(f"Loaded {target_url}")
            state_snapshots.append({"url": target_url, "step": "initial", "action": "page_load"})

            # Browse and collect prices
            nova.act(
                "Browse the site and look for products, services, or offers with prices. "
                "Note any displayed prices and whether they change as you navigate. "
                "Look for discounts, special offers, or loyalty program requirements.",
                max_steps=10,
            )
            interacted_controls.append("browse_prices")
            activity_log.append("Browsed for price information")

            self._capture_screenshot(
                audit_id, nova, "pricing_comparison", persona, "first_pass", screenshot_paths, screenshot_urls
            )

            # Extract pricing observations
            pricing_result = nova.act_get(
                "Analyze the pricing observed. What prices were found and in what context? "
                "Are there variations for the same item? Signs of bait-and-switch? "
                "Are there persona-specific offers (e.g., 'new customer', 'member price')? "
                "Are discounts hidden behind loyalty programs? Any dynamic pricing indicators?",
                schema=PricingComparisonObservation.model_json_schema(),
            )

            try:
                pricing_data = PricingComparisonObservation.model_validate(
                    pricing_result.parsed_response if hasattr(pricing_result, "parsed_response") else {}
                )
            except Exception:
                pricing_data = PricingComparisonObservation(
                    price_variations_detected=False,
                    bait_and_switch_suspected=False,
                    loyalty_program_pressure=False,
                )

            # Continue browsing to check for price changes
            nova.act(
                "Continue browsing, try to add items to cart or proceed toward checkout. "
                "Note any price changes between browsing and checkout stages.",
                max_steps=8,
            )
            interacted_controls.append("continue_browsing")
            activity_log.append("Continued browsing to check price consistency")

            self._capture_screenshot(
                audit_id, nova, "pricing_comparison", persona, "second_pass", screenshot_paths, screenshot_urls
            )

            # Re-extract pricing observations
            final_pricing_result = nova.act_get(
                "Re-analyze prices. Have they changed from earlier observations? "
                "Any price discrepancies between product page and checkout? "
                "Final price comparison data.",
                schema=PricingComparisonObservation.model_json_schema(),
            )

            try:
                final_pricing_data = PricingComparisonObservation.model_validate(
                    final_pricing_result.parsed_response if hasattr(final_pricing_result, "parsed_response") else {}
                )
                pricing_data = final_pricing_data
            except Exception:
                pass

            state_snapshots.append(
                {
                    "url": nova.page.url if hasattr(nova, "page") else target_url,
                    "step": "pricing_check",
                    "action": "price_comparison",
                    "prices": pricing_data.prices_found,
                }
            )

            # Calculate price delta if multiple prices found
            price_delta = 0.0
            if len(pricing_data.prices_found) >= 2:
                try:
                    prices = [float(p.get("value", 0)) for p in pricing_data.prices_found if p.get("value")]
                    if len(prices) >= 2:
                        price_delta = max(prices) - min(prices)
                except (ValueError, TypeError):
                    pass

            # Build observation evidence
            friction_indicators: list[str] = []
            if pricing_data.bait_and_switch_suspected:
                friction_indicators.append("Bait-and-switch suspected")
            if pricing_data.loyalty_program_pressure:
                friction_indicators.append("Loyalty program required for pricing")

            evidence = ObservationEvidence(
                screenshot_urls=screenshot_urls,
                screenshot_paths=screenshot_paths,
                button_labels=pricing_data.persona_specific_offers,
                checkbox_states={},
                price_points=pricing_data.prices_found,
                text_snippets=pricing_data.dynamic_pricing_indicators,
                headings=["Pricing"] if pricing_data.prices_found else [],
                page_title="Pricing Comparison Analysis",
                dom_excerpt=f"Prices found: {len(pricing_data.prices_found)}, Variations: {pricing_data.price_variations_detected}",
                step_count=len(interacted_controls),
                friction_indicators=friction_indicators,
                activity_log=activity_log,
                metadata={
                    "source": "nova_act",
                    "source_label": "Nova Act AI-driven browser automation",
                    "site_host": urlparse(target_url).netloc,
                    "page_url": nova.page.url if hasattr(nova, "page") else target_url,
                    "interacted_controls": interacted_controls,
                    "scenario_state_found": len(pricing_data.prices_found) > 0,
                    "action_count": len(interacted_controls),
                    "observed_price_delta": price_delta,
                    "state_snapshots": state_snapshots,
                },
            )

            return JourneyObservation(
                scenario="pricing_comparison",
                persona=persona,
                target_url=target_url,
                final_url=nova.page.url if hasattr(nova, "page") else target_url,
                evidence=evidence,
            )

    def _capture_screenshot(
        self,
        audit_id: str,
        nova: Any,
        scenario: str,
        persona: str,
        step: str,
        screenshot_paths: list[str],
        screenshot_urls: list[str],
    ) -> None:
        """Capture and save a screenshot using Nova Act's Playwright page."""
        try:
            if hasattr(nova, "page") and nova.page:
                screenshot_bytes = nova.page.screenshot()
                filename = f"screenshots/{audit_id}/{scenario}_{persona}_{step}.png"
                saved = self.storage.save_bytes(filename, screenshot_bytes, "image/png")
                if saved.public_url:
                    screenshot_urls.append(saved.public_url)
                if saved.absolute_path:
                    screenshot_paths.append(saved.absolute_path)
        except Exception as e:
            logger.warning(f"Failed to capture screenshot for {scenario}/{persona}/{step}: {e}")

    def _error_observation(
        self,
        target_url: str,
        scenario: str,
        persona: str,
        error: str,
    ) -> JourneyObservation:
        """Create a fallback observation when an error occurs."""
        return JourneyObservation(
            scenario=scenario,
            persona=persona,
            target_url=target_url,
            final_url=target_url,
            evidence=ObservationEvidence(
                screenshot_urls=[],
                screenshot_paths=[],
                button_labels=[],
                checkbox_states={},
                price_points=[],
                text_snippets=[f"Error: {error}"],
                headings=[],
                page_title="Error",
                dom_excerpt=f"Error occurred: {error}",
                step_count=0,
                friction_indicators=["Audit scenario failed"],
                activity_log=[f"Error: {error}"],
                metadata={
                    "source": "nova_act",
                    "source_label": "Nova Act AI-driven browser automation",
                    "site_host": urlparse(target_url).netloc,
                    "page_url": target_url,
                    "interacted_controls": [],
                    "scenario_state_found": False,
                    "action_count": 0,
                    "observed_price_delta": 0.0,
                    "state_snapshots": [],
                    "error": error,
                },
            ),
        )

    def _empty_result(
        self,
        target_url: str,
        scenarios: list[str],
        personas: list[str],
        reason: str,
    ) -> BrowserRunResult:
        """Create an empty result when no valid scenarios or personas."""
        return BrowserRunResult(
            observations=[],
            summary={
                "mode": "nova_act",
                "evidence_origin": "nova_act",
                "evidence_origin_label": "Nova Act AI-driven browser automation",
                "observation_count": 0,
                "scenarios": scenarios,
                "personas": personas,
                "error": reason,
            },
        )
