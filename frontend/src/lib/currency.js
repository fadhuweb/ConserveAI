// The optimiser works in USD (the catalog stores cost_usd). The UI shows NGN,
// so we convert at the boundary with a single fixed rate (adjust here if needed).
export const NGN_PER_USD = 1600;

export const usdToNgn = (usd) => Math.round((usd || 0) * NGN_PER_USD);
export const ngnToUsd = (ngn) => Math.round((ngn || 0) / NGN_PER_USD);

export const fmtNGN = (usd) => `₦${usdToNgn(usd).toLocaleString()}`;
