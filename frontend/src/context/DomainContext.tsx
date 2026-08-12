import { createContext, useContext } from "react";
import {
  DEFAULT_DOMAIN,
  type OhmDomain,
} from "../features/settings/domainPreference";

interface DomainContextValue {
  domain: OhmDomain;
  setDomain: (domain: OhmDomain) => void;
}

export const DomainContext = createContext<DomainContextValue>({
  domain: DEFAULT_DOMAIN,
  setDomain: () => {},
});

export function useDomain() {
  return useContext(DomainContext);
}
