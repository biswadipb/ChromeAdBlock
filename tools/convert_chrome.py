#!/usr/bin/env python3
"""Convert Adblock Plus filter lists (EasyList etc.) into data for the Chrome (MV3) extension.

Writes into extension/:
  rulesets/<id>.json     declarativeNetRequest static rulesets (network blocking), <= CHUNK rules each
  cosmetic/NN.json       per-site element-hiding selectors, sharded by domain hash
  generic-index.json     class/id lookup table for generic element hiding
  generic.css            generic selectors that are not simple class/id selectors
  meta.json              ruleset order + counts (the service worker enables as many as Chrome allows)
  manifest.json          rule_resources section is rewritten

Usage: convert_chrome.py [--extension-dir extension]
"""
import argparse, json, os, re, shutil, sys, urllib.request
from collections import defaultdict

ADULT = "https://raw.githubusercontent.com/easylist/easylist/master/easylist_adult/"
UB = "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/"
AG = "https://filters.adtidy.org/extension/ublock/filters/"
GROUPS = [  # order = priority when Chrome cannot enable every ruleset
    ("easylist", ["https://easylist.to/easylist/easylist.txt"]),
    ("adguard-base", [AG + "2.txt"]),
    ("easyprivacy", ["https://easylist.to/easylist/easyprivacy.txt"]),
    ("ublock-privacy", [UB + "privacy.txt"]),
    ("annoyance", ["https://easylist.to/easylist/fanboy-annoyance.txt"]),
    ("adguard-annoyances", [AG + "14.txt"]),
    ("cookies", ["https://secure.fanboy.co.nz/fanboy-cookiemonster.txt"]),
    ("malware", ["https://malware-filter.gitlab.io/malware-filter/urlhaus-filter-agh-online.txt",
                 "https://raw.githubusercontent.com/DandelionSprout/adfilt/master/Dandelion%20Sprout's%20Anti-Malware%20List.txt",
                 UB + "badware.txt"]),
    ("phishing", ["https://malware-filter.gitlab.io/malware-filter/phishing-filter-agh.txt"]),
    ("ublock-filters", [UB + "filters.txt"]),
    ("adult", [ADULT + n + ".txt" for n in
               ("adult_adservers", "adult_thirdparty", "adult_specific_block", "adult_specific_hide")]),
    ("nocoin", ["https://raw.githubusercontent.com/hoshsadiq/adblock-nocoin-list/master/nocoin.txt"]),
]
CHUNK = 29000          # Chrome guarantees 30,000 enabled static rules per extension
SHARDS = 64
ENABLED_BY_DEFAULT = {"core", "easylist-1"}

TYPES = {"script": "script", "image": "image", "stylesheet": "stylesheet",
         "xmlhttprequest": "xmlhttprequest", "subdocument": "sub_frame", "object": "object",
         "font": "font", "media": "media", "ping": "ping", "websocket": "websocket",
         "other": "other", "document": "main_frame"}
IGNORED_OPTS = {"all"}
BAD_SELECTOR = re.compile(r":-abp-|:has-text|:xpath|:matches-|:contains|:upward|:nth-ancestor|:remove|:style|:watch-attr|:min-text|:others|:not\(:|\\|[{}]")
SIMPLE = re.compile(r"^([a-z0-9]*)([.#])([\w\-]+)$", re.I)


def fetch(src):
    if re.match(r"https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": "ChromeAdBlock-converter"})
        return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    return open(src, encoding="utf-8", errors="replace").read()


def fnv(s):
    h = 0x811C9DC5
    for b in s.encode():
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def split_domains(spec, sep):
    inc, exc = [], []
    for d in spec.split(sep):
        d = d.strip().lower()
        if not d or "*" in d or "/" in d or not d.isascii():
            continue
        (exc if d.startswith("~") else inc).append(d.lstrip("~"))
    return inc, exc


def url_filter(p):
    """ABP pattern -> Chrome urlFilter (same syntax). Returns '' for match-all, None if unsupported."""
    if p.startswith("/") and p.endswith("/") and len(p) > 2:
        return None
    if not p.isascii() or " " in p:
        return None
    body = p[2:] if p.startswith("||") else p[1:] if p.startswith("|") else p
    body = body[:-1] if body.endswith("|") else body
    if "|" in body:
        return None
    if p.startswith("||*") or p in ("*", "|", "||"):
        return None
    return p


def parse_network(line, exception):
    pattern, opts = line, ""
    m = re.match(r"^(.*)\$([a-z0-9_\-~=|,.*/]*)$", line, re.I)
    if m and not line.startswith("/"):
        pattern, opts = m.group(1), m.group(2)
    uf = url_filter(pattern)
    if uf is None:
        return None
    cond = {}
    if uf:
        cond["urlFilter"] = uf
    types, neg = [], []
    important = False
    for o in filter(None, opts.split(",")):
        n = o.lstrip("~").lower()
        negated = o.startswith("~")
        if n in ("third-party", "3p"):
            cond["domainType"] = "firstParty" if negated else "thirdParty"
        elif n in ("first-party", "1p"):
            cond["domainType"] = "thirdParty" if negated else "firstParty"
        elif n.startswith("domain="):
            inc, exc = split_domains(n[7:], "|")
            if not inc and not exc:
                return None
            if inc: cond["initiatorDomains"] = inc
            if exc: cond["excludedInitiatorDomains"] = exc
        elif n == "match-case":
            cond["isUrlFilterCaseSensitive"] = True
        elif n == "important":
            important = True
        elif n in IGNORED_OPTS:
            continue
        elif n == "popup":
            if not negated: types.append(None)  # marker: popup-only rules are unsupported
        elif n in TYPES:
            (neg if negated else types).append(TYPES[n])
        else:
            return None  # csp, redirect, removeparam, denyallow, header, ...
    if exception and any(o.lstrip("~").lower() in ("document", "elemhide", "generichide", "genericblock", "ghide")
                         for o in filter(None, opts.split(","))):
        return None
    if types:
        real = sorted({t for t in types if t})
        if not real:
            return None
        cond["resourceTypes"] = real
    elif neg:
        cond["excludedResourceTypes"] = sorted(set(neg))
    if not cond:
        return None
    return {"priority": 2 if exception else (3 if important else 1),
            "action": {"type": "allow" if exception else "block"}, "condition": cond}


def parse_lists(texts, net, generic, domain_css, stats):
    for text in texts:
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith(("!", "[")):
                continue
            if any(x in line for x in ("#?#", "#$#", "#@#", "#%#", "##+js", "#@$#")):
                stats["skipped"] += 1
                continue
            if "##" in line:
                doms, sel = line.split("##", 1)
                sel = sel.strip()
                if not sel or BAD_SELECTOR.search(sel) or not sel.isascii():
                    stats["skipped"] += 1
                    continue
                if not doms:
                    generic.add(sel)
                else:
                    inc, exc = split_domains(doms, ",")
                    if not inc:
                        stats["skipped"] += 1
                        continue
                    for d in inc:
                        domain_css[d].add(sel)
                continue
            if re.search(r"#[@?$%]*#", line):
                stats["skipped"] += 1
                continue
            exception = line.startswith("@@")
            rule = parse_network(line[2:] if exception else line, exception)
            if rule is None:
                stats["skipped"] += 1
                continue
            net.append(rule)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extension-dir", default=os.path.join(os.path.dirname(__file__), "..", "extension"))
    a = ap.parse_args()
    ext = os.path.abspath(a.extension_dir)
    stats = defaultdict(int)
    for d in ("rulesets", "cosmetic"):
        shutil.rmtree(os.path.join(ext, d), ignore_errors=True)

    generic, domain_css = set(), defaultdict(set)
    seen, rulesets = set(), []

    core = json.load(open(os.path.join(ext, "core-rules.json")))
    write_json(os.path.join(ext, "rulesets", "core.json"), core)
    rulesets.append({"id": "core", "group": "core", "count": len(core)})

    for gid, urls in GROUPS:
        net = []
        parse_lists([fetch(u) for u in urls], net, generic, domain_css, stats)
        uniq = []
        for r in net:
            k = json.dumps(r, sort_keys=True)
            if k not in seen:
                seen.add(k)
                uniq.append(r)
        for i in range(0, len(uniq), CHUNK):
            chunk = uniq[i:i + CHUNK]
            rid = f"{gid}-{i // CHUNK + 1}"
            rules = [dict(id=n + 1, **r) for n, r in enumerate(chunk)]
            write_json(os.path.join(ext, "rulesets", rid + ".json"), rules)
            rulesets.append({"id": rid, "group": gid, "count": len(rules)})
        print(f"{gid}: {len(uniq)} network rules")

    # ---- generic element hiding ----
    idx = {"c": defaultdict(list), "i": defaultdict(list)}
    complex_sel = []
    for s in sorted(generic):
        m = SIMPLE.match(s)
        if m:
            tag, kind, tok = m.groups()
            idx["c" if kind == "." else "i"][tok.lower()].append(s)
        else:
            complex_sel.append(s)
    compact = {}
    for kind in ("c", "i"):
        sym = "." if kind == "c" else "#"
        out = {}
        for tok, sels in idx[kind].items():
            out[tok] = 1 if sels == [sym + tok] else sels
        compact[kind] = out
    write_json(os.path.join(ext, "generic-index.json"), compact)
    with open(os.path.join(ext, "generic.css"), "w") as f:
        f.write("\n".join(s + "{display:none!important}" for s in complex_sel) + "\n")

    # ---- per-site element hiding, sharded ----
    shards = defaultdict(dict)
    for d, sels in domain_css.items():
        shards[fnv(d) % SHARDS][d] = sorted(sels)
    for n, data in shards.items():
        write_json(os.path.join(ext, "cosmetic", f"{n:02d}.json"), data)

    write_json(os.path.join(ext, "meta.json"), {
        "rulesets": rulesets, "shards": SHARDS,
        "generic": {"classes": len(compact["c"]), "ids": len(compact["i"]), "complex": len(complex_sel)},
        "domains": len(domain_css)})

    # ---- manifest ----
    mp = os.path.join(ext, "manifest.json")
    m = json.load(open(mp))
    m["declarative_net_request"] = {"rule_resources": [
        {"id": r["id"], "enabled": r["id"] in ENABLED_BY_DEFAULT, "path": f"rulesets/{r['id']}.json"}
        for r in rulesets]}
    json.dump(m, open(mp, "w"), indent=2)

    total = sum(r["count"] for r in rulesets)
    print(f"rulesets: {len(rulesets)}  network rules: {total}  generic class/id: "
          f"{len(compact['c'])}+{len(compact['i'])}  generic css: {len(complex_sel)}  "
          f"sites: {len(domain_css)}  skipped(unsupported): {stats['skipped']}")


if __name__ == "__main__":
    main()
