// Artist booking demo customer search/filter + artist profile renderer.
// Demo: simulated payments. Fictional roster only; no network calls.
// Package labels use p.label; prices use integer paise and search includes city.
// mountApp owns the application shell; init/mountShell are reusable search views.
// Local assembly wires the actual booking, shared-state and dashboard modules.
import { ARTISTS } from './data.js';
import { getState, updateState, subscribe } from './state.js';
import { quote, createBooking } from './booking.js';
import { renderArtist } from './artist.js';
import { renderAdmin, transitionBooking } from './admin.js';
import { submitBooking, toBookingInput, onReady, localDateISO, availableTimes } from './integration.js';
export function filterArtists(artists, { query = "", genre = "", city = "" } = {}) {
  const q = String(query).trim().toLowerCase();
  return artists.filter((a) =>
    (!q || a.name.toLowerCase().includes(q) || a.genre.toLowerCase().includes(q) || a.city.toLowerCase().includes(q)) &&
    (!genre || a.genre === genre) &&
    (!city || a.city === city));
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export function formatINR(paise) {
  const n = Number.isSafeInteger(paise) && paise >= 0 ? paise : 0;
  return "\u20B9" + Math.floor(n / 100).toLocaleString("en-IN") + "." + String(n % 100).padStart(2, "0");
}

export function renderResults(list) {
  if (!list.length) {
    return '<p class="empty" role="status">No artists match your search. Try clearing filters.</p>';
  }
  return '<ul class="results" aria-label="Artists">' + list.map((a, index) => {
    const initials = a.name.replace(/\(fictional\)/gi, '').trim().split(/\s+/)
      .filter((word) => !['the', 'dj'].includes(word.toLowerCase())).slice(0, 2)
      .map((word) => word[0]).join('').toUpperCase();
    const fees = (a.packages || []).map((p) => p.feePaise).filter((fee) => Number.isSafeInteger(fee) && fee > 0);
    const price = fees.length ? `<span class="price-prefix">From <span class="currency">INR</span></span><strong class="artist-price">${formatINR(Math.min(...fees))}</strong>` : '<span class="price-prefix">Explore packages</span>';
    return `<li><button type="button" class="artist-card tone-${index % 4}" data-id="${esc(a.id)}">` +
      `<span class="artist-art" aria-hidden="true"><span class="art-orbit"></span><span class="artist-initials">${esc(initials)}</span><span class="art-caption">LIVE SESSIONS</span></span>` +
      `<span class="artist-card-body"><span class="artist-badges"><span class="genre-badge">${esc(a.genre)}</span><span class="city-badge">${esc(a.city)}</span></span>` +
      `<span class="artist-name">${esc(a.name)}</span><span class="artist-package-count">${(a.packages || []).length} performance ${(a.packages || []).length === 1 ? 'package' : 'packages'}</span>` +
      `<span class="artist-card-footer"><span class="artist-pricing">${price}</span><span class="artist-action">View artist <span aria-hidden="true">\u2197</span></span></span></span></button></li>`;
  }).join("") + "</ul>";
}

export function renderProfile(a) {
  if (!a) return '<p role="status">Artist not found.</p>';
  const pk = (a.packages || []).map((p) => `<li>${esc(p.label ?? p.id)}: ${formatINR(p.feePaise)}</li>`).join("");
  const sl = (a.slots || []).map((s) => `<li>${esc(s)}</li>`).join("");
  return `<section class="profile" aria-labelledby="pf-h"><h2 id="pf-h" tabindex="-1">${esc(a.name)}</h2>` +
    `<p>${esc(a.genre)} \u00B7 ${esc(a.city)} (fictional artist)</p><ul class="packages">${pk}</ul>` +
    (sl ? `<p class="note">Typical performance times. Select a date to check local demo availability.</p><ul class="slots" aria-label="Typical performance times">${sl}</ul>` : "") +
    '<p class="demo">Demo: simulated payments.</p>' +
    '<button type="button" class="back">Back to results</button></section>';
}

function options(artists, k) {
  return [...new Set(artists.map((a) => a[k]))].sort()
    .map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join("");
}

// Shared controller: form controls + output container.
function wire(form, read, out, artists) {
  let lastId = null;
  const show = () => {
    out.innerHTML = renderResults(filterArtists(artists, read()));
    if (lastId) {
      const sel = typeof CSS !== "undefined" && CSS.escape ? CSS.escape(lastId) : lastId;
      out.querySelector(`[data-id="${sel}"]`)?.focus();
    }
  };
  form.addEventListener("input", () => { lastId = null; show(); });
  form.addEventListener("change", () => { lastId = null; show(); });
  form.addEventListener("submit", (e) => e.preventDefault());
  out.addEventListener("click", (e) => {
    const card = e.target.closest(".artist-card");
    if (card) {
      lastId = card.dataset.id;
      out.innerHTML = renderProfile(artists.find((a) => a.id === lastId));
      out.querySelector("h2")?.focus();
    } else if (e.target.closest(".back")) show();
  });
  out.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && out.querySelector(".profile")) show();
  });
  show();
  return { show };
}

export function init(root, artists) {
  root.innerHTML = '<p class="demo">Demo: simulated payments.</p>' +
    '<form role="search" class="filters"><label>Search <input type="search" name="query"></label>' +
    `<label>Genre <select name="genre"><option value="">All</option>${options(artists, "genre")}</select></label>` +
    `<label>City <select name="city"><option value="">All</option>${options(artists, "city")}</select></label></form>` +
    '<div class="out" aria-live="polite"></div>';
  const form = root.querySelector("form");
  return wire(form, () => Object.fromEntries(new FormData(form)), root.querySelector(".out"), artists);
}

// Binds the existing index.html shell. Returns null if shell IDs are absent.
export function mountShell(doc, artists) {
  const form = doc.getElementById("filters"), q = doc.getElementById("q");
  const g = doc.getElementById("genre"), c = doc.getElementById("city");
  const out = doc.getElementById("artist-list");
  if (!form || !q || !g || !c || !out) return null;
  g.insertAdjacentHTML("beforeend", options(artists, "genre"));
  c.insertAdjacentHTML("beforeend", options(artists, "city"));
  return wire(form, () => ({ query: q.value, genre: g.value, city: c.value }), out, artists);
}

const mounted = new WeakMap();

// Real shell bootstrap. Importing in Node without a document has no side effects.
export function mountApp(doc = globalThis.document, host = globalThis) {
  if (!doc?.getElementById('app')) return null;
  if (mounted.has(doc)) return mounted.get(doc);
  const byId = (id) => doc.getElementById(id);
  const main = byId('app'), filters = byId('filters');
  const genre = byId('genre'), city = byId('city'), query = byId('q');
  genre.innerHTML = '<option value="">All genres</option>' + options(ARTISTS, 'genre');
  city.innerHTML = '<option value="">All cities</option>' + options(ARTISTS, 'city');
  updateState({ artists: ARTISTS });
  let view = 'search';
  const chosenArtist = () => ARTISTS.find((a) => a.id === getState().selectedArtistId) || ARTISTS[0];
  const announce = (message) => { byId('app-status').textContent = message; };
  const results = () => {
    byId('artist-list').innerHTML = renderResults(filterArtists(ARTISTS, {
      query: query.value, genre: genre.value, city: city.value,
    }));
  };
  const dashboards = () => {
    const state = { ...getState(), artists: ARTISTS };
    byId('artist-root').innerHTML = renderArtist(state, chosenArtist().id);
    byId('admin-root').innerHTML = renderAdmin(state);
    const select = byId('dashboard-artist-select');
    select.innerHTML = ARTISTS.map((a) => `<option value="${esc(a.id)}"${a.id === chosenArtist().id ? ' selected' : ''}>${esc(a.name)}</option>`).join('');
  };
  const refreshBookingTimes = () => {
    const form = byId('booking-form');
    if (!form) return;
    const artist = chosenArtist(), date = form.elements.date.value;
    const open = availableTimes(artist, date, getState().bookings);
    const select = form.elements.time, selected = select.value;
    select.disabled = !date || open.length === 0;
    select.innerHTML = `<option value="">${!date ? 'Choose a date first' : open.length ? 'Choose a time' : 'No times left for this date'}</option>` +
      open.map((time) => `<option value="${esc(time)}">${esc(time)}</option>`).join('');
    if (open.includes(selected)) select.value = selected;
  };
  const bookingForm = () => {
    const artist = chosenArtist();
    const today = localDateISO();
    byId('booking-panel').innerHTML = `<h2>${esc(artist.name)}</h2>` +
      '<p>Choose a date, available time and package. This creates a local demo booking only.</p>' +
      `<form id="booking-form" class="booking-form"><label>Date (India local time) <input name="date" type="date" min="${today}" required></label>` +
      '<label>Time <select name="time" required disabled><option value="">Choose a date first</option></select></label>' +
      '<label>Package <select name="packageId" required><option value="">Choose a package</option>' + artist.packages.map((p) => `<option value="${esc(p.id)}">${esc(p.label)} — ${formatINR(p.feePaise)}</option>`).join('') + '</select></label>' +
      '<p id="booking-quote" aria-live="polite">Select a package to see the 20% simulated advance plus the ₹500 platform fee.</p>' +
      '<button type="submit">Confirm simulated booking</button><p id="booking-errors" role="alert"></p></form>';
    refreshBookingTimes();
  };
  const route = () => {
    const [requested, id] = String(host.location?.hash || '#search').slice(1).split('/');
    view = ['search', 'profile', 'booking', 'artist', 'admin'].includes(requested) ? requested : 'search';
    if (id && ARTISTS.some((a) => a.id === id)) updateState({ selectedArtistId: id });
    for (const section of main.querySelectorAll('.view')) section.hidden = section.id !== 'view-' + view;
    for (const link of doc.querySelectorAll('.app-nav a')) {
      if (link.dataset.view === view) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    }
    if (view === 'profile') {
      const artist = chosenArtist();
      byId('view-profile').innerHTML = renderProfile(artist) + `<p><a class="button" href="#booking/${esc(artist.id)}">Choose a slot and book</a></p>`;
    }
    if (view === 'booking') bookingForm();
    dashboards();
  };
  const navigate = (hash) => {
    if (host.location) host.location.hash = hash;
    route();
  };
  filters.addEventListener('submit', (event) => event.preventDefault());
  filters.addEventListener('input', results);
  filters.addEventListener('change', results);
  main.addEventListener('click', (event) => {
    const card = event.target.closest?.('.artist-card');
    if (card) { navigate('#profile/' + card.dataset.id); return; }
    if (event.target.closest?.('.back')) { navigate('#search'); return; }
    const transition = event.target.closest?.('[data-booking][data-to]');
    if (transition) {
      try {
        updateState(transitionBooking(getState(), transition.dataset.booking, transition.dataset.to));
        announce('Demo booking status updated to ' + transition.dataset.to + '.');
      } catch (error) { announce(error.message); }
    }
  });
  main.addEventListener('change', (event) => {
    if (event.target.name === 'date') refreshBookingTimes();
    if (event.target.id === 'dashboard-artist-select') {
      updateState({ selectedArtistId: event.target.value });
    }
    if (event.target.name === 'packageId') {
      const pkg = chosenArtist().packages.find((p) => p.id === event.target.value);
      const total = pkg ? quote(pkg.feePaise) : null;
      byId('booking-quote').textContent = total
        ? `Artist fee ${formatINR(total.total)} · 20% simulated advance ${formatINR(total.advance)} · Platform fee ${formatINR(total.platformFee)} · Simulated due now ${formatINR(total.dueNow)} · Artist balance ${formatINR(total.balance)}.`
        : 'Select a package to see the 20% simulated advance plus the ₹500 platform fee.';
    }
  });
  main.addEventListener('input', (event) => {
    if (event.target.name === 'date') refreshBookingTimes();
  });
  main.addEventListener('submit', (event) => {
    if (event.target.id !== 'booking-form') return;
    event.preventDefault();
    const form = event.target;
    if (!form.reportValidity()) return;
    const input = toBookingInput(chosenArtist(), form.elements.packageId.value, form.elements.date.value, form.elements.time.value);
    const result = submitBooking(input, { getState, updateState, createBooking, artists: ARTISTS });
    if (!result.ok) { byId('booking-errors').textContent = result.errors.join(' '); return; }
    const b = result.booking;
    byId('booking-panel').innerHTML = `<h2>Simulated booking confirmed</h2><p>Reference <strong>${esc(b.id)}</strong></p>` +
      `<p>${esc(b.artistName)} · ${esc(b.date)} at ${esc(b.time)}</p>` +
      `<p>Artist fee: ${formatINR(b.total)}. 20% simulated advance: ${formatINR(b.advance)}. Platform fee: ${formatINR(b.platformFee)}.</p>` +
      `<p><b>Simulated due now: ${formatINR(b.dueNow)}</b>. Artist balance: ${formatINR(b.balance)}.</p>` +
      '<p>No real payment was made. This booking is stored only in this browser.</p><p><a href="#artist">See artist booking</a> · <a href="#admin">See admin booking</a> · <a href="#search">Find another artist</a></p>';
    announce('Simulated booking confirmed. Artist and admin views updated.');
  });
  byId('reset-demo').addEventListener('click', () => {
    if (!host.confirm?.('Delete all local demo bookings and reset this demo?')) return;
    updateState({ bookings: [], selectedArtistId: null });
    filters.reset(); results(); navigate('#search'); announce('Local demo bookings cleared.');
  });
  host.addEventListener?.('hashchange', route);
  const unsubscribe = subscribe(() => { dashboards(); refreshBookingTimes(); });
  const controller = { route, navigate, unsubscribe };
  mounted.set(doc, controller);
  results(); route();
  return controller;
}

onReady(() => mountApp());
