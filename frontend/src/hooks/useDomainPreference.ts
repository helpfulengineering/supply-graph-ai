import { useEffect, useRef, useState } from "react";
import { fetchDefaultDomain } from "../api/ohm/utility";
import {
  DEFAULT_DOMAIN,
  STORAGE_KEY,
  parseDomain,
  type OhmDomain,
} from "../features/settings/domainPreference";

function getInitialDomain(): OhmDomain {
  try {
    return parseDomain(localStorage.getItem(STORAGE_KEY));
  } catch {
    return DEFAULT_DOMAIN;
  }
}

function hasStoredPreference(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) != null;
  } catch {
    return false;
  }
}

export function useDomainPreference() {
  const [domain, setDomainState] = useState<OhmDomain>(getInitialDomain);
  // Only a *first* visit (no stored preference yet) should adopt the server's
  // configured default — e.g. a cooking-domain Azure instance defaulting new
  // browsers to "cooking". Once a choice exists, localStorage owns it.
  const hadStoredPreference = useRef(hasStoredPreference());
  const userChanged = useRef(false);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, domain);
    } catch {
      // ignore (private browsing, quota, etc.)
    }
  }, [domain]);

  useEffect(() => {
    if (hadStoredPreference.current) return;
    let cancelled = false;
    fetchDefaultDomain().then((serverDefault) => {
      if (cancelled || userChanged.current || !serverDefault) return;
      setDomainState(parseDomain(serverDefault));
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    domain,
    setDomain: (next: OhmDomain) => {
      userChanged.current = true;
      setDomainState(parseDomain(next));
    },
  };
}
