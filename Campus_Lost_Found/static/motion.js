/* Optional presentation effects: page content and controls work without this file. */
(() => {
  "use strict";

  const initialize = () => {
    const root = document.documentElement;
    const toggle = document.getElementById("motion-toggle");
    const label = toggle && toggle.querySelector("[data-motion-label]");
    const storageKey = "campus-motion";
    const entranceSelector = [
      ".notice-card", ".category-tile", ".analytics-card",
      ".analytics-metrics > div", ".stage2-card", ".how-steps li",
      ".form-card", ".side-note", ".hero-orbit",
      ".admin-stat", ".admin-card", ".admin-tool",
      ".admin-table tbody tr", ".admin-latest li", ".detail-main"
    ].join(",");
    const seen = new WeakSet();
    const animations = new Set();
    const ripples = new Map();
    let observer = null;
    let preference = null;
    let manualOff = false;
    let enabled = false;

    const transitioning = () => ["active", "leaving"].includes(root.dataset.pageTransition);
    const markVisible = () => {
      document.querySelectorAll(`${entranceSelector}, .analytics-chart`).forEach((element) => {
        const bounds = element.getBoundingClientRect();
        if (bounds.height && bounds.bottom > 0 && bounds.top < window.innerHeight)
          seen.add(element);
      });
    };

    // Storage and media-query APIs can be unavailable in private or embedded views.
    try {
      manualOff = window.localStorage.getItem(storageKey) === "off";
    } catch (_) { /* The current page still has a working motion switch. */ }
    try {
      preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    } catch (_) { /* Use the manual preference when matchMedia is unavailable. */ }

    const removeRipple = (ripple) => {
      window.clearTimeout(ripples.get(ripple));
      ripples.delete(ripple);
      ripple.remove();
    };

    const stop = () => {
      if (observer) {
        observer.disconnect();
        observer = null;
      }
      animations.forEach((animation) => {
        try { animation.cancel(); } catch (_) { /* Already detached or finished. */ }
      });
      animations.clear();
      ripples.forEach((_, ripple) => removeRipple(ripple));
    };

    const play = (element, frames, options) => {
      if (!enabled || transitioning() || typeof element.animate !== "function") return;
      try {
        const animation = element.animate(frames, options);
        animations.add(animation);
        animation.onfinish = () => animations.delete(animation);
        animation.oncancel = () => animations.delete(animation);
      } catch (_) {
        // Unsupported effects leave the original, fully visible element untouched.
      }
    };

    const enter = (element, index) => {
      // No backwards fill: queued elements keep their normal visible appearance.
      const delay = (index % 5) * 45;
      if (element.matches(".analytics-chart")) {
        element.querySelectorAll('rect[class^="bar-"]').forEach((bar, barIndex) => {
          play(bar, [
            { transform: "scaleX(0.2)", transformOrigin: "left center", opacity: 0.7 },
            { transform: "scaleX(1)", transformOrigin: "left center", opacity: 1 }
          ], {
            duration: 720,
            delay: (barIndex % 6) * 38,
            easing: "cubic-bezier(0.22, 1, 0.36, 1)",
            fill: "none"
          });
        });
        return;
      }
      const row = element.matches("tr, .admin-latest li");
      play(element, [
        { transform: row ? "translateY(7px)" : "translateY(18px) scale(0.985)", opacity: row ? 0.8 : 0.55 },
        { transform: "translateY(0) scale(1)", opacity: 1 }
      ], {
        duration: row ? 360 : element.matches(".hero-orbit") ? 800 : 620,
        delay,
        easing: "cubic-bezier(0.22, 1, 0.36, 1)",
        fill: "none"
      });
    };

    const start = () => {
      if (observer || !enabled || transitioning() || typeof window.IntersectionObserver !== "function" ||
          typeof Element.prototype.animate !== "function") return;
      try {
        observer = new IntersectionObserver((entries) => {
          if (!enabled || transitioning()) return;
          let index = 0;
          entries.forEach((entry) => {
            if (!entry.isIntersecting || seen.has(entry.target)) return;
            seen.add(entry.target);
            observer && observer.unobserve(entry.target);
            enter(entry.target, index++);
          });
        }, { threshold: 0.08, rootMargin: "0px 0px -16px 0px" });
        document.querySelectorAll(`${entranceSelector}, .analytics-chart`).forEach((element) => {
          if (!seen.has(element)) observer.observe(element);
        });
      } catch (_) {
        if (observer) observer.disconnect();
        observer = null;
      }
    };

    const applyPreference = () => {
      const systemReduced = Boolean(preference && preference.matches);
      enabled = !manualOff && !systemReduced;
      root.dataset.motion = enabled ? "on" : "off";
      if (toggle) {
        toggle.hidden = false;
        toggle.setAttribute("aria-pressed", String(!enabled));
        toggle.setAttribute("aria-disabled", String(systemReduced));
        toggle.title = systemReduced
          ? "Motion is reduced by your device setting"
          : enabled ? "Pause decorative animations" : "Enable decorative animations";
      }
      if (label) label.textContent = enabled ? "Motion on" : "Motion off";
      document.dispatchEvent(new CustomEvent("campus:motion-change", { detail: { enabled } }));
      if (enabled) start();
      else stop();
    };

    if (toggle) {
      toggle.addEventListener("click", () => {
        if (preference && preference.matches) return;
        manualOff = !manualOff;
        try {
          window.localStorage.setItem(storageKey, manualOff ? "off" : "on");
        } catch (_) { /* Persisting is optional; this page still updates immediately. */ }
        applyPreference();
      });
    }

    if (preference) {
      if (typeof preference.addEventListener === "function") {
        preference.addEventListener("change", applyPreference);
      } else if (typeof preference.addListener === "function") {
        preference.addListener(applyPreference);
      }
    }
    window.addEventListener("storage", (event) => {
      if (event.key !== storageKey && event.key !== null) return;
      manualOff = event.newValue === "off";
      applyPreference();
    });

    document.addEventListener("campus:transition-start", stop);
    document.addEventListener("campus:page-ready", (event) => {
      // The new page has already appeared as a snapshot; do not animate it twice.
      if (event.detail.native) markVisible();
      start();
    });
    document.addEventListener("campus:motion-refresh", () => {
      try { manualOff = window.localStorage.getItem(storageKey) === "off"; } catch (_) {}
      applyPreference();
    });

    // Bubble only: this listener never delays, cancels, or redirects a real action.
    document.addEventListener("click", (event) => {
      if (!enabled || event.defaultPrevented || !(event.target instanceof Element)) return;
      const button = event.target.closest("button, .button");
      if (!button || button === toggle || button.matches(":disabled, [aria-disabled='true']")) return;
      const bounds = button.getBoundingClientRect();
      if (!bounds.width || !bounds.height) return;
      button.querySelectorAll(".motion-ripple").forEach(removeRipple);
      const ripple = document.createElement("span");
      const size = Math.max(bounds.width, bounds.height) * 2;
      const x = event.detail === 0 ? bounds.width / 2 : event.clientX - bounds.left;
      const y = event.detail === 0 ? bounds.height / 2 : event.clientY - bounds.top;
      ripple.className = "motion-ripple";
      ripple.setAttribute("aria-hidden", "true");
      ripple.style.width = `${size}px`;
      ripple.style.height = `${size}px`;
      ripple.style.left = `${x - size / 2}px`;
      ripple.style.top = `${y - size / 2}px`;
      ripple.addEventListener("animationend", () => removeRipple(ripple), { once: true });
      button.appendChild(ripple);
      ripples.set(ripple, window.setTimeout(() => removeRipple(ripple), 900));
    });

    if (root.dataset.pageTransition === "complete") markVisible();
    applyPreference();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
