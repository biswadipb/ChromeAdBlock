// Page-world script: blocks popups/popunders and script-driven redirects without a user click.
(() => {
  const active = () => navigator.userActivation ? navigator.userActivation.isActive : true;

  const realOpen = window.open;
  window.open = function (url, ...rest) {
    if (!active()) return null;
    // Even with a click, drop popups to a different site opened from a link-less click (popunder pattern).
    try {
      const u = new URL(url, location.href);
      if (u.origin !== location.origin && window.__lastClickTarget === document.body) return null;
    } catch (_) {}
    return realOpen.call(this, url, ...rest);
  };
  addEventListener("click", (e) => { window.__lastClickTarget = e.target; }, true);

  // Block programmatic clicks on off-site links (a common redirect trick).
  const realClick = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () {
    if (!active() && this.origin && this.origin !== location.origin) return;
    return realClick.apply(this, arguments);
  };

  // Block off-site <form> auto-submits with no user gesture.
  const realSubmit = HTMLFormElement.prototype.submit;
  HTMLFormElement.prototype.submit = function () {
    try {
      if (!active() && new URL(this.action, location.href).origin !== location.origin) return;
    } catch (_) {}
    return realSubmit.apply(this, arguments);
  };

  // Stop pages from trapping you with "are you sure you want to leave" loops.
  const realAdd = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (type, ...r) {
    if (type === "beforeunload" && this === window && !active()) return;
    return realAdd.call(this, type, ...r);
  };
})();
