// Artist booking demo shared booking state. Demo: simulated payments.
// Client-side only: no server, auth, network or real payment.
const STORAGE_KEY = 'artist-booking.state';
const VERSION = 1;
const INITIAL = { version: VERSION, bookings: [], selectedArtistId: null };

function deepFreeze(o) {
  if (o && typeof o === 'object' && !Object.isFrozen(o)) {
    Object.freeze(o);
    for (const k of Object.keys(o)) deepFreeze(o[k]);
  }
  return o;
}
function clone(v) { return v === undefined ? v : JSON.parse(JSON.stringify(v)); }
function validBookings(v) {
  return Array.isArray(v) && v.every((b) => b && typeof b === 'object' && !Array.isArray(b));
}

function safeStorage() {
  try {
    const s = globalThis.localStorage;
    if (!s) return null;
    const t = '__artist-booking_probe__';
    s.setItem(t, t); s.removeItem(t);
    return s;
  } catch { return null; }
}

function load() {
  const s = safeStorage();
  if (!s) return clone(INITIAL);
  try {
    const raw = s.getItem(STORAGE_KEY);
    if (!raw) return clone(INITIAL);
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || parsed.version !== VERSION ||
        !validBookings(parsed.bookings)) return clone(INITIAL);
    return { ...clone(INITIAL), ...parsed, version: VERSION };
  } catch { return clone(INITIAL); }
}

function persist(st) {
  const s = safeStorage();
  if (!s) return false;
  try { s.setItem(STORAGE_KEY, JSON.stringify(st)); return true; } catch { return false; }
}

let state = deepFreeze(load());
const subscribers = new Set();

export function getState() { return state; }

export function updateState(patch) {
  const p = typeof patch === 'function' ? patch(state) : patch;
  if (!p || typeof p !== 'object' || Array.isArray(p)) throw new TypeError('patch must be an object');
  const next = { ...clone(state), ...clone(p), version: VERSION };
  if (!validBookings(next.bookings)) throw new TypeError('bookings must be an array of records');
  if (next.selectedArtistId !== null && typeof next.selectedArtistId !== 'string') {
    throw new TypeError('selectedArtistId must be a string or null');
  }
  state = deepFreeze(next);
  persist(state);
  for (const fn of [...subscribers]) {
    try { fn(state); } catch (e) { /* isolate subscriber errors */ }
  }
  return state;
}

export function subscribe(fn) {
  if (typeof fn !== 'function') throw new TypeError('subscriber must be a function');
  subscribers.add(fn);
  return () => subscribers.delete(fn);
}

export function resetState() {
  return updateState({ ...clone(INITIAL), artists: [] });
}

export const __test = { STORAGE_KEY, VERSION, load };
