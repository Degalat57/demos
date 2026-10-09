'use strict';
(function () {
  var PER_PAGE = 25;
  var records = [];
  var results = [];
  var page = 1;

  var els = {
    form: document.getElementById('search-form'),
    q: document.getElementById('q'),
    county: document.getElementById('county'),
    yearFrom: document.getElementById('year-from'),
    yearTo: document.getElementById('year-to'),
    fuzzy: document.getElementById('fuzzy'),
    sort: document.getElementById('sort'),
    results: document.getElementById('results'),
    count: document.querySelector('[data-testid="result-count"]'),
    empty: document.getElementById('empty-state'),
    pagination: document.getElementById('pagination'),
    prev: document.getElementById('prev-page'),
    next: document.getElementById('next-page'),
    pageInfo: document.getElementById('page-info'),
    exportBtn: document.getElementById('export-csv')
  };

  ARCHIVE_COUNTIES.forEach(function (c) {
    var o = document.createElement('option');
    o.value = c; o.textContent = c;
    els.county.appendChild(o);
  });

  function initFromUrl() {
    var p = new URLSearchParams(location.search);
    els.q.value = p.get('q') || '';
    els.county.value = p.get('county') || '';
    els.yearFrom.value = p.get('year-from') || '';
    els.yearTo.value = p.get('year-to') || '';
    els.fuzzy.checked = p.get('fuzzy') !== '0';
    els.sort.value = p.get('sort') || 'relevance';
    page = Math.max(1, parseInt(p.get('page') || '1', 10) || 1);
  }

  function getOpts() {
    return {
      q: els.q.value,
      county: els.county.value,
      yearFrom: els.yearFrom.value,
      yearTo: els.yearTo.value,
      fuzzy: els.fuzzy.checked
    };
  }

  function syncUrl(push) {
    var p = new URLSearchParams();
    if (els.q.value) p.set('q', els.q.value);
    if (els.county.value) p.set('county', els.county.value);
    if (els.yearFrom.value) p.set('year-from', els.yearFrom.value);
    if (els.yearTo.value) p.set('year-to', els.yearTo.value);
    if (!els.fuzzy.checked) p.set('fuzzy', '0');
    if (els.sort.value !== 'relevance') p.set('sort', els.sort.value);
    if (page > 1) p.set('page', String(page));
    var url = location.pathname + (p.toString() ? '?' + p.toString() : '');
    if (push) history.pushState({}, '', url);
    else history.replaceState({}, '', url);
  }

  function sortResults(list) {
    var mode = els.sort.value;
    var out = list.slice();
    if (mode === 'death-asc' || mode === 'death-desc') {
      out.sort(function (a, b) {
        return mode === 'death-asc'
          ? String(a.record.death_date).localeCompare(String(b.record.death_date))
          : String(b.record.death_date).localeCompare(String(a.record.death_date));
      });
    } else if (mode === 'surname') {
      out.sort(function (a, b) {
        return a.record.surname.localeCompare(b.record.surname, 'en',
          { sensitivity: 'base' });
      });
    } else {
      out.sort(function (a, b) { return b.score - a.score; });
    }
    return out;
  }

  function runSearch(push) {
    var opts = getOpts();
    results = sortResults(search(records, opts));
    var totalPages = Math.max(1, Math.ceil(results.length / PER_PAGE));
    if (page > totalPages) page = totalPages;
    render();
    syncUrl(push);
    try {
      sessionStorage.setItem('archive-result-ids',
        JSON.stringify(results.map(function (r) { return r.record.record_id; })));
    } catch (e) { /* storage unavailable */ }
  }

  function render() {
    var totalPages = Math.max(1, Math.ceil(results.length / PER_PAGE));
    els.count.textContent = results.length + (results.length === 1 ? ' record' : ' records');
    els.results.innerHTML = '';
    els.empty.hidden = results.length !== 0;
    var start = (page - 1) * PER_PAGE;
    var slice = results.slice(start, start + PER_PAGE);
    slice.forEach(function (r) {
      var rec = r.record;
      var art = document.createElement('article');
      art.className = 'result';
      art.setAttribute('data-testid', 'result');
      var html = '<h3><a href="record.html?id=' + encodeURIComponent(rec.record_id) + '">' +
        escapeHtml(rec.surname) + ', ' + escapeHtml(rec.given_names) + '</a></h3>' +
        '<p>Died ' + escapeHtml(rec.death_date) + ' &middot; ' + escapeHtml(rec.county) +
        ' &middot; ' + escapeHtml(rec.cemetery) + '</p><p>';
      if (r.fuzzy) html += '<span class="tag">similar spelling</span>';
      if (rec._imported) html += '<span class="badge badge-import">added by staff (this browser)</span>';
      html += '<span class="tag">SYNTHETIC SAMPLE</span></p>';
      art.innerHTML = html;
      els.results.appendChild(art);
    });
    els.pagination.hidden = totalPages <= 1;
    els.pageInfo.textContent = 'Page ' + page + ' of ' + totalPages;
    els.prev.disabled = page <= 1;
    els.next.disabled = page >= totalPages;
  }

  function exportCsv() {
    var header = RECORD_FIELDS.slice();
    var rows = [header];
    results.forEach(function (r) {
      rows.push(header.map(function (f) { return r.record[f]; }));
    });
    downloadText('historic-burial-records-export.csv', toCSV(rows));
  }

  var debounceTimer = null;
  function debouncedSearch() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () { page = 1; runSearch(false); }, 200);
  }

  els.form.addEventListener('submit', function (e) {
    e.preventDefault();
    page = 1;
    runSearch(true);
  });
  ['input', 'change'].forEach(function (ev) {
    [els.q, els.county, els.yearFrom, els.yearTo, els.fuzzy].forEach(function (el) {
      el.addEventListener(ev, debouncedSearch);
    });
  });
  els.sort.addEventListener('change', function () { runSearch(false); });
  els.prev.addEventListener('click', function () { page--; runSearch(true); window.scrollTo(0, 0); });
  els.next.addEventListener('click', function () { page++; runSearch(true); window.scrollTo(0, 0); });
  els.exportBtn.addEventListener('click', exportCsv);
  window.addEventListener('popstate', function () {
    initFromUrl();
    runSearch(false);
  });

  loadRecords().then(function (r) {
    records = r;
    initFromUrl();
    runSearch(false);
  }).catch(function (err) {
    els.count.textContent = 'Could not load records: ' + err.message;
  });
})();
