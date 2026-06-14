export function LogoMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 120" className={className} role="img" aria-label="Tendari mark">
      <path
        d="M30 86 C24 64 52 56 70 70 C84 81 73 98 55 92 C40 87 41 68 60 71 C77 74 84 62 87 51 C90 40 82 33 74 36 C66 39 67 49 75 49"
        fill="none"
        stroke="currentColor"
        strokeWidth={7}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <LogoMark className="h-7 w-7 text-forest" />
      <span className="text-xl font-semibold tracking-tight text-deep-green">
        Tendari
      </span>
    </span>
  );
}
