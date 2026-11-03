const API_URL = "http://127.0.0.1:6969";

// Intercept downloads and redirect to Pixel Downloader
chrome.downloads.onCreated.addListener(async (downloadItem) => {
  const url = downloadItem.url;

  // Skip blob, data, chrome URLs
  if (url.startsWith("blob:") || url.startsWith("data:") || url.startsWith("chrome")) {
    return;
  }

  // Cancel the browser download
  chrome.downloads.cancel(downloadItem.id, async () => {
    // Send to Pixel Downloader
    try {
      const filename = downloadItem.filename
        ? downloadItem.filename.split("/").pop()
        : url.split("/").pop().split("?")[0] || "download";

      const response = await fetch(`${API_URL}/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, filename })
      });

      const data = await response.json();
      console.log("[Pixel Downloader] Queued:", data);

      // Show notification
      chrome.notifications?.create({
        type: "basic",
        iconUrl: "icons/icon48.png",
        title: "Pixel Downloader",
        message: `Download queued: ${filename}`
      });

    } catch (e) {
      console.error("[Pixel Downloader] Failed to send to app:", e);
    }
  });
});

// Right-click context menu — Download with Pixel Downloader
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
    title: "Download Page URL with Pixel Downloader",
    contexts: ["page"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  let url = null;

  if (info.menuItemId === "pixel-download-link") {
    url = info.linkUrl;
  } else if (info.menuItemId === "pixel-download-video") {
    url = info.srcUrl;
  } else if (info.menuItemId === "pixel-download-page") {
    url = info.pageUrl;
  }

  if (!url) return;

  try {
    const filename = url.split("/").pop().split("?")[0] || "download";
    const response = await fetch(`${API_URL}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, filename })
    });
    const data = await response.json();
    console.log("[Pixel Downloader] Context menu queued:", data);
  } catch (e) {
    console.error("[Pixel Downloader] Context menu error:", e);
  }
});

// Listen for messages from popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "ping") {
    fetch(`${API_URL}/ping`)
      .then(r => r.json())
      .then(data => sendResponse({ ok: true, data }))
      .catch(() => sendResponse({ ok: false }));
    return true;
  }

  if (msg.action === "add") {
    fetch(`${API_URL}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: msg.url, filename: msg.filename })
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
