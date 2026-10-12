// Artist booking demo integration adapter. Demo: simulated payments.
// Smallest repair for known gaps: booking.js createBooking is pure, so the
// caller appends the mapped booking to shared state; dashboard fields mapped.
// No network, payment, auth or external URLs.
import { isSlotOccupied } from './booking.js';

// Booking dates use the artists' India-local calendar, independently of the
// browser's timezone. Inject an instant in tests; never use UTC date slicing.
function localClock(referenceDate) {
  if (!(referenceDate instanceof Date) || !Number.isFinite(referenceDate.getTime())) {
    throw new TypeError('referenceDate must be a valid Date');
  }
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(referenceDate);
  const value = (type) => parts.find((p) => p.type === type).value;
  return { date: `${value('year')}-${value('month')}-${value('day')}`,
    minutes: Number(value('hour')) * 60 + Number(value('minute')) };
}

export function localDateISO(referenceDate = new Date()) {
  return localClock(referenceDate).date;
}

export function availableTimes(artist, date, bookings = [], referenceDate = new Date()) {
  const clock = localClock(referenceDate);
  if (!artist || !Array.isArray(artist.slots) || typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return [];
  if (date < clock.date) return [];
  // A slot denotes the start of its minute. The entire current minute is
  // unavailable, including when the supplied instant is exactly on its start.
  return artist.slots.filter((time) => {
    if (typeof time !== 'string' || !/^([01]\d|2[0-3]):[0-5]\d$/.test(time)) return false;
    const [hour, minute] = time.split(':').map(Number);
    return (date > clock.date || hour * 60 + minute > clock.minutes) &&
      !isSlotOccupied(bookings, artist.id, date, time);
  });
}

// Contract mapping: slot=time, feePaise=total, advancePaise=advance, packageName=packageId.
export function toDashboardBooking(b, artists = []) {
  const a = artists.find((x) => x.id === b.artistId);
  const pkg = a?.packages?.find((p) => p.id === b.packageId);
  return { ...b, slot: b.time, feePaise: b.total, advancePaise: b.advance,
    packageName: pkg?.label || b.packageId, artistName: a ? a.name : b.artistId };
}

// UI passes package:{id, fee: feePaise} as data.js packages use feePaise.
export function toBookingInput(artist, packageId, date, time) {
  const p = (artist && artist.packages || []).find((x) => x.id === packageId);
  return { artistId: artist ? artist.id : '', date, time,
    package: p ? { id: p.id, fee: p.feePaise } : null };
}

// deps: {getState, updateState, createBooking, artists}
export function submitBooking(input, deps, referenceDate = new Date()) {
  const today = localDateISO(referenceDate);
  if (typeof input?.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(input.date) && input.date < today) {
    return { ok: false, errors: ['Choose today or a future date (India local time).'] };
  }
  const artist = (deps.artists || []).find((a) => a.id === input?.artistId);
  const pkg = artist?.packages.find((p) => p.id === input?.package?.id);
  if (!artist || !pkg || pkg.feePaise !== input.package.fee || !artist.slots.includes(input.time)) {
    return { ok: false, errors: ['Choose an available artist, package and time from this demo roster.'] };
  }
  const existing = deps.getState().bookings || [];
  if (!availableTimes(artist, input.date, existing, referenceDate).includes(input.time)) {
    return { ok: false, errors: ['Choose an unbooked future performance time (India local time).'] };
  }
  const r = deps.createBooking(input, existing);
  if (!r.ok) return r;
  const mapped = toDashboardBooking(r.booking, deps.artists || []);
  deps.updateState((s) => ({ bookings: [...(s.bookings || []), mapped] }));
  return { ok: true, booking: mapped };
}

// Initialize on DOMContentLoaded or immediately if DOM already ready.
export function onReady(fn, doc = globalThis.document) {
  if (!doc) return false;
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', fn, { once: true });
  else fn();
  return true;
}
