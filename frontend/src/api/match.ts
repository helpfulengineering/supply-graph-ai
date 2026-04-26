import { post } from "./client";
import type { MatchRequest, MatchResponse } from "../types/match";

export function runMatch(req: MatchRequest): Promise<MatchResponse> {
  return post<MatchResponse>("/match", req);
}
