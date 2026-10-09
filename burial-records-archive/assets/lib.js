'use strict';
/* Shared library: data loading, normalisation, fuzzy matching, CSV, validation, storage. */

var ARCHIVE_COUNTIES = ['Ashford', 'Briarwood', 'Calder', 'Elmhurst', 'Fairhaven',
  'Glenmoor', 'Hollis', 'Ivydale', 'Juniper', 'Kestrel', 'Lowell'];
var IMPORT_KEY = 'archive-imports-v1';
var RECORD_FIELDS = ['record_id', 'surname', 'given_names', 'maiden_name', 'sex',
  'age_at_death', 'birth_date', 'death_date', 'burial_date', 'county',
  'place_of_death', 'cemetery', 'funeral_cost', 'informant', 'ledger_book',
  'ledger_page', 'notes', 'transcriber', 'scan'];

/* ---------- storage ---------- */

function getImports() {
  try {
    var v = JSON.parse(localStorage.getItem(IMPORT_KEY) || '[]');
    return Array.isArray(v) ? v : [];
  } catch (e) { return []; }
}

function saveImports(list) {
  localStorage.setItem(IMPORT_KEY, JSON.stringify(list));
}

function clearImports() {
  localStorage.removeItem(IMPORT_KEY);
}

function loadRecords() {
  return fetch('data/records.json').then(function (r) {
    if (!r.ok) throw new Error('Could not load data/records.json');
    return r.json();
  }).then(function (base) {
    var imps = getImports();
    for (var i = 0; i < imps.length; i++) imps[i]._imported = true;
    return base.concat(imps);
  });
}

/* ---------- normalisation ---------- */

function normalize(s) {
  return String(s == null ? '' : s).toLowerCase().normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function soundex(s) {
  s = String(s || '').toLowerCase().replace(/[^a-z]/g, '');
  if (!s) return '';
  var codes = { b: '1', f: '1', p: '1', v: '1', c: '2', g: '2', j: '2', k: '2',
    q: '2', s: '2', x: '2', z: '2', d: '3', t: '3', l: '4', m: '5', n: '5', r: '6' };
  var out = s.charAt(0).toUpperCase();
  var prev = codes[s.charAt(0)] || '';
  for (var i = 1; i < s.length && out.length < 4; i++) {
    var ch = s.charAt(i);
    if (ch === 'h' || ch === 'w') continue;
    var c = codes[ch] || '';
    if (c && c !== prev) out += c;
    prev = c;
  }
  while (out.length < 4) out += '0';
  return out;
}

function dlDistance(a, b) {
  var m = a.length, n = b.length;
  if (m === 0) return n;
  if (n === 0) return m;
  var d = [];
  for (var i = 0; i <= m; i++) { d[i] = [i]; for (var j = 1; j <= n; j++) d[i][j] = 0; }
  for (var j = 0; j <= n; j++) d[0][j] = j;
  for (var i = 1; i <= m; i++) {
    for (var j = 1; j <= n; j++) {
      var cost = a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1;
      var v = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
      if (i > 1 && j > 1 && a.charAt(i - 1) === b.charAt(j - 2) &&
          a.charAt(i - 2) === b.charAt(j - 1)) {
        v = Math.min(v, d[i - 2][j - 2] + 1);
      }
      d[i][j] = v;
    }
  }
  return d[m][n];
}

/* ---------- search ---------- */

function prepareRecord(r) {
  if (r._prepared) return r._prepared;
  var p = {};
  ['surname', 'given_names', 'maiden_name'].forEach(function (f) {
    var toks = normalize(r[f]).split(' ').filter(Boolean);
    p[f] = { toks: toks, sdx: toks.map(soundex) };
  });
  r._prepared = p;
  return p;
}

function tokenMatch(qt, qsdx, field, fuzzy) {
  var best = 0;
  for (var i = 0; i < field.toks.length; i++) {
    var ft = field.toks[i];
    var s = 0;
    if (ft === qt) s = 1;
    else if (ft.indexOf(qt) === 0) s = 0.9;
    else if (fuzzy) {
      if (field.sdx[i] && field.sdx[i] === qsdx) s = Math.max(s, 0.75);
      var d = dlDistance(qt, ft);
      if (qt.length >= 4 && d === 1) s = Math.max(s, 0.7);
      if (qt.length >= 7 && d === 2) s = Math.max(s, 0.5);
    }
    if (s > best) best = s;
  }
  return best;
}

/* search(records, {q, county, yearFrom, yearTo, fuzzy}) -> [{record, score, fuzzy}] */
function search(records, opts) {
  var county = opts.county || '';
  var yF = opts.yearFrom ? parseInt(opts.yearFrom, 10) : null;
  var yT = opts.yearTo ? parseInt(opts.yearTo, 10) : null;
  var fuzzy = !!opts.fuzzy;
  var pool = [];
  for (var i = 0; i < records.length; i++) {
    var r = records[i];
    if (county && r.county !== county) continue;
    var y = r.death_date ? parseInt(String(r.death_date).slice(0, 4), 10) : NaN;
    if (yF && !(y >= yF)) continue;
    if (yT && !(y <= yT)) continue;
    pool.push(r);
  }
  var qn = normalize(opts.q || '');
  if (!qn) {
    return pool.map(function (r) { return { record: r, score: 0, fuzzy: false }; });
  }
  var qts = qn.split(' ').filter(Boolean);
  var qsdx = qts.map(soundex);
  var out = [];
  for (var k = 0; k < pool.length; k++) {
    var rec = pool[k];
    var p = prepareRecord(rec);
    var total = 0, ok = true, fuzzyHit = false;
    for (var t = 0; t < qts.length; t++) {
      var best = 0;
      for (var f = 0; f < 3; f++) {
        var fname = ['surname', 'given_names', 'maiden_name'][f];
        var s = tokenMatch(qts[t], qsdx[t], p[fname], fuzzy);
        if (s > best) best = s;
        if (fuzzy && (s === 0.75 || s === 0.7 || s === 0.5)) fuzzyHit = true;
      }
      if (best === 0) { ok = false; break; }
      total += best;
    }
    if (ok) out.push({ record: rec, score: total / qts.length, fuzzy: fuzzyHit });
  }
  return out;
}

/* ---------- CSV ---------- */

function parseCSV(text) {
  text = String(text == null ? '' : text);
  if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
  var rows = [], row = [], field = '', inQ = false, i, c;
  for (i = 0; i < text.length; i++) {
    c = text.charAt(i);
    if (inQ) {
      if (c === '"') {
        if (text.charAt(i + 1) === '"') { field += '"'; i++; }
        else inQ = false;
      } else field += c;
    } else {
      if (c === '"') inQ = true;
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
      else if (c === '\r') {
        if (text.charAt(i + 1) !== '\n') { row.push(field); rows.push(row); row = []; field = ''; }
      } else field += c;
    }
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row); }
  return rows.filter(function (r) {
    return r.length > 1 || String(r[0] || '').trim() !== '';
  });
}

function csvField(v) {
  v = String(v == null ? '' : v);
  return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
}

function toCSV(rows) {
  return rows.map(function (r) { return r.map(csvField).join(','); }).join('\r\n');
}

var HEADER_ALIASES = {
  'record id': 'record_id', 'id': 'record_id',
  'surname': 'surname', 'last name': 'surname', 'last_name': 'surname', 'family name': 'surname',
  'given names': 'given_names', 'given name': 'given_names', 'first name': 'given_names',
  'first names': 'given_names', 'givennames': 'given_names',
  'maiden name': 'maiden_name',
  'sex': 'sex', 'gender': 'sex',
  'age at death': 'age_at_death', 'age': 'age_at_death',
  'birth date': 'birth_date', 'date of birth': 'birth_date', 'born': 'birth_date',
  'death date': 'death_date', 'date of death': 'death_date', 'died': 'death_date',
  'burial date': 'burial_date', 'date of burial': 'burial_date', 'buried': 'burial_date',
  'county': 'county',
  'place of death': 'place_of_death', 'place': 'place_of_death',
  'cemetery': 'cemetery',
  'funeral cost': 'funeral_cost', 'cost': 'funeral_cost',
  'informant': 'informant',
  'ledger book': 'ledger_book', 'book': 'ledger_book',
  'ledger page': 'ledger_page', 'page': 'ledger_page',
  'notes': 'notes', 'note': 'notes',
  'transcriber': 'transcriber',
  'scan': 'scan', 'scan file': 'scan', 'scan filename': 'scan'
};

function canonicalHeader(h) {
  var k = normalize(h).replace(/\s+/g, ' ');
  if (HEADER_ALIASES[k]) return HEADER_ALIASES[k];
  var k2 = k.replace(/ /g, '_');
  if (HEADER_ALIASES[k2]) return HEADER_ALIASES[k2];
  return k2;
}

/* ---------- dates ---------- */

function daysInMonth(y, m) {
  return [31, (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28,
    31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
}

function validYmd(y, m, d) {
  return y >= 1800 && y <= 2100 && m >= 1 && m <= 12 && d >= 1 && d <= daysInMonth(y, m);
}

/* Returns {ok, empty, iso, msg}. allowYearOnly permits a bare YYYY (birth_date). */
function parseDateValue(v, allowYearOnly) {
  v = String(v == null ? '' : v).trim();
  if (!v) return { ok: true, empty: true, iso: '' };
  var m;
  m = v.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (m) {
    var y = +m[1], mo = +m[2], d = +m[3];
    if (!validYmd(y, mo, d)) return { ok: false, msg: 'Not a real calendar date: "' + v + '"' };
    return { ok: true, iso: y + '-' + String(mo).padStart(2, '0') + '-' + String(d).padStart(2, '0') };
  }
  m = v.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (m) {
    var mo2 = +m[1], d2 = +m[2], y2 = +m[3];
    if (!validYmd(y2, mo2, d2)) return { ok: false, msg: 'Not a real calendar date: "' + v + '"' };
    return { ok: true, iso: y2 + '-' + String(mo2).padStart(2, '0') + '-' + String(d2).padStart(2, '0') };
  }
  m = v.match(/^(\d{4})$/);
  if (m && allowYearOnly) return { ok: true, iso: v };
  return { ok: false, msg: 'Unrecognised date: "' + v + '" (use YYYY-MM-DD or M/D/YYYY' +
    (allowYearOnly ? ' or a 4-digit year' : '') + ')' };
}

/* ---------- import validation ---------- */

/* rows: array of {field: value} with canonical field names.
   existingRecords: full archive (base + imports).
   Returns [{row, record, errors, warnings, status}] */
function validateImport(rows, existingRecords) {
  var existingIds = {};
  existingRecords.forEach(function (r) { existingIds[r.record_id] = true; });
  var fileIds = {};
  var results = [];
  rows.forEach(function (row, idx) {
    var errors = {}, warnings = {};
    var rec = { synthetic: true };
    RECORD_FIELDS.forEach(function (f) {
      rec[f] = row[f] !== undefined ? String(row[f] == null ? '' : row[f]).trim() : '';
    });
    if (!rec.transcriber) rec.transcriber = 'Staff import';

    if (!rec.surname) errors.surname = 'Surname is required';

    var dd = parseDateValue(rec.death_date, false);
    if (dd.empty) errors.death_date = 'Death date is required';
    else if (!dd.ok) errors.death_date = dd.msg;
    else rec.death_date = dd.iso;

    var bd = parseDateValue(rec.birth_date, true);
    if (!bd.ok) errors.birth_date = bd.msg;
    else if (!bd.empty) rec.birth_date = bd.iso;
    if (bd.empty) rec.birth_date = '';

    var bud = parseDateValue(rec.burial_date, false);
    if (!bud.ok) errors.burial_date = bud.msg;
    else if (!bud.empty) {
      rec.burial_date = bud.iso;
      if (dd.ok && !dd.empty && bud.iso < dd.iso) {
        errors.burial_date = 'Burial date is before the death date';
      }
    }
    if (bud.empty) rec.burial_date = '';

    if (!rec.county) errors.county = 'County is required';
    else {
      var found = null;
      for (var i = 0; i < ARCHIVE_COUNTIES.length; i++) {
        if (ARCHIVE_COUNTIES[i].toLowerCase() === rec.county.toLowerCase()) { found = ARCHIVE_COUNTIES[i]; break; }
      }
      if (found) rec.county = found;
      else {
        var best = null, bestD = 99;
        for (var j = 0; j < ARCHIVE_COUNTIES.length; j++) {
          var dist = dlDistance(normalize(rec.county), normalize(ARCHIVE_COUNTIES[j]));
          if (dist < bestD) { bestD = dist; best = ARCHIVE_COUNTIES[j]; }
        }
        errors.county = 'Unknown county "' + rec.county + '" (did you mean ' + best + '?)';
      }
    }

    if (rec.age_at_death !== '') {
      var a = parseInt(rec.age_at_death, 10);
      if (isNaN(a) || a < 0 || a > 120) errors.age_at_death = 'Age must be a number between 0 and 120';
      else rec.age_at_death = a;
    } else rec.age_at_death = '';

    if (rec.ledger_page !== '') {
      var p = parseInt(rec.ledger_page, 10);
      if (isNaN(p) || p < 1) errors.ledger_page = 'Ledger page must be a positive integer';
      else rec.ledger_page = p;
    } else rec.ledger_page = '';

    if (rec.sex) {
      var s = rec.sex.toUpperCase();
      if (s === 'M' || s === 'F') rec.sex = s;
      else warnings.sex = 'Unrecognised sex "' + rec.sex + '" (expected M or F)';
    }

    if (rec.record_id) {
      if (existingIds[rec.record_id]) {
        errors.record_id = 'Duplicate record_id (already in the archive): ' + rec.record_id;
      } else if (fileIds[rec.record_id]) {
        errors.record_id = 'Duplicate record_id within this file: ' + rec.record_id;
      } else fileIds[rec.record_id] = true;
    } else if (dd.ok && !dd.empty) {
      var year = dd.iso.slice(0, 4), seq = 1, id;
      do { id = 'HBR-' + year + '-' + String(seq).padStart(4, '0'); seq++; }
      while (existingIds[id] || fileIds[id]);
      fileIds[id] = true;
      rec.record_id = id;
    } else {
      errors.record_id = 'A record ID cannot be generated without a valid death date';
    }

    if (!rec.place_of_death) warnings.place_of_death = 'Place of death is missing';
    if (!rec.cemetery) warnings.cemetery = 'Cemetery is missing';

    var status = Object.keys(errors).length ? 'error'
      : (Object.keys(warnings).length ? 'warning' : 'ok');
    results.push({ row: idx + 1, record: rec, errors: errors, warnings: warnings, status: status });
  });
  return results;
}

/* ---------- misc ---------- */

function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function downloadText(filename, text, mime) {
  var blob = new Blob([text], { type: mime || 'text/csv;charset=utf-8' });
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}
