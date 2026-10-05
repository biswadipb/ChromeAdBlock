// Generic element hiding: report the classes/ids present on the page and hide whichever
// ones the filter lists flag (same approach uBlock Origin uses, so no giant stylesheet per page).
(() => {
  if (!document.documentElement) return;
  const seenC = new Set(), seenI = new Set();
  let pendC = [], pendI = [], timer = null, style = null;

  function flush() {
    timer = null;
    if (!pendC.length && !pendI.length) return;
    const msg = { t: "generic", classes: pendC, ids: pendI };
    pendC = []; pendI = [];
    try {
      chrome.runtime.sendMessage(msg, (sels) => {
        if (chrome.runtime.lastError || !sels || !sels.length) return;
        if (!style) {
          style = document.createElement("style");
          (document.head || document.documentElement).appendChild(style);
        }
        style.textContent += sels.map((s) => `${s}{display:none!important}`).join("\n") + "\n";
      });
    } catch (_) { /* extension reloaded */ }
  }
  function collect(el) {
    if (el.nodeType !== 1) return;
    if (el.id && !seenI.has(el.id)) { seenI.add(el.id); pendI.push(el.id); }
    for (const c of el.classList) if (!seenC.has(c)) { seenC.add(c); pendC.push(c); }
  }
  function scan(root) {
    collect(root);
    if (root.querySelectorAll) root.querySelectorAll("[class],[id]").forEach(collect);
    if (!timer && (pendC.length || pendI.length)) timer = setTimeout(flush, 120);
  }
  new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type === "attributes") collect(m.target);
      else m.addedNodes.forEach((n) => n.nodeType === 1 && scan(n));
    }
    if (!timer && (pendC.length || pendI.length)) timer = setTimeout(flush, 120);
  }).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "id"] });
  scan(document.documentElement);

  // Remove invisible full-page overlays that hijack clicks to open ads (top frame only).
  if (window.top === window) {
    setInterval(() => {
      const vw = innerWidth, vh = innerHeight;
      for (const el of document.body ? document.body.children : []) {
        const cs = getComputedStyle(el);
        if (cs.position !== "fixed" && cs.position !== "absolute") continue;
        const r = el.getBoundingClientRect();
        const covers = r.width >= vw * 0.9 && r.height >= vh * 0.9;
        const invisible = parseFloat(cs.opacity) < 0.05 || cs.backgroundColor === "rgba(0, 0, 0, 0)";
        const empty = !el.innerText.trim() && !el.querySelector("img,video,input,button,form");
        if (covers && invisible && empty && (parseInt(cs.zIndex) || 0) > 999) el.remove();
      }
    }, 1000);
  }
})();
