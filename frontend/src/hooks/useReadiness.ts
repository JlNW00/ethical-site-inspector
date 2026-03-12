import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { Readiness } from "../api/types";

export function useReadiness() {
  const [data, setData] = useState<Readiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const readiness = await api.getReadiness();
        if (!cancelled) {
          setData(readiness);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load readiness");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return { data, loading, error };
}
