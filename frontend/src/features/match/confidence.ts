/**
 * Confidence presentation mapper (pure, unit-tested) — module 5.
 * Maps a 0..1 confidence/score to a label + badge variant, reused across match.
 */
export function confidenceToken(score: number): {
  label: string;
  variant: "green" | "yellow" | "red";
} {
  if (score >= 0.8) return { label: "High", variant: "green" };
  if (score >= 0.5) return { label: "Medium", variant: "yellow" };
  return { label: "Low", variant: "red" };
}

export function confidencePct(score: number): number {
  return Math.round(Math.max(0, Math.min(1, score)) * 100);
}
