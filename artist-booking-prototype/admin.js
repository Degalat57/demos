// admin.js - Artist booking synthetic demo admin view. Demo: simulated payments.
// Pure rendering + pure transition helpers; no network, no auth, no persistence.

export const TRANSITIONS = Object.freeze({
  pending: Object.freeze(["confirmed", "cancelled"]),
  confirmed: Object.freeze(["completed", "cancelled"]),
  completed: Object.freeze([]),
  cancelled: Object.freeze([]),
});

export function canTransition(from, to) {
  return Object.prototype.hasOwnProperty.call(TRANSITIONS, from) && TRANSITIONS[from].includes(to);
}

// Returns a patch for updateState(patch); never mutates the given state.
export function transitionBooking(state, bookingId, to) {
  const bookings = Array.isArray(state?.bookings) ? state.bookings : [];
  const b = bookings.find((x) => x && x.id === bookingId);
  if (!b) throw new Error("unknown booking: " + bookingId);
  if (!canTransition(b.status, to)) throw new Error("illegal transition " + b.status + " -> " + to);
  return { bookings: bookings.map((x) => (x.id === bookingId ? { ...x, status: to } : x)) };
}

function esc(v) {
  return String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Integration repair: authoritative booking.js schema uses time/advance;
// dashboard-mapped records use slot/advancePaise. Accept both.
function slotOf(b) { return b.slot != null ? b.slot : (b.time || ""); }
function advanceOf(b) { return Number.isInteger(b.advancePaise) ? b.advancePaise : b.advance; }

export function formatINR(paise) {
  const n = Number.isSafeInteger(paise) && paise >= 0 ? paise : 0;
  return "\u20B9" + Math.floor(n / 100) + "." + String(n % 100).padStart(2, "0");
}

export function summarize(state) {
  const bookings = Array.isArray(state?.bookings) ? state.bookings.filter((b) => b && typeof b === 'object') : [];
  const byStatus = { pending: 0, confirmed: 0, completed: 0, cancelled: 0 };
  let advance = 0;
  for (const b of bookings) {
    if (Object.prototype.hasOwnProperty.call(byStatus, b.status)) byStatus[b.status] += 1;
    const a = advanceOf(b);
    if (b.status !== "cancelled" && Number.isSafeInteger(a) && a >= 0) {
      if (!Number.isSafeInteger(advance + a)) throw new RangeError('simulated advance exceeds safe range');
      advance += a;
    }
  }
  return { total: bookings.length, byStatus, simulatedAdvancePaise: advance };
}

export function renderAdmin(state) {
  const artists = Array.isArray(state?.artists) ? state.artists : [];
  const bookings = Array.isArray(state?.bookings) ? state.bookings.filter((b) => b && typeof b === 'object') : [];
  const name = (id) => { const a = artists.find((x) => x.id === id); return a ? a.name : id; };
  const s = summarize(state);
  const rows = bookings.map((b) => {
    const actions = (Object.prototype.hasOwnProperty.call(TRANSITIONS, b.status) ? TRANSITIONS[b.status] : [])
      .map((t) => `<button data-booking="${esc(b.id)}" data-to="${esc(t)}">${esc(t)}</button>`).join("");
    return `<tr><td>${esc(b.id)}</td><td>${esc(name(b.artistId))}</td><td>${esc(b.date || "")} ${esc(slotOf(b))}</td><td>${esc(b.status)}</td><td>${formatINR(advanceOf(b))}</td><td>${actions}</td></tr>`;
  }).join("");
  const artistRows = artists.map((a) => {
    const n = bookings.filter((b) => b.artistId === a.id && b.status !== "cancelled").length;
    return `<li>${esc(a.name)} (${n} active)</li>`;
  }).join("");
  return `<section class="admin"><p class="demo-banner">Demo: simulated payments</p>` +
    `<h2>Summary</h2><p>Total ${s.total}; pending ${s.byStatus.pending}; confirmed ${s.byStatus.confirmed}; completed ${s.byStatus.completed}; cancelled ${s.byStatus.cancelled}; simulated advance ${formatINR(s.simulatedAdvancePaise)}</p>` +
    `<h2>Artists</h2><ul>${artistRows}</ul>` +
    `<h2>Bookings</h2><table><thead><tr><th scope="col">Reference</th><th scope="col">Artist</th><th scope="col">Date and time</th><th scope="col">Status</th><th scope="col">Simulated advance</th><th scope="col">Actions</th></tr></thead><tbody>${rows}</tbody></table></section>`;
}
