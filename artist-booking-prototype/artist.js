// artist.js - Artist booking synthetic demo. Renders artist dashboard from shared state.
// All amounts are SIMULATED integer INR paise; no real revenue or payments.
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const toInt = (v) => (Number.isSafeInteger(v) && v >= 0 ? v : 0);
export const formatPaise = (p) => {
  const n = toInt(p);
  return 'INR ' + Math.floor(n / 100) + '.' + String(n % 100).padStart(2, '0');
};
// Integration adapter: authoritative booking schema (booking.js createBooking) ->
// dashboard fields. slot=time, feePaise=total, advancePaise=advance, packageName=packageId.
// Existing dashboard-shaped fields win, so previously stored bookings render unchanged.
export function toDashboardBooking(b) {
  const x = b && typeof b === 'object' ? b : {};
  return {
    ...x,
    slot: x.slot ?? x.time,
    feePaise: x.feePaise ?? x.total,
    advancePaise: x.advancePaise ?? x.advance,
    packageName: x.packageName ?? x.packageId,
  };
}
export function summarize(bookings) {
  const counts = {};
  let advance = 0, pending = 0;
  for (const b of bookings) {
    const s = String(b.status || 'unknown');
    Object.defineProperty(counts, s, { value: (Object.prototype.hasOwnProperty.call(counts, s) ? counts[s] : 0) + 1, enumerable: true, configurable: true, writable: true });
    if (s === 'cancelled') continue;
    const a = toInt(b.advancePaise), p = Math.max(0, toInt(b.feePaise) - a);
    if (!Number.isSafeInteger(advance + a) || !Number.isSafeInteger(pending + p)) throw new RangeError('simulated totals exceed safe range');
    advance += a;
    pending += p;
  }
  return { counts, simulatedAdvancePaise: advance, simulatedBalancePaise: pending };
}
export function renderArtist(state, artistId) {
  const all = Array.isArray(state && state.bookings) ? state.bookings.map(toDashboardBooking) : [];
  const bookings = artistId == null ? all : all.filter((b) => b.artistId === artistId);
  const sum = summarize(bookings);
  const rows = bookings.map((b) => `<tr><td>${esc(b.id)}</td><td>${esc(b.artistName || b.artistId)}</td><td>${esc(b.date)} ${esc(b.slot)}</td><td>${esc(b.packageName)}</td><td>${esc(b.status)}</td><td>${formatPaise(b.feePaise)}</td><td>${formatPaise(b.advancePaise)}</td></tr>`).join('');
  const counts = Object.entries(sum.counts).map(([k, v]) => `<li>${esc(k)}: ${v}</li>`).join('');
  return `<section class="artist-dashboard"><p class="demo-banner">Demo: simulated payments</p>`
    + `<h2>Artist dashboard</h2><ul class="status-counts">${counts || '<li>No bookings yet</li>'}</ul>`
    + `<p class="earnings">Simulated advance (not real revenue): ${formatPaise(sum.simulatedAdvancePaise)}</p>`
    + `<p class="balance">Simulated balance due: ${formatPaise(sum.simulatedBalancePaise)}</p>`
    + `<table><thead><tr><th>ID</th><th>Artist</th><th>Slot</th><th>Package</th><th>Status</th><th>Fee</th><th>Advance</th></tr></thead><tbody>${rows}</tbody></table></section>`;
}
