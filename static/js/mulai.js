/*
 * Shared motion helpers for the member-facing pages.
 *
 * The site is server-rendered with page-specific JS written inline, and that
 * stays true. This file exists only for the handful of effects that would
 * otherwise be copy-pasted into five templates: reveal on scroll, numbers
 * counting up, bars growing, and the progress rings filling.
 *
 * Rules it follows:
 *
 * - **Nothing here is required for the page to work.** Every element it touches
 *   renders complete and readable without it. The only thing that hides content
 *   is `.mg-reveal`, and that is gated on the `mg-js` class this file adds, so a
 *   browser with JS off never hides anything.
 * - **prefers-reduced-motion wins.** Everything jumps straight to its final
 *   state, no transitions, no counting.
 * - **Opt in from the markup**, with data attributes, so a template asks for an
 *   effect rather than this file knowing about pages.
 */
(function () {
  "use strict";

  var root = document.documentElement;
  var calm =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // base.html adds `mg-js` before first paint and takes it back off if this file
  // never arrives. Claiming it here is what stops that fallback firing.
  window.mgReady = true;
  if (calm) root.classList.remove("mg-js");

  var EASE_OUT = function (t) {
    return 1 - Math.pow(1 - t, 3);
  };

  function animate(duration, step, done) {
    var started = null;
    function frame(now) {
      if (started === null) started = now;
      var progress = Math.min(1, (now - started) / duration);
      step(EASE_OUT(progress));
      if (progress < 1) window.requestAnimationFrame(frame);
      else if (done) done();
    }
    window.requestAnimationFrame(frame);
  }

  /* Count a number up from zero. Reads data-count-up as the target. */
  function countUp(el) {
    var target = parseFloat(el.dataset.countUp);
    if (isNaN(target)) return;
    var decimals = (el.dataset.countDecimals | 0) || 0;
    var suffix = el.dataset.countSuffix || "";

    function show(value) {
      el.textContent =
        value.toLocaleString("id-ID", {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        }) + suffix;
    }

    if (calm || target <= 0) {
      show(target);
      return;
    }
    // Small numbers get a shorter run, so a streak of 3 does not crawl.
    var duration = Math.min(900, 260 + Math.abs(target) * 12);
    show(0);
    animate(duration, function (t) {
      show(target * t);
    });
  }

  /* Grow a bar to data-grow (any CSS width, e.g. "62%"). */
  function grow(el) {
    var to = el.dataset.grow;
    if (!to) return;
    if (calm) {
      el.style.width = to;
      return;
    }
    // The transition has to be off while the start value is set, or setting the
    // width to zero merely *animates towards* zero, and the target below then
    // overrides that mid-flight from the value it started at: no movement at all.
    // Measured frame by frame; a nested requestAnimationFrame did not fix it and
    // neither did forcing a reflow on its own.
    el.style.transition = "none";
    el.style.width = "0";
    void el.offsetWidth; // flush the zero before the transition comes back
    el.style.transition = "";
    el.style.width = to;
  }

  /* Sweep a conic-gradient ring from empty to data-ring percent. */
  function ring(el) {
    var target = parseFloat(el.dataset.ring);
    if (isNaN(target)) return;
    if (calm || target <= 0) {
      el.style.setProperty("--pct", target);
      return;
    }
    el.style.setProperty("--pct", 0);
    animate(700, function (t) {
      el.style.setProperty("--pct", (target * t).toFixed(1));
    });
  }

  /* Reveal on scroll, so a long page animates as you reach it rather than
     spending its whole budget above the fold. */
  function reveal() {
    var items = Array.prototype.slice.call(document.querySelectorAll(".mg-reveal"));
    if (!items.length) return;

    if (calm || !("IntersectionObserver" in window)) {
      items.forEach(function (item) {
        item.classList.add("is-in");
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-in");
          observer.unobserve(entry.target);
          runEffectsIn(entry.target);
        });
      },
      // Slightly before it scrolls in, so it is already settled on arrival.
      { rootMargin: "0px 0px -40px 0px", threshold: 0.05 }
    );
    items.forEach(function (item) {
      observer.observe(item);
    });
  }

  /* Effects inside a container, run when it appears. Marked as done so a
     nested element is never animated twice. */
  function runEffectsIn(scope) {
    var selectors = [
      ["[data-count-up]", countUp],
      ["[data-grow]", grow],
      ["[data-ring]", ring],
    ];
    selectors.forEach(function (pair) {
      Array.prototype.slice.call(scope.querySelectorAll(pair[0])).forEach(function (el) {
        if (el.dataset.mgDone) return;
        el.dataset.mgDone = "1";
        pair[1](el);
      });
    });
  }

  function start() {
    reveal();
    // Anything not inside a .mg-reveal container still runs now.
    runEffectsIn(document);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
