(function () {
  "use strict";

  const shell = document.getElementById("site-faq-drawer");
  const panel = document.getElementById("site-faq-panel");
  const openButtons = Array.from(document.querySelectorAll(".js-faq-open"));

  if (!shell || !panel || !openButtons.length) return;

  const closeButtons = Array.from(shell.querySelectorAll(".js-faq-close"));
  const focusableSelector = [
    "a[href]",
    "button:not([disabled])",
    "summary",
    "input:not([disabled])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    '[tabindex]:not([tabindex="-1"])',
  ].join(",");
  let opener = null;

  function setExpanded(expanded) {
    openButtons.forEach((button) => {
      button.setAttribute("aria-expanded", String(expanded));
    });
  }

  function openFaq(event) {
    opener = event.currentTarget;
    shell.classList.add("is-open");
    shell.setAttribute("aria-hidden", "false");
    document.body.classList.add("faq-drawer-open");
    setExpanded(true);
    window.requestAnimationFrame(() => panel.focus());
  }

  function closeFaq() {
    if (!shell.classList.contains("is-open")) return;

    shell.classList.remove("is-open");
    shell.setAttribute("aria-hidden", "true");
    document.body.classList.remove("faq-drawer-open");
    setExpanded(false);
    if (opener) opener.focus();
  }

  function keepFocusInPanel(event) {
    if (event.key !== "Tab" || !shell.classList.contains("is-open")) return;

    const focusable = Array.from(panel.querySelectorAll(focusableSelector)).filter(
      (element) => element.offsetParent !== null
    );
    if (!focusable.length) {
      event.preventDefault();
      panel.focus();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  openButtons.forEach((button) => button.addEventListener("click", openFaq));
  closeButtons.forEach((button) => button.addEventListener("click", closeFaq));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeFaq();
    keepFocusInPanel(event);
  });
})();
