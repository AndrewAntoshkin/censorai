// Shared visual semantics for risk levels — muted but legible, token-based.

export type RiskLevelKey = "critical" | "warning" | "info";

export const RISK_LEVEL_STYLES: Record<
  RiskLevelKey,
  { badge: string; dot: string; bar: string }
> = {
  critical: {
    badge: "bg-critical-soft text-critical",
    dot: "bg-critical",
    bar: "bg-critical",
  },
  warning: {
    badge: "bg-warning-soft text-warning",
    dot: "bg-warning",
    bar: "bg-warning",
  },
  info: {
    badge: "bg-info-soft text-info",
    dot: "bg-info",
    bar: "bg-info",
  },
};

export function riskLevelStyle(level: string | null | undefined) {
  return RISK_LEVEL_STYLES[(level as RiskLevelKey) ?? "info"] ?? RISK_LEVEL_STYLES.info;
}
