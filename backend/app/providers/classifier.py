from __future__ import annotations

import json
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.config import Config

from app.core.config import PROJECT_ROOT, Settings
from app.schemas.runtime import ClassifiedFinding, RuleFindingDraft


PROMPT_PATH = PROJECT_ROOT / "backend" / "app" / "prompts" / "nova_classifier_prompt.txt"


@lru_cache(maxsize=1)
def get_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


class ClassifierProvider(ABC):
    @abstractmethod
    def classify(self, draft: RuleFindingDraft) -> ClassifiedFinding:
        raise NotImplementedError


class MockClassifierProvider(ClassifierProvider):
    def classify(self, draft: RuleFindingDraft) -> ClassifiedFinding:
        severity = draft.severity
        confidence = min(0.97, 0.72 + (draft.trust_impact / 30))
        payload = draft.evidence_payload
        site_host = str(payload.get("site_host") or "the audited site")
        page_title = str(payload.get("page_title") or "")
        source_label = str(payload.get("source_label") or "Observed")
        context_label = f'on "{page_title}"' if page_title else f"on {site_host}"
        quote = str(payload.get("matched_quote") or draft.evidence_excerpt)
        matched_buttons = [str(item) for item in payload.get("matched_buttons", []) if item][:3]
        matched_prices = payload.get("matched_prices", [])
        step_count = int(payload.get("step_count") or 0)

        explanation = self._build_explanation(
            draft=draft,
            source_label=source_label,
            context_label=context_label,
            quote=quote,
            matched_buttons=matched_buttons,
            matched_prices=matched_prices,
            step_count=step_count,
        )
        remediation_map = {
            "asymmetric_choice": "Present acceptance and refusal actions with equal prominence and plain-language labels.",
            "hidden_costs": "Expose total price, fees, and optional extras before commitment and keep totals stable through checkout.",
            "confirmshaming": "Replace loaded dismissal copy with neutral wording that respects user agency.",
            "obstruction": "Reduce steps, remove support detours, and give users a direct path to their intended outcome.",
            "sneaking": "Default optional checkboxes to off and require explicit user action for add-ons or consent.",
            "urgency": "Only show urgency when it is verifiable and time-bounded; otherwise remove it.",
        }
        return ClassifiedFinding(
            explanation=explanation,
            remediation=remediation_map.get(
                draft.pattern_family,
                "Simplify the flow and make user-impacting choices more explicit.",
            ),
            confidence=round(confidence, 2),
            severity=severity,
        )

    def _build_explanation(
        self,
        *,
        draft: RuleFindingDraft,
        source_label: str,
        context_label: str,
        quote: str,
        matched_buttons: list[str],
        matched_prices: list,
        step_count: int,
    ) -> str:
        if draft.pattern_family == "hidden_costs" and len(matched_prices) >= 2:
            first_price = matched_prices[0]
            last_price = matched_prices[-1]
            return (
                f"{source_label} evidence {context_label} showed a visible price movement from "
                f"{first_price.get('raw', first_price.get('value'))} to {last_price.get('raw', last_price.get('value'))}. "
                f"The finding is grounded in the specific labels captured during the {draft.scenario.replace('_', ' ')} journey, not a generic heuristic."
            )

        if draft.pattern_family == "asymmetric_choice":
            controls = ", ".join(f'"{label}"' for label in matched_buttons) or f'"{quote}"'
            return (
                f"{source_label} evidence {context_label} surfaced approval-oriented controls such as {controls}. "
                f"The audit did not capture an equally explicit refusal action in the same view for the {draft.persona.replace('_', ' ')} persona."
            )

        if draft.pattern_family == "obstruction":
            return (
                f"{source_label} evidence {context_label} required {step_count} captured interaction steps before the journey stabilized. "
                f"This indicates the user path adds avoidable friction during the {draft.scenario.replace('_', ' ')} flow."
            )

        if draft.pattern_family == "sneaking":
            controls = ", ".join(f'"{label}"' for label in matched_buttons) or f'"{quote}"'
            return (
                f"{source_label} evidence {context_label} showed optional choices tied to {controls}. "
                f"That makes the final user choice less explicit than it should be for a trust-sensitive flow."
            )

        return (
            f"{source_label} evidence {context_label} surfaced the line \"{quote[:160]}\" during the "
            f"{draft.scenario.replace('_', ' ')} journey for the {draft.persona.replace('_', ' ')} persona. "
            f"This finding is tied to the captured UI state rather than a generic dark-pattern template."
        )


class LiveNovaClassifierProvider(ClassifierProvider):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.fallback = MockClassifierProvider()
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
            config=Config(read_timeout=300, retries={"max_attempts": 3, "mode": "standard"}),
        )

    def classify(self, draft: RuleFindingDraft) -> ClassifiedFinding:
        if not self.settings.nova_ready:
            return self.fallback.classify(draft)

        prompt_payload = {
            "scenario": draft.scenario,
            "persona": draft.persona,
            "pattern_family": draft.pattern_family,
            "severity": draft.severity,
            "title": draft.title,
            "evidence_excerpt": draft.evidence_excerpt,
            "rule_reason": draft.rule_reason,
            "trust_impact": draft.trust_impact,
            "evidence_payload": draft.evidence_payload,
        }
        content = [{"text": json.dumps(prompt_payload, indent=2)}]
        first_image = next(iter(draft.evidence_payload.get("screenshot_paths", [])), None)
        if first_image and Path(first_image).exists():
            content.append(
                {
                    "image": {
                        "format": Path(first_image).suffix.lstrip(".") or "png",
                        "source": {"bytes": Path(first_image).read_bytes()},
                    }
                }
            )

        try:
            response = self.client.converse(
                modelId=self.settings.nova_model_id,
                system=[{"text": get_prompt()}],
                messages=[{"role": "user", "content": content}],
                inferenceConfig={"temperature": 0.2, "maxTokens": 900},
            )
            raw_text = "".join(
                part.get("text", "")
                for part in response["output"]["message"]["content"]
                if isinstance(part, dict)
            )
            parsed = self._parse_response(raw_text)
            return ClassifiedFinding(
                explanation=parsed["explanation"],
                remediation=parsed["remediation"],
                confidence=float(parsed["confidence"]),
                severity=str(parsed.get("severity", draft.severity)),
            )
        except Exception:
            return self.fallback.classify(draft)

    @staticmethod
    def _parse_response(raw_text: str) -> dict[str, str | float]:
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(raw_text[start : end + 1])
            raise
