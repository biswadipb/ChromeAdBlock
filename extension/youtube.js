// Fallback: if an ad still plays, skip it.
const SKIP = ".ytp-skip-ad-button, .ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-ad-skip-button-slot button";

function tick() {
  const player = document.querySelector(".html5-video-player");
  const video = document.querySelector("video.html5-main-video, #movie_player video");
  if (!player || !video) return;

  if (player.classList.contains("ad-showing")) {
    video.muted = true;
    video.playbackRate = 16;
    if (isFinite(video.duration) && video.duration > 0) video.currentTime = video.duration;
    document.querySelector(SKIP)?.click();
  }
  document.querySelector(".ytp-ad-overlay-close-button")?.click();
}

setInterval(tick, 300);
new MutationObserver(tick).observe(document, { childList: true, subtree: true });
