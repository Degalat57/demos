/* Digital Vehicle Inspection demo app.
   Sections: helpers | state/storage | toast/modal | router/nav | views | photos | init */
(function () {
  'use strict';

  // ---------- helpers ----------
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  var uid = function (p) { return (p || 'id') + '-' + Math.random().toString(36).slice(2, 9); };
  var fmtTime = function (iso) {
    var d = new Date(iso);
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  };
  var fmtDate = function (iso) {
    var d = new Date(iso);
    return d.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
  };
  var todayKey = function () {
    var d = new Date(); d.setHours(0, 0, 0, 0);
    return d.toISOString().slice(0, 10);
  };
  var isToday = function (iso) { return String(iso).slice(0, 10) === todayKey(); };
  var debounce = function (fn, ms) {
    var t; return function () {
      var a = arguments, c = this;
      clearTimeout(t); t = setTimeout(function () { fn.apply(c, a); }, ms);
    };
  };

  var STATUSES = ['waiting', 'accepted', 'in_progress', 'inspection_complete', 'customer_contacted', 'approved', 'completed'];
  var STATUS_LABELS = {
    waiting: 'Waiting', accepted: 'Accepted', in_progress: 'In Progress',
    inspection_complete: 'Inspection Complete', customer_contacted: 'Customer Contacted',
    approved: 'Approved', completed: 'Completed'
  };
  var STATUS_CLASSES = {
    waiting: 'amber', accepted: 'amber', in_progress: 'blue',
    inspection_complete: 'blue', customer_contacted: 'blue',
    approved: 'green', completed: 'green'
  };
  var GYR = { G: { cls: 'green', label: 'Good' }, Y: { cls: 'amber', label: 'Soon' }, R: { cls: 'red', label: 'Replace' } };
  var OKREC = { ok: { cls: 'green', label: 'OK' }, rec: { cls: 'red', label: 'Recommended' } };
  var REC_LABELS = { ok: 'OK', soon: 'Soon', future: 'Future', now: 'Needs attention now' };
  var SECTIONS = ['tires', 'brakes', 'tpms', 'notes', 'photos'];
  var SECTION_LABELS = { tires: 'Tires', brakes: 'Brakes', tpms: 'TPMS/Susp/Align', notes: 'Notes', photos: 'Photos' };

  var tireStatusFromTread = function (t) {
    if (t == null || t === '') return null;
    t = Number(t);
    if (isNaN(t)) return null;
    if (t >= 6) return 'G';
    if (t >= 4) return 'Y';
    return 'R';
  };
  var padStatusFromMm = function (mm) {
    if (mm == null || mm === '') return null;
    mm = Number(mm);
    if (isNaN(mm)) return null;
    if (mm >= 5) return 'G';
    if (mm >= 3) return 'Y';
    return 'R';
  };
  var rotorToGyr = function (r) { return r === 'good' ? 'G' : r === 'worn' ? 'Y' : r === 'replace' ? 'R' : null; };
  var worst = function (list) {
    if (list.indexOf('R') >= 0) return 'R';
    if (list.indexOf('Y') >= 0) return 'Y';
    if (list.indexOf('G') >= 0) return 'G';
    return null;
  };
  var sectionStatus = function (insp, section) {
    if (section === 'tires') {
      return worst(['LF', 'RF', 'LR', 'RR'].map(function (p) { return insp.tires[p].status; }).filter(Boolean));
    }
    if (section === 'brakes') {
      return worst([padStatusFromMm(insp.brakes.frontPadsMm), padStatusFromMm(insp.brakes.rearPadsMm),
        rotorToGyr(insp.brakes.frontRotor), rotorToGyr(insp.brakes.rearRotor)].filter(Boolean));
    }
    if (section === 'tpms') {
      var l = [];
      if (insp.tpms.status) l.push(insp.tpms.status === 'ok' ? 'G' : 'R');
      if (insp.suspension.status) l.push(insp.suspension.status === 'ok' ? 'G' : 'R');
      if (insp.alignment.status) l.push(insp.alignment.status === 'ok' ? 'G' : 'R');
      return worst(l);
    }
    return null;
  };
  var pill = function (cls, label, extra) {
    return '<span class="pill pill-' + cls + (extra ? ' ' + extra : '') + '">' + esc(label) + '</span>';
  };

  // ---------- state / storage ----------
  var STORE_KEY = 'dvi-demo-v1';
  var state = null;

  function loadState() {
    try {
      var raw = localStorage.getItem(STORE_KEY);
      if (raw) { state = JSON.parse(raw); return; }
    } catch (e) { /* fall through to seed */ }
    resetState();
  }
  function resetState() {
    state = JSON.parse(JSON.stringify(window.DVI_SEED));
    saveState();
  }
  function saveState() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); }
    catch (e) { toast('Storage full — could not save'); }
  }
  var saveSoon = debounce(saveState, 300);

  function getJob(id) { return state.jobs.find(function (j) { return j.id === id; }); }
  function getInspection(id) { return state.inspections.find(function (i) { return i.id === id; }); }
  function getVehicle(id) { return state.vehicles.find(function (v) { return v.id === id; }); }
  function getCustomer(id) { return state.customers.find(function (c) { return c.id === id; }); }
  function inspForJob(job) { return job.inspectionId ? getInspection(job.inspectionId) : null; }

  function advanceJob(job, status, by) {
    job.status = status;
    job.timeline.push({ status: status, at: new Date().toISOString(), by: by || job.tech || null });
    saveState();
  }

  // ---------- toast / modal ----------
  var toastTimer = null;
  function toast(msg) {
    var t = $('#toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('show'); }, 1800);
  }
  function openModal(html) {
    var root = $('#modal-root');
    root.innerHTML = '<div class="modal-backdrop" data-close="1"><div class="modal" role="dialog" aria-modal="true">' + html + '</div></div>';
    root.querySelector('.modal-backdrop').addEventListener('click', function (e) {
      if (e.target.getAttribute('data-close')) closeModal();
    });
    document.addEventListener('keydown', escClose);
  }
  function escClose(e) { if (e.key === 'Escape') closeModal(); }
  function closeModal() {
    $('#modal-root').innerHTML = '';
    document.removeEventListener('keydown', escClose);
  }

  // ---------- router / nav ----------
  var routes = [
    { re: /^#\/today$/, view: viewToday, chrome: true },
    { re: /^#\/new$/, view: viewNew, chrome: true },
    { re: /^#\/job\/([\w-]+)$/, view: viewJob, chrome: true },
    { re: /^#\/inspect\/([\w-]+)\/(\w+)$/, view: viewInspect, chrome: true },
    { re: /^#\/summary\/([\w-]+)$/, view: viewSummary, chrome: true },
    { re: /^#\/r\/([\w-]+)$/, view: viewReport, chrome: false },
    { re: /^#\/sheet\/([\w-]+)$/, view: viewSheet, chrome: false },
    { re: /^#\/search$/, view: viewSearch, chrome: true },
    { re: /^#\/settings$/, view: viewSettings, chrome: true }
  ];

  function navigate(hash) { location.hash = hash; }

  function render() {
    var hash = location.hash || '#/today';
    if (hash === '#' || hash === '') hash = '#/today';
    var m, route = null, args = [];
    for (var i = 0; i < routes.length; i++) {
      m = hash.match(routes[i].re);
      if (m) { route = routes[i]; args = m.slice(1); break; }
    }
    var chrome = route ? route.chrome : true;
    renderChrome(chrome);
    var main = $('#view');
    if (!route) { main.innerHTML = notFound(); return; }
    route.view.apply(null, [main].concat(args));
    main.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  function notFound() {
    return '<section class="card"><h2>Page not found</h2><p><a href="#/today">Go to Today\'s Jobs</a></p></section>';
  }

  function renderChrome(chrome) {
    var header = $('#shop-header'), nav = $('#main-nav');
    var cfg = window.DVI_CONFIG;
    if (!chrome) {
      header.innerHTML = ''; header.style.display = 'none';
      nav.innerHTML = ''; nav.style.display = 'none';
      document.body.classList.add('no-nav');
      return;
    }
    document.body.classList.remove('no-nav');
    header.style.display = '';
    nav.style.display = '';
    header.innerHTML =
      '<div class="header-inner">' +
      '<div class="brand"><svg class="brand-icon" aria-hidden="true"><use href="#i-tire"/></svg>' +
      '<div><h1>' + esc(cfg.shopName) + '</h1><p class="tagline">' + esc(cfg.tagline) + '</p></div></div>' +
      '<a class="phone-link" href="tel:' + esc(cfg.phone) + '">' + esc(cfg.phone) + '</a>' +
      '</div>';
    var items = [['today', '#/today', 'Today'], ['new', '#/new', 'New'], ['search', '#/search', 'Search'], ['settings', '#/settings', 'Settings']];
    var cur = (location.hash || '#/today').split('/')[1] || 'today';
    nav.innerHTML = '<ul>' + items.map(function (it) {
      return '<li><a href="' + it[1] + '" data-testid="nav-' + it[0] + '" class="nav-link' + (cur === it[0] ? ' active' : '') + '">' +
        '<svg class="nav-icon" aria-hidden="true"><use href="#i-' + it[0] + '"/></svg><span>' + it[2] + '</span></a></li>';
    }).join('') + '</ul>';
  }

  // ---------- shared fragments ----------
  function svgDefs() {
    return '<svg style="display:none" aria-hidden="true">' +
      '<symbol id="i-tire" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4" stroke="currentColor" stroke-width="2"/></symbol>' +
      '<symbol id="i-today" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="17" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 9h18M8 2v4M16 2v4" stroke="currentColor" stroke-width="2"/></symbol>' +
      '<symbol id="i-new" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></symbol>' +
      '<symbol id="i-search" viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M15.5 15.5L21 21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></symbol>' +
      '<symbol id="i-settings" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1" stroke="currentColor" stroke-width="2"/></symbol>' +
      '<symbol id="i-camera" viewBox="0 0 24 24"><path d="M4 8h3l2-2h6l2 2h3v12H4z" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="13" r="3.5" fill="none" stroke="currentColor" stroke-width="2"/></symbol>' +
      '<symbol id="i-check" viewBox="0 0 24 24"><path d="M4 12l5 5L20 6" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"/></symbol>' +
      '</svg>';
  }

  function jobCard(job) {
    var v = getVehicle(job.vehicleId), c = getCustomer(job.customerId);
    var tech = job.tech ? '<span class="avatar" title="' + esc(job.tech) + '">' + esc(job.tech[0]) + '</span>' : '';
    return '<a class="card job-card" data-testid="job-card" href="#/job/' + job.id + '">' +
      '<div class="job-top"><span class="veh">' + esc(v.year) + ' ' + esc(v.make) + ' ' + esc(v.model) + '</span>' +
      pill(STATUS_CLASSES[job.status], STATUS_LABELS[job.status]) + '</div>' +
      '<div class="plate">' + esc(v.plate) + '</div>' +
      '<div class="job-meta"><span>' + esc(c.name) + '</span><span>' + fmtTime(job.scheduledAt) + '</span></div>' +
      '<div class="complaint">' + esc(job.complaint) + '</div>' +
      '<div class="job-bottom">' + tech + '<span class="link-hint">Open job →</span></div>' +
      '</a>';
  }

  // ---------- view: today ----------
  function viewToday(main) {
    var cfg = window.DVI_CONFIG;
    var today = new Date().toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    var jobs = state.jobs.filter(function (j) { return isToday(j.scheduledAt); });
    var groups = {
      waiting: jobs.filter(function (j) { return j.status === 'waiting'; }),
      in_progress: jobs.filter(function (j) { return ['accepted', 'in_progress', 'inspection_complete', 'customer_contacted', 'approved'].indexOf(j.status) >= 0; }),
      completed: jobs.filter(function (j) { return j.status === 'completed'; })
    };
    main.innerHTML = svgDefs() +
      '<div class="page-head"><h2>Today\'s Jobs</h2><p class="date-line">' + esc(today) + '</p></div>' +
      '<div class="tabs" role="tablist">' +
      ['waiting', 'in_progress', 'completed'].map(function (k) {
        return '<button type="button" role="tab" data-testid="tab-' + k + '" class="tab' + (k === 'waiting' ? ' active' : '') +
          '" aria-selected="' + (k === 'waiting') + '">' + (k === 'in_progress' ? 'In Progress' : k === 'waiting' ? 'Waiting' : 'Completed') +
          ' <span class="count">' + groups[k].length + '</span></button>';
      }).join('') +
      '</div>' +
      '<div class="job-list" id="job-list"></div>' +
      '<div class="actions"><a class="btn btn-primary" data-testid="new-vehicle" href="#/new">+ New Vehicle</a></div>';

    var list = $('#job-list');
    function show(k) {
      list.innerHTML = groups[k].length ? groups[k].map(jobCard).join('') :
        '<p class="empty">No jobs in this tab today.</p>';
    }
    show('waiting');
    $$('.tab', main).forEach(function (tab) {
      tab.addEventListener('click', function () {
        $$('.tab', main).forEach(function (t) { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); });
        tab.classList.add('active'); tab.setAttribute('aria-selected', 'true');
        show(tab.getAttribute('data-testid').replace('tab-', ''));
      });
    });
  }

  // ---------- view: new ----------
  function viewNew(main) {
    var years = [];
    var maxYear = new Date().getFullYear() + 1;
    for (var y = maxYear; y >= 1990; y--) years.push(y);
    var makes = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Nissan', 'Subaru', 'Hyundai', 'Kia', 'Volkswagen', 'BMW', 'Mercedes-Benz', 'Mazda', 'Jeep', 'Dodge', 'GMC', 'Tesla'];
    main.innerHTML = svgDefs() +
      '<div class="page-head"><h2>New Vehicle / Work Order</h2></div>' +
      '<form id="new-form" class="card form" novalidate>' +
      '<h3>Customer</h3>' +
      '<div class="grid2">' +
      '<div class="field"><label for="cust-name">Name *</label><input id="cust-name" name="cust-name" autocomplete="off" required></div>' +
      '<div class="field"><label for="cust-phone">Phone *</label><input id="cust-phone" name="cust-phone" type="tel" autocomplete="off" required></div>' +
      '</div>' +
      '<h3>Vehicle</h3>' +
      '<div class="grid2">' +
      '<div class="field"><label for="veh-year">Year</label><select id="veh-year" name="veh-year"><option value="">—</option>' +
      years.map(function (y) { return '<option value="' + y + '">' + y + '</option>'; }).join('') + '</select></div>' +
      '<div class="field"><label for="veh-make">Make</label><input id="veh-make" name="veh-make" list="makes-list" autocomplete="off"><datalist id="makes-list">' +
      makes.map(function (m) { return '<option value="' + esc(m) + '"></option>'; }).join('') + '</datalist></div>' +
      '<div class="field"><label for="veh-model">Model</label><input id="veh-model" name="veh-model" autocomplete="off"></div>' +
      '<div class="field"><label for="veh-plate">Plate *</label><input id="veh-plate" name="veh-plate" autocomplete="off" required></div>' +
      '<div class="field"><label for="veh-mileage">Mileage</label><input id="veh-mileage" name="veh-mileage" type="number" min="0" inputmode="numeric" autocomplete="off"></div>' +
      '</div>' +
      '<div class="field"><label for="complaint">Complaint / reason for visit</label><textarea id="complaint" name="complaint" rows="3"></textarea></div>' +
      '<div id="match-hint" class="match-hint" aria-live="polite"></div>' +
      '<div id="form-errors" role="alert" class="form-errors"></div>' +
      '<div class="actions"><button type="submit" class="btn btn-primary" data-testid="create-work-order">Create Work Order</button></div>' +
      '</form>';

    var phoneIn = $('#cust-phone'), plateIn = $('#veh-plate'), hint = $('#match-hint');
    function matchHint() {
      hint.innerHTML = '';
      var digits = phoneIn.value.replace(/\D/g, '');
      var c = digits.length >= 6 ? state.customers.find(function (x) { return x.phone.replace(/\D/g, '').indexOf(digits) >= 0; }) : null;
      if (c) {
        hint.innerHTML = 'Existing customer: ' + esc(c.name) + ' <button type="button" class="btn btn-small" id="use-cust">Use existing</button>';
        $('#use-cust').addEventListener('click', function () {
          $('#cust-name').value = c.name; phoneIn.value = c.phone; hint.innerHTML = '';
        });
        return;
      }
      var p = plateIn.value.trim();
      if (p) {
        var v = state.vehicles.find(function (x) { return x.plate.toLowerCase() === p.toLowerCase(); });
        if (v) {
          var vc = getCustomer(v.customerId);
          hint.innerHTML = 'Existing vehicle: ' + esc(v.year + ' ' + v.make + ' ' + v.model) + ' (' + esc(vc.name) + ') <button type="button" class="btn btn-small" id="use-veh">Use existing</button>';
          $('#use-veh').addEventListener('click', function () {
            $('#cust-name').value = vc.name; phoneIn.value = vc.phone;
            $('#veh-year').value = v.year; $('#veh-make').value = v.make; $('#veh-model').value = v.model;
            plateIn.value = v.plate; $('#veh-mileage').value = v.mileage; hint.innerHTML = '';
          });
        }
      }
    }
    phoneIn.addEventListener('input', matchHint);
    plateIn.addEventListener('input', matchHint);

    $('#new-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var errs = $('#form-errors');
      var name = $('#cust-name').value.trim(), phone = phoneIn.value.trim(), plate = plateIn.value.trim();
      var missing = [];
      if (!name) missing.push('Name is required');
      if (!phone) missing.push('Phone is required');
      if (!plate) missing.push('Plate is required');
      if (missing.length) { errs.innerHTML = missing.map(function (m) { return '<p>⚠ ' + esc(m) + '</p>'; }).join(''); return; }
      errs.innerHTML = '';
      var cust = state.customers.find(function (x) { return x.phone.replace(/\D/g, '') === phone.replace(/\D/g, ''); });
      if (!cust) { cust = { id: uid('c'), name: name, phone: phone }; state.customers.push(cust); }
      var veh = state.vehicles.find(function (x) { return x.plate.toLowerCase() === plate.toLowerCase(); });
      if (!veh) {
        veh = { id: uid('v'), customerId: cust.id, year: Number($('#veh-year').value) || new Date().getFullYear(),
          make: $('#veh-make').value.trim() || 'Unknown', model: $('#veh-model').value.trim() || 'Unknown',
          plate: plate, mileage: Number($('#veh-mileage').value) || 0 };
        state.vehicles.push(veh);
      }
      var job = { id: uid('j'), vehicleId: veh.id, customerId: cust.id,
        complaint: $('#complaint').value.trim() || 'General inspection',
        scheduledAt: new Date().toISOString(), status: 'waiting', tech: null,
        timeline: [{ status: 'waiting', at: new Date().toISOString(), by: null }], inspectionId: null };
      state.jobs.push(job);
      saveState();
      toast('Work order created');
      navigate('#/job/' + job.id);
    });
  }

  // ---------- view: job detail ----------
  function viewJob(main, jobId) {
    var job = getJob(jobId);
    if (!job) { main.innerHTML = notFound(); return; }
    var v = getVehicle(job.vehicleId), c = getCustomer(job.customerId);
    var insp = inspForJob(job);
    var reached = {};
    job.timeline.forEach(function (t) { reached[t.status] = t; });

    var controls = '';
    if (job.status === 'waiting') {
      controls = '<div class="field inline"><label for="tech-select">Technician</label><select id="tech-select">' +
        '<option value="">— choose —</option>' + state.techs.map(function (t) { return '<option value="' + esc(t) + '">' + esc(t) + '</option>'; }).join('') +
        '</select></div><div class="actions"><button type="button" class="btn btn-primary" data-testid="accept-job">Accept Job</button></div>';
    } else if (job.status === 'accepted') {
      controls = '<div class="actions"><button type="button" class="btn btn-primary" data-testid="start-inspection">Start Inspection</button></div>';
    } else if (job.status === 'in_progress') {
      controls = '<div class="actions"><a class="btn btn-primary" href="#/inspect/' + insp.id + '/tires">Continue Inspection</a></div>';
    } else if (job.status === 'inspection_complete') {
      controls = '<div class="actions"><a class="btn" data-testid="view-report" href="#/summary/' + insp.id + '">View Report</a>' +
        '<button type="button" class="btn btn-primary" data-testid="mark-contacted">Mark customer contacted</button></div>';
    } else if (job.status === 'customer_contacted') {
      controls = '<div class="actions"><a class="btn" data-testid="view-report" href="#/summary/' + insp.id + '">View Report</a>' +
        '<button type="button" class="btn btn-primary" data-testid="customer-approved">Customer approved</button></div>';
    } else if (job.status === 'approved') {
      controls = '<div class="actions"><a class="btn" data-testid="view-report" href="#/summary/' + insp.id + '">View Report</a>' +
        '<button type="button" class="btn btn-primary" data-testid="complete-job">Complete job</button></div>';
    } else if (job.status === 'completed' && insp) {
      controls = '<div class="actions"><a class="btn" data-testid="view-report" href="#/summary/' + insp.id + '">View Report</a>' +
        '<a class="btn" href="#/sheet/' + insp.id + '">Print filled sheet</a></div>';
    }

    main.innerHTML = svgDefs() +
      '<div class="page-head"><a class="back" href="#/today">← Today</a><h2>' + esc(v.year) + ' ' + esc(v.make) + ' ' + esc(v.model) + '</h2></div>' +
      '<div class="card">' +
      '<div class="grid2">' +
      '<p><strong>Plate:</strong> ' + esc(v.plate) + '</p>' +
      '<p><strong>Mileage:</strong> ' + esc(v.mileage.toLocaleString()) + '</p>' +
      '<p><strong>Customer:</strong> ' + esc(c.name) + '</p>' +
      '<p><strong>Phone:</strong> <a href="tel:' + esc(c.phone) + '">' + esc(c.phone) + '</a></p>' +
      '<p><strong>Scheduled:</strong> ' + fmtTime(job.scheduledAt) + '</p>' +
      '<p><strong>Status:</strong> ' + pill(STATUS_CLASSES[job.status], STATUS_LABELS[job.status]) + '</p>' +
      '</div>' +
      '<p><strong>Complaint:</strong> ' + esc(job.complaint) + '</p>' +
      (job.tech ? '<p><strong>Technician:</strong> ' + esc(job.tech) + '</p>' : '') +
      '</div>' +
      '<div class="card"><h3>Status timeline</h3><ol class="timeline" data-testid="timeline">' +
      STATUSES.map(function (s) {
        var r = reached[s];
        return '<li class="' + (r ? 'done' : '') + '">' +
          (r ? '<svg class="check" aria-hidden="true"><use href="#i-check"/></svg>' : '<span class="check-dot" aria-hidden="true"></span>') +
          '<span class="tl-label">' + STATUS_LABELS[s] + '</span>' +
          (r ? '<span class="tl-time">' + fmtTime(r.at) + (r.by ? ' · ' + esc(r.by) : '') + '</span>' : '') +
          '</li>';
      }).join('') + '</ol></div>' +
      '<div class="card">' + controls + '</div>';

    var acceptBtn = $('[data-testid="accept-job"]', main);
    if (acceptBtn) acceptBtn.addEventListener('click', function () {
      var t = $('#tech-select').value;
      if (!t) { toast('Choose a technician first'); return; }
      job.tech = t;
      advanceJob(job, 'accepted', t);
      toast('Job accepted by ' + t);
      render();
    });
    var startBtn = $('[data-testid="start-inspection"]', main);
    if (startBtn) startBtn.addEventListener('click', function () {
      var insp2 = inspForJob(job);
      if (!insp2) {
        insp2 = blankInspection(job);
        state.inspections.push(insp2);
        job.inspectionId = insp2.id;
      }
      advanceJob(job, 'in_progress');
      navigate('#/inspect/' + insp2.id + '/tires');
    });
    var mc = $('[data-testid="mark-contacted"]', main);
    if (mc) mc.addEventListener('click', function () { advanceJob(job, 'customer_contacted'); toast('Customer contacted'); render(); });
    var ca = $('[data-testid="customer-approved"]', main);
    if (ca) ca.addEventListener('click', function () { advanceJob(job, 'approved'); toast('Customer approved'); render(); });
    var cj = $('[data-testid="complete-job"]', main);
    if (cj) cj.addEventListener('click', function () { advanceJob(job, 'completed'); toast('Job completed'); render(); });
  }

  function blankInspection(job) {
    var v = getVehicle(job.vehicleId);
    return {
      id: uid('i'), jobId: job.id, vehicleId: job.vehicleId,
      date: todayKey(), tech: job.tech || '',
      tires: { LF: { tread: null, status: null }, RF: { tread: null, status: null }, LR: { tread: null, status: null }, RR: { tread: null, status: null }, notes: '' },
      brakes: { frontPadsMm: null, frontRotor: null, rearPadsMm: null, rearRotor: null },
      tpms: { status: null, tpmNumber: '' },
      suspension: { status: null, items: { innerTieRod: false, outerTieRod: false, controlArm: false, shock: false, strut: false, other: false }, otherText: '' },
      alignment: { status: null, alg: null },
      notes: '',
      recommended: { tires: null, alignment: null, tpms: null, brakes: null, suspension: null },
      photos: []
    };
  }

  // ---------- view: inspect ----------
  function viewInspect(main, inspId, section) {
    var insp = getInspection(inspId);
    if (!insp || SECTIONS.indexOf(section) < 0) { main.innerHTML = notFound(); return; }
    var idx = SECTIONS.indexOf(section);

    var body = '';
    if (section === 'tires') body = tiresForm(insp);
    else if (section === 'brakes') body = brakesForm(insp);
    else if (section === 'tpms') body = tpmsForm(insp);
    else if (section === 'notes') body = notesForm(insp);
    else body = photosForm(insp);

    main.innerHTML = svgDefs() +
      '<div class="page-head"><a class="back" href="#/job/' + esc(insp.jobId) + '">← Job</a><h2>Inspection — ' + esc(SECTION_LABELS[section]) + '</h2></div>' +
      '<div class="section-tabs" data-testid="section-tabs" role="tablist">' +
      SECTIONS.map(function (s) {
        return '<a class="section-tab' + (s === section ? ' active' : '') + '" role="tab" aria-selected="' + (s === section) +
          '" href="#/inspect/' + insp.id + '/' + s + '">' + esc(SECTION_LABELS[s]) + '</a>';
      }).join('') + '</div>' +
      '<div class="card">' + body + '</div>' +
      '<div class="actions pager">' +
      (idx > 0 ? '<a class="btn" href="#/inspect/' + insp.id + '/' + SECTIONS[idx - 1] + '">← Back</a>' : '') +
      (idx < SECTIONS.length - 1 ? '<a class="btn btn-primary" href="#/inspect/' + insp.id + '/' + SECTIONS[idx + 1] + '">Next →</a>'
        : '<button type="button" class="btn btn-primary" data-testid="finish-inspection">Finish inspection</button>') +
      '</div>';

    bindInspectEvents(main, insp, section);

    var fin = $('[data-testid="finish-inspection"]', main);
    if (fin) fin.addEventListener('click', function () {
      var job = getJob(insp.jobId);
      if (job && job.status === 'in_progress') advanceJob(job, 'inspection_complete');
      toast('Inspection complete');
      navigate('#/summary/' + insp.id);
    });
  }

  function tireBox(insp, pos) {
    var t = insp.tires[pos];
    var suggested = tireStatusFromTread(t.tread);
    return '<div class="wheel-box" data-testid="tire-' + pos + '">' +
      '<h4>' + pos + '</h4>' +
      '<div class="field"><label for="tread-' + pos + '">Tread /32</label>' +
      '<input id="tread-' + pos + '" class="tread-input" data-tire="' + pos + '" type="number" inputmode="numeric" min="0" max="20" value="' + (t.tread != null ? esc(t.tread) : '') + '"></div>' +
      '<div class="gyr-row" role="group" aria-label="' + pos + ' status">' +
      ['G', 'Y', 'R'].map(function (s) {
        return '<button type="button" class="btn gyr gyr-' + s + (t.status === s ? ' selected' : '') +
          '" data-tire="' + pos + '" data-status="' + s + '" aria-pressed="' + (t.status === s) + '">' + GYR[s].label + '</button>';
      }).join('') + '</div>' +
      (suggested ? '<p class="hint">Suggested: ' + GYR[suggested].label + '</p>' : '') +
      '<button type="button" class="btn btn-small cam-btn" data-cam="tires"><svg class="nav-icon" aria-hidden="true"><use href="#i-camera"/></svg> Photo</button>' +
      '</div>';
  }
  function tiresForm(insp) {
    return '<div class="car-diagram">' +
      '<div class="wheel-grid">' + ['LF', 'RF', 'LR', 'RR'].map(function (p) { return tireBox(insp, p); }).join('') + '</div>' +
      '</div>' +
      '<div class="field"><label for="tire-notes">Tire notes</label><textarea id="tire-notes" rows="3">' + esc(insp.tires.notes) + '</textarea></div>';
  }

  function rotorButtons(insp, end) {
    var val = end === 'front' ? insp.brakes.frontRotor : insp.brakes.rearRotor;
    return '<div class="gyr-row" role="group" aria-label="' + end + ' rotor">' +
      ['good', 'worn', 'replace'].map(function (r) {
        var s = rotorToGyr(r);
        return '<button type="button" class="btn gyr gyr-' + s + (val === r ? ' selected' : '') +
          '" data-rotor="' + end + '" data-val="' + r + '" aria-pressed="' + (val === r) + '">' +
          (r === 'good' ? 'Good' : r === 'worn' ? 'Worn' : 'Replace') + '</button>';
      }).join('') + '</div>';
  }
  function brakesForm(insp) {
    var fp = padStatusFromMm(insp.brakes.frontPadsMm), rp = padStatusFromMm(insp.brakes.rearPadsMm);
    return '<div class="grid2">' +
      '<div><h4>Front</h4>' +
      '<div class="field"><label for="front-pads">Front pads (mm)</label>' +
      '<input id="front-pads" type="number" inputmode="decimal" min="0" max="20" value="' + (insp.brakes.frontPadsMm != null ? esc(insp.brakes.frontPadsMm) : '') + '"></div>' +
      (fp ? '<p class="hint">Pad status: ' + pill(GYR[fp].cls, GYR[fp].label) + '</p>' : '') +
      '<p class="label-like">Front rotor</p>' + rotorButtons(insp, 'front') + '</div>' +
      '<div><h4>Rear</h4>' +
      '<div class="field"><label for="rear-pads">Rear pads (mm)</label>' +
      '<input id="rear-pads" type="number" inputmode="decimal" min="0" max="20" value="' + (insp.brakes.rearPadsMm != null ? esc(insp.brakes.rearPadsMm) : '') + '"></div>' +
      (rp ? '<p class="hint">Pad status: ' + pill(GYR[rp].cls, GYR[rp].label) + '</p>' : '') +
      '<p class="label-like">Rear rotor</p>' + rotorButtons(insp, 'rear') + '</div>' +
      '</div>';
  }

  function tpmsForm(insp) {
    var susItems = [['innerTieRod', 'Inner Tie Rod'], ['outerTieRod', 'Outer Tie Rod'], ['controlArm', 'Control Arm'], ['shock', 'Shock'], ['strut', 'Strut'], ['other', 'Other']];
    return '<h4>TPMS</h4>' +
      '<div class="gyr-row" role="group" aria-label="TPMS status">' +
      ['ok', 'rec'].map(function (s) {
        return '<button type="button" class="btn okrec' + (insp.tpms.status === s ? ' selected' : '') +
          '" data-tpms="' + s + '" aria-pressed="' + (insp.tpms.status === s) + '">' + OKREC[s].label + '</button>';
      }).join('') + '</div>' +
      '<div class="field"><label for="tpm-number">TPM #</label><input id="tpm-number" value="' + esc(insp.tpms.tpmNumber) + '"></div>' +
      '<h4>Suspension</h4>' +
      '<div class="gyr-row" role="group" aria-label="Suspension status">' +
      ['ok', 'rec'].map(function (s) {
        return '<button type="button" class="btn okrec' + (insp.suspension.status === s ? ' selected' : '') +
          '" data-susp="' + s + '" aria-pressed="' + (insp.suspension.status === s) + '">' + OKREC[s].label + '</button>';
      }).join('') + '</div>' +
      '<fieldset class="check-grid"><legend>Suspension items</legend>' +
      susItems.map(function (it) {
        return '<label class="check"><input type="checkbox" data-sus-item="' + it[0] + '"' + (insp.suspension.items[it[0]] ? ' checked' : '') + '> ' + it[1] + '</label>';
      }).join('') + '</fieldset>' +
      '<div class="field"><label for="sus-other-text">Other (describe)</label><input id="sus-other-text" value="' + esc(insp.suspension.otherText) + '"></div>' +
      '<h4>Alignment</h4>' +
      '<div class="gyr-row" role="group" aria-label="Alignment status">' +
      ['ok', 'rec'].map(function (s) {
        return '<button type="button" class="btn okrec' + (insp.alignment.status === s ? ' selected' : '') +
          '" data-align="' + s + '" aria-pressed="' + (insp.alignment.status === s) + '">' + OKREC[s].label + '</button>';
      }).join('') + '</div>' +
      '<fieldset><legend>ALG</legend><div class="gyr-row">' +
      ['79', '89', '99', '120'].map(function (a) {
        return '<label class="check radio"><input type="radio" name="alg" value="' + a + '"' + (insp.alignment.alg === a ? ' checked' : '') + '> $' + a + '</label>';
      }).join('') + '</div></fieldset>';
  }

  function notesForm(insp) {
    var rows = [['tires', 'Tires'], ['alignment', 'Alignment'], ['tpms', 'TPMS'], ['brakes', 'Brakes'], ['suspension', 'Suspension']];
    var cols = [['ok', 'OK'], ['soon', 'Soon'], ['future', 'Future'], ['now', 'Now']];
    return '<div class="field"><label for="insp-notes">Notes</label><textarea id="insp-notes" rows="5">' + esc(insp.notes) + '</textarea></div>' +
      '<h4>Recommended repairs</h4>' +
      '<table class="rec-table"><thead><tr><th scope="col"></th>' +
      cols.map(function (c) { return '<th scope="col">' + c[1] + '</th>'; }).join('') + '</tr></thead><tbody>' +
      rows.map(function (r) {
        return '<tr><th scope="row">' + r[1] + '</th>' + cols.map(function (c) {
          return '<td><label class="check radio"><input type="radio" name="rec-' + r[0] + '" value="' + c[0] + '"' +
            (insp.recommended[r[0]] === c[0] ? ' checked' : '') + ' aria-label="' + r[1] + ' ' + c[1] + '"></label></td>';
        }).join('') + '</tr>';
      }).join('') + '</tbody></table>';
  }

  function photosForm(insp) {
    var cats = ['tires', 'brakes', 'tpms', 'suspension', 'alignment', 'other'];
    return '<div class="field"><label for="photo-category">Photo category</label>' +
      '<select id="photo-category">' + cats.map(function (c) { return '<option value="' + c + '">' + c + '</option>'; }).join('') + '</select></div>' +
      '<div class="field"><label for="photo-input">Add photos / video</label>' +
      '<input type="file" id="photo-input" data-testid="photo-input" accept="image/*,video/*" capture="environment" multiple></div>' +
      '<p class="hint">Images are resized on-device before saving.</p>' +
      cats.map(function (c) {
        var ph = insp.photos.filter(function (p) { return p.category === c; });
        if (!ph.length) return '';
        return '<h4>' + esc(c) + '</h4><div class="photo-grid">' + ph.map(function (p) {
          return '<figure class="photo-thumb" data-testid="photo-thumb" data-photo="' + p.id + '">' +
            (p.isVideo ? '<div class="video-placeholder">Video (' + esc(p.note || '') + ')</div>'
              : '<img src="' + p.dataUrl + '" alt="' + esc(p.note || c + ' photo') + '">') +
            '<figcaption><input class="photo-note" data-note="' + p.id + '" value="' + esc(p.note) + '" placeholder="Note" aria-label="Photo note">' +
            '<button type="button" class="btn btn-small btn-danger" data-del-photo="' + p.id + '">Delete</button></figcaption></figure>';
        }).join('') + '</div>';
      }).join('');
  }

  function bindInspectEvents(main, insp, section) {
    var touch = function () { saveSoon(); toast('Saved'); };
    var numOrNull = function (v) { return v === '' || v == null ? null : Number(v); };

    if (section === 'tires') {
      $$('.tread-input', main).forEach(function (inp) {
        inp.addEventListener('input', function () {
          var pos = inp.getAttribute('data-tire');
          insp.tires[pos].tread = numOrNull(inp.value);
          if (!inp.dataset.manual) {
            insp.tires[pos].status = tireStatusFromTread(inp.value);
            $$('[data-tire="' + pos + '"][data-status]', main).forEach(function (b) {
              b.setAttribute('aria-pressed', String(b.getAttribute('data-status') === insp.tires[pos].status));
            });
          }
          touch();
        });
      });
      $$('[data-tire][data-status]', main).forEach(function (btn) {
        btn.addEventListener('click', function () {
          var pos = btn.getAttribute('data-tire'), s = btn.getAttribute('data-status');
          insp.tires[pos].status = insp.tires[pos].status === s ? null : s;
          var inp = $('#tread-' + pos, main); if (inp) inp.dataset.manual = '1';
          saveState(); render();
        });
      });
      $('#tire-notes', main).addEventListener('input', function (e) { insp.tires.notes = e.target.value; touch(); });
    }
    if (section === 'brakes') {
      $('#front-pads', main).addEventListener('input', function (e) { insp.brakes.frontPadsMm = numOrNull(e.target.value); touch(); });
      $('#rear-pads', main).addEventListener('input', function (e) { insp.brakes.rearPadsMm = numOrNull(e.target.value); touch(); });
      $$('[data-rotor]', main).forEach(function (btn) {
        btn.addEventListener('click', function () {
          var end = btn.getAttribute('data-rotor'), val = btn.getAttribute('data-val');
          var cur = end === 'front' ? insp.brakes.frontRotor : insp.brakes.rearRotor;
          var next = cur === val ? null : val;
          if (end === 'front') insp.brakes.frontRotor = next; else insp.brakes.rearRotor = next;
          saveState(); render();
        });
      });
    }
    if (section === 'tpms') {
      $$('[data-tpms]', main).forEach(function (b) {
        b.addEventListener('click', function () {
          var s = b.getAttribute('data-tpms');
          insp.tpms.status = insp.tpms.status === s ? null : s; saveState(); render();
        });
      });
      $('#tpm-number', main).addEventListener('input', function (e) { insp.tpms.tpmNumber = e.target.value; touch(); });
      $$('[data-susp]', main).forEach(function (b) {
        b.addEventListener('click', function () {
          var s = b.getAttribute('data-susp');
          insp.suspension.status = insp.suspension.status === s ? null : s; saveState(); render();
        });
      });
      $$('[data-sus-item]', main).forEach(function (cb) {
        cb.addEventListener('change', function () { insp.suspension.items[cb.getAttribute('data-sus-item')] = cb.checked; touch(); });
      });
      $('#sus-other-text', main).addEventListener('input', function (e) { insp.suspension.otherText = e.target.value; touch(); });
      $$('[data-align]', main).forEach(function (b) {
        b.addEventListener('click', function () {
          var s = b.getAttribute('data-align');
          insp.alignment.status = insp.alignment.status === s ? null : s; saveState(); render();
        });
      });
      $$('input[name="alg"]', main).forEach(function (r) {
        r.addEventListener('change', function () { insp.alignment.alg = r.checked ? r.value : insp.alignment.alg; touch(); });
      });
    }
    if (section === 'notes') {
      $('#insp-notes', main).addEventListener('input', function (e) { insp.notes = e.target.value; touch(); });
      $$('input[name^="rec-"]', main).forEach(function (r) {
        r.addEventListener('change', function () {
          insp.recommended[r.name.replace('rec-', '')] = r.value; touch();
        });
      });
    }
    if (section === 'photos') bindPhotoEvents(main, insp);

    // camera shortcut buttons (tires section)
    $$('[data-cam]', main).forEach(function (btn) {
      btn.addEventListener('click', function () {
        navigate('#/inspect/' + insp.id + '/photos');
        setTimeout(function () {
          var sel = $('#photo-category'); if (sel) sel.value = btn.getAttribute('data-cam');
        }, 50);
      });
    });
  }

  // ---------- photos ----------
  function bindPhotoEvents(main, insp) {
    var input = $('#photo-input', main);
    input.addEventListener('change', function () {
      var cat = $('#photo-category').value;
      var files = Array.prototype.slice.call(input.files);
      var pending = files.length;
      if (!pending) return;
      files.forEach(function (file) {
        if (file.type.indexOf('video/') === 0) {
          if (file.size < 4 * 1024 * 1024) {
            var fr = new FileReader();
            fr.onload = function () {
              insp.photos.push({ id: uid('p'), category: cat, dataUrl: fr.result, note: '', at: new Date().toISOString(), isVideo: true });
              if (--pending === 0) { saveState(); render(); toast('Saved'); }
            };
            fr.readAsDataURL(file);
          } else {
            toast('Videos upload to cloud storage in the production app');
            if (--pending === 0) { saveState(); render(); }
          }
          return;
        }
        downscaleImage(file, function (dataUrl) {
          insp.photos.push({ id: uid('p'), category: cat, dataUrl: dataUrl, note: '', at: new Date().toISOString(), isVideo: false });
          if (--pending === 0) { saveState(); render(); toast('Saved'); }
        });
      });
    });
    $$('[data-del-photo]', main).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-del-photo');
        insp.photos = insp.photos.filter(function (p) { return p.id !== id; });
        saveState(); render(); toast('Photo deleted');
      });
    });
    $$('.photo-note', main).forEach(function (inp) {
      inp.addEventListener('input', function () {
        var p = insp.photos.find(function (x) { return x.id === inp.getAttribute('data-note'); });
        if (p) { p.note = inp.value; saveSoon(); }
      });
    });
  }

  function downscaleImage(file, cb) {
    var fr = new FileReader();
    fr.onload = function () {
      var img = new Image();
      img.onload = function () {
        var max = 1280;
        var w = img.width, h = img.height;
        if (w > max || h > max) {
          var scale = Math.min(max / w, max / h);
          w = Math.round(w * scale); h = Math.round(h * scale);
        }
        var canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        cb(canvas.toDataURL('image/jpeg', 0.8));
      };
      img.onerror = function () { toast('Could not read image'); };
      img.src = fr.result;
    };
    fr.readAsDataURL(file);
  }

  // ---------- summary helpers ----------
  function tireFinding(insp) {
    var parts = ['LF', 'RF', 'LR', 'RR'].map(function (p) {
      return p + ' ' + (insp.tires[p].tread != null ? insp.tires[p].tread + '/32' : '—');
    });
    var worstPos = ['LF', 'RF', 'LR', 'RR'].reduce(function (a, b) {
      var ra = insp.tires[a].status, rb = insp.tires[b].status;
      var rank = { R: 3, Y: 2, G: 1 };
      return (rank[rb] || 0) > (rank[ra] || 0) ? b : a;
    }, 'LF');
    var extra = '';
    var ws = insp.tires[worstPos].status;
    if (ws === 'R') extra = ' — ' + worstPos + ' tire needs replacement';
    else if (ws === 'Y') extra = ' — ' + worstPos + ' tire wearing, replace soon';
    return parts.join(', ') + extra;
  }
  function brakeFinding(insp) {
    var b = insp.brakes;
    var f = 'Front ' + (b.frontPadsMm != null ? b.frontPadsMm + 'mm' : '—') + ' pads, rotor ' + (b.frontRotor || '—');
    var r = 'Rear ' + (b.rearPadsMm != null ? b.rearPadsMm + 'mm' : '—') + ' pads, rotor ' + (b.rearRotor || '—');
    return f + '; ' + r;
  }
  function tpmsFinding(insp) {
    var bits = [];
    bits.push('TPMS ' + (insp.tpms.status === 'ok' ? 'OK' : insp.tpms.status === 'rec' ? 'needs service' : '—') +
      (insp.tpms.tpmNumber ? ' (TPM #' + insp.tpms.tpmNumber + ')' : ''));
    var items = Object.keys(insp.suspension.items).filter(function (k) { return insp.suspension.items[k]; });
    bits.push('Suspension ' + (insp.suspension.status === 'ok' ? 'OK' : insp.suspension.status === 'rec' ? 'recommended' : '—') +
      (items.length ? ': ' + items.join(', ') : ''));
    bits.push('Alignment ' + (insp.alignment.status === 'ok' ? 'OK' : insp.alignment.status === 'rec' ? 'recommended' : '—') +
      (insp.alignment.alg ? ' ($' + insp.alignment.alg + ')' : ''));
    return bits.join(' · ');
  }

  function summaryRows(insp) {
    var t = sectionStatus(insp, 'tires'), b = sectionStatus(insp, 'brakes'), tp = sectionStatus(insp, 'tpms');
    return [
      { name: 'Tires', cls: t ? GYR[t].cls : 'none', label: t ? GYR[t].label : 'Not recorded', text: tireFinding(insp) },
      { name: 'Brakes', cls: b ? GYR[b].cls : 'none', label: b ? GYR[b].label : 'Not recorded', text: brakeFinding(insp) },
      { name: 'TPMS', cls: insp.tpms.status ? OKREC[insp.tpms.status].cls : 'none', label: insp.tpms.status ? OKREC[insp.tpms.status].label : 'Not recorded', text: 'TPMS ' + (insp.tpms.status ? OKREC[insp.tpms.status].label : 'not recorded') },
      { name: 'Suspension', cls: insp.suspension.status ? OKREC[insp.suspension.status].cls : 'none', label: insp.suspension.status ? OKREC[insp.suspension.status].label : 'Not recorded', text: insp.suspension.status ? ('Suspension ' + OKREC[insp.suspension.status].label) : 'Not recorded' },
      { name: 'Alignment', cls: insp.alignment.status ? OKREC[insp.alignment.status].cls : 'none', label: insp.alignment.status ? OKREC[insp.alignment.status].label : 'Not recorded', text: insp.alignment.status ? ('Alignment ' + OKREC[insp.alignment.status].label + (insp.alignment.alg ? ' ($' + insp.alignment.alg + ')' : '')) : 'Not recorded' }
    ];
  }

  // ---------- view: summary ----------
  function viewSummary(main, inspId) {
    var insp = getInspection(inspId);
    if (!insp) { main.innerHTML = notFound(); return; }
    var job = getJob(insp.jobId), v = getVehicle(insp.vehicleId), c = getCustomer(job ? job.customerId : null);
    main.innerHTML = svgDefs() +
      '<div class="page-head"><a class="back" href="#/job/' + esc(insp.jobId) + '">← Job</a><h2>Shop Summary</h2></div>' +
      '<div class="card"><div class="grid2">' +
      '<p><strong>Vehicle:</strong> ' + esc(v.year + ' ' + v.make + ' ' + v.model) + ' · ' + esc(v.plate) + '</p>' +
      '<p><strong>Customer:</strong> ' + esc(c ? c.name : '') + '</p>' +
      '<p><strong>Date:</strong> ' + esc(insp.date) + ' · <strong>Tech:</strong> ' + esc(insp.tech) + '</p>' +
      '</div></div>' +
      '<div class="card"><table class="summary-table"><thead><tr><th scope="col">Section</th><th scope="col">Status</th><th scope="col">Finding</th></tr></thead><tbody>' +
      summaryRows(insp).map(function (r) {
        return '<tr><th scope="row">' + esc(r.name) + '</th><td>' + pill(r.cls === 'none' ? 'none' : r.cls, r.label) + '</td><td>' + esc(r.text) + '</td></tr>';
      }).join('') + '</tbody></table></div>' +
      (insp.notes ? '<div class="card"><h3>Notes</h3><p>' + esc(insp.notes) + '</p></div>' : '') +
      '<div class="card"><h3>Recommended repairs</h3><ul class="rec-list">' +
      Object.keys(insp.recommended).filter(function (k) { return insp.recommended[k]; }).map(function (k) {
        return '<li>' + esc(k.charAt(0).toUpperCase() + k.slice(1)) + ': ' + pill(insp.recommended[k] === 'ok' ? 'green' : insp.recommended[k] === 'soon' ? 'amber' : 'red', REC_LABELS[insp.recommended[k]]) + '</li>';
      }).join('') + '</ul></div>' +
      '<div class="actions">' +
      '<button type="button" class="btn btn-primary" data-testid="send-to-customer">Send to Customer</button>' +
      '<a class="btn" href="#/sheet/' + insp.id + '">Print filled sheet</a>' +
      '<a class="btn" href="#/r/' + insp.id + '">Open customer report</a>' +
      '</div>';

    $('[data-testid="send-to-customer"]', main).addEventListener('click', function () {
      var cfg = window.DVI_CONFIG;
      var first = (c ? c.name : '').split(' ')[0];
      var link = cfg.reportBaseUrl + '#/r/' + insp.id;
      var msg = 'Hi ' + first + ', your vehicle inspection from ' + cfg.shopName + ' is complete. View your report, photos and recommendations: ' + link;
      openModal('<h3>Send to customer</h3>' +
        '<p class="hint">Demo: no message is sent</p>' +
        '<textarea rows="5" readonly aria-label="SMS preview" class="sms-preview">' + esc(msg) + '</textarea>' +
        '<p class="hint">Report link: <a data-testid="report-link" href="' + esc(link) + '" target="_blank" rel="noopener">' + esc(link) + '</a></p>' +
        '<div class="actions">' +
        '<button type="button" class="btn" id="copy-link">Copy link</button>' +
        '<a class="btn btn-primary" id="sms-link" href="sms:' + encodeURIComponent(c ? c.phone : '') + '?&body=' + encodeURIComponent(msg) + '">Open SMS app</a>' +
        '<button type="button" class="btn" data-close="1">Close</button></div>');
      function markContacted() {
        if (job && ['inspection_complete'].indexOf(job.status) >= 0) advanceJob(job, 'customer_contacted');
      }
      $('#copy-link').addEventListener('click', function () {
        var done = function () { toast('Link copied'); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(link).then(done, done);
        else done();
        markContacted();
      });
      $('#sms-link').addEventListener('click', markContacted);
    });
  }

  // ---------- view: customer report ----------
  function viewReport(main, inspId) {
    var insp = getInspection(inspId);
    if (!insp) { main.innerHTML = notFound(); return; }
    var job = getJob(insp.jobId), v = getVehicle(insp.vehicleId);
    var c = getCustomer(job ? job.customerId : null);
    var cfg = window.DVI_CONFIG;
    var recGroups = { now: [], soon: [], future: [], ok: [] };
    Object.keys(insp.recommended).forEach(function (k) {
      var val = insp.recommended[k];
      if (val) recGroups[val].push(k.charAt(0).toUpperCase() + k.slice(1));
    });
    function photosFor(cat) {
      return insp.photos.filter(function (p) { return p.category === cat; });
    }
    function photoHtml(cat) {
      var ph = photosFor(cat);
      if (!ph.length) return '';
      return '<div class="photo-grid report-photos">' + ph.map(function (p) {
        return p.isVideo ? '<figure class="photo-thumb"><div class="video-placeholder">Video</div></figure>' :
          '<figure class="photo-thumb"><button type="button" class="lightbox-btn" data-img="' + p.id + '"><img src="' + p.dataUrl + '" alt="' + esc(p.note || cat + ' photo') + '"></button>' +
          (p.note ? '<figcaption>' + esc(p.note) + '</figcaption>' : '') + '</figure>';
      }).join('') + '</div>';
    }
    main.innerHTML = svgDefs() +
      '<div class="report" data-testid="customer-report">' +
      '<header class="report-header"><div><h1>' + esc(cfg.shopName) + '</h1><p>' + esc(cfg.tagline) + '</p></div>' +
      '<p class="report-date">' + esc(insp.date) + '</p></header>' +
      '<div class="report-veh"><h2>' + esc(v.year) + ' ' + esc(v.make) + ' ' + esc(v.model) + '</h2>' +
      '<p>Plate ' + esc(v.plate) + ' · ' + esc(v.mileage.toLocaleString()) + ' miles · Technician: ' + esc(insp.tech) + '</p></div>' +
      '<h3>Inspection summary</h3>' +
      '<ul class="summary-list">' + summaryRows(insp).map(function (r) {
        return '<li><span>' + esc(r.name) + '</span> ' + pill(r.cls === 'none' ? 'none' : r.cls, r.label) + '</li>';
      }).join('') + '</ul>' +
      '<details><summary>Tires</summary><p>' + esc(tireFinding(insp)) + '</p>' +
      (insp.tires.notes ? '<p>' + esc(insp.tires.notes) + '</p>' : '') + photoHtml('tires') + '</details>' +
      '<details><summary>Brakes</summary><p>' + esc(brakeFinding(insp)) + '</p>' + photoHtml('brakes') + '</details>' +
      '<details><summary>TPMS / Suspension / Alignment</summary><p>' + esc(tpmsFinding(insp)) + '</p>' + photoHtml('tpms') + photoHtml('suspension') + photoHtml('alignment') + '</details>' +
      (insp.notes ? '<details open><summary>Technician notes</summary><p>' + esc(insp.notes) + '</p></details>' : '') +
      '<h3>Recommended repairs</h3>' +
      (recGroups.now.length ? '<p><strong>Needs attention now:</strong> ' + esc(recGroups.now.join(', ')) + '</p>' : '') +
      (recGroups.soon.length ? '<p><strong>Soon:</strong> ' + esc(recGroups.soon.join(', ')) + '</p>' : '') +
      (recGroups.future.length ? '<p><strong>Future:</strong> ' + esc(recGroups.future.join(', ')) + '</p>' : '') +
      photoHtml('other') +
      '<footer class="report-footer"><p>Questions? Call <a href="tel:' + esc(cfg.phone) + '">' + esc(cfg.phone) + '</a></p>' +
      '<p class="hint">Demo — synthetic data only</p></footer>' +
      '</div>';

    $$('.lightbox-btn', main).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var p = insp.photos.find(function (x) { return x.id === btn.getAttribute('data-img'); });
        if (!p) return;
        openModal('<img class="lightbox-img" src="' + p.dataUrl + '" alt="' + esc(p.note || 'Photo') + '"><div class="actions"><button type="button" class="btn" data-close="1">Close</button></div>');
      });
    });
  }

  // ---------- view: printable sheet ----------
  function tick(val, match) { return val === match ? '<span class="tick">✓</span>' : '<span class="tick tick-empty"></span>'; }
  function viewSheet(main, inspId) {
    var insp = getInspection(inspId);
    if (!insp) { main.innerHTML = notFound(); return; }
    var job = getJob(insp.jobId), v = getVehicle(insp.vehicleId), c = getCustomer(job ? job.customerId : null);
    var susItems = [['innerTieRod', 'Inner Tie Rod'], ['outerTieRod', 'Outer Tie Rod'], ['controlArm', 'Control Arm'], ['shock', 'Shock'], ['strut', 'Strut'], ['other', 'Other']];
    var recRows = [['tires', 'Tires'], ['alignment', 'Alignment'], ['tpms', 'TPMS'], ['brakes', 'Brakes'], ['suspension', 'Suspension']];
    var recCols = [['ok', 'OK'], ['soon', 'Soon'], ['future', 'Future'], ['now', 'Now']];
    main.innerHTML = svgDefs() +
      '<div class="sheet" id="sheet">' +
      '<div class="sheet-head"><h1>' + esc(window.DVI_CONFIG.shopName) + ' — Vehicle Inspection Sheet</h1>' +
      '<table class="sheet-meta"><tbody><tr>' +
      '<th>Date</th><td>' + esc(insp.date) + '</td><th>Tech</th><td>' + esc(insp.tech) + '</td>' +
      '<th>Customer</th><td>' + esc(c ? c.name : '') + '</td><th>Phone</th><td>' + esc(c ? c.phone : '') + '</td></tr><tr>' +
      '<th>Year</th><td>' + esc(v.year) + '</td><th>Model</th><td>' + esc(v.make + ' ' + v.model) + '</td>' +
      '<th>Plate</th><td>' + esc(v.plate) + '</td><th>Mileage</th><td>' + esc(v.mileage) + '</td>' +
      '</tr></tbody></table></div>' +
      '<section class="sheet-panel panel-tires"><h2>Tires</h2><table class="sheet-table"><thead><tr><th></th><th>Tread /32</th><th>Good</th><th>Soon</th><th>Replace</th></tr></thead><tbody>' +
      ['LF', 'RF', 'LR', 'RR'].map(function (p) {
        var t = insp.tires[p];
        return '<tr><th>' + p + '</th><td>' + (t.tread != null ? esc(t.tread) : '—') + '</td>' +
          '<td>' + tick(t.status, 'G') + '</td><td>' + tick(t.status, 'Y') + '</td><td>' + tick(t.status, 'R') + '</td></tr>';
      }).join('') + '</tbody></table>' +
      (insp.tires.notes ? '<p>Notes: ' + esc(insp.tires.notes) + '</p>' : '') + '</section>' +
      '<section class="sheet-panel panel-brakes"><h2>Brakes</h2><table class="sheet-table"><thead><tr><th></th><th>Pads mm</th><th>Good</th><th>Worn</th><th>Replace</th></tr></thead><tbody>' +
      '<tr><th>Front</th><td>' + (insp.brakes.frontPadsMm != null ? esc(insp.brakes.frontPadsMm) : '—') + '</td>' +
      '<td>' + tick(insp.brakes.frontRotor, 'good') + '</td><td>' + tick(insp.brakes.frontRotor, 'worn') + '</td><td>' + tick(insp.brakes.frontRotor, 'replace') + '</td></tr>' +
      '<tr><th>Rear</th><td>' + (insp.brakes.rearPadsMm != null ? esc(insp.brakes.rearPadsMm) : '—') + '</td>' +
      '<td>' + tick(insp.brakes.rearRotor, 'good') + '</td><td>' + tick(insp.brakes.rearRotor, 'worn') + '</td><td>' + tick(insp.brakes.rearRotor, 'replace') + '</td></tr>' +
      '</tbody></table></section>' +
      '<section class="sheet-panel panel-tpms"><h2>TPMS / Suspension / Alignment</h2>' +
      '<p>TPMS: OK ' + tick(insp.tpms.status, 'ok') + ' Rec ' + tick(insp.tpms.status, 'rec') +
      (insp.tpms.tpmNumber ? ' · TPM #' + esc(insp.tpms.tpmNumber) : '') + '</p>' +
      '<p>Suspension: OK ' + tick(insp.suspension.status, 'ok') + ' Rec ' + tick(insp.suspension.status, 'rec') + ' — ' +
      susItems.map(function (it) { return it[1] + ' ' + tick(insp.suspension.items[it[0]], true); }).join(' · ') +
      (insp.suspension.otherText ? ' · Other: ' + esc(insp.suspension.otherText) : '') + '</p>' +
      '<p>Alignment: OK ' + tick(insp.alignment.status, 'ok') + ' Rec ' + tick(insp.alignment.status, 'rec') +
      ' · ALG: ' + ['79', '89', '99', '120'].map(function (a) { return a + ' ' + tick(insp.alignment.alg, a); }).join(' ') + '</p></section>' +
      '<section class="sheet-panel panel-notes"><h2>Notes</h2><p>' + esc(insp.notes || '—') + '</p></section>' +
      '<section class="sheet-panel panel-rec"><h2>Recommended repairs</h2><table class="sheet-table"><thead><tr><th></th>' +
      recCols.map(function (c2) { return '<th>' + c2[1] + '</th>'; }).join('') + '</tr></thead><tbody>' +
      recRows.map(function (r) {
        return '<tr><th>' + r[1] + '</th>' + recCols.map(function (c2) {
          return '<td>' + tick(insp.recommended[r[0]], c2[0]) + '</td>';
        }).join('') + '</tr>';
      }).join('') + '</tbody></table></section>' +
      '</div>' +
      '<div class="actions no-print"><a class="btn" href="#/summary/' + insp.id + '">← Back to summary</a>' +
      '<button type="button" class="btn btn-primary" id="print-btn">Print</button></div>';
    $('#print-btn').addEventListener('click', function () { window.print(); });
  }

  // ---------- view: search ----------
  function viewSearch(main) {
    main.innerHTML = svgDefs() +
      '<div class="page-head"><h2>Customer &amp; Vehicle History</h2></div>' +
      '<div class="card"><div class="field"><label for="search-input">Search name, phone or plate</label>' +
      '<input id="search-input" data-testid="search-input" type="search" autocomplete="off" placeholder="e.g. Jamie, 5552100101, DEMO-101"></div>' +
      '<div id="search-results" class="search-results"></div></div>';

    var input = $('#search-input'), results = $('#search-results');
    function run() {
      var q = input.value.trim().toLowerCase();
      var digits = q.replace(/\D/g, '');
      if (!q) { results.innerHTML = '<p class="hint">Type to search customers and vehicles.</p>'; return; }
      var vehs = state.vehicles.filter(function (v) {
        var c = getCustomer(v.customerId);
        return c.name.toLowerCase().indexOf(q) >= 0 ||
          (digits.length && c.phone.replace(/\D/g, '').indexOf(digits) >= 0) ||
          v.plate.toLowerCase().indexOf(q) >= 0;
      });
      results.innerHTML = vehs.length ? vehs.map(function (v) {
        var c = getCustomer(v.customerId);
        var insps = state.inspections.filter(function (i) { return i.vehicleId === v.id; });
        return '<div class="search-result" data-testid="search-result"><div class="job-top">' +
          '<span class="veh">' + esc(v.year) + ' ' + esc(v.make) + ' ' + esc(v.model) + '</span><span class="plate">' + esc(v.plate) + '</span></div>' +
          '<p>' + esc(c.name) + ' · ' + esc(c.phone) + '</p>' +
          (insps.length ? '<ul class="hist-list">' + insps.map(function (i) {
            var st = sectionStatus(i, 'tires') || 'G';
            var all = [sectionStatus(i, 'tires'), sectionStatus(i, 'brakes'), sectionStatus(i, 'tpms')].filter(Boolean);
            var w = worst(all) || 'G';
            return '<li>' + esc(i.date) + ' — overall ' + pill(GYR[w].cls, GYR[w].label) +
              ' <a href="#/r/' + i.id + '">View report</a></li>';
          }).join('') + '</ul>' : '<p class="hint">No past inspections.</p>') +
          '</div>';
      }).join('') : '<p class="empty">No matches found.</p>';
    }
    input.addEventListener('input', run);
    run();
  }

  // ---------- view: settings ----------
  function viewSettings(main) {
    main.innerHTML = svgDefs() +
      '<div class="page-head"><h2>Settings</h2></div>' +
      '<div class="card"><h3>Demo data</h3>' +
      '<p>Reset all data to the original synthetic seed data. This clears any changes you have made.</p>' +
      '<button type="button" class="btn btn-danger" data-testid="reset-demo">Reset demo data</button></div>' +
      '<div class="card"><h3>About</h3>' +
      '<p>' + esc(window.DVI_CONFIG.shopName) + ' — ' + esc(window.DVI_CONFIG.tagline) + '</p>' +
      '<p>This is a clickable sales demo of a digital vehicle inspection app. All data is synthetic and stored only in this browser (localStorage). No data leaves your device.</p>' +
      '<p>Phone: <a href="tel:' + esc(window.DVI_CONFIG.phone) + '">' + esc(window.DVI_CONFIG.phone) + '</a></p></div>';
    $('[data-testid="reset-demo"]', main).addEventListener('click', function () {
      resetState();
      toast('Demo data reset');
      navigate('#/today');
    });
  }

  // ---------- init ----------
  loadState();
  window.addEventListener('hashchange', render);
  render();

  try {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('sw.js').catch(function () { /* ignore */ });
    }
  } catch (e) { /* ignore */ }
})();
