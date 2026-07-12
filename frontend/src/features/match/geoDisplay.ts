/**
 * Display helpers so geo filter UIs always show full names, even when
 * facility payloads store ISO country codes or US state abbreviations.
 */

const COUNTRY_NAMES: Record<string, string> = {
  AD: "Andorra",
  AE: "United Arab Emirates",
  AR: "Argentina",
  AT: "Austria",
  AU: "Australia",
  BE: "Belgium",
  BR: "Brazil",
  CA: "Canada",
  CH: "Switzerland",
  CL: "Chile",
  CN: "China",
  CO: "Colombia",
  CZ: "Czechia",
  DE: "Germany",
  DK: "Denmark",
  ES: "Spain",
  FI: "Finland",
  FR: "France",
  GB: "United Kingdom",
  GR: "Greece",
  HK: "Hong Kong",
  HU: "Hungary",
  IE: "Ireland",
  IL: "Israel",
  IN: "India",
  IT: "Italy",
  JP: "Japan",
  KR: "South Korea",
  MX: "Mexico",
  NL: "Netherlands",
  NO: "Norway",
  NZ: "New Zealand",
  PL: "Poland",
  PT: "Portugal",
  RO: "Romania",
  RU: "Russia",
  SE: "Sweden",
  SG: "Singapore",
  TH: "Thailand",
  TR: "Turkey",
  TW: "Taiwan",
  UA: "Ukraine",
  US: "United States",
  USA: "United States",
  ZA: "South Africa",
};

const US_STATE_NAMES: Record<string, string> = {
  AL: "Alabama",
  AK: "Alaska",
  AZ: "Arizona",
  AR: "Arkansas",
  CA: "California",
  CO: "Colorado",
  CT: "Connecticut",
  DE: "Delaware",
  FL: "Florida",
  GA: "Georgia",
  HI: "Hawaii",
  ID: "Idaho",
  IL: "Illinois",
  IN: "Indiana",
  IA: "Iowa",
  KS: "Kansas",
  KY: "Kentucky",
  LA: "Louisiana",
  ME: "Maine",
  MD: "Maryland",
  MA: "Massachusetts",
  MI: "Michigan",
  MN: "Minnesota",
  MS: "Mississippi",
  MO: "Missouri",
  MT: "Montana",
  NE: "Nebraska",
  NV: "Nevada",
  NH: "New Hampshire",
  NJ: "New Jersey",
  NM: "New Mexico",
  NY: "New York",
  NC: "North Carolina",
  ND: "North Dakota",
  OH: "Ohio",
  OK: "Oklahoma",
  OR: "Oregon",
  PA: "Pennsylvania",
  RI: "Rhode Island",
  SC: "South Carolina",
  SD: "South Dakota",
  TN: "Tennessee",
  TX: "Texas",
  UT: "Utah",
  VT: "Vermont",
  VA: "Virginia",
  WA: "Washington",
  WV: "West Virginia",
  WI: "Wisconsin",
  WY: "Wyoming",
  DC: "District of Columbia",
};

/** Invert a code→name map so names resolve back to codes for matching. */
function invert(map: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [code, name] of Object.entries(map)) {
    out[name.toLowerCase()] = code;
  }
  return out;
}

const COUNTRY_BY_NAME = invert(COUNTRY_NAMES);
const STATE_BY_NAME = invert(US_STATE_NAMES);

export function displayCountryName(raw: string | null | undefined): string {
  if (!raw?.trim()) return "";
  const s = raw.trim();
  const upper = s.toUpperCase();
  return COUNTRY_NAMES[upper] ?? s;
}

export function displayRegionName(raw: string | null | undefined): string {
  if (!raw?.trim()) return "";
  const s = raw.trim();
  const upper = s.toUpperCase();
  return US_STATE_NAMES[upper] ?? s;
}

/** Canonical key for comparing country values (code or full name). */
export function countryMatchKey(raw: string | null | undefined): string {
  if (!raw?.trim()) return "";
  const s = raw.trim();
  const upper = s.toUpperCase();
  if (COUNTRY_NAMES[upper]) return COUNTRY_NAMES[upper].toLowerCase();
  const fromName = COUNTRY_BY_NAME[s.toLowerCase()];
  if (fromName) return (COUNTRY_NAMES[fromName] ?? fromName).toLowerCase();
  return s.toLowerCase();
}

/** Canonical key for comparing region/state values. */
export function regionMatchKey(raw: string | null | undefined): string {
  if (!raw?.trim()) return "";
  const s = raw.trim();
  const upper = s.toUpperCase();
  if (US_STATE_NAMES[upper]) return US_STATE_NAMES[upper].toLowerCase();
  const fromName = STATE_BY_NAME[s.toLowerCase()];
  if (fromName) return (US_STATE_NAMES[fromName] ?? fromName).toLowerCase();
  return s.toLowerCase();
}

export function cityMatchKey(raw: string | null | undefined): string {
  return (raw ?? "").trim().toLowerCase();
}
