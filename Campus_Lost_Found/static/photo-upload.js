(() => {
  "use strict";
  const field = document.querySelector("[data-photo-upload]");
  if (!field || typeof FileReader === "undefined") return;
  const input = field.querySelector("input[type=file]");
  const surface = field.querySelector(".photo-surface");
  const choose = field.querySelector(".photo-choose");
  const clear = field.querySelector(".photo-clear");
  const preview = field.querySelector(".photo-preview");
  const icon = field.querySelector(".photo-icon");
  const title = field.querySelector(".photo-title");
  const description = field.querySelector(".photo-description");
  const error = field.querySelector(".photo-error");
  const status = field.querySelector(".photo-sr-status");
  const initialTitle = title.textContent;
  const initialDescription = description.textContent;
  let revision = 0;
  let reader = null;

  const reset = (message = "") => {
    revision += 1;
    if (reader && reader.readyState === FileReader.LOADING) reader.abort();
    input.value = "";
    input.setCustomValidity("");
    delete field.dataset.selected;
    preview.hidden = true;
    preview.removeAttribute("src");
    icon.removeAttribute("hidden");
    clear.hidden = true;
    title.textContent = initialTitle;
    description.textContent = initialDescription;
    choose.textContent = "Choose photo";
    error.hidden = !message;
    error.textContent = message;
  };

  const update = () => {
    const file = input.files[0];
    if (!file) {
      reset();
      return;
    }
    const extension = file.name.split(".").pop().toLowerCase();
    const expectedType = extension === "png" ? "image/png" : /^(jpe?g)$/.test(extension) ? "image/jpeg" : "";
    if (!expectedType || file.type !== expectedType) {
      reset("Choose a JPG or PNG photo with the matching file extension.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      reset("This photo is too large. Choose a file no larger than 5 MB.");
      return;
    }
    const current = ++revision;
    if (reader && reader.readyState === FileReader.LOADING) reader.abort();
    error.hidden = true;
    error.textContent = "";
    title.textContent = file.name;
    description.textContent = "Preparing your preview…";
    clear.hidden = false;
    choose.textContent = "Change photo";
    preview.hidden = true;
    icon.removeAttribute("hidden");
    delete field.dataset.selected;
    reader = new FileReader();
    reader.onerror = () => {
      if (current === revision) reset("This photo could not be read. Please choose another JPG or PNG.");
    };
    reader.onload = () => {
      if (current !== revision) return;
      const image = new Image();
      image.onerror = () => {
        if (current === revision) reset("This file is not a readable photo. Please choose another JPG or PNG.");
      };
      image.onload = () => {
        if (current !== revision) return;
        if (image.naturalWidth * image.naturalHeight > 12000000) {
          reset("This photo is over 12 megapixels. Choose a smaller image.");
          return;
        }
        preview.src = image.src;
        preview.hidden = false;
        icon.setAttribute("hidden", "");
        field.dataset.selected = "true";
        const size = file.size >= 1024 * 1024 ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(file.size / 1024))} KB`;
        description.textContent = `${size} · ${image.naturalWidth} × ${image.naturalHeight} · Ready to attach`;
        input.setCustomValidity("");
        status.textContent = `${file.name} selected. Photo preview ready.`;
      };
      image.src = reader.result;
    };
    reader.readAsDataURL(file);
  };

  choose.addEventListener("click", () => input.click());
  input.addEventListener("change", update);
  clear.addEventListener("click", () => {
    reset();
    status.textContent = field.dataset.editing === "true" ? "New photo selection cleared. Your existing photograph will be kept." : "Photo selection cleared.";
    choose.focus();
  });
  input.form.addEventListener("reset", () => {
    reset();
    status.textContent = "Photo selection cleared.";
  });
  // Only replace the native chooser after all enhancement handlers are ready.
  input.hidden = true;
  surface.hidden = false;
  if (input.files.length) update();
})();
