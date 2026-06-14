/** Format integer cents as a currency string. */
export function formatMoney(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format((cents || 0) / 100);
}

/** Parse a user-typed amount (dollars) into integer cents. */
export function parseMoneyToCents(input: string): number {
  const n = parseFloat(String(input).replace(/[^0-9.]/g, ""));
  return Number.isFinite(n) ? Math.round(n * 100) : 0;
}
