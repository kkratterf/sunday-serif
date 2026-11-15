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
  // The text font is preloaded; the FX build (~1.8 MB a style) waits until the visitor moves the
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

  // ---------- The Grain font: Sunday Serif Grain, the Grain Blur axis ----------
  // Same idea: ~1.5 MB a style, loaded when the effects come into view, when the tester moves
  // Grain Blur, or when the print menu picks it. Until then var(--grain) is the text font.
  var grainState = 0;
  function loadGrain() {
    if (grainState || !document.fonts || !document.fonts.load) return;
    grainState = 1;
    Promise.all([
      document.fonts.load('400 1em "Sunday Serif Grain"'),
      document.fonts.load('italic 400 1em "Sunday Serif Grain"'),
    ]).then(function () { grainState = 2; root.classList.add("grain-ready"); }, function () { grainState = 0; });
  }
  if ("IntersectionObserver" in window) {
    var grainObserver = new IntersectionObserver(function (entries) {
      if (entries.some(function (e) { return e.isIntersecting; })) { loadGrain(); grainObserver.disconnect(); }
    }, { rootMargin: "0px" });
    $$("#effects").forEach(function (el) { grainObserver.observe(el); });
  } else { loadGrain(); }

  // ---------- Print menu: one effect for the whole page ----------
  // "Serif" is the clean print. The others set data-print on <html>; the CSS then sets every
  // text on the page, interface included, in Sunday Serif FX with that effect.
  var printBtn = $("[data-print-toggle]");
  var printMenu = $("[data-print-menu]");
  if (printBtn && printMenu) {
    var setPrint = function (v) {
      if (v && v !== "serif") { if (v === "grain") loadGrain(); else loadFx(); root.dataset.print = v; } else { delete root.dataset.print; v = "serif"; }
      $$("input", printMenu).forEach(function (i) { i.checked = i.value === v; });
      try { if (v === "serif") localStorage.removeItem("print"); else localStorage.setItem("print", v); } catch (e) {}
    };
    var open = function (on) {
      printMenu.hidden = !on;
      printBtn.setAttribute("aria-expanded", String(on));
      if (on) { var c = $("input:checked", printMenu); if (c) c.focus(); }
    };
    setPrint(root.dataset.print || "serif");
    printBtn.addEventListener("click", function (e) { e.stopPropagation(); open(printMenu.hidden); });
    printMenu.addEventListener("change", function (e) { setPrint(e.target.value); });
    printMenu.addEventListener("click", function (e) { e.stopPropagation(); });
    document.addEventListener("click", function () { if (!printMenu.hidden) open(false); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !printMenu.hidden) { open(false); printBtn.focus(); }
    });
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
    var state = { wght: 400, italic: false, invert: false, size: 96, burn: 0, inkb: 0, worn: 0, gran: 0 };
    var weightNames = { 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold" };
    var EFFECTS = ["burn", "inkb", "worn", "gran"];
    var weightLabel = function (w) { return weightNames[w] ? weightNames[w] + " " + w : String(w); };

    function render() {
      sample.style.fontWeight = String(state.wght);
      sample.style.fontStyle = state.italic ? "italic" : "normal";
      sample.style.fontSize = state.size + "px";
      // Grain Blur lives in its own family (Regular only): the weight waits at 400 meanwhile.
      var grain = state.gran !== 0;
      sample.style.fontFamily = grain ? "var(--grain)" : "";
      sample.style.fontWeight = grain ? "400" : String(state.wght);
      sample.style.fontSynthesis = grain ? "none" : "";
      sample.style.fontVariationSettings = grain ? '"GRAN" ' + state.gran
        : '"BURN" ' + state.burn + ', "INKB" ' + state.inkb + ', "WORN" ' + state.worn;
      $("[data-weight-control]", tester).classList.toggle("is-off", grain);
      stage.classList.toggle("inverted", state.invert);
      out("wght").textContent = weightLabel(state.wght);
      out("size").textContent = state.size;
      out("burn").textContent = state.burn;
      out("inkb").textContent = state.inkb;
      out("worn").textContent = state.worn;
      out("gran").textContent = state.gran;
      // One effect at a time: while one is off its base, the other two wait at theirs.
      var on = EFFECTS.filter(function (n) { return state[n] !== 0; })[0];
      EFFECTS.forEach(function (n) { ctl(n).closest(".control").classList.toggle("is-off", !!on && on !== n); });
    }

    ["italic", "invert"].forEach(function (name) {
      ctl(name).addEventListener("change", function (e) { state[name] = e.target.checked; render(); });
    });
    ["wght", "size", "burn", "inkb", "worn", "gran"].forEach(function (name) {
      ctl(name).addEventListener("input", function (e) {
        var v = Number(e.target.value);
        // The weight slider clicks into Regular, Medium, SemiBold and Bold when it passes close by.
        if (name === "wght") { [400, 500, 600, 700].forEach(function (s) { if (Math.abs(v - s) <= 6) v = s; }); }
        if (EFFECTS.indexOf(name) >= 0) {
          EFFECTS.forEach(function (o) { if (o !== name && state[o] !== 0) { state[o] = 0; ctl(o).value = 0; } });
        }
        if (name === "gran") loadGrain();
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
