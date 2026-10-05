# Installing ChromeAdBlock

Takes about two minutes. Works in Chrome 120 or later, and in Edge, Brave and other Chromium browsers.

## Option 1: download the ready-to-load zip (recommended)

1. Go to the [latest release](https://github.com/biswadipb/ChromeAdBlock/releases/latest) and download **ChromeAdBlock.zip**.
2. Unzip it. Keep the unzipped folder somewhere permanent, such as `~/ChromeAdBlock`. Chrome loads the extension from that folder, so do not delete or move it afterwards.
3. In Chrome, open `chrome://extensions`.
4. Turn on **Developer mode** (the toggle at the top right).
5. Click **Load unpacked**, then select the unzipped folder (the one that contains `manifest.json`).
6. The extension appears with a blue shield icon. Pin it from the puzzle-piece menu if you want it visible.

## Option 2: build from source

Needs Python 3.

```bash
git clone https://github.com/biswadipb/ChromeAdBlock.git ~/ChromeAdBlock
```

```bash
cd ~/ChromeAdBlock && python3 tools/convert_chrome.py
```

Then follow steps 3 to 5 above, choosing the `extension` folder inside the repo.

## Check that it works

1. Open `chrome://extensions` and make sure **Chrome Ad Blocker** is on and shows no **Errors** button.
2. Open a news site and a YouTube video.
3. To check how many rule lists are active, click **service worker** on the extension's card, then in the console that opens run:
   ```js
   chrome.declarativeNetRequest.getEnabledRulesets()
   ```
   You should see about eight entries, such as `core`, `easylist-1`, `easylist-2`, `easyprivacy-1`, and so on.

## Updating

The filter lists change daily. To update:

1. Download the newest **ChromeAdBlock.zip** from the release, and unzip it over the old folder (replace the files).
2. In `chrome://extensions`, click the circular reload icon on the extension's card.

If you built from source, run `python3 tools/convert_chrome.py` again and click the reload icon.

## Troubleshooting

### "Disable developer mode extensions" appears every time Chrome starts

This is Chrome's standard warning for unpacked extensions. Click the **X** to dismiss it. It cannot be turned off for unpacked extensions. Installing from the Chrome Web Store would remove it.

### "Manifest file is missing or unreadable" or "Could not load ... generic.css"

You loaded the repo's `extension` folder without generating its data files. Run `python3 tools/convert_chrome.py` first, or use the zip from the release (Option 1), which already has them.

### The extension shows an Errors button

Click **Errors** and read the message. Rule-parsing problems appear here. Open an issue with the message.

### Fewer rule lists are enabled than expected

Chrome shares a pool of 330,000 static rules among all your extensions, and this extension needs about 126,000. If other extensions use much of the pool, the lower-priority lists (adult, trackers) are skipped. Disable another ad blocker you no longer need, then reload this extension.

### YouTube shows a dark screen and a spinner for as long as an ad would last

Something is blocking YouTube's own ad requests, so the player waits out the ad before playing. This project avoids that with an allow rule for YouTube's first-party requests (in `extension/core-rules.json`). If you added your own rules, make sure none block `youtube.com/api/stats/ads`, `/pagead`, `/ptracking` or `/get_midroll_`.

### A website is broken

Open `chrome://extensions`, click **Details** on the extension, and set **Site access** to **On click** or **On specific sites** to exclude that site. Then open an issue with the site's name.

### Make it work in Incognito

Open **Details** on the extension and turn on **Allow in Incognito**.
