/**
 * AI-FACE Clinical Platform - Institutional Diagnostic Workstation ES6 Application
 * Precision healthcare UI following Apple Human Interface Guidelines (HIG).
 */

// Global Application State
let clinicalInfo = null;
let currentSelectedFile = null;
let batchFiles = [];
let batchResults = [];
let liveStream = null;
let liveInterval = null;
let liveShowEmotions = false;
let liveStartTime = null;
let isAnalyzingFrame = false;
let overlayMode = "clean"; // "clean" (CSS Reticle) or "classic" (OpenCV SHORE Burn-in)
let isCameraMirrored = true; // Natural selfie/mirror orientation

// Initialize on Load
document.addEventListener("DOMContentLoaded", async () => {
  await loadClinicalInfo();
  setupDropZone();
});

function setupDropZone() {
  const dropZone = document.getElementById("drop-zone");
  if (!dropZone) return;

  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add("drag-over");
    }, false);
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove("drag-over");
    }, false);
  });

  dropZone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files.length > 0) {
      setPhotoFile(files[0]);
    }
  });
}

// Navigation Tab Switcher
function switchTab(tabName) {
  document.querySelectorAll(".tab-pane").forEach(el => {
    el.style.display = "none";
  });
  document.querySelectorAll(".seg-btn").forEach(el => {
    el.classList.remove("active");
    el.setAttribute("aria-current", "false");
  });

  const activeContent = document.getElementById(`tab-content-${tabName}`);
  const activeBtn = document.getElementById(`tab-btn-${tabName}`);
  if (activeContent) activeContent.style.display = "block";
  if (activeBtn) {
    activeBtn.classList.add("active");
    activeBtn.setAttribute("aria-current", "page");
  }

  // Safe resource cleanup when navigating away from Live Camera
  if (tabName !== "live" && liveStream) {
    stopCamera();
  }
}

// Load Metadata Dictionary
async function loadClinicalInfo() {
  try {
    const res = await fetch("/api/v1/clinical/info");
    if (res.ok) {
      clinicalInfo = await res.json();
    }
  } catch (err) {
    console.error("Failed to load clinical info metadata:", err);
  }
}

// Helper: FACS Action Unit Discrete Intensity Level
function getAUIntensityLetter(score) {
  if (score >= 0.85) return "E";
  if (score >= 0.70) return "D";
  if (score >= 0.50) return "C";
  if (score >= 0.30) return "B";
  if (score >= 0.10) return "A";
  return "0";
}

// 5-Zone Metric Mathematics (Gavrilescu 2019)
const ZONES = [0, 15, 30, 60, 80, 100];
const ZONE_WORDS = ['Normal', 'Mild', 'Moderate', 'Severe', 'Extreme'];
const ZONE_FILLS = ['#34C759', '#FF9F0A', '#FF6A1A', '#FF3B30', '#C4001A'];
const ZONE_TEXTS = ['#1F7A3A', '#9A5B00', '#B14100', '#C4251C', '#A50015'];

function zoneOf(v) {
  let i = 0;
  while (i < 4 && v >= ZONES[i + 1]) i++;
  return i;
}

function place(v) {
  const x = Math.max(0, Math.min(100, v));
  const i = zoneOf(x);
  return (i * 20 + ((x - ZONES[i]) / (ZONES[i + 1] - ZONES[i])) * 20).toFixed(1) + '%';
}

function updateDassItem(scoreEl, levelEl, barEl, rawScore) {
  const pct = Math.round((rawScore || 0) * 100);
  const z = zoneOf(pct);
  if (scoreEl) scoreEl.textContent = `${pct}%`;
  if (levelEl) {
    levelEl.textContent = ZONE_WORDS[z];
    levelEl.style.color = ZONE_TEXTS[z];
  }
  if (barEl) {
    barEl.style.width = place(pct);
    barEl.style.minWidth = pct > 0 ? '8px' : '0px';
    barEl.style.background = ZONE_FILLS[z];
  }
}

// =========================================================================
// TAB 1: LIVE WEBCAM MONITORING & TOAST SYSTEM
// =========================================================================

// Precision Apple SF-Symbols style monochrome vector icons (No AI slop emojis)
const SVG_ICONS = {
  camera: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>`,
  stop: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FF453A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><rect x="9" y="9" width="6" height="6"></rect></svg>`,
  mirror: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>`,
  overlay: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>`,
  radar: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path><path d="M2 12h20"></path></svg>`,
  check: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#34C759" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
  file: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>`,
  download: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>`,
  info: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`,
};

function showToast(message, iconKey = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = "toast-pill";
  const iconSvg = SVG_ICONS[iconKey] || SVG_ICONS.info;
  toast.innerHTML = `<span class="toast-icon-wrap">${iconSvg}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add("out");
    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, 250);
  }, 2200);
}

function toggleCameraMirror() {
  isCameraMirrored = !isCameraMirrored;
  const video = document.getElementById("webcam-video");
  const label = document.getElementById("live-mirror-label");
  const toggleBtn = document.getElementById("live-mirror-toggle");
  const track = toggleBtn ? toggleBtn.querySelector(".switch-track") : null;

  if (isCameraMirrored) {
    if (video) video.classList.add("camera-mirror");
    if (label) label.textContent = "Balik tampilan seperti cermin";
    if (track) track.className = "switch-track on";
    if (toggleBtn) toggleBtn.setAttribute("aria-checked", "true");
  } else {
    if (video) video.classList.remove("camera-mirror");
    if (label) label.textContent = "Orientasi sensor asli (OFF)";
    if (track) track.className = "switch-track";
    if (toggleBtn) toggleBtn.setAttribute("aria-checked", "false");
  }
  showToast(`Mode Cermin: ${isCameraMirrored ? 'Aktif' : 'Nonaktif'} (M)`, "mirror");
}

function toggleOverlayDisplayMode() {
  overlayMode = (overlayMode === "clean") ? "classic" : "clean";
  const label = document.getElementById("live-overlay-mode-label");
  const overlay = document.getElementById("live-annotated-overlay");
  const faceBox = document.getElementById("live-face-box");
  const pillLeft = document.getElementById("live-hud-pill-left");
  const pillRight = document.getElementById("live-hud-pill-right");
  const toggleBtn = document.getElementById("live-overlay-toggle");
  const track = toggleBtn ? toggleBtn.querySelector(".switch-track") : null;

  if (overlayMode === "clean") {
    if (label) label.textContent = "Tampilkan overlay deteksi lama (OFF)";
    if (track) track.className = "switch-track";
    if (toggleBtn) toggleBtn.setAttribute("aria-checked", "false");
    if (overlay) overlay.style.display = "none";
    if (pillLeft) pillLeft.style.display = "flex";
    if (pillRight) pillRight.style.display = "flex";
  } else {
    if (label) label.textContent = "Overlay deteksi lama (ON)";
    if (track) track.className = "switch-track on";
    if (toggleBtn) toggleBtn.setAttribute("aria-checked", "true");
    if (faceBox) faceBox.style.display = "none";
    if (pillLeft) pillLeft.style.display = "none";
    if (pillRight) pillRight.style.display = "none";
  }
  showToast(`Overlay: ${overlayMode === 'clean' ? 'Retikel Bersih' : 'Klasik SHORE'} (C)`, "overlay");
}

function toggleLiveEmotions() {
  liveShowEmotions = !liveShowEmotions;
  const toggleBtn = document.getElementById("live-emotion-toggle");
  const track = toggleBtn ? toggleBtn.querySelector(".switch-track") : null;

  if (liveShowEmotions) {
    if (track) track.className = "switch-track on";
    if (toggleBtn) toggleBtn.setAttribute("aria-checked", "true");
  } else {
    if (track) track.className = "switch-track";
    if (toggleBtn) toggleBtn.setAttribute("aria-checked", "false");
  }
}

function handleVideoBoxClick(event) {
  // Prevent click bubbling from control buttons inside video container
  if (event.target.closest("button") || event.target.closest("a")) return;
  toggleLiveEmotions();
  showToast(`Mode Emosi: ${liveShowEmotions ? 'Aktif' : 'Nonaktif'} (E)`, "radar");
}

// Global hotkeys for precision navigation
window.addEventListener("keydown", (e) => {
  if (document.activeElement && ["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
    if (e.key === "Escape") document.activeElement.blur();
    return;
  }

  if (e.key === "Escape") {
    closeLightbox();
    closeAUInspector();
    return;
  }

  if (e.key === "e" || e.key === "E") {
    toggleLiveEmotions();
    showToast(`Mode Emosi: ${liveShowEmotions ? 'Aktif' : 'Nonaktif'} (E)`, "radar");
  } else if (e.key === "m" || e.key === "M") {
    toggleCameraMirror();
  } else if (e.key === "c" || e.key === "C") {
    toggleOverlayDisplayMode();
  } else if (e.key === " " || e.code === "Space") {
    e.preventDefault();
    if (liveStream) {
      stopCamera();
    } else {
      startCamera();
    }
  } else if (e.key === "1") {
    switchTab("live");
  } else if (e.key === "2") {
    switchTab("photo");
  } else if (e.key === "3") {
    switchTab("batch");
  } else if (e.key === "4") {
    switchTab("glossary");
  }
});

async function startCamera() {
  const video = document.getElementById("webcam-video");
  const placeholder = document.getElementById("camera-placeholder");
  const btnStart = document.getElementById("btn-start-camera");
  const btnStop = document.getElementById("btn-stop-camera");
  const statusDot = document.getElementById("live-status-dot");
  const statusText = document.getElementById("live-status-text");
  const targetStatus = document.getElementById("live-target-status");
  const stripStatus = document.getElementById("control-strip-status");

  try {
    // Request native high-definition stream without forcing restrictive 4:3 crop
    liveStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280, max: 1920 },
        height: { ideal: 720, max: 1080 },
        facingMode: "user"
      },
      audio: false
    });
    video.srcObject = liveStream;
    await video.play();

    // Dynamically conform the viewport to the exact aspect ratio of the camera
    const updateViewportRatio = () => {
      if (video.videoWidth && video.videoHeight) {
        const box = document.getElementById("live-video-box");
        if (box) {
          box.style.aspectRatio = `${video.videoWidth} / ${video.videoHeight}`;
        }
      }
    };
    video.onloadedmetadata = updateViewportRatio;
    updateViewportRatio();

    if (placeholder) placeholder.style.display = "none";
    if (btnStart) btnStart.style.display = "none";
    if (btnStop) btnStop.style.display = "flex";

    if (statusDot) {
      statusDot.className = "hud-dot active";
    }
    if (statusText) {
      statusText.textContent = "LIVE FEED";
    }
    if (targetStatus) {
      targetStatus.textContent = "| AKTIF";
    }
    if (stripStatus) {
      stripStatus.textContent = "Sensor Aktif (15 Hz)";
    }

    liveStartTime = Date.now();
    const subjId = "SUBJ-" + Math.random().toString(36).substring(2, 6).toUpperCase();
    const subjIdEl = document.getElementById("live-subject-id");
    if (subjIdEl) subjIdEl.textContent = subjId;

    isAnalyzingFrame = false;

    // Stream telemetry frames at ~10-15 Hz (100ms cycle)
    liveInterval = setInterval(captureAndSendLiveFrame, 100);
    showToast("Kamera aktif · 15 Hz stream", "camera");
  } catch (err) {
    alert("Tidak dapat mengakses sensor kamera: " + err.message);
  }
}

function stopCamera() {
  if (liveInterval) clearInterval(liveInterval);
  if (liveStream) {
    liveStream.getTracks().forEach(track => track.stop());
    liveStream = null;
  }

  showToast("Kamera dinonaktifkan", "stop");

  const video = document.getElementById("webcam-video");
  if (video) video.srcObject = null;

  const box = document.getElementById("live-video-box");
  if (box) box.style.aspectRatio = "16 / 9";

  const placeholder = document.getElementById("camera-placeholder");
  if (placeholder) placeholder.style.display = "flex";

  const overlay = document.getElementById("live-annotated-overlay");
  if (overlay) {
    overlay.src = "";
    overlay.style.display = "none";
  }

  const faceBox = document.getElementById("live-face-box");
  if (faceBox) faceBox.style.display = "none";

  const statusDot = document.getElementById("live-status-dot");
  if (statusDot) statusDot.className = "hud-dot";

  const statusText = document.getElementById("live-status-text");
  if (statusText) statusText.textContent = "Standby";

  const targetStatus = document.getElementById("live-target-status");
  if (targetStatus) targetStatus.textContent = "| TERHENTI";

  const stripStatus = document.getElementById("control-strip-status");
  if (stripStatus) stripStatus.textContent = "Siap Memulai";

  isAnalyzingFrame = false;

  const btnStart = document.getElementById("btn-start-camera");
  const btnStop = document.getElementById("btn-stop-camera");
  if (btnStart) btnStart.style.display = "flex";
  if (btnStop) btnStop.style.display = "none";
}

async function captureAndSendLiveFrame() {
  if (isAnalyzingFrame) return; // Prevent network backlog piling

  const video = document.getElementById("webcam-video");
  const canvas = document.getElementById("capture-canvas");
  if (!video || video.readyState < 2 || !video.videoWidth) return;

  isAnalyzingFrame = true;
  const startTime = Date.now();

  // Scale frame to diagnostic payload size while strictly preserving native aspect ratio
  const vw = video.videoWidth || 640;
  const vh = video.videoHeight || 480;
  const targetW = Math.min(vw, 640);
  const targetH = Math.round(targetW / (vw / vh));
  canvas.width = targetW;
  canvas.height = targetH;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, targetW, targetH);

  canvas.toBlob(async (blob) => {
    if (!blob) {
      isAnalyzingFrame = false;
      return;
    }
    const formData = new FormData();
    formData.append("file", blob, "live_frame.jpg");
    formData.append("show_emotions", liveShowEmotions ? "true" : "false");
    const subjId = document.getElementById("live-subject-id")?.textContent || "Subject";
    formData.append("subject_id", subjId);
    formData.append("mirror", isCameraMirrored ? "true" : "false");

    const uptimeSec = liveStartTime ? ((Date.now() - liveStartTime) / 1000).toFixed(1) : "0.0";
    formData.append("uptime", uptimeSec);

    try {
      const res = await fetch("/api/v1/analyze/frame", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        const latency = Date.now() - startTime;
        updateLiveDashboard(data, latency);
      }
    } catch (err) {
      // Frame drop silently handled
    } finally {
      isAnalyzingFrame = false;
    }
  }, "image/jpeg", 0.70);
}

function updateLiveDashboard(data, latencyMs = 0) {
  // 1. Update Viewfinder Reticle / Overlay
  const faceBox = document.getElementById("live-face-box");
  const targetStatus = document.getElementById("live-target-status");
  const overlay = document.getElementById("live-annotated-overlay");

  if (overlayMode === "clean") {
    if (overlay) overlay.style.display = "none";

    if (data.face_bbox && faceBox) {
      // Render smooth CSS face tracking bounding box (accounting for mirror mode)
      const bb = data.face_bbox;
      const bbLeft = isCameraMirrored
        ? Math.max(0, (1.0 - (bb.x + bb.width)) * 100)
        : Math.max(0, bb.x * 100);
      faceBox.style.left = `${bbLeft}%`;
      faceBox.style.top = `${Math.max(0, bb.y * 100)}%`;
      faceBox.style.width = `${Math.min(100, bb.width * 100)}%`;
      faceBox.style.height = `${Math.min(100, bb.height * 100)}%`;
      faceBox.style.display = "block";
      if (targetStatus) targetStatus.textContent = "| TRACKING";
    } else {
      if (faceBox) faceBox.style.display = "none";
      if (targetStatus) targetStatus.textContent = "| MENCARI WAJAH";
    }
  } else {
    // Classic SHORE burn-in overlay mode
    if (faceBox) faceBox.style.display = "none";
    if (data.annotated_image_base64 && overlay) {
      overlay.src = data.annotated_image_base64;
      overlay.style.display = "block";
    }
    if (targetStatus) {
      targetStatus.textContent = data.face_detected ? "| TERDETEKSI" : "| MENCARI WAJAH";
    }
  }

  // 2. Latency & Telemetry
  const latencyEl = document.getElementById("live-latency-indicator");
  if (latencyEl && latencyMs > 0) {
    latencyEl.textContent = `${latencyMs} ms`;
  }
  const fpsEl = document.getElementById("live-fps-indicator");
  if (fpsEl) {
    fpsEl.textContent = "15 Hz";
  }

  if (liveStartTime) {
    const elapsed = ((Date.now() - liveStartTime) / 1000).toFixed(1);
    const uptimeEl = document.getElementById("live-uptime");
    if (uptimeEl) uptimeEl.textContent = `${elapsed} s`;
  }

  // 3. Distress Level Assessment
  const distBadge = document.getElementById("live-distress-badge");
  if (distBadge) {
    const distLvl = data.distress_level || "Low";
    distBadge.textContent = distLvl;
    const l = distLvl.toLowerCase();
    if (l.includes("extreme") || l.includes("high") || l.includes("severe")) {
      distBadge.style.color = "#C4251C";
    } else if (l.includes("mod") || l.includes("mild")) {
      distBadge.style.color = "#9A5B00";
    } else {
      distBadge.style.color = "#1F7A3A";
    }
  }

  // 4. Tri-Axial DASS-3 Clinical Scales (Apple 5-Zone Track)
  if (data.dass_clinical_assessment) {
    const dass = data.dass_clinical_assessment;
    updateDassItem(
      document.getElementById("live-dep-score"),
      document.getElementById("live-dep-level"),
      document.getElementById("live-dep-bar"),
      dass.depression?.score
    );
    updateDassItem(
      document.getElementById("live-anx-score"),
      document.getElementById("live-anx-level"),
      document.getElementById("live-anx-bar"),
      dass.anxiety?.score
    );
    updateDassItem(
      document.getElementById("live-str-score"),
      document.getElementById("live-str-level"),
      document.getElementById("live-str-bar"),
      dass.stress?.score
    );
  }

  // 5. Active Muscular Action Units (Apple Inset 5-Dot Meter)
  const aus = data.facs_action_units || {};
  const activeContainer = document.getElementById("live-active-aus");
  if (activeContainer) {
    const activeList = Object.entries(aus).filter(([_, v]) => v >= 0.1);

    if (activeList.length === 0) {
      activeContainer.innerHTML = `<div class="au-empty-state">Otot wajah santai / tonus netral (Semua Level 0)</div>`;
    } else {
      activeContainer.innerHTML = activeList.map(([au, val], idx) => {
        const letter = getAUIntensityLetter(val);
        const meta = (clinicalInfo?.facs_metadata || {})[au] || {};
        const name = meta.name || au;
        const n = letter === 'E' ? 5 : letter === 'D' ? 4 : letter === 'C' ? 3 : letter === 'B' ? 2 : 1;
        const dotsHtml = [1, 2, 3, 4, 5].map(k => `
          <span class="au-dot ${k <= n ? 'active' : ''}"></span>
        `).join('');

        return `
          <div class="card-row-wrapper">
            <div class="au-row interactive ${idx === 0 ? 'first' : ''}" onclick="openAUInspector('${au}', ${val})" title="Klik untuk telaah klinis ${au}">
              <span class="au-name-col">
                <span class="au-name">${name}</span>
                <span class="au-code num">${au}</span>
              </span>
              <span class="au-meter-col">
                <span class="au-dots">${dotsHtml}</span>
                <span class="au-letter num">${letter}</span>
              </span>
            </div>
          </div>
        `;
      }).join("");
    }
  }
}

// =========================================================================
// TAB 2: SINGLE PHOTO DIAGNOSTIC
// =========================================================================

function handlePhotoSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  setPhotoFile(file);
}

function setPhotoFile(file) {
  currentSelectedFile = file;

  const btnAnalyze = document.getElementById("btn-analyze-photo");
  if (btnAnalyze) btnAnalyze.disabled = false;

  const dropContent = document.getElementById("drop-zone-content");
  if (dropContent) {
    const objectUrl = URL.createObjectURL(file);
    dropContent.innerHTML = `
      <div class="dropzone-thumb-wrapper">
        <img src="${objectUrl}" alt="Thumbnail" class="dropzone-thumb-img" />
        <div style="flex: 1; min-width: 0;">
          <div style="font-size: 14px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${file.name}</div>
          <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${(file.size / 1024).toFixed(1)} KB · Siap dianalisis</div>
        </div>
        <button type="button" class="pill-mini-btn" onclick="event.stopPropagation(); document.getElementById('photo-input').click();">Ganti</button>
      </div>
    `;
  }
  showToast(`Foto terpilih: ${file.name}`, "file");
}

async function uploadAndAnalyzePhoto() {
  if (!currentSelectedFile) return;

  const btn = document.getElementById("btn-analyze-photo");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Menganalisis...";
  }

  const showEmotions = document.getElementById("photo-show-emotions")?.checked || false;
  const formData = new FormData();
  formData.append("file", currentSelectedFile);
  formData.append("show_emotions", showEmotions ? "true" : "false");

  try {
    const res = await fetch("/api/v1/analyze/photo", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Gagal mengeksekusi analisis: " + (await res.text()));
    const data = await res.json();
    renderPhotoResults(data);
    showToast("Analisis klinis foto selesai", "check");
  } catch (err) {
    alert(err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Eksekusi Analisis Klinis";
    }
  }
}

function renderPhotoResults(data) {
  const emptyState = document.getElementById("photo-empty-state");
  const container = document.getElementById("photo-result-container");
  if (emptyState) emptyState.style.display = "none";
  if (container) container.style.display = "flex";

  // Previews
  const origPreview = document.getElementById("photo-original-preview");
  const annotPreview = document.getElementById("photo-annotated-preview");
  if (origPreview && currentSelectedFile) {
    origPreview.src = URL.createObjectURL(currentSelectedFile);
    origPreview.style.display = "block";
  }
  if (annotPreview) {
    annotPreview.src = data.annotated_image_base64 || (origPreview ? origPreview.src : "");
    annotPreview.style.display = "block";
  }

  // DASS-3 Diagnosis Cards
  if (data.dass_clinical_assessment) {
    const dass = data.dass_clinical_assessment;

    const depScore = Math.round((dass.depression?.score || 0) * 100);
    const depScoreEl = document.getElementById("photo-dep-score");
    const depBadge = document.getElementById("photo-dep-badge");
    if (depScoreEl) depScoreEl.textContent = `${depScore}%`;
    if (depBadge) {
      const z = zoneOf(depScore);
      depBadge.textContent = ZONE_WORDS[z];
      depBadge.style.color = ZONE_TEXTS[z];
    }

    const anxScore = Math.round((dass.anxiety?.score || 0) * 100);
    const anxScoreEl = document.getElementById("photo-anx-score");
    const anxBadge = document.getElementById("photo-anx-badge");
    if (anxScoreEl) anxScoreEl.textContent = `${anxScore}%`;
    if (anxBadge) {
      const z = zoneOf(anxScore);
      anxBadge.textContent = ZONE_WORDS[z];
      anxBadge.style.color = ZONE_TEXTS[z];
    }

    const strScore = Math.round((dass.stress?.score || 0) * 100);
    const strScoreEl = document.getElementById("photo-str-score");
    const strBadge = document.getElementById("photo-str-badge");
    if (strScoreEl) strScoreEl.textContent = `${strScore}%`;
    if (strBadge) {
      const z = zoneOf(strScore);
      strBadge.textContent = ZONE_WORDS[z];
      strBadge.style.color = ZONE_TEXTS[z];
    }
  }

  // Populate 31 FACS Action Units Table
  populateAUTable(data.facs_action_units || {});
}

function populateAUTable(facsAUs) {
  const tbody = document.getElementById("au-table-body");
  if (!tbody) return;

  const metadata = clinicalInfo?.facs_metadata || {};

  const rows = Object.entries(facsAUs).map(([au, val]) => {
    const meta = metadata[au] || { name: "Action Unit", muscle: "-", region: "-", clinical_meaning: "-" };
    const letter = getAUIntensityLetter(val);
    const pct = Math.round(val * 100);
    const isHighlight = letter !== "0";

    return `
      <tr onclick="openAUInspector('${au}', ${val})" style="cursor: pointer; ${isHighlight ? 'background: rgba(10, 100, 224, 0.05); font-weight: 500;' : ''}" title="Klik untuk telaah klinis ${au}">
        <td class="num" style="font-weight: 700; color: ${isHighlight ? 'var(--accent)' : 'var(--text-secondary)'};">${au}</td>
        <td style="color: var(--text-primary); font-weight: 500;">${meta.name}</td>
        <td style="color: var(--text-secondary); font-style: italic;">${meta.muscle}</td>
        <td class="num" style="text-align: center; font-weight: 600; color: ${isHighlight ? 'var(--accent)' : 'var(--text-secondary)'};">${letter}</td>
        <td class="num">${pct}%</td>
        <td style="color: var(--text-secondary); max-width: 280px; line-height: 1.4;">${meta.clinical_meaning}</td>
      </tr>
    `;
  });

  tbody.innerHTML = rows.join("");
}

function filterAUTable() {
  const query = (document.getElementById("au-search")?.value || "").toLowerCase();
  const rows = document.querySelectorAll("#au-table-body tr");
  rows.forEach(r => {
    const text = r.textContent.toLowerCase();
    r.style.display = text.includes(query) ? "" : "none";
  });
}

// =========================================================================
// TAB 3: BATCH DATASET PROCESSING
// =========================================================================

function handleBatchSelect(event) {
  batchFiles = Array.from(event.target.files);
  const countEl = document.getElementById("batch-file-count");
  const btnProcess = document.getElementById("btn-process-batch");

  if (countEl) countEl.textContent = `${batchFiles.length} berkas terpilih`;
  if (btnProcess) btnProcess.disabled = batchFiles.length === 0;
}

async function processBatchPhotos() {
  if (batchFiles.length === 0) return;

  const btnProcess = document.getElementById("btn-process-batch");
  const btnDownload = document.getElementById("btn-download-csv");
  const progContainer = document.getElementById("batch-progress-container");
  const progBar = document.getElementById("batch-progress-bar");
  const progText = document.getElementById("batch-progress-text");
  const progPct = document.getElementById("batch-progress-percent");
  const tbody = document.getElementById("batch-table-body");

  if (btnProcess) btnProcess.disabled = true;
  if (btnDownload) btnDownload.disabled = true;
  if (progContainer) progContainer.style.display = "block";
  batchResults = [];
  if (tbody) tbody.innerHTML = "";

  for (let i = 0; i < batchFiles.length; i++) {
    const file = batchFiles[i];
    const formData = new FormData();
    formData.append("file", file);
    formData.append("show_emotions", "false");

    try {
      const res = await fetch("/api/v1/analyze/photo", { method: "POST", body: formData });
      if (res.ok) {
        const item = await res.json();
        batchResults.push(item);
        appendBatchRow(item);
      }
    } catch (e) {
      console.error("Batch file processing error:", file.name, e);
    }

    const pct = Math.round(((i + 1) / batchFiles.length) * 100);
    if (progBar) progBar.style.width = pct + "%";
    if (progPct) progPct.textContent = pct + "%";
    if (progText) progText.textContent = `Memproses ${i + 1} / ${batchFiles.length}...`;
  }

  if (btnProcess) btnProcess.disabled = false;
  if (btnDownload) btnDownload.disabled = batchResults.length === 0;
  if (progText) progText.textContent = `Selesai! Berhasil memproses ${batchResults.length} berkas citra.`;
}

function appendBatchRow(item) {
  const tbody = document.getElementById("batch-table-body");
  if (!tbody) return;

  const dass = item.dass_clinical_assessment || { depression: {}, anxiety: {}, stress: {} };
  const emo = item.emotions || {};

  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td class="num" style="font-weight: 600;">${item.image_name}</td>
    <td style="text-align: center;">
      <span style="font-size: 12px; font-weight: 600; color: ${item.face_detected ? '#1F7A3A' : '#C4251C'};">
        ${item.face_detected ? 'TERDETEKSI' : 'NIHIL'}
      </span>
    </td>
    <td>
      <span style="font-weight: 600;">${item.distress_level}</span>
    </td>
    <td class="num">
      ${dass.depression?.level || '-'} (${Math.round((dass.depression?.score || 0) * 100)}%)
    </td>
    <td class="num">
      ${dass.anxiety?.level || '-'} (${Math.round((dass.anxiety?.score || 0) * 100)}%)
    </td>
    <td class="num">
      ${dass.stress?.level || '-'} (${Math.round((dass.stress?.score || 0) * 100)}%)
    </td>
    <td class="num">${emo.valence !== undefined ? emo.valence.toFixed(2) : '-'}</td>
  `;
  tbody.appendChild(tr);
}

function downloadBatchCSV() {
  if (batchResults.length === 0) return;

  const headers = [
    "image_name",
    "face_detected",
    "distress_level",
    "distress_score",
    "depression_level",
    "depression_score",
    "anxiety_level",
    "anxiety_score",
    "stress_level",
    "stress_score",
    "valence"
  ];

  const rows = batchResults.map(r => {
    const dass = r.dass_clinical_assessment || {};
    const dep = dass.depression || {};
    const anx = dass.anxiety || {};
    const str = dass.stress || {};
    const emo = r.emotions || {};

    return [
      `"${r.image_name}"`,
      r.face_detected,
      `"${r.distress_level}"`,
      r.distress_score !== null ? r.distress_score : "",
      `"${dep.level || ''}"`,
      dep.score !== undefined ? dep.score.toFixed(3) : "",
      `"${anx.level || ''}"`,
      anx.score !== undefined ? anx.score.toFixed(3) : "",
      `"${str.level || ''}"`,
      str.score !== undefined ? str.score.toFixed(3) : "",
      emo.valence !== undefined ? emo.valence.toFixed(3) : "",
    ].join(",");
  });

  const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `aiface_cohort_summary_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast("File rekap CSV berhasil diunduh", "download");
}

// =========================================================================
// INTERACTIVE CLINICAL INSPECTOR & LIGHTBOX MODAL
// =========================================================================

function openAUInspector(auCode, val = null) {
  const meta = (clinicalInfo?.facs_metadata || {})[auCode] || {};
  const letter = val !== null ? getAUIntensityLetter(val) : "-";
  const name = meta.name || auCode;
  const muscle = meta.muscle || "Musculus facialis";
  const region = meta.region || "Wajah";
  const clinicalMeaning = meta.clinical_meaning || "Aktivitas motorik ekspresi wajah.";

  let modal = document.getElementById("au-inspector-modal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "au-inspector-modal";
    modal.className = "modal-backdrop";
    modal.onclick = (e) => {
      if (e.target === modal) closeAUInspector();
    };
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="modal-card" onclick="event.stopPropagation()">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
        <div>
          <span style="display: inline-block; padding: 2px 8px; border-radius: 6px; background: rgba(10, 100, 224, 0.12); color: var(--accent); font-weight: 700; font-size: 12px; margin-bottom: 4px;">${auCode}</span>
          <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: var(--text-primary);">${name}</h3>
        </div>
        <button class="modal-close-btn" onclick="closeAUInspector()" aria-label="Tutup">
          <svg width="14" height="14" viewBox="0 0 14 14"><path d="M2 2l10 10M12 2L2 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
      </div>
      <div style="display: flex; flex-direction: column; gap: 10px; font-size: 13px; line-height: 18px;">
        <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: #F8F8FA; border-radius: 10px;">
          <span style="color: var(--text-secondary);">Wilayah Anatomi</span>
          <span style="font-weight: 600; color: var(--text-primary);">${region}</span>
        </div>
        <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: #F8F8FA; border-radius: 10px;">
          <span style="color: var(--text-secondary);">Musculus Anatomi</span>
          <span style="font-weight: 600; color: var(--text-primary); font-style: italic;">${muscle}</span>
        </div>
        ${val !== null ? `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #F8F8FA; border-radius: 10px;">
          <span style="color: var(--text-secondary);">Intensitas Terdeteksi</span>
          <span style="font-weight: 700; color: var(--accent);">${letter} (${Math.round(val * 100)}%)</span>
        </div>` : ''}
        <div style="padding: 10px 12px; background: #F2F2F7; border-radius: 10px;">
          <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 4px;">Signifikansi Klinis &amp; DASS-3</div>
          <div style="color: var(--text-primary);">${clinicalMeaning}</div>
        </div>
      </div>
      <button class="apple-btn" style="width: 100%; margin-top: 18px;" onclick="closeAUInspector()">Tutup Telaah</button>
    </div>
  `;
  modal.style.display = "flex";
}

function closeAUInspector() {
  const modal = document.getElementById("au-inspector-modal");
  if (modal) modal.style.display = "none";
}

function openLightbox(imgSrc, title = "Citra Pasien") {
  if (!imgSrc) return;
  const modal = document.getElementById("lightbox-modal");
  const img = document.getElementById("lightbox-img");
  const titleEl = document.getElementById("lightbox-title");
  if (modal && img) {
    img.src = imgSrc;
    if (titleEl) titleEl.textContent = title;
    modal.style.display = "flex";
  }
}

function closeLightbox() {
  const modal = document.getElementById("lightbox-modal");
  if (modal) modal.style.display = "none";
}
