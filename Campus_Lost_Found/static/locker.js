(() => {
  "use strict";
  const app = document.querySelector(".locker-app");
  if (!app || !window.fetch || !window.FormData || !window.DOMParser) return;

  const controls = app.querySelector("#locker-controls");
  const status = app.querySelector("#locker-status");
  const visual = app.querySelector(".locker-visual");
  let busy = false;
  let mustRefresh = false;
  app.querySelector(".locker-feedback").hidden = false;
  visual.classList.add("locker-interactive");

  function report(message, state = "ready") {
    status.textContent = message;
    app.dataset.requestState = state;
  }

  function setBusy(value) {
    busy = value;
    app.setAttribute("aria-busy", String(value));
    app.querySelectorAll("[data-locker-form] button").forEach(button => {
      button.disabled = value || mustRefresh || button.dataset.unavailable === "true";
    });
    controls.querySelector("select").disabled = value || mustRefresh;
    app.querySelectorAll("button[data-locker-refresh]").forEach(button => {
      button.disabled = value;
    });
  }

  function updatePage(page, preserveSelection) {
    const incoming = page.querySelector(".locker-app");
    const reading = incoming && incoming.querySelector("#locker-reading");
    const history = incoming && incoming.querySelector("#locker-history");
    const incomingSelect = incoming && incoming.querySelector("#locker-controls select");
    const incomingVisual = incoming && incoming.querySelector(".locker-visual");
    if (!reading || !history || !incomingSelect || !incomingVisual) {
      throw new Error("The session or response changed. Reload this page to sign in again.");
    }
    const selected = controls.querySelector("select");
    const priorValue = selected.value;
    const savedValue = incomingSelect.value;
    const priorEvent = app.querySelector("#locker-history td").textContent;
    app.querySelector("#locker-reading").replaceChildren(...reading.childNodes);
    app.querySelector("#locker-history").replaceChildren(...history.childNodes);
    selected.replaceChildren(...incomingSelect.childNodes);
    // Moving options can change their live selected state as the old select empties.
    selected.value = savedValue;
    if (preserveSelection && [...selected.options].some(option => option.value === priorValue)) {
      selected.value = priorValue;
    }
    controls.querySelector('[name="action"][value="heartbeat"]').dataset.unavailable =
      incoming.querySelector('[name="action"][value="heartbeat"]').dataset.unavailable;
    controls.querySelector('[name="csrf"]').value = incoming.querySelector('#locker-controls [name="csrf"]').value;
    // Keep this node: its transform can now move smoothly between door states.
    visual.dataset.door = incomingVisual.dataset.door;
    const newest = app.querySelector("#locker-history tr");
    if (newest && newest.querySelector("td").textContent !== priorEvent) {
      newest.classList.add("is-new-reading");
    }
  }

  async function requestUpdate(form, submitter) {
    if (busy || (form && mustRefresh)) return;
    const focused = document.activeElement;
    const anchor = controls;
    let anchorTop = null;
    let body;
    if (form) {
      body = new FormData(form);
      if (submitter && submitter.name) body.set(submitter.name, submitter.value);
    }
    setBusy(true);
    report(form ? "Saving reading…" : "Checking the latest state…", "pending");
    let response;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      response = await fetch(window.location.pathname, {
        method: form ? "POST" : "GET",
        body,
        credentials: "same-origin",
        cache: "no-store",
        redirect: "follow",
        signal: controller.signal
      });
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      if (!response.ok) {
        const message = page.querySelector(".empty h1 + p");
        throw new Error(message ? message.textContent : "The reading could not be saved. Refresh status and try again.");
      }
      if (new URL(response.url).pathname !== window.location.pathname) {
        mustRefresh = true;
        report("Your session has expired. Reload this page and sign in again.", "error");
        return;
      }
      anchorTop = anchor.getBoundingClientRect().top;
      updatePage(page, !form);
      mustRefresh = false;
      const state = visual.dataset.door;
      const action = body && body.get("action");
      report(form ? (action === "heartbeat" ? "Heartbeat saved. Door state is unchanged." :
        action === "reset" ? "Assignment reset. The locker is closed." :
        `Reading saved. Door is ${state}.`) : `Status refreshed. Door is ${state === "unknown" ? "not yet recorded" : state}.`);
    } catch (error) {
      // A lost response may follow a successful write. Never resend a POST automatically.
      mustRefresh = !response || response.ok || response.status >= 500;
      report(mustRefresh ? "The result could not be confirmed. Refresh status before trying another action." : error.message, "error");
    } finally {
      window.clearTimeout(timeout);
      setBusy(false);
      const currentFocus = document.activeElement;
      if (focused && focused.isConnected && !focused.disabled &&
          (currentFocus === focused || currentFocus === document.body)) {
        focused.focus({preventScroll: true});
      }
      // Compensate for state text changing height, keeping the controls at the same position.
      const shift = anchorTop === null ? 0 : anchor.getBoundingClientRect().top - anchorTop;
      if (Math.abs(shift) > 1) {
        window.scrollTo({top: window.scrollY + shift, left: window.scrollX, behavior: "instant"});
      }
    }
  }

  app.addEventListener("submit", event => {
    const form = event.target.closest("[data-locker-form]");
    if (!form) return;
    event.preventDefault();
    requestUpdate(form, event.submitter);
  });

  app.addEventListener("click", event => {
    const refresh = event.target.closest("[data-locker-refresh]");
    if (!refresh || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    requestUpdate(null, null);
  });
})();
