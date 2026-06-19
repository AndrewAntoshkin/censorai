export function SectionHeading({
  line1,
  line2,
  subtitle,
  dark = false,
  className = "",
}: {
  line1: string;
  line2?: string;
  subtitle?: string;
  dark?: boolean;
  className?: string;
}) {
  return (
    <div className={className}>
      <h2
        className={`landing-heading font-normal ${
          dark ? "text-[var(--v7-white)]" : "text-[var(--v7-ink)]"
        }`}
      >
        <span
          className={
            dark ? "text-[var(--v7-text-muted)]" : "text-[var(--v7-ink-muted)]"
          }
        >
          {line1}
        </span>
        {line2 ? (
          <>
            <br />
            <span className="font-medium">{line2}</span>
          </>
        ) : null}
      </h2>
      {subtitle ? (
        <p
          className={`mt-4 max-w-xl text-[var(--landing-body)] leading-[1.65] ${
            dark ? "text-[var(--v7-text-subtle)]" : "text-[var(--v7-ink-muted)]"
          }`}
        >
          {subtitle}
        </p>
      ) : null}
    </div>
  );
}
