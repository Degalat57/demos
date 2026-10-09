(function () {
  'use strict';

  var VERSION = '1.0.0';

  function toF(c) {
    return Math.round((c * 9) / 5 + 32);
  }

  function fmt(seconds) {
    var s = Math.max(0, Math.ceil(seconds));
    var m = Math.floor(s / 60);
    var r = s % 60;
    return m + ':' + (r < 10 ? '0' + r : '' + r);
  }

  function clamp(n, a, b) {
    return Math.min(b, Math.max(a, n));
  }

  var CUP_SIZES = [
    { id: 'cup', label: '1 cup (250 ml)', ml: 250, cups: 1 },
    { id: 'two', label: '2 cups (500 ml)', ml: 500, cups: 2 },
    { id: 'pot', label: 'Teapot (750 ml)', ml: 750, cups: 3 }
  ];

  var STAGE_HINTS = [
    { at: 0.0, text: 'Leaves unfurling...' },
    { at: 0.4, text: 'Flavour developing...' },
    { at: 0.75, text: 'Almost there...' }
  ];

  function stageHint(progress) {
    var out = STAGE_HINTS[0].text;
    for (var i = 0; i < STAGE_HINTS.length; i++) {
      if (progress >= STAGE_HINTS[i].at) out = STAGE_HINTS[i].text;
    }
    return out;
  }

  function el(tag, cls, attrs) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (attrs) {
      for (var k in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, k)) {
          if (k === 'text') n.textContent = attrs[k];
          else if (k === 'html') n.innerHTML = attrs[k];
          else n.setAttribute(k, attrs[k]);
        }
      }
    }
    return n;
  }

  function SteepTimer(root) {
    this.root = root;
    this.config = this.readConfig();
    this.speed = parseFloat(root.getAttribute('data-speed')) || 1;
    this.state = 'idle';
    this.teaIndex = 0;
    this.cupIndex = 0;
    this.infusion = 1;
    this.remaining = 0;
    this.duration = 0;
    this.startedAt = 0;
    this.pausedRemaining = 0;
    this.rafId = null;
    this.intervalId = null;
    this.audioCtx = null;
    this.titleTimer = null;
    this.originalTitle = document.title;
    this.boundKey = this.onKey.bind(this);
    this.boundVis = this.onVisibility.bind(this);
    this.build();
    this.render();
  }

  SteepTimer.prototype.readConfig = function () {
    var node = this.root.querySelector('[data-steep-config]');
    var cfg = { teas: [], showFahrenheit: true, chime: true, heading: '', subheading: '' };
    if (node) {
      try {
        var parsed = JSON.parse(node.textContent);
        if (parsed && typeof parsed === 'object') {
          cfg.teas = Array.isArray(parsed.teas) ? parsed.teas : [];
          cfg.showFahrenheit = parsed.showFahrenheit !== false;
          cfg.chime = parsed.chime !== false;
          cfg.heading = parsed.heading || '';
          cfg.subheading = parsed.subheading || '';
        }
      } catch (e) {
        cfg.teas = [];
      }
    }
    if (!cfg.teas.length) {
      cfg.teas = [
        {
          type: 'tea',
          label: 'Tea',
          tempC: 90,
          seconds: 180,
          gramsPerCup: 2.5,
          infusions: 1,
          incrementSeconds: 0,
          note: ''
        }
      ];
    }
    cfg.teas = cfg.teas.map(function (t) {
      return {
        type: String(t.type || 'tea'),
        label: String(t.label || t.type || 'Tea'),
        tempC: Number(t.tempC) || 90,
        seconds: Number(t.seconds) || 180,
        gramsPerCup: Number(t.gramsPerCup) || 2.5,
        infusions: clamp(Number(t.infusions) || 1, 1, 8),
        incrementSeconds: Number(t.incrementSeconds) || 0,
        note: String(t.note || '')
      };
    });
    return cfg;
  };

  SteepTimer.prototype.currentTea = function () {
    return this.config.teas[this.teaIndex] || this.config.teas[0];
  };

  SteepTimer.prototype.build = function () {
    var self = this;
    var body = this.root.querySelector('[data-steep-body]');
    if (!body) return;
    body.innerHTML = '';

    if (this.config.teas.length > 1) {
      var seg = el('div', 'steep-timer__segment', { role: 'group', 'aria-label': 'Choose tea type' });
      this.config.teas.forEach(function (tea, i) {
        var b = el('button', 'steep-timer__seg-btn', {
          type: 'button',
          'data-testid': 'tea-option',
          'data-index': String(i),
          'aria-pressed': i === self.teaIndex ? 'true' : 'false'
        });
        b.textContent = tea.label;
        b.addEventListener('click', function () {
          self.selectTea(i);
        });
        seg.appendChild(b);
      });
      this.segEl = seg;
      body.appendChild(seg);
    } else {
      this.segEl = null;
    }

    var chips = el('div', 'steep-timer__chips');
    this.tempChip = el('span', 'steep-timer__chip');
    this.leafChip = el('span', 'steep-timer__chip');
    this.timeChip = el('span', 'steep-timer__chip');
    chips.appendChild(this.tempChip);
    chips.appendChild(this.leafChip);
    chips.appendChild(this.timeChip);
    body.appendChild(chips);

    var cupRow = el('div', 'steep-timer__cup-row');
    var cupLabel = el('label', 'steep-timer__cup-label', { for: 'steep-cup-' + this.uid() });
    cupLabel.textContent = 'Cup size';
    var cupSel = el('select', 'steep-timer__cup-select', {
      id: cupLabel.getAttribute('for'),
      'data-testid': 'cup-size',
      'aria-label': 'Cup size'
    });
    CUP_SIZES.forEach(function (c, i) {
      var o = el('option', null, { value: c.id });
      o.textContent = c.label;
      if (i === self.cupIndex) o.selected = true;
      cupSel.appendChild(o);
    });
    cupSel.addEventListener('change', function () {
      self.cupIndex = cupSel.selectedIndex;
      self.render();
    });
    this.cupSel = cupSel;
    cupRow.appendChild(cupLabel);
    cupRow.appendChild(cupSel);
    body.appendChild(cupRow);

    var ringWrap = el('div', 'steep-timer__ring-wrap');
    var steam = el('div', 'steep-timer__steam', { 'aria-hidden': 'true' });
    steam.innerHTML =
      '<svg viewBox="0 0 40 60" width="40" height="60" focusable="false">' +
      '<path class="steep-timer__steam-path" d="M14 56 C 8 44, 22 40, 16 28 C 10 16, 24 12, 18 2" />' +
      '<path class="steep-timer__steam-path steep-timer__steam-path--b" d="M26 56 C 20 46, 34 42, 28 30 C 22 18, 34 14, 28 4" />' +
      '</svg>';
    ringWrap.appendChild(steam);

    var size = 220;
    var r = 96;
    var c = 2 * Math.PI * r;
    var svgNS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('class', 'steep-timer__ring');
    svg.setAttribute('viewBox', '0 0 ' + size + ' ' + size);
    svg.setAttribute('width', String(size));
    svg.setAttribute('height', String(size));
    svg.setAttribute('data-testid', 'ring');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Steep progress');

    var track = document.createElementNS(svgNS, 'circle');
    track.setAttribute('class', 'steep-timer__ring-track');
    track.setAttribute('cx', String(size / 2));
    track.setAttribute('cy', String(size / 2));
    track.setAttribute('r', String(r));
    svg.appendChild(track);

    var prog = document.createElementNS(svgNS, 'circle');
    prog.setAttribute('class', 'steep-timer__ring-progress');
    prog.setAttribute('cx', String(size / 2));
    prog.setAttribute('cy', String(size / 2));
    prog.setAttribute('r', String(r));
    prog.setAttribute('stroke-dasharray', String(c));
    prog.setAttribute('stroke-dashoffset', String(c));
    prog.setAttribute('transform', 'rotate(-90 ' + size / 2 + ' ' + size / 2 + ')');
    svg.appendChild(prog);
    this.ringProgress = prog;
    this.ringCircumference = c;

    ringWrap.appendChild(svg);

    var center = el('div', 'steep-timer__center');
    this.timeEl = el('div', 'steep-timer__time', { 'data-testid': 'time' });
    this.timeEl.textContent = fmt(this.currentTea().seconds);
    this.infusionEl = el('div', 'steep-timer__infusion', { 'data-testid': 'infusion' });
    center.appendChild(this.timeEl);
    center.appendChild(this.infusionEl);
    ringWrap.appendChild(center);
    body.appendChild(ringWrap);

    var hint = el('p', 'steep-timer__hint');
    this.hintEl = hint;
    body.appendChild(hint);

    var note = el('p', 'steep-timer__note');
    this.noteEl = note;
    body.appendChild(note);

    var controls = el('div', 'steep-timer__controls');
    this.startBtn = el('button', 'steep-timer__btn steep-timer__btn--primary', {
      type: 'button',
      'data-testid': 'start',
      'aria-label': 'Start steeping'
    });
    this.startBtn.textContent = 'Start';
    this.startBtn.addEventListener('click', function () {
      self.toggle();
    });

    this.resetBtn = el('button', 'steep-timer__btn', {
      type: 'button',
      'data-testid': 'reset',
      'aria-label': 'Reset timer'
    });
    this.resetBtn.textContent = 'Reset';
    this.resetBtn.addEventListener('click', function () {
      self.reset();
    });

    this.nextBtn = el('button', 'steep-timer__btn steep-timer__btn--next', {
      type: 'button',
      'data-testid': 'next-infusion',
      'aria-label': 'Start next infusion'
    });
    this.nextBtn.textContent = 'Next infusion';
    this.nextBtn.hidden = true;
    this.nextBtn.addEventListener('click', function () {
      self.nextInfusion();
    });

    controls.appendChild(this.startBtn);
    controls.appendChild(this.resetBtn);
    controls.appendChild(this.nextBtn);
    body.appendChild(controls);

    this.statusEl = this.root.querySelector('[data-testid="status"]');

    this.root.addEventListener('keydown', this.boundKey);
    document.addEventListener('visibilitychange', this.boundVis);
    window.addEventListener('focus', this.boundVis);
  };

  SteepTimer.prototype.uid = function () {
    if (!this._uid) {
      this._uid = 'st' + Math.random().toString(36).slice(2, 8);
    }
    return this._uid;
  };

  SteepTimer.prototype.selectTea = function (i) {
    if (i === this.teaIndex) return;
    this.teaIndex = i;
    this.infusion = 1;
    this.reset();
    if (this.segEl) {
      var btns = this.segEl.querySelectorAll('[data-testid="tea-option"]');
      for (var k = 0; k < btns.length; k++) {
        btns[k].setAttribute('aria-pressed', String(Number(btns[k].getAttribute('data-index')) === i));
      }
    }
    this.render();
  };

  SteepTimer.prototype.durationFor = function (infusion) {
    var tea = this.currentTea();
    var extra = (infusion - 1) * tea.incrementSeconds;
    return tea.seconds + extra;
  };

  SteepTimer.prototype.render = function () {
    var tea = this.currentTea();
    var cup = CUP_SIZES[this.cupIndex] || CUP_SIZES[0];
    var grams = tea.gramsPerCup * cup.cups;

    var tempText = tea.tempC + ' C';
    if (this.config.showFahrenheit) {
      tempText += ' / ' + toF(tea.tempC) + ' F';
    }
    this.tempChip.textContent = tempText;
    this.leafChip.textContent = (Math.round(grams * 10) / 10) + ' g leaf';
    this.timeChip.textContent = fmt(tea.seconds) + ' steep';

    this.infusionEl.textContent = 'Infusion ' + this.infusion + ' of ' + tea.infusions;
    this.noteEl.textContent = tea.note || '';

    if (this.state === 'idle' || this.state === 'ready') {
      this.timeEl.textContent = fmt(this.durationFor(this.infusion));
      this.setRing(0);
    } else {
      this.timeEl.textContent = fmt(this.remaining);
      var dur = this.duration || 1;
      this.setRing(1 - this.remaining / dur);
    }

    if (this.state === 'steeping') {
      var dur2 = this.duration || 1;
      this.hintEl.textContent = stageHint(1 - this.remaining / dur2);
    } else if (this.state === 'paused') {
      this.hintEl.textContent = 'Paused - take your time.';
    } else if (this.state === 'ready') {
      this.hintEl.textContent = 'Ready. Pour and enjoy.';
    } else {
      this.hintEl.textContent = 'Press start when the water is ready.';
    }

    this.updateButtons();
  };

  SteepTimer.prototype.setRing = function (progress) {
    if (!this.ringProgress) return;
    var p = clamp(progress, 0, 1);
    var offset = this.ringCircumference * (1 - p);
    this.ringProgress.setAttribute('stroke-dashoffset', String(offset));
  };

  SteepTimer.prototype.updateButtons = function () {
    if (this.state === 'steeping') {
      this.startBtn.textContent = 'Pause';
      this.startBtn.setAttribute('aria-label', 'Pause steeping');
    } else if (this.state === 'paused') {
      this.startBtn.textContent = 'Resume';
      this.startBtn.setAttribute('aria-label', 'Resume steeping');
    } else if (this.state === 'ready') {
      this.startBtn.textContent = 'Start';
      this.startBtn.setAttribute('aria-label', 'Start steeping');
    } else {
      this.startBtn.textContent = 'Start';
      this.startBtn.setAttribute('aria-label', 'Start steeping');
    }

    var tea = this.currentTea();
    var more = this.infusion < tea.infusions;
    this.nextBtn.hidden = !(this.state === 'ready' && more);
    if (more) {
      this.nextBtn.textContent = 'Next infusion (+' + tea.incrementSeconds + 's)';
    }
  };

  SteepTimer.prototype.toggle = function () {
    if (this.state === 'steeping') {
      this.pause();
    } else if (this.state === 'paused') {
      this.resume();
    } else {
      this.start();
    }
  };

  SteepTimer.prototype.start = function () {
    this.ensureAudio();
    this.duration = this.durationFor(this.infusion);
    this.remaining = this.duration;
    this.startedAt = Date.now();
    this.state = 'steeping';
    this.root.setAttribute('data-state', 'steeping');
    this.root.classList.remove('is-ready');
    this.setStatus('Steeping. ' + this.currentTea().label + '.');
    this.tick();
  };

  SteepTimer.prototype.pause = function () {
    if (this.state !== 'steeping') return;
    this.pausedRemaining = this.remaining;
    this.state = 'paused';
    this.root.setAttribute('data-state', 'paused');
    this.stopLoop();
    this.setStatus('Paused.');
    this.render();
  };

  SteepTimer.prototype.resume = function () {
    if (this.state !== 'paused') return;
    this.startedAt = Date.now() - (this.duration - this.pausedRemaining) * 1000 / this.speed;
    this.state = 'steeping';
    this.root.setAttribute('data-state', 'steeping');
    this.setStatus('Steeping.');
    this.tick();
  };

  SteepTimer.prototype.reset = function () {
    this.stopLoop();
    this.stopTitleFlash();
    this.state = 'idle';
    this.root.setAttribute('data-state', 'idle');
    this.root.classList.remove('is-ready');
    this.remaining = 0;
    this.duration = 0;
    this.setStatus('');
    this.render();
  };

  SteepTimer.prototype.nextInfusion = function () {
    var tea = this.currentTea();
    if (this.infusion >= tea.infusions) return;
    this.infusion += 1;
    this.stopTitleFlash();
    this.state = 'idle';
    this.root.setAttribute('data-state', 'idle');
    this.root.classList.remove('is-ready');
    this.render();
    this.start();
  };

  SteepTimer.prototype.tick = function () {
    var self = this;
    this.stopLoop();
    var useRaf = typeof window.requestAnimationFrame === 'function';
    var loop = function () {
      var elapsed = (Date.now() - self.startedAt) / 1000 * self.speed;
      self.remaining = self.duration - elapsed;
      if (self.remaining <= 0) {
        self.remaining = 0;
        self.render();
        self.finish();
        return;
      }
      self.render();
      if (useRaf) {
        self.rafId = window.requestAnimationFrame(loop);
      }
    };
    if (useRaf) {
      this.rafId = window.requestAnimationFrame(loop);
    } else {
      this.intervalId = window.setInterval(loop, 250);
    }
  };

  SteepTimer.prototype.stopLoop = function () {
    if (this.rafId != null) {
      if (typeof window.cancelAnimationFrame === 'function') {
        window.cancelAnimationFrame(this.rafId);
      }
      this.rafId = null;
    }
    if (this.intervalId != null) {
      window.clearInterval(this.intervalId);
      this.intervalId = null;
    }
  };

  SteepTimer.prototype.finish = function () {
    this.stopLoop();
    this.state = 'ready';
    this.root.setAttribute('data-state', 'ready');
    this.root.classList.add('is-ready');
    this.setStatus('Your tea is ready - enjoy!');
    this.render();
    if (this.config.chime) this.playChime();
    if (navigator && typeof navigator.vibrate === 'function') {
      try {
        navigator.vibrate([200, 100, 200]);
      } catch (e) {}
    }
    this.flashTitle();
  };

  SteepTimer.prototype.setStatus = function (msg) {
    if (this.statusEl) this.statusEl.textContent = msg;
  };

  SteepTimer.prototype.ensureAudio = function () {
    if (this.audioCtx) return;
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (Ctx) this.audioCtx = new Ctx();
    } catch (e) {
      this.audioCtx = null;
    }
  };

  SteepTimer.prototype.playChime = function () {
    try {
      this.ensureAudio();
      var ctx = this.audioCtx;
      if (!ctx) return;
      if (ctx.state === 'suspended' && typeof ctx.resume === 'function') {
        ctx.resume();
      }
      var now = ctx.currentTime;
      var tones = [
        { f: 660, t: 0 },
        { f: 880, t: 0.28 }
      ];
      for (var i = 0; i < tones.length; i++) {
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.value = tones[i].f;
        var start = now + tones[i].t;
        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.exponentialRampToValueAtTime(0.18, start + 0.04);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.9);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(start);
        osc.stop(start + 1.0);
      }
    } catch (e) {}
  };

  SteepTimer.prototype.flashTitle = function () {
    var self = this;
    this.stopTitleFlash();
    var alt = false;
    this.titleTimer = window.setInterval(function () {
      if (document.hidden) {
        document.title = alt ? "Tea's ready!" : self.originalTitle;
        alt = !alt;
      } else {
        self.stopTitleFlash();
      }
    }, 1200);
  };

  SteepTimer.prototype.stopTitleFlash = function () {
    if (this.titleTimer != null) {
      window.clearInterval(this.titleTimer);
      this.titleTimer = null;
      document.title = this.originalTitle;
    }
  };

  SteepTimer.prototype.onVisibility = function () {
    if (!document.hidden) {
      this.stopTitleFlash();
    }
  };

  SteepTimer.prototype.onKey = function (e) {
    if (e.key === ' ' || e.key === 'Spacebar' || e.code === 'Space') {
      var t = e.target;
      if (t && (t.tagName === 'BUTTON' || t.tagName === 'SELECT' || t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) {
        return;
      }
      e.preventDefault();
      this.toggle();
    }
  };

  SteepTimer.prototype.destroy = function () {
    this.stopLoop();
    this.stopTitleFlash();
    this.root.removeEventListener('keydown', this.boundKey);
    document.removeEventListener('visibilitychange', this.boundVis);
    window.removeEventListener('focus', this.boundVis);
  };

  var instances = [];

  function init(root) {
    if (!root || root.__steepTimer) return root && root.__steepTimer;
    var inst = new SteepTimer(root);
    root.__steepTimer = inst;
    instances.push(inst);
    return inst;
  }

  function initAll(scope) {
    var ctx = scope || document;
    var nodes = ctx.querySelectorAll('[data-steep-timer]');
    for (var i = 0; i < nodes.length; i++) {
      init(nodes[i]);
    }
  }

  window.SteepTimer = { init: init, initAll: initAll, version: VERSION };

  function boot() {
    initAll(document);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  document.addEventListener('shopify:section:load', function (e) {
    if (e && e.target) initAll(e.target);
  });
})();
