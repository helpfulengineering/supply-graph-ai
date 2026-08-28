/** Registering a unit: three fields, and what makes them valid. */
import type { AssetCreateRequest } from "@/api/ohm/asset";

export interface AssetFormState {
  manifestId: string;
  assetTag: string;
  location: string;
}

export const EMPTY_ASSET_FORM: AssetFormState = {
  manifestId: "",
  assetTag: "",
  location: "",
};

export interface AssetFormErrors {
  manifestId?: string;
  assetTag?: string;
}

export function assetFormErrors(state: AssetFormState): AssetFormErrors {
  const errors: AssetFormErrors = {};
  if (!state.manifestId) {
    errors.manifestId = "Choose the design this unit was built from.";
  }
  if (!state.assetTag.trim()) {
    errors.assetTag =
      "Give the unit a tag — a serial number or a location code.";
  }
  return errors;
}

export function isAssetFormValid(state: AssetFormState): boolean {
  return Object.keys(assetFormErrors(state)).length === 0;
}

export function toCreateRequest(state: AssetFormState): AssetCreateRequest {
  return {
    manifest_id: state.manifestId,
    asset_tag: state.assetTag.trim(),
    location: state.location.trim() || null,
  };
}
