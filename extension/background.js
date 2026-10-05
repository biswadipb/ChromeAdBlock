// Service worker: (1) enables as many network rulesets as Chrome's static-rule budget allows,
// (2) injects per-site element-hiding CSS on navigation, (3) answers generic class/id lookups.

const url = (p) => chrome.runtime.getURL(p);
const getJson = async (p) => (await fetch(url(p))).json();
const css = (sels) => sels.map((s) => `${s}{display:none!important}`).join("\n");

// ---- network rulesets ------------------------------------------------------------------
async function enableRulesets() {
  const meta = await getJson("meta.json");
  const enabled = new Set(await chrome.declarativeNetRequest.getEnabledRulesets());
  let room = await chrome.declarativeNetRequest.getAvailableStaticRuleCount();
  const add = [];
  for (const r of meta.rulesets) {
    if (enabled.has(r.id)) continue;
    if (r.count <= room) { add.push(r.id); room -= r.count; }
  }
  if (add.length) {
    try { await chrome.declarativeNetRequest.updateEnabledRulesets({ enableRulesetIds: add }); }
    catch (e) { console.warn("Could not enable rulesets", add, e); }
  }
}
chrome.runtime.onInstalled.addListener(enableRulesets);
chrome.runtime.onStartup.addListener(enableRulesets);

// ---- per-site element hiding ------------------------------------------------------------
function fnv(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
  return h >>> 0;
}
let shardCount = null;
const shardCache = new Map();
async function shard(n) {
  if (!shardCache.has(n)) {
    const p = String(n).padStart(2, "0");
    shardCache.set(n, fetch(url(`cosmetic/${p}.json`)).then((r) => (r.ok ? r.json() : {})).catch(() => ({})));
  }
  return shardCache.get(n);
}
async function domainSelectors(host) {
  if (shardCount === null) shardCount = (await getJson("meta.json")).shards;
  const parts = host.split(".");
  const out = [];
  for (let i = 0; i < parts.length - 1; i++) {
    const d = parts.slice(i).join(".");
    const data = await shard(fnv(d) % shardCount);
    if (data[d]) out.push(...data[d]);
  }
  return out;
}
chrome.webNavigation.onCommitted.addListener(async (d) => {
  if (!/^https?:/.test(d.url)) return;
  try {
    const sels = await domainSelectors(new URL(d.url).hostname);
    if (sels.length) {
      await chrome.scripting.insertCSS({
        target: { tabId: d.tabId, frameIds: [d.frameId] }, css: css(sels), origin: "USER" });
    }
  } catch (_) { /* tab closed or page not scriptable */ }
});

// ---- generic class/id lookups from the content script -----------------------------------------
let genericIndex = null;
async function lookupGeneric(classes, ids) {
  genericIndex ||= getJson("generic-index.json");
  const idx = await genericIndex;
  const out = new Set();
  const add = (map, tok, sym) => {
    const v = map[tok];
    if (v === 1) out.add(sym + tok);
    else if (v) v.forEach((s) => out.add(s));
  };
  classes.forEach((c) => add(idx.c, c.toLowerCase(), "."));
  ids.forEach((i) => add(idx.i, i.toLowerCase(), "#"));
  return [...out];
}
chrome.runtime.onMessage.addListener((msg, _sender, send) => {
  if (msg && msg.t === "generic") {
    lookupGeneric(msg.classes || [], msg.ids || []).then(send, () => send([]));
    return true;  // async response
  }
});
