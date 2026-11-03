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
  if (isVideoSite(url)) return null; // let yt-dlp name it
  try {
    const path = new URL(url).pathname;
    const name = path.split("/").pop().split("?")[0];
    return name || "download";
  } catch { return "download"; }
}

// Intercept browser downloads
chrome.downloads.onCreated.addListener(async (downloadItem) => {
  const url = downloadItem.url;
  if (url.startsWith("blob:") || url.startsWith("data:") || url.startsWith("chrome")) return;

  chrome.downloads.cancel(downloadItem.id, async () => {
    try {
      const filename = getFilename(url);
      const body = { url };
      if (filename) body.filename = filename;

      const response = await fetch(`${API_URL}/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      const data = await response.json();
      console.log("[Pixel Downloader] Queued:", data);

      chrome.notifications?.create({
        type: "basic",
        iconUrl: "icons/icon48.png",
        title: "Pixel Downloader",
        message: `Download queued: ${filename || url}`
      });

    } catch (e) {
      console.error("[Pixel Downloader] Failed:", e);
    }
  });
});

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
  const body = { url };
  if (filename) body.filename = filename;

  try {
    await fetch(`${API_URL}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
  } catch (e) {
    console.error("[Pixel Downloader] Context menu error:", e);
  }
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
    const body = { url: msg.url };
    if (msg.filename) body.filename = msg.filename;
    fetch(`${API_URL}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
      .then(r => r.json())
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
