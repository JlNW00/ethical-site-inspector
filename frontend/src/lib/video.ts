/**
 * Video key parsing utility.
 *
 * The video_urls dict uses keys in format "{scenario}_{persona}", where both
 * scenario and persona are snake_case identifiers that may contain underscores.
 * Since the underscore separator is ambiguous (e.g., "cookie_consent_privacy_sensitive"),
 * we must cross-reference against known scenario and persona names to find valid split points.
 *
 * @see .factory/library/video-data-model.md
 */

export interface ParsedVideoKey {
  scenario: string;
  persona: string;
}

/**
 * Parse a video_urls key to extract scenario and persona names.
 *
 * The key format is "{scenario}_{persona}" where both parts may contain underscores.
 * We try all combinations of known scenarios and personas to find a valid match.
 *
 * @param key - The video_urls key (e.g., "cookie_consent_privacy_sensitive")
 * @param scenarios - Array of valid scenario identifiers from audit.selected_scenarios
 * @param personas - Array of valid persona identifiers from audit.selected_personas
 * @returns ParsedVideoKey with scenario and persona, or null if no valid parse found
 *
 * @example
 * ```ts
 * const key = "cookie_consent_privacy_sensitive";
 * const scenarios = ["cookie_consent", "checkout_flow"];
 * const personas = ["privacy_sensitive", "cost_sensitive"];
 * parseVideoKey(key, scenarios, personas);
 * // Returns: { scenario: "cookie_consent", persona: "privacy_sensitive" }
 * ```
 */
export function parseVideoKey(key: string, scenarios: string[], personas: string[]): ParsedVideoKey | null {
  // Try all possible splits: for each known scenario, check if key starts with it
  for (const scenario of scenarios) {
    // Key should be "{scenario}_{persona}"
    const prefix = `${scenario}_`;
    if (key.startsWith(prefix)) {
      const persona = key.slice(prefix.length);
      // Verify this persona is in the known personas list
      if (personas.includes(persona)) {
        return { scenario, persona };
      }
    }
  }

  // No valid parse found
  return null;
}

/**
 * Parse all video URLs from the video_urls dict.
 *
 * @param videoUrls - The video_urls dict from Audit, or null/undefined
 * @param scenarios - Array of valid scenario identifiers
 * @param personas - Array of valid persona identifiers
 * @returns Array of parsed video entries with url, scenario, persona, and original key
 */
export interface VideoEntry {
  url: string;
  scenario: string;
  persona: string;
  key: string;
}

export function parseVideoUrls(
  videoUrls: Record<string, string> | null | undefined,
  scenarios: string[],
  personas: string[],
): VideoEntry[] {
  if (!videoUrls || Object.keys(videoUrls).length === 0) {
    return [];
  }

  const entries: VideoEntry[] = [];

  for (const [key, url] of Object.entries(videoUrls)) {
    const parsed = parseVideoKey(key, scenarios, personas);
    if (parsed) {
      entries.push({
        url,
        scenario: parsed.scenario,
        persona: parsed.persona,
        key,
      });
    }
  }

  return entries;
}
