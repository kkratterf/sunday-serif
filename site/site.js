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
    window.addEventListener("pointermove", function (e) {
      if (e.pointerType !== "mouse") return;
      if (hero.contains(e.target)) loadFx();
      // Left edge: the ink spreads (-40); right edge: the strokes burn thin (+40).
      target = ((e.clientX / window.innerWidth) * 2 - 1) * 40;
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
    var cssOut = $("[data-css-out]");
    var ctl = function (name) { return $('[data-ctl="' + name + '"]', tester); };
    var out = function (name) { return $('[data-out="' + name + '"]', tester); };
    var state = { wght: 400, italic: false, invert: false, size: 96, burn: 0, inkb: 0, worn: 0 };
    var weightNames = { 400: "Regular", 500: "Medium", 600: "SemiBold" };
    var weightLabel = function (w) { return weightNames[w] ? w + " " + weightNames[w] : String(w); };

    function cssText() {
      var lines = [];
      var fx = state.burn || state.inkb || state.worn;
      lines.push(fx ? 'font-family: "Sunday Serif FX", "Sunday Serif", serif; /* the effects build */' : 'font-family: "Sunday Serif", Georgia, serif;');
      lines.push("font-weight: " + state.wght + ";" + (weightNames[state.wght] ? " /* " + weightNames[state.wght] + " */" : ""));
      if (state.italic) lines.push("font-style: italic;");
      lines.push("font-size: " + state.size + "px;");
      var axes = [];
      if (state.burn) axes.push('"BURN" ' + state.burn);
      if (state.inkb) axes.push('"INKB" ' + state.inkb);
      if (state.worn) axes.push('"WORN" ' + state.worn);
      if (axes.length) lines.push("font-variation-settings: " + axes.join(", ") + ";");
      return ".sunday {\n  " + lines.join("\n  ") + "\n}";
    }

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
      $$("[data-preset]", tester).forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.dataset.preset === [state.burn, state.inkb, state.worn].join(",")));
      });
      if (cssOut) cssOut.textContent = cssText();
    }

    ["italic", "invert"].forEach(function (name) {
      ctl(name).addEventListener("change", function (e) { state[name] = e.target.checked; render(); });
    });
    ["wght", "size", "burn", "inkb", "worn"].forEach(function (name) {
      ctl(name).addEventListener("input", function (e) {
        var v = Number(e.target.value);
        // The weight slider clicks into Regular, Medium and SemiBold when it passes close by.
        if (name === "wght") { [400, 500, 600].forEach(function (s) { if (Math.abs(v - s) <= 6) v = s; }); }
        state[name] = v; render();
      });
    });
    $$("[data-preset]", tester).forEach(function (b) {
      b.addEventListener("click", function () {
        var v = b.dataset.preset.split(",").map(Number);
        state.burn = v[0]; state.inkb = v[1]; state.worn = v[2];
        ctl("burn").value = v[0]; ctl("inkb").value = v[1]; ctl("worn").value = v[2];
        render();
      });
    });

    // Start smaller on phones so the sample fits.
    if (window.innerWidth < 600) { state.size = 56; ctl("size").value = 56; }
    // Paste as plain text only.
    sample.addEventListener("paste", function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData("text/plain");
      document.execCommand("insertText", false, text);
    });
    render();
  }

  // ---------- Copy buttons ----------
  $$("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var el = document.getElementById(btn.dataset.copy);
      if (el) copy(el.textContent, "CSS copied");
    });
  });

  // ---------- Effect cards: tap to pause on touch screens ----------
  $$(".effect").forEach(function (card) {
    card.addEventListener("click", function () { card.classList.toggle("paused"); });
  });

  // ---------- Glyph browser ----------
  var grid = $("[data-glyph-grid]");
  var groups = window.SUNDAY_GLYPHS || [];
  if (grid && groups.length) {
    var zoom = $("[data-glyph-zoom]");
    var zChar = $("[data-zoom-char]");
    var zName = $("[data-zoom-name]");
    var zCode = $("[data-zoom-code]");
    var filterBox = $("[data-glyph-filter]");
    var active = null;
    var total = 0;
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

    var names = ["All"].concat(groups.map(function (g) { total += g.glyphs.length; return g.name; }));
    names.forEach(function (name, i) {
      var b = document.createElement("button");
      b.type = "button"; b.textContent = name; b.setAttribute("aria-pressed", String(i === 0));
      b.addEventListener("click", function () {
        $$("button", filterBox).forEach(function (o) { o.setAttribute("aria-pressed", String(o === b)); });
        build(name);
      });
      filterBox.appendChild(b);
    });
    bindSeg($('[data-seg="glyph-style"]'), function (v) {
      grid.classList.toggle("italic", v === "italic");
      zoom.classList.toggle("italic", v === "italic");
    });
    $$("[data-glyph-count]").forEach(function (el) { el.textContent = total; });
    build("All");
  }
})();
