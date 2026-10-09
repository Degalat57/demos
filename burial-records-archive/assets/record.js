'use strict';
(function () {
  var LABELS = [
    ['record_id', 'Record ID'], ['surname', 'Surname'], ['given_names', 'Given names'],
    ['maiden_name', 'Maiden name'], ['sex', 'Sex'], ['age_at_death', 'Age at death'],
    ['birth_date', 'Birth date'], ['death_date', 'Death date'], ['burial_date', 'Burial date'],
    ['county', 'County'], ['place_of_death', 'Place of death'], ['cemetery', 'Cemetery'],
    ['funeral_cost', 'Funeral cost'], ['informant', 'Informant'],
    ['ledger_book', 'Ledger book'], ['ledger_page', 'Ledger page'],
    ['notes', 'Notes'], ['transcriber', 'Transcriber']
  ];

  var els = {
    notFound: document.getElementById('not-found'),
    view: document.getElementById('record-view'),
    title: document.getElementById('record-title'),
    importedBadge: document.getElementById('imported-badge'),
    nav: document.getElementById('record-nav'),
    prev: document.getElementById('prev-record'),
    next: document.getElementById('next-record'),
    navPos: document.getElementById('record-nav-pos'),
    fields: document.getElementById('record-fields'),
    citation: document.getElementById('citation'),
    copyBtn: document.getElementById('copy-citation'),
    copyStatus: document.getElementById('copy-status'),
    frame: document.getElementById('scan-frame'),
    canvas: document.getElementById('scan-canvas'),
    img: document.getElementById('scan-img'),
    missing: document.getElementById('scan-missing'),
    zoomIn: document.getElementById('zoom-in'),
    zoomOut: document.getElementById('zoom-out'),
    reset: document.getElementById('zoom-reset'),
    rotate: document.getElementById('rotate'),
    openFull: document.getElementById('open-full')
  };

  var citationText = '';

  function fmt(v) {
    return (v === '' || v == null) ? '—' : String(v);
  }

  function renderRecord(rec) {
    document.title = rec.surname + ', ' + rec.given_names +
      ' - Historic Burial Records Archive (demo)';
    els.title.textContent = rec.surname + ', ' + rec.given_names;
    els.importedBadge.hidden = !rec._imported;
    LABELS.forEach(function (pair) {
      var dt = document.createElement('dt');
      dt.textContent = pair[1];
      var dd = document.createElement('dd');
      dd.textContent = fmt(rec[pair[0]]);
      els.fields.appendChild(dt);
      els.fields.appendChild(dd);
    });
    var today = new Date();
    var dateStr = today.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    citationText = 'Historic Burial Records, Ledger ' + rec.ledger_book + ', page ' +
      rec.ledger_page + ', record ' + rec.record_id +
      ' (synthetic sample), accessed ' + dateStr + '.';
    els.citation.textContent = citationText;
    renderNav(rec.record_id);
    renderScan(rec);
  }

  function renderNav(id) {
    var ids = [];
    try { ids = JSON.parse(sessionStorage.getItem('archive-result-ids') || '[]'); }
    catch (e) { return; }
    if (!Array.isArray(ids) || ids.length < 2) return;
    var idx = ids.indexOf(id);
    if (idx < 0) return;
    els.nav.hidden = false;
    els.navPos.textContent = 'Result ' + (idx + 1) + ' of ' + ids.length;
    if (idx > 0) {
      els.prev.href = 'record.html?id=' + encodeURIComponent(ids[idx - 1]);
    } else { els.prev.style.display = 'none'; }
    if (idx < ids.length - 1) {
      els.next.href = 'record.html?id=' + encodeURIComponent(ids[idx + 1]);
    } else { els.next.style.display = 'none'; }
  }

  /* ---- scan viewer ---- */
  var scale = 1, rot = 0, tx = 0, ty = 0;
  var ptrs = new Map();
  var lastDist = 0;

  function apply() {
    els.canvas.style.transform =
      'translate(-50%, -50%) translate(' + tx + 'px, ' + ty + 'px) rotate(' + rot + 'deg) scale(' + scale + ')';
  }

  function setScale(s) {
    scale = Math.min(8, Math.max(0.2, s));
    apply();
  }

  function fitScale() {
    var f = document.getElementById('scan-frame'), w = els.img.naturalWidth, h = els.img.naturalHeight;
    if (!f || !w || !h) return 1;
    return Math.min(f.clientWidth / w, f.clientHeight / h) * 0.95;
  }
  function resetView() { scale = fitScale(); rot = 0; tx = 0; ty = 0; apply(); }

  function ptrDist() {
    var v = Array.from(ptrs.values());
    return Math.hypot(v[0].x - v[1].x, v[0].y - v[1].y);
  }

  function renderScan(rec) {
    if (!rec.scan || rec._imported) {
      els.img.hidden = true;
      els.missing.hidden = false;
      els.missing.textContent = rec._imported
        ? 'No scan is available: this record was added by staff in this browser. In production, scans are uploaded to storage and linked automatically.'
        : 'No scan is available for this record.';
      return;
    }
    var url = 'data/' + rec.scan;
    els.img.alt = 'Ledger scan for record ' + rec.record_id + ': ' + rec.surname +
      ', ' + rec.given_names + ', died ' + rec.death_date + ', ' + rec.county +
      '. Marked SYNTHETIC SAMPLE.';
    els.img.onerror = function () {
      els.img.hidden = true;
      els.missing.hidden = false;
      els.missing.textContent = 'The scan file could not be loaded.';
    };
    els.img.onload = function () { resetView(); };
    els.img.src = url;
    els.openFull.href = url;
  }

  els.zoomIn.addEventListener('click', function () { setScale(scale * 1.25); });
  els.zoomOut.addEventListener('click', function () { setScale(scale / 1.25); });
  els.reset.addEventListener('click', resetView);
  els.rotate.addEventListener('click', function () { rot = (rot + 90) % 360; apply(); });

  els.frame.addEventListener('pointerdown', function (e) {
    els.frame.setPointerCapture(e.pointerId);
    ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (ptrs.size === 2) lastDist = ptrDist();
  });
  els.frame.addEventListener('pointermove', function (e) {
    if (!ptrs.has(e.pointerId)) return;
    if (ptrs.size === 1) {
      var prev = ptrs.get(e.pointerId);
      tx += e.clientX - prev.x;
      ty += e.clientY - prev.y;
      ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      apply();
    } else if (ptrs.size === 2) {
      var p0 = ptrs.get(Array.from(ptrs.keys())[0]);
      ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      var d = ptrDist();
      if (lastDist > 0) setScale(scale * (d / lastDist));
      lastDist = d;
    }
  });
  ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (ev) {
    els.frame.addEventListener(ev, function (e) { ptrs.delete(e.pointerId); });
  });
  els.frame.addEventListener('wheel', function (e) {
    e.preventDefault();
    setScale(scale * (e.deltaY < 0 ? 1.1 : 1 / 1.1));
  }, { passive: false });
  els.frame.addEventListener('keydown', function (e) {
    if (e.key === '+' || e.key === '=') { setScale(scale * 1.25); e.preventDefault(); }
    else if (e.key === '-' || e.key === '_') { setScale(scale / 1.25); e.preventDefault(); }
    else if (e.key === '0') { resetView(); e.preventDefault(); }
  });

  els.copyBtn.addEventListener('click', function () {
    function done(ok) {
      els.copyStatus.textContent = ok ? 'Copied.' : 'Copy failed — select the text manually.';
      setTimeout(function () { els.copyStatus.textContent = ''; }, 2500);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(citationText).then(function () { done(true); },
        function () { done(fallbackCopy()); });
    } else {
      done(fallbackCopy());
    }
  });

  function fallbackCopy() {
    var ta = document.createElement('textarea');
    ta.value = citationText;
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    ta.remove();
    return ok;
  }

  var id = new URLSearchParams(location.search).get('id');
  loadRecords().then(function (records) {
    var rec = null;
    for (var i = 0; i < records.length; i++) {
      if (records[i].record_id === id) { rec = records[i]; break; }
    }
    if (!rec) { els.notFound.hidden = false; return; }
    els.view.hidden = false;
    renderRecord(rec);
  }).catch(function () {
    els.notFound.hidden = false;
    els.notFound.querySelector('p').textContent =
      'The records could not be loaded. Please try again.';
  });
})();
