import { post } from "./client";
import type { RFQGenerateRequest, RFQGenerateResponse } from "../types/rfq";

export function generateRfq(
  request: RFQGenerateRequest
): Promise<RFQGenerateResponse> {
  return post<RFQGenerateResponse>("/rfq/generate", request);
}

export interface PackageBuildResult {
  status: string;
  data: {
    metadata: {
      package_name: string;
      version: string;
      [key: string]: unknown;
    };
  };
}

export function buildPackage(manifestId: string): Promise<PackageBuildResult> {
  return post<PackageBuildResult>(`/package/build/${manifestId}`, {});
}
