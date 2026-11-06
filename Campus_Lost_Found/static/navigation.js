/* Early, same-origin page transitions. Native navigation is never intercepted. */
(() => {
  "use strict";
  const root = document.documentElement;
  const tabs = ["/admin", "/admin/notices", "/admin/users"];
  const previousPageKey = "campus-transition-source";
  let currentTransition = null;

  const motionAllowed = () => {
    let savedOff = root.dataset.motion === "off";
    try { savedOff = localStorage.getItem("campus-motion") === "off"; } catch (_) {}
    let reduced = false;
    try { reduced = matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (_) {}
    root.dataset.motion = savedOff || reduced ? "off" : "on";
    return !savedOff && !reduced;
  };

  const direction = (activation, previous) => {
    try {
      const source = activation && activation.from && activation.from.url ? activation.from : previous;
      const destination = activation && activation.entry || { url: location.href };
      const from = new URL(source.url);
      const to = new URL(destination.url);
      const oldTab = tabs.indexOf(from.pathname);
      const newTab = tabs.indexOf(to.pathname);
      if (oldTab >= 0 && newTab >= 0 && oldTab !== newTab)
        return newTab < oldTab ? "back" : "forward";
      if (activation && activation.navigationType === "traverse" &&
          destination.index < source.index) return "back";
      if (from.pathname === to.pathname &&
          Number(to.searchParams.get("page") || 1) < Number(from.searchParams.get("page") || 1))
        return "back";
    } catch (_) { /* Direction is decorative; navigation does not depend on it. */ }
    return "forward";
  };

  const reset = (native = false) => {
    currentTransition = null;
    root.dataset.pageTransition = native ? "complete" : "entry";
    root.removeAttribute("data-page-direction");
    document.dispatchEvent(new CustomEvent("campus:page-ready", { detail: { native } }));
  };

  motionAllowed();
  root.dataset.pageTransition = "entry";

  window.addEventListener("pageswap", (event) => {
    if (!event.viewTransition) return;
    // Skipped transitions also reject ready; handle them before any early return.
    event.viewTransition.ready.catch(() => {});
    if (!motionAllowed()) {
      event.viewTransition.skipTransition();
      return;
    }
    const source = { url: location.href, index: window.navigation && navigation.currentEntry.index,
      at: Date.now() };
    // Some privacy settings omit activation.from; keep a short-lived, per-tab fallback.
    try { sessionStorage.setItem(previousPageKey, JSON.stringify(source)); } catch (_) {}
    root.dataset.pageDirection = direction(event.activation, source);
    root.dataset.pageTransition = "leaving";
    document.dispatchEvent(new CustomEvent("campus:transition-start"));
    event.viewTransition.finished.then(() => reset(true), () => reset(true));
  });

  window.addEventListener("pagereveal", (event) => {
    const allowed = motionAllowed();
    const transition = event.viewTransition;
    let previous = null;
    try {
      previous = JSON.parse(sessionStorage.getItem(previousPageKey));
      sessionStorage.removeItem(previousPageKey);
      if (!previous || Date.now() - previous.at > 10000) previous = null;
    } catch (_) {}
    if (!transition) {
      reset(false);
      return;
    }
    currentTransition = transition;
    root.dataset.pageDirection = direction(window.navigation && window.navigation.activation, previous);
    root.dataset.pageTransition = "active";
    document.dispatchEvent(new CustomEvent("campus:transition-start"));
    if (!allowed) transition.skipTransition();
    transition.ready.catch(() => {});
    transition.finished.then(() => reset(true), () => reset(true));
  });

  document.addEventListener("campus:motion-change", (event) => {
    if (!event.detail.enabled && currentTransition) currentTransition.skipTransition();
  });

  // Restore current preferences after history navigation, including BFCache.
  window.addEventListener("pageshow", (event) => {
    if (!event.persisted) return;
    motionAllowed();
    document.dispatchEvent(new CustomEvent("campus:motion-refresh"));
  });
})();
