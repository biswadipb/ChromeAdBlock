// Runs in the page's own JS world: strips ad data from YouTube's player responses.
(() => {
  const AD_KEYS = ["adPlacements", "adSlots", "playerAds"];
  const clean = (o) => {
    if (o && typeof o === "object") {
      for (const k of AD_KEYS) if (k in o) delete o[k];
      if (o.playerResponse) clean(o.playerResponse);
      if (o.response) clean(o.response);
    }
    return o;
  };

  const origParse = JSON.parse;
  JSON.parse = function (...a) { return clean(origParse.apply(this, a)); };

  const origJson = Response.prototype.json;
  Response.prototype.json = function () {
    return origJson.call(this).then(clean);
  };

  let pr;
  try {
    Object.defineProperty(window, "ytInitialPlayerResponse", {
      configurable: true,
      get: () => pr,
      set: (v) => { pr = clean(v); },
    });
  } catch (_) {}
})();
