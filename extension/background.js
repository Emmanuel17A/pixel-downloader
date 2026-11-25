const API_URL = "http://127.0.0.1:6969";

const VIDEO_DOMAINS = [
  "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
  "tiktok.com", "instagram.com", "twitter.com", "x.com",
  "facebook.com", "twitch.tv", "bilibili.com"
];

function isVideoSite(url) {
  try {
    const host = new URL(url).hostname.replace("www.", "");
    return VIDEO_DOMAINS.some(d => host.includes(d));
  } catch { return false; }
}

function getFilename(url) {
  if (isVideoSite(url)) return null;
  try {
    const path = new URL(url).pathname;
    const name = path.split("/").pop().split("?")[0];
    return name || "download";
  } catch { return "download"; }
}

async function sendToPixel(url, filename) {
  const body = { url };
  if (filename) body.filename = filename;
  try {
    const response = await fetch(`${API_URL}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    return await response.json();
  } catch (e) {
    console.error("[Pixel Downloader] Failed:", e);
  }
}

// ── REMOVED auto-intercept ──────────────────────────────────────
// We no longer intercept chrome.downloads.onCreated automatically
// User must explicitly use right-click or popup to send to Pixel
// This lets normal browser downloads work as usual
// ───────────────────────────────────────────────────────────────

// Context menus
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "pixel-download-link",
    title: "Download with Pixel Downloader",
    contexts: ["link"]
  });
  chrome.contextMenus.create({
    id: "pixel-download-video",
    title: "Download Video with Pixel Downloader",
    contexts: ["video", "audio"]
  });
  chrome.contextMenus.create({
    id: "pixel-download-page",
    title: "Download Page with Pixel Downloader",
    contexts: ["page"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  let url = null;
  if (info.menuItemId === "pixel-download-link")  url = info.linkUrl;
  if (info.menuItemId === "pixel-download-video") url = info.srcUrl;
  if (info.menuItemId === "pixel-download-page")  url = info.pageUrl;
  if (!url) return;

  const filename = getFilename(url);
  await sendToPixel(url, filename);

  chrome.notifications?.create({
    type: "basic",
    iconUrl: "icons/icon48.png",
    title: "Pixel Downloader",
    message: `Queued: ${filename || url}`
  });
});

// Popup messages
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "ping") {
    fetch(`${API_URL}/ping`)
      .then(r => r.json())
      .then(data => sendResponse({ ok: true, data }))
      .catch(() => sendResponse({ ok: false }));
    return true;
  }
  if (msg.action === "add") {
    sendToPixel(msg.url, msg.filename)
      .then(data => sendResponse({ ok: true, data }))
      .catch(e => sendResponse({ ok: false, error: e.message }));
    return true;
  }
  if (msg.action === "status") {
    fetch(`${API_URL}/status`)
      .then(r => r.json())
      .then(data => sendResponse({ ok: true, data }))
      .catch(() => sendResponse({ ok: false }));
    return true;
  }
});
