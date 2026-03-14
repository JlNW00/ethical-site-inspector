import { describe, it, expect } from "vitest";
import { parseVideoKey, parseVideoUrls } from "./video";

describe("parseVideoKey", () => {
  const scenarios = ["cookie_consent", "checkout_flow", "newsletter_signup"];
  const personas = ["privacy_sensitive", "cost_sensitive", "exit_intent"];

  it("parses simple scenario-persona combinations", () => {
    expect(parseVideoKey("cookie_consent_privacy_sensitive", scenarios, personas)).toEqual({
      scenario: "cookie_consent",
      persona: "privacy_sensitive",
    });
  });

  it("parses different scenario-persona combinations", () => {
    expect(parseVideoKey("checkout_flow_cost_sensitive", scenarios, personas)).toEqual({
      scenario: "checkout_flow",
      persona: "cost_sensitive",
    });
  });

  it("returns null for unknown scenario", () => {
    expect(parseVideoKey("unknown_scenario_privacy_sensitive", scenarios, personas)).toBeNull();
  });

  it("returns null for unknown persona", () => {
    expect(parseVideoKey("cookie_consent_unknown_persona", scenarios, personas)).toBeNull();
  });

  it("returns null for keys without underscore separator", () => {
    expect(parseVideoKey("invalidkey", scenarios, personas)).toBeNull();
  });

  it("returns null for empty key", () => {
    expect(parseVideoKey("", scenarios, personas)).toBeNull();
  });

  it("handles multi-word scenario and persona names correctly", () => {
    const complexScenarios = ["checkout_flow", "newsletter_signup", "account_creation_flow"];
    const complexPersonas = ["privacy_sensitive", "cost_sensitive", "tech_savvy_user"];

    expect(parseVideoKey("account_creation_flow_tech_savvy_user", complexScenarios, complexPersonas)).toEqual({
      scenario: "account_creation_flow",
      persona: "tech_savvy_user",
    });
  });

  it("prefers longer scenario match over shorter partial match", () => {
    // If we had both "checkout" and "checkout_flow" as scenarios,
    // the longer match should win
    const mixedScenarios = ["checkout", "checkout_flow"];
    expect(parseVideoKey("checkout_flow_privacy_sensitive", mixedScenarios, personas)).toEqual({
      scenario: "checkout_flow",
      persona: "privacy_sensitive",
    });
  });

  it("handles edge case with persona containing scenario substring", () => {
    const edgeScenarios = ["signup"];
    const edgePersonas = ["signup_flow_tester"];
    expect(parseVideoKey("signup_signup_flow_tester", edgeScenarios, edgePersonas)).toEqual({
      scenario: "signup",
      persona: "signup_flow_tester",
    });
  });
});

describe("parseVideoUrls", () => {
  const scenarios = ["cookie_consent", "checkout_flow"];
  const personas = ["privacy_sensitive", "cost_sensitive"];

  it("returns empty array for null video_urls", () => {
    expect(parseVideoUrls(null, scenarios, personas)).toEqual([]);
  });

  it("returns empty array for undefined video_urls", () => {
    expect(parseVideoUrls(undefined, scenarios, personas)).toEqual([]);
  });

  it("returns empty array for empty video_urls object", () => {
    expect(parseVideoUrls({}, scenarios, personas)).toEqual([]);
  });

  it("parses all valid video URLs", () => {
    const videoUrls = {
      cookie_consent_privacy_sensitive: "/videos/1.webm",
      checkout_flow_cost_sensitive: "/videos/2.webm",
    };

    const result = parseVideoUrls(videoUrls, scenarios, personas);
    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      url: "/videos/1.webm",
      scenario: "cookie_consent",
      persona: "privacy_sensitive",
      key: "cookie_consent_privacy_sensitive",
    });
    expect(result[1]).toEqual({
      url: "/videos/2.webm",
      scenario: "checkout_flow",
      persona: "cost_sensitive",
      key: "checkout_flow_cost_sensitive",
    });
  });

  it("filters out invalid keys", () => {
    const videoUrls = {
      cookie_consent_privacy_sensitive: "/videos/valid.webm",
      unknown_scenario_cost_sensitive: "/videos/invalid.webm",
      cookie_consent_unknown_persona: "/videos/invalid2.webm",
    };

    const result = parseVideoUrls(videoUrls, scenarios, personas);
    expect(result).toHaveLength(1);
    expect(result[0].scenario).toBe("cookie_consent");
    expect(result[0].persona).toBe("privacy_sensitive");
  });

  it("handles multi-word scenario and persona names", () => {
    const complexScenarios = ["cookie_consent", "newsletter_signup"];
    const complexPersonas = ["privacy_sensitive", "exit_intent"];

    const videoUrls = {
      newsletter_signup_exit_intent: "/videos/exit.webm",
    };

    const result = parseVideoUrls(videoUrls, complexScenarios, complexPersonas);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      url: "/videos/exit.webm",
      scenario: "newsletter_signup",
      persona: "exit_intent",
      key: "newsletter_signup_exit_intent",
    });
  });
});
