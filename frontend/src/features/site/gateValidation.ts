/**
 * Client-side mirror of the checks in `ohmgr_gate_signin`.
 *
 * The RPC validates the same three things and raises on any of them, so this
 * is not the security boundary — it exists so a typo comes back as a message
 * under the field instead of a swallowed failure. The limits are copied from
 * supabase/schema.sql deliberately: if they drift, the server stays right and
 * the form becomes wrong, which is the safe direction to be wrong in.
 */

export const NAME_MAX = 120;
export const EMAIL_MAX = 254;

/** The SQL regex, transliterated: no spaces or @ in either half, one dot-suffix. */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export interface GateFieldErrors {
  name?: string;
  email?: string;
}

export function gateFieldErrors(name: string, email: string): GateFieldErrors {
  const errors: GateFieldErrors = {};
  const trimmedName = name.trim();
  const trimmedEmail = email.trim();

  if (trimmedName === "") errors.name = "Enter a name.";
  else if (trimmedName.length > NAME_MAX)
    errors.name = `Keep the name under ${NAME_MAX} characters.`;

  if (trimmedEmail === "") errors.email = "Enter an email address.";
  else if (trimmedEmail.length > EMAIL_MAX)
    errors.email = `Keep the email under ${EMAIL_MAX} characters.`;
  else if (!EMAIL_RE.test(trimmedEmail)) errors.email = "Enter a valid email address.";

  return errors;
}

/** True when nothing is wrong — the form's submit condition. */
export function gateFieldsValid(errors: GateFieldErrors): boolean {
  return !errors.name && !errors.email;
}
