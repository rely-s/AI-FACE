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
});

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
// TAB 1: LIVE WEBCAM MONITORING
// =========================================================================

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
}

function toggleOverlayDisplayMode() {
  overlayMode = (overlayMode === "clean") ? "classic" : "clean";
  const label = document.getElementById("live-overlay-mode-label");
  const overlay = document.getElementById("live-annotated-overlay");
  const faceBox = document.getElementById("live-face-box");
  const toggleBtn = document.getElementById("live-overlay-toggle");
  const track = toggleBtn ? toggleBtn.querySelector(".switch-track") : null;

  if (overlayMode === "clean") {
    if (label) label.textContent = "Tampilkan overlay deteksi lama (OFF)";
    if (track) track.className = "switch-track";
    if (toggleBtn) toggleBtn.setAttribute("aria-checked", "false");
    if (overlay) overlay.style.display = "none";
  } else {
    if (label) label.textContent = "Overlay deteksi lama (ON)";
    if (track) track.className = "switch-track on";
    if (toggleBtn) toggleBtn.setAttribute("aria-checked", "true");
    if (faceBox) faceBox.style.display = "none";
  }
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
}

// Global hotkey: 'E' or 'e' to toggle emotion calculation
window.addEventListener("keydown", (e) => {
  if (e.key === "e" || e.key === "E") {
    if (document.activeElement && ["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
      return;
    }
    toggleLiveEmotions();
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

  try {
    liveStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: "user"
      },
      audio: false
    });
    video.srcObject = liveStream;
    await video.play();

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

    liveStartTime = Date.now();
    const subjId = "SUBJ-" + Math.random().toString(36).substring(2, 6).toUpperCase();
    const subjIdEl = document.getElementById("live-subject-id");
    if (subjIdEl) subjIdEl.textContent = subjId;

    isAnalyzingFrame = false;

    // Stream telemetry frames at ~10-15 Hz (100ms cycle)
    liveInterval = setInterval(captureAndSendLiveFrame, 100);
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

  const video = document.getElementById("webcam-video");
  if (video) video.srcObject = null;

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

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

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
            <div class="au-row ${idx === 0 ? 'first' : ''}">
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
  currentSelectedFile = file;

  const btnAnalyze = document.getElementById("btn-analyze-photo");
  if (btnAnalyze) btnAnalyze.disabled = false;

  const dropZone = document.getElementById("drop-zone");
  if (dropZone) {
    dropZone.innerHTML = `
      <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">${file.name}</div>
      <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">${(file.size / 1024).toFixed(1)} KB</div>
      <button type="button" class="apple-btn secondary" style="margin-top: 12px; min-height: 32px; font-size: 13px;">Ganti Berkas</button>
    `;
  }
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
  }
  if (annotPreview) {
    annotPreview.src = data.annotated_image_base64 || (origPreview ? origPreview.src : "");
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
      <tr style="${isHighlight ? 'background: rgba(10, 100, 224, 0.05); font-weight: 500;' : ''}">
        <td class="num" style="font-weight: 700; color: ${isHighlight ? 'var(--accent)' : 'var(--text-secondary)'};">${au}</td>
        <td style="color: var(--text-primary);">${meta.name}</td>
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
}
