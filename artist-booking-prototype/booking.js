// Demo: simulated payments. No real payment, network or backend.
// All money values are integer INR paise.
export const ADVANCE_PERCENT = 20;
export const PLATFORM_FEE_PAISE = 50000;

export function quote(packageFee) {
  if (!Number.isSafeInteger(packageFee) || packageFee <= 0) {
    throw new Error('packageFee must be a positive integer number of paise');
  }
  // 20% advance, rounded half-up to the nearest paise using integer math only.
  const advance = Math.floor(packageFee / 5) + (packageFee % 5 >= 3 ? 1 : 0);
  // total remains the artist's package fee. The platform fee is separate and
  // due now with the advance; it never reduces the artist's remaining balance.
  return { total: packageFee, advance, balance: packageFee - advance,
    platformFee: PLATFORM_FEE_PAISE, dueNow: advance + PLATFORM_FEE_PAISE,
    currency: 'INR', unit: 'paise' };
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

function validDate(s) {
  if (typeof s !== 'string' || !DATE_RE.test(s)) return false;
  const [y, m, d] = s.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
}

// input: {artistId, date:'YYYY-MM-DD', time:'HH:MM', package:{id, fee}, customer?}
// existing: array of prior bookings (e.g. from getState().bookings); not mutated.
export function isSlotOccupied(existing, artistId, date, time) {
  const key = `${artistId}|${date}|${time}`;
  return (Array.isArray(existing) ? existing : []).some((b) => b && b.status !== 'cancelled' && (
    (typeof b.artistId === 'string' && typeof b.date === 'string' && typeof (b.time ?? b.slot) === 'string')
      ? b.artistId === artistId && b.date === date && (b.time ?? b.slot) === time
      : b.key === key));
}

export function createBooking(input, existing = []) {
  const prior = Array.isArray(existing) ? existing : [];
  const errors = [];
  const i = input || {};
  if (typeof i.artistId !== 'string' || !i.artistId.trim()) errors.push('artistId required');
  if (!validDate(i.date)) errors.push('valid date (YYYY-MM-DD) required');
  if (typeof i.time !== 'string' || !TIME_RE.test(i.time)) errors.push('valid time (HH:MM) required');
  const pkg = i.package;
  if (!pkg || typeof pkg.id !== 'string' || !pkg.id.trim() || !Number.isSafeInteger(pkg.fee) || pkg.fee <= 0) {
    errors.push('package with id and positive integer paise fee required');
  }
  if (errors.length) return { ok: false, errors };
  const key = `${i.artistId}|${i.date}|${i.time}`;
  if (isSlotOccupied(prior, i.artistId, i.date, i.time)) {
    return { ok: false, errors: ['slot already booked'] };
  }
  const q = quote(pkg.fee);
  const ids = new Set(prior.map((b) => b && b.id));
  let n = prior.length + 1;
  const suffix = key.replace(/[^A-Za-z0-9]/g, '');
  while (ids.has(`DEMO-${n}-${suffix}`)) n += 1;
  const booking = {
    id: `DEMO-${n}-${suffix}`,
    key,
    artistId: i.artistId,
    date: i.date,
    time: i.time,
    packageId: pkg.id,
    ...q,
    status: 'confirmed',
    payment: { simulated: true, paidAdvance: q.advance,
      paidPlatformFee: q.platformFee, paidNow: q.dueNow, note: 'Demo: simulated payments' },
  };
  return { ok: true, booking };
}
