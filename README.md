# ChromeAdBlock

A Chrome (Manifest V3) extension that blocks ads, trackers, malware domains, popups and redirects on every site, with extra YouTube ad skipping. It is the Chrome version of [SafariAdBlock](https://github.com/biswadipb/SafariAdBlock) and uses the same filter lists.

## Features

- **Filter lists:** EasyList and AdGuard Base (ads); EasyPrivacy and uBlock privacy (trackers); Fanboy's Annoyance List, AdGuard Annoyances and the EasyList Cookie List (popups, social widgets, cookie banners); URLhaus, Dandelion Sprout's Anti-Malware List, uBlock badware and the malware-filter phishing list (malware, scam and phishing hosts); uBlock filters; EasyList Adult; NoCoin (crypto miners). About 193,000 network rules, plus element hiding for about 67,000 sites and thousands of generic ad selectors.
- **Popup and redirect protection:** blocks popups and popunders without a click, off-site auto-redirects and invisible click-hijacking overlays.
- **YouTube:** strips ad data from the player before YouTube's own code reads it, and skips any ad that still plays. YouTube's own requests are deliberately not blocked (see Troubleshooting).
- **Rebuilt daily:** a GitHub Action converts the latest lists and publishes a ready-to-load zip.

## Install

See [INSTALL.md](INSTALL.md) for the full guide. Short version:

1. Download **ChromeAdBlock.zip** from the [latest release](../../releases/latest) and unzip it.
2. Open `chrome://extensions` and turn on **Developer mode** (top right).
3. Click **Load unpacked** and choose the unzipped folder.

Requires Chrome 120 or later (also works in Edge, Brave and other Chromium browsers).

## Build from source

Needs Python 3 only.

```bash
git clone https://github.com/biswadipb/ChromeAdBlock.git
cd ChromeAdBlock
python3 tools/convert_chrome.py
```

This downloads the filter lists and generates `extension/rulesets/`, `extension/cosmetic/`, `extension/generic-index.json`, `extension/generic.css` and `extension/meta.json`. Then load the `extension/` folder as above. The generated files are not stored in git.

## Updating

Download the newest zip from the release, unzip over the old folder (or into a new one), and click the reload icon on the extension's card in `chrome://extensions`. Or rebuild from source as above.

## How it works

| Piece | File | What it does |
|---|---|---|
| Network blocking | `extension/rulesets/*.json` | `declarativeNetRequest` static rulesets. Chrome guarantees 30,000 enabled rules per extension and shares a larger pool (330,000) across all extensions. Only the first EasyList ruleset is enabled by manifest; `background.js` enables the rest, in priority order, as far as the pool allows. |
| Per-site hiding | `extension/cosmetic/*.json` | Selectors for specific sites, sharded by domain hash. The service worker injects the CSS for a site when you navigate to it. |
| Generic hiding | `extension/generic-index.json`, `cosmetic.js` | The page reports its class and id names; only the ones the lists flag are hidden. This avoids loading 40,000 selectors on every page. |
| Popups and redirects | `extension/popup-guard.js` | Runs in the page's own context before any page script. |
| YouTube | `youtube-inject.js`, `youtube.js`, `youtube.css`, `core-rules.json` | Strips ad data, skips ads, and exempts YouTube's first-party requests from blocking. |

## Troubleshooting

See also [INSTALL.md](INSTALL.md).

- **Chrome says "Disable developer mode extensions" at startup:** this is Chrome's standard warning for unpacked extensions. Click the X to dismiss it. Publishing to the Chrome Web Store removes it.
- **Fewer rules than expected:** other extensions share Chrome's static-rule pool. If it runs low, the lower-priority rulesets (the last ones in `tools/convert_chrome.py`'s `GROUPS` order, such as adult and nocoin) are left off. Check the extension's service worker console and run `chrome.declarativeNetRequest.getEnabledRulesets()`.
- **YouTube shows a dark screen and spinner for as long as an ad would last:** something is blocking YouTube's own ad requests, so the player waits out the ad. Don't add rules that block `youtube.com/api/stats/ads`, `/pagead`, `/ptracking` or `/get_midroll_`. `core-rules.json` has an allow rule for YouTube's first-party requests.
- **A site is broken:** click the extension's card in `chrome://extensions`, open **Details** and set **Site access** to **On click** or **On specific sites**, or open an issue with the site's name.

## Limitations

Chrome's API cannot run EasyList's advanced rules (scriptlets, `:has-text()` selectors, redirects and similar), so about 44,000 lines (mostly AdGuard script and extended-selector rules) are skipped. Popups opened with `window.open` are blocked by a script, not a network rule, so a page that opens a popup in a way the script does not intercept can still succeed. Coverage is close to, but not the same as, uBlock Origin. Some ads are inserted into video streams by the server and cannot be removed this way.
