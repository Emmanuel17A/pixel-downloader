const API = "http://127.0.0.1:6969";

const dot = document.getElementById("dot");
const statusText = document.getElementById("status-text");
const downloadBtn = document.getElementById("download-btn");
const urlInput = document.getElementById("url-input");
const filenameInput = document.getElementById("filename-input");
const toast = document.getElementById("toast");
const activeCount = document.getElementById("active-count");
const queuedCount = document.getElementById("queued-count");

function showToast(msg, type) {
  toast.textContent = msg;
  toast.className = `toast ${type}`;
  setTimeout(() => { toast.className = "toast"; }, 3000);
}

async function checkConnection() {
  try {
    const r = await fetch(`${API}/ping`);
    const d = await r.json();
    dot.className = "dot online";
    statusText.textContent = "Connected to Pixel Downloader";
    downloadBtn.disabled = false;
    loadStats();
  } catch {
    dot.className = "dot offline";
    statusText.textContent = "App not running — open Pixel Downloader";
    downloadBtn.disabled = true;
  }
}

async function loadStats() {
  try {
    const r = await fetch(`${API}/status`);
    const d = await r.json();
    activeCount.textContent = d.active?.length ?? 0;
    queuedCount.textContent = d.queued ?? 0;
  } catch {}
}

downloadBtn.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  const filename = filenameInput.value.trim() || url.split("/").pop().split("?")[0];
  if (!url) { showToast("Please enter a URL", "error"); return; }

  try {
    const r = await fetch(`${API}/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, filename })
    });
    const d = await r.json();
    showToast(`Queued: ${filename}`, "success");
    urlInput.value = "";
    filenameInput.value = "";
    loadStats();
  } catch {
    showToast("Failed to connect to app", "error");
  }
});

document.getElementById("tab-btn").addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) urlInput.value = tabs[0].url;
  });
});

checkConnection();
setInterval(loadStats, 3000);
