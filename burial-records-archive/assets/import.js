'use strict';
(function () {
  var els = {
    file: document.getElementById('csv-file'),
    text: document.getElementById('csv-text'),
    parse: document.getElementById('parse'),
    template: document.getElementById('download-template'),
    parseError: document.getElementById('parse-error'),
    previewSection: document.getElementById('preview-section'),
    table: document.getElementById('preview-table'),
    head: document.getElementById('preview-head'),
    body: document.getElementById('preview-body'),
    summary: document.getElementById('import-summary'),
    importSection: document.getElementById('import-section'),
    importValid: document.getElementById('import-valid'),
    clearImports: document.getElementById('clear-imports'),
    importResult: document.getElementById('import-result'),
    importedCount: document.getElementById('imported-count')
  };

  var baseRecords = [];
  var results = null;

  function refreshBase() {
    return loadRecords().then(function (r) { baseRecords = r; updateImportedCount(); });
  }

  function updateImportedCount() {
    var n = getImports().length;
    els.importedCount.textContent = n
      ? n + ' record' + (n === 1 ? '' : 's') + ' currently imported in this browser.'
      : 'No records imported in this browser yet.';
    if (n) els.importSection.hidden = false;
  }

  function showError(msg) {
    els.parseError.textContent = msg;
    els.parseError.hidden = false;
  }

  function parseCsvText(text) {
    els.parseError.hidden = true;
    results = null;
    var raw;
    try { raw = parseCSV(text); }
    catch (e) { showError('Could not parse CSV: ' + e.message); return; }
    if (raw.length < 2) { showError('The CSV needs a header row and at least one data row.'); return; }
    var headers = raw[0].map(canonicalHeader);
    var rows = [];
    for (var i = 1; i < raw.length; i++) {
      if (!raw[i].some(function (c) { return String(c).trim() !== ''; })) continue;
      var obj = {};
      headers.forEach(function (h, j) { obj[h] = raw[i][j] !== undefined ? raw[i][j] : ''; });
      rows.push(obj);
    }
    if (!rows.length) { showError('No data rows found.'); return; }
    results = validateImport(rows, baseRecords);
    renderPreview();
  }

  function renderPreview() {
    els.previewSection.hidden = false;
    els.importSection.hidden = false;
    var ok = 0, warn = 0, err = 0;
    results.forEach(function (r) {
      if (r.status === 'ok') ok++;
      else if (r.status === 'warning') warn++;
      else err++;
    });
    els.summary.textContent = results.length + ' rows: ' + ok + ' ok, ' +
      warn + ' warning' + (warn === 1 ? '' : 's') + ', ' + err + ' error' + (err === 1 ? '' : 's');

    els.head.innerHTML = '';
    ['Row', 'Status'].concat(RECORD_FIELDS).forEach(function (h) {
      var th = document.createElement('th');
      th.textContent = h;
      els.head.appendChild(th);
    });

    els.body.innerHTML = '';
    results.forEach(function (r) {
      var tr = document.createElement('tr');
      var tdRow = document.createElement('td');
      tdRow.textContent = r.row;
      tr.appendChild(tdRow);
      var tdStatus = document.createElement('td');
      tdStatus.setAttribute('data-testid', 'row-status');
      tdStatus.className = 'status-' + r.status;
      tdStatus.textContent = r.status;
      tr.appendChild(tdStatus);
      RECORD_FIELDS.forEach(function (f) {
        var td = document.createElement('td');
        td.textContent = r.record[f] === '' ? '' : String(r.record[f]);
        if (r.errors[f]) {
          td.className = 'cell-error';
          td.title = r.errors[f];
        } else if (r.warnings[f]) {
          td.className = 'cell-warn';
          td.title = r.warnings[f];
        }
        tr.appendChild(td);
      });
      els.body.appendChild(tr);
    });
  }

  els.file.addEventListener('change', function () {
    var f = els.file.files && els.file.files[0];
    if (!f) return;
    var reader = new FileReader();
    reader.onload = function () { parseCsvText(String(reader.result)); };
    reader.onerror = function () { showError('Could not read the file.'); };
    reader.readAsText(f);
  });

  els.parse.addEventListener('click', function () {
    var t = els.text.value.trim();
    if (!t) { showError('Paste some CSV text first, or choose a file above.'); return; }
    parseCsvText(t);
  });

  els.template.addEventListener('click', function (e) {
    e.preventDefault();
    var header = RECORD_FIELDS.join(',');
    var example = ['HBR-1934-0172', 'Johnson', 'Robert Lee', '', 'M', '62',
      '1872-03-14', '1934-05-02', '1934-05-05', 'Ashford', 'Millbrook',
      'Mt. Zion Cemetery (fictional)', '$45.00', 'Annie Johnson', 'Book 7', '112',
      'Example row for the import template', 'Volunteer A',
      'scans/HBR-1934-0172.svg'].map(csvField).join(',');
    downloadText('import-template.csv', header + '\r\n' + example + '\r\n');
  });

  els.importValid.addEventListener('click', function () {
    if (!results) return;
    var valid = results.filter(function (r) { return r.status !== 'error'; })
      .map(function (r) { return r.record; });
    if (!valid.length) {
      els.importResult.textContent = 'There are no valid rows to import.';
      return;
    }
    var existing = getImports();
    var existingIds = {};
    baseRecords.forEach(function (r) { existingIds[r.record_id] = true; });
    var added = 0;
    valid.forEach(function (rec) {
      if (existingIds[rec.record_id]) return;
      delete rec._prepared;
      existing.push(rec);
      existingIds[rec.record_id] = true;
      added++;
    });
    saveImports(existing);
    refreshBase();
    els.importResult.innerHTML = 'Imported ' + added + ' record' +
      (added === 1 ? '' : 's') + ' into this browser. ' +
      '<a href="index.html">Search the archive</a> to see them (they are badged ' +
      '“added by staff (this browser)”).';
  });

  els.clearImports.addEventListener('click', function () {
    // Two-step confirm in the page (window.confirm is unavailable in some embedded viewers).
    if (els.clearImports.dataset.armed !== '1') {
      els.clearImports.dataset.armed = '1';
      els.clearImports.textContent = 'Click again to remove imported records';
      setTimeout(function () { els.clearImports.dataset.armed = ''; els.clearImports.textContent = 'Clear imported records'; }, 4000);
      return;
    }
    els.clearImports.dataset.armed = ''; els.clearImports.textContent = 'Clear imported records';
    clearImports();
    refreshBase();
    els.importResult.textContent = 'Imported records cleared from this browser.';
  });

  refreshBase();
})();
