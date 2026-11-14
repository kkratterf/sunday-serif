// Sunday Serif website: theme, hero, type tester, glyph browser and copy buttons. No dependencies.
(function () {
  "use strict";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- Toast ----------
  var toastEl = $("[data-toast]");
  var toastTimer;
  function toast(text) {
    if (!toastEl) return;
    toastEl.textContent = text;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("show"); }, 1600);
  }
  function copy(text, label) {
    var done = function () { toast(label || "Copied"); };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
    } else { fallbackCopy(text); done(); }
  }
  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
  }

  // ---------- Theme ----------
  var root = document.documentElement;
  function currentTheme() {
    if (root.dataset.theme) return root.dataset.theme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  $$("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) {}
    });
  });

  // ---------- Header border on scroll ----------
  var top = $(".top");
  var onScroll = function () { if (top) top.classList.toggle("scrolled", window.scrollY > 8); };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // ---------- The FX font: loaded only when an effect is about to show ----------
  // The text font is preloaded; the FX build (~1 MB a style) waits until the visitor moves the
  // mouse over the page or nears the tester or the effects. Until then var(--fx) is the text
  // font, which looks the same with every effect at 0.
  var fxState = 0; // 0 not asked, 1 loading, 2 ready
  function loadFx() {
    if (fxState || !document.fonts || !document.fonts.load) return;
    fxState = 1;
    Promise.all([
      document.fonts.load('400 1em "Sunday Serif FX"'),
      document.fonts.load('italic 400 1em "Sunday Serif FX"'),
    ]).then(function () { fxState = 2; root.classList.add("fx-ready"); }, function () { fxState = 0; });
  }
  if ("IntersectionObserver" in window) {
    var fxObserver = new IntersectionObserver(function (entries) {
      if (entries.some(function (e) { return e.isIntersecting; })) { loadFx(); fxObserver.disconnect(); }
    }, { rootMargin: "0px" });
    $$("[data-stage], #effects").forEach(function (el) { fxObserver.observe(el); });
  } else { loadFx(); }

  // ---------- Hero: Light Burn follows the pointer ----------
  var hero = $("[data-hero]");
  if (hero && !reduceMotion) {
    var target = 0, value = 0, raf = 0;
    var tick = function () {
      value += (target - value) * 0.08;
      hero.style.setProperty("--burn", value.toFixed(1));
      raf = Math.abs(target - value) > 0.2 ? requestAnimationFrame(tick) : 0;
    };
    // The closer the pointer is to the middle of the name, the more exposed it gets (+80, past
    // the +65 alternates); away from it the light goes and the ink spreads, down to -50.
    // The box is the text itself (the h1 spans the whole width), measured with a Range.
    var NEAR = 80, FAR = -50, EDGE = 1.15, OUT = 3;
    var range = document.createRange();
    window.addEventListener("pointermove", function (e) {
      if (e.pointerType !== "mouse") return;
      loadFx();
      range.selectNodeContents(hero);
      var r = range.getBoundingClientRect();
      // 0 in the middle of the name, 1 on its edge, OUT and beyond far away
      var d = Math.hypot((e.clientX - (r.left + r.width / 2)) / (r.width / 2), (e.clientY - (r.top + r.height / 2)) / (r.height / 2));
      target = d <= EDGE ? NEAR * (1 - d / EDGE) : FAR * Math.min(1, (d - EDGE) / (OUT - EDGE));
      if (!raf) raf = requestAnimationFrame(tick);
    }, { passive: true });
  }

  // ---------- Segmented controls ----------
  function bindSeg(seg, onChange) {
    var buttons = $$("button", seg);
    buttons.forEach(function (b) {
      b.addEventListener("click", function () {
        buttons.forEach(function (o) { o.setAttribute("aria-checked", String(o === b)); });
        onChange(b.dataset.value);
      });
    });
  }

  // ---------- Type tester ----------
  var tester = $("[data-tester]");
  if (tester) {
    var sample = $("[data-sample]", tester);
    var stage = $("[data-stage]", tester);
    var ctl = function (name) { return $('[data-ctl="' + name + '"]', tester); };
    var out = function (name) { return $('[data-out="' + name + '"]', tester); };
    var state = { wght: 400, italic: false, invert: false, size: 96, burn: 0, inkb: 0, worn: 0 };
    var weightNames = { 400: "Regular", 500: "Medium", 600: "SemiBold" };
    var EFFECTS = ["burn", "inkb", "worn"];
    var weightLabel = function (w) { return weightNames[w] ? weightNames[w] + " " + w : String(w); };

    function render() {
      sample.style.fontWeight = String(state.wght);
      sample.style.fontStyle = state.italic ? "italic" : "normal";
      sample.style.fontSize = state.size + "px";
      sample.style.fontVariationSettings = '"BURN" ' + state.burn + ', "INKB" ' + state.inkb + ', "WORN" ' + state.worn;
      stage.classList.toggle("inverted", state.invert);
      out("wght").textContent = weightLabel(state.wght);
      out("size").textContent = state.size;
      out("burn").textContent = state.burn;
      out("inkb").textContent = state.inkb;
      out("worn").textContent = state.worn;
      // One effect at a time: while one is off its base, the other two wait at theirs.
      var on = EFFECTS.filter(function (n) { return state[n] !== 0; })[0];
      EFFECTS.forEach(function (n) { ctl(n).closest(".control").classList.toggle("is-off", !!on && on !== n); });
    }

    ["italic", "invert"].forEach(function (name) {
      ctl(name).addEventListener("change", function (e) { state[name] = e.target.checked; render(); });
    });
    ["wght", "size", "burn", "inkb", "worn"].forEach(function (name) {
      ctl(name).addEventListener("input", function (e) {
        var v = Number(e.target.value);
        // The weight slider clicks into Regular, Medium and SemiBold when it passes close by.
        if (name === "wght") { [400, 500, 600].forEach(function (s) { if (Math.abs(v - s) <= 6) v = s; }); }
        if (EFFECTS.indexOf(name) >= 0) {
          EFFECTS.forEach(function (o) { if (o !== name && state[o] !== 0) { state[o] = 0; ctl(o).value = 0; } });
        }
        state[name] = v; render();
      });
    });

    // Start smaller on phones so the sample fits.
    if (window.innerWidth < 600) { state.size = 56; ctl("size").value = 56; }
    // Reset puts every control back where the page started.
    var initial = JSON.parse(JSON.stringify(state));
    $("[data-reset]", tester).addEventListener("click", function () {
      Object.keys(initial).forEach(function (k) {
        state[k] = initial[k];
        var c = ctl(k);
        if (c) { if (c.type === "checkbox") c.checked = state[k]; else c.value = state[k]; }
      });
      render();
    });
    // Paste as plain text only.
    sample.addEventListener("paste", function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData("text/plain");
      document.execCommand("insertText", false, text);
    });
    render();
  }

  // ---------- Glyph browser ----------
  var grid = $("[data-glyph-grid]");
  var groups = window.SUNDAY_GLYPHS || [];
  if (grid && groups.length) {
    var zoom = $("[data-glyph-zoom]");
    var zChar = $("[data-zoom-char]");
    var zName = $("[data-zoom-name]");
    var zCode = $("[data-zoom-code]");
    var active = null;
    var hex = function (cp) { return "U+" + cp.toString(16).toUpperCase().padStart(4, "0"); };
    // Combining marks are drawn on a no-break space so they show on their own.
    var show = function (cp) { return /Marks/.test(this) ? " " + String.fromCodePoint(cp) : String.fromCodePoint(cp); };

    function select(btn) {
      if (active) active.classList.remove("active");
      active = btn; btn.classList.add("active");
      zChar.textContent = btn.textContent;
      zName.textContent = btn.dataset.name;
      zCode.textContent = hex(Number(btn.dataset.cp));
    }

    function build(groupName) {
      grid.textContent = "";
      var frag = document.createDocumentFragment();
      groups.forEach(function (g) {
        if (groupName !== "All" && g.name !== groupName) return;
        g.glyphs.forEach(function (item) {
          var b = document.createElement("button");
          b.type = "button";
          b.setAttribute("role", "listitem");
          b.textContent = show.call(g.name, item[0]);
          b.dataset.cp = item[0];
          b.dataset.name = item[1];
          b.title = item[1] + " " + hex(item[0]);
          frag.appendChild(b);
        });
      });
      grid.appendChild(frag);
      var first = grid.querySelector("button");
      if (first) select(first);
    }

    grid.addEventListener("pointerover", function (e) { if (e.target.dataset && e.target.dataset.cp) select(e.target); });
    grid.addEventListener("focusin", function (e) { if (e.target.dataset && e.target.dataset.cp) select(e.target); });
    grid.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      select(b);
      copy(String.fromCodePoint(Number(b.dataset.cp)), "Copied " + hex(Number(b.dataset.cp)));
    });

    bindSeg($('[data-seg="glyph-style"]'), function (v) {
      grid.classList.toggle("italic", v === "italic");
      zoom.classList.toggle("italic", v === "italic");
    });
    build("All");
  }
})();
