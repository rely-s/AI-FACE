/**
 * AI-FACE Clinical Platform - Institutional Diagnostic Workstation ES6 Application
 * Precision healthcare UI without AI slop, neon artifacts, or frame tearing.
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
let overlayMode = "clean"; // "clean" (SVG Reticle) or "classic" (OpenCV SHORE Burn-in)
let isCameraMirrored = true; // Natural selfie/mirror orientation

// Initialize on Load
document.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  await loadClinicalInfo();
});

// Navigation Tab Switcher
function switchTab(tabName) {
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".nav-tab").forEach(el => {
    el.classList.remove("active");
    el.classList.add("text-slate-300");
  });

  const activeContent = document.getElementById(`tab-content-${tabName}`);
  const activeBtn = document.getElementById(`tab-btn-${tabName}`);
  if (activeContent) activeContent.classList.remove("hidden");
  if (activeBtn) {
    activeBtn.classList.add("active");
    activeBtn.classList.remove("text-slate-300");
  }

  // Safe resource cleanup when navigating away from Live Camera
  if (tabName !== "live" && liveStream) {
    stopCamera();
  }

  if (window.lucide) {
    lucide.createIcons();
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

// Helper: Clinical Triage Badge Classes
function getBadgeClass(level) {
  const l = (level || "").toLowerCase();
  if (l.includes("normal") || l === "low") return "badge-normal";
  if (l.includes("mild")) return "badge-mild";
  if (l.includes("moderate")) return "badge-moderate";
  if (l.includes("extremely")) return "badge-extremely-severe";
  if (l.includes("severe") || l === "high") return "badge-severe";
  return "badge-normal";
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

function getAUPillClass(letter) {
  switch (letter) {
    case "A": return "au-pill-a";
    case "B": return "au-pill-b";
    case "C": return "au-pill-c";
    case "D": return "au-pill-d";
    case "E": return "au-pill-e";
    default: return "au-pill-0";
  }
}

// =========================================================================
// TAB 1: LIVE WEBCAM MONITORING
// =========================================================================

function toggleCameraMirror() {
  isCameraMirrored = !isCameraMirrored;
  const video = document.getElementById("webcam-video");
  const overlay = document.getElementById("live-annotated-overlay");
  const label = document.getElementById("live-mirror-label");
  const btn = document.getElementById("live-mirror-toggle");

  if (isCameraMirrored) {
    if (video) video.classList.add("camera-mirror");
    if (overlay) overlay.classList.add("camera-mirror");
    if (label) label.textContent = "Mirror: ON";
    if (btn) btn.className = "text-[11px] px-2.5 py-1 rounded-md font-medium border flex items-center gap-1.5 transition border-[#192853] bg-[#192853] text-[#FFE14F] shadow-sm";
  } else {
    if (video) video.classList.remove("camera-mirror");
    if (overlay) overlay.classList.remove("camera-mirror");
    if (label) label.textContent = "Mirror: OFF";
    if (btn) btn.className = "text-[11px] px-2.5 py-1 rounded-md font-medium border flex items-center gap-1.5 transition border-[#192853]/20 bg-white text-[#4A5F82] hover:border-[#192853] hover:text-[#192853] shadow-sm";
  }
  if (window.lucide) lucide.createIcons();
}

function toggleOverlayDisplayMode() {
  overlayMode = (overlayMode === "clean") ? "classic" : "clean";
  const label = document.getElementById("live-overlay-mode-label");
  const overlay = document.getElementById("live-annotated-overlay");
  const faceBox = document.getElementById("live-face-box");

  if (overlayMode === "clean") {
    if (label) label.textContent = "Retikel Medis (Bersih)";
    if (overlay) overlay.classList.add("hidden");
  } else {
    if (label) label.textContent = "Burn-in Klasik (SHORE)";
    if (faceBox) faceBox.classList.add("hidden");
  }
}

function toggleLiveEmotions() {
  liveShowEmotions = !liveShowEmotions;
  const btn = document.getElementById("live-emotion-toggle");
  if (!btn) return;

  if (liveShowEmotions) {
    btn.innerHTML = `<i data-lucide="toggle-right" class="w-3.5 h-3.5 text-[#FFE14F]"></i>
                     <span>Mode Lengkap (+Emosi)</span>
                     <kbd class="px-1 py-0.2 bg-[#192853] rounded text-[9px] font-mono text-[#FFE14F]">E</kbd>`;
    btn.className = "text-[11px] px-2.5 py-1 rounded-md font-medium border flex items-center gap-1.5 transition border-[#192853] bg-[#192853] text-[#FFE14F] shadow-sm";
  } else {
    btn.innerHTML = `<i data-lucide="toggle-left" class="w-3.5 h-3.5 text-[#192853]"></i>
                     <span>Mode Klinis Murni (OFF)</span>
                     <kbd class="px-1 py-0.2 bg-[#ECF4F7] rounded text-[9px] font-mono text-[#192853] border border-[#192853]/20">E</kbd>`;
    btn.className = "text-[11px] px-2.5 py-1 rounded-md font-medium border flex items-center gap-1.5 transition border-[#192853]/20 bg-white text-[#4A5F82] hover:border-[#192853] hover:text-[#192853] shadow-sm";
  }
  if (window.lucide) lucide.createIcons();
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

    placeholder.classList.add("hidden");
    btnStart.classList.add("hidden");
    btnStop.classList.remove("hidden");

    if (statusDot) {
      statusDot.className = "w-2 h-2 rounded-full bg-[#FFE14F] animate-pulse";
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
  if (placeholder) placeholder.classList.remove("hidden");

  const overlay = document.getElementById("live-annotated-overlay");
  if (overlay) {
    overlay.src = "";
    overlay.classList.add("hidden");
  }

  const faceBox = document.getElementById("live-face-box");
  if (faceBox) faceBox.classList.add("hidden");

  const statusDot = document.getElementById("live-status-dot");
  if (statusDot) statusDot.className = "w-2 h-2 rounded-full bg-slate-500";

  const targetStatus = document.getElementById("live-target-status");
  if (targetStatus) targetStatus.textContent = "| TERHENTI";

  isAnalyzingFrame = false;

  const btnStart = document.getElementById("btn-start-camera");
  const btnStop = document.getElementById("btn-stop-camera");
  if (btnStart) btnStart.classList.remove("hidden");
  if (btnStop) btnStop.classList.add("hidden");
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
    if (overlay) overlay.classList.add("hidden");

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
      faceBox.classList.remove("hidden");
      if (targetStatus) targetStatus.textContent = "| TRACKING";
    } else {
      if (faceBox) faceBox.classList.add("hidden");
      if (targetStatus) targetStatus.textContent = "| MENCARI WAJAH";
    }
  } else {
    // Classic SHORE burn-in overlay mode
    if (faceBox) faceBox.classList.add("hidden");
    if (data.annotated_image_base64 && overlay) {
      overlay.src = data.annotated_image_base64;
      overlay.classList.remove("hidden");
    }
    if (targetStatus) {
      targetStatus.textContent = data.face_detected ? "| TERDETEKSI" : "| MENCARI WAJAH";
    }
  }

  // 2. Latency & Uptime Telemetry
  const latencyEl = document.getElementById("live-latency-indicator");
  if (latencyEl && latencyMs > 0) {
    latencyEl.textContent = `Latency: ${latencyMs} ms`;
  }

  if (liveStartTime) {
    const elapsed = ((Date.now() - liveStartTime) / 1000).toFixed(1);
    const uptimeEl = document.getElementById("live-uptime");
    if (uptimeEl) uptimeEl.textContent = `${elapsed}s`;
  }

  // 3. Distress Level Triage Badge
  const distBadge = document.getElementById("live-distress-badge");
  if (distBadge) {
    const distLvl = data.distress_level || "NO_FACE";
    distBadge.textContent = distLvl;
    distBadge.className = `text-[10px] font-bold px-2 py-0.5 rounded mt-1 inline-block ${getBadgeClass(distLvl)}`;
  }

  // 4. Tri-Axial DASS-3 Clinical Scales
  if (data.dass_clinical_assessment) {
    const dass = data.dass_clinical_assessment;

    // Depression (DEP)
    const depScore = Math.round((dass.depression.score || 0) * 100);
    const depScoreEl = document.getElementById("live-dep-score");
    const depLvlEl = document.getElementById("live-dep-level");
    const depBarEl = document.getElementById("live-dep-bar");
    if (depScoreEl) depScoreEl.textContent = `${depScore}%`;
    if (depLvlEl) {
      depLvlEl.textContent = dass.depression.level;
      depLvlEl.className = `text-[10px] font-bold px-1.5 py-0.5 rounded ${getBadgeClass(dass.depression.level)}`;
    }
    if (depBarEl) depBarEl.style.width = `${Math.min(100, depScore)}%`;

    // Anxiety (ANX)
    const anxScore = Math.round((dass.anxiety.score || 0) * 100);
    const anxScoreEl = document.getElementById("live-anx-score");
    const anxLvlEl = document.getElementById("live-anx-level");
    const anxBarEl = document.getElementById("live-anx-bar");
    if (anxScoreEl) anxScoreEl.textContent = `${anxScore}%`;
    if (anxLvlEl) {
      anxLvlEl.textContent = dass.anxiety.level;
      anxLvlEl.className = `text-[10px] font-bold px-1.5 py-0.5 rounded ${getBadgeClass(dass.anxiety.level)}`;
    }
    if (anxBarEl) anxBarEl.style.width = `${Math.min(100, anxScore)}%`;

    // Stress (STR)
    const strScore = Math.round((dass.stress.score || 0) * 100);
    const strScoreEl = document.getElementById("live-str-score");
    const strLvlEl = document.getElementById("live-str-level");
    const strBarEl = document.getElementById("live-str-bar");
    if (strScoreEl) strScoreEl.textContent = `${strScore}%`;
    if (strLvlEl) {
      strLvlEl.textContent = dass.stress.level;
      strLvlEl.className = `text-[10px] font-bold px-1.5 py-0.5 rounded ${getBadgeClass(dass.stress.level)}`;
    }
    if (strBarEl) strBarEl.style.width = `${Math.min(100, strScore)}%`;
  }

  // 5. Active Muscular Action Units
  const aus = data.facs_action_units || {};
  const activeContainer = document.getElementById("live-active-aus");
  if (activeContainer) {
    const activeList = Object.entries(aus).filter(([_, v]) => v >= 0.1);

    if (activeList.length === 0) {
      activeContainer.innerHTML = `<span class="text-xs text-slate-500 italic">Otot wajah santai / tonus netral (Semua Level 0)</span>`;
    } else {
      activeContainer.innerHTML = activeList.map(([au, val]) => {
        const letter = getAUIntensityLetter(val);
        const pillClass = getAUPillClass(letter);
        const meta = (clinicalInfo?.facs_metadata || {})[au] || {};
        const titleText = `${au}: ${meta.name || ''} (${meta.muscle || ''}) - ${meta.clinical_meaning || ''}`;
        return `
          <span class="inline-flex items-center gap-1.5 text-[11px] font-mono px-2 py-0.5 rounded border border-[#192853]/15 bg-white text-[#192853] shadow-sm cursor-help" title="${titleText}">
            <span class="text-[#192853] font-bold">${au}</span>
            <span class="px-1 py-0.2 rounded text-[10px] font-bold ${pillClass}">${letter}</span>
          </span>`;
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
      <div class="w-10 h-10 rounded-full bg-[#FFE14F] border border-[#192853]/20 flex items-center justify-center text-[#192853] mx-auto mb-2 shadow-sm">
        <i data-lucide="check" class="w-5 h-5"></i>
      </div>
      <p class="text-xs font-semibold text-[#192853] truncate max-w-xs mx-auto font-mono">${file.name}</p>
      <p class="text-[10px] text-[#7287A5] font-mono tabular-nums mt-0.5">${(file.size / 1024).toFixed(1)} KB</p>
      <button type="button" class="mt-2 text-[11px] font-medium text-[#192853] font-bold underline">Ganti Berkas</button>
    `;
    if (window.lucide) lucide.createIcons();
  }
}

async function uploadAndAnalyzePhoto() {
  if (!currentSelectedFile) return;

  const btn = document.getElementById("btn-analyze-photo");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i> Menganalisis...`;
    if (window.lucide) lucide.createIcons();
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
      btn.innerHTML = `<i data-lucide="sparkles" class="w-3.5 h-3.5"></i> Eksekusi Analisis Klinis`;
      if (window.lucide) lucide.createIcons();
    }
  }
}

function renderPhotoResults(data) {
  const emptyState = document.getElementById("photo-empty-state");
  const container = document.getElementById("photo-result-container");
  if (emptyState) emptyState.classList.add("hidden");
  if (container) container.classList.remove("hidden");

  // Previews
  const origPreview = document.getElementById("photo-original-preview");
  const annotPreview = document.getElementById("photo-annotated-preview");
  if (origPreview && currentSelectedFile) {
    origPreview.src = URL.createObjectURL(currentSelectedFile);
  }
  if (annotPreview) {
    annotatedSrc = data.annotated_image_base64 || (origPreview ? origPreview.src : "");
    annotPreview.src = annotatedSrc;
  }

  // DASS-3 Diagnosis Cards
  if (data.dass_clinical_assessment) {
    const dass = data.dass_clinical_assessment;

    // Depression
    const depScore = Math.round((dass.depression.score || 0) * 100);
    const depScoreEl = document.getElementById("photo-dep-score");
    const depBadge = document.getElementById("photo-dep-badge");
    if (depScoreEl) depScoreEl.textContent = `${depScore}%`;
    if (depBadge) {
      depBadge.textContent = dass.depression.level;
      depBadge.className = `text-[10px] font-bold px-2 py-0.5 rounded ${getBadgeClass(dass.depression.level)}`;
    }

    // Anxiety
    const anxScore = Math.round((dass.anxiety.score || 0) * 100);
    const anxScoreEl = document.getElementById("photo-anx-score");
    const anxBadge = document.getElementById("photo-anx-badge");
    if (anxScoreEl) anxScoreEl.textContent = `${anxScore}%`;
    if (anxBadge) {
      anxBadge.textContent = dass.anxiety.level;
      anxBadge.className = `text-[10px] font-bold px-2 py-0.5 rounded ${getBadgeClass(dass.anxiety.level)}`;
    }

    // Stress
    const strScore = Math.round((dass.stress.score || 0) * 100);
    const strScoreEl = document.getElementById("photo-str-score");
    const strBadge = document.getElementById("photo-str-badge");
    if (strScoreEl) strScoreEl.textContent = `${strScore}%`;
    if (strBadge) {
      strBadge.textContent = dass.stress.level;
      strBadge.className = `text-[10px] font-bold px-2 py-0.5 rounded ${getBadgeClass(dass.stress.level)}`;
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
    const pillClass = getAUPillClass(letter);
    const pct = Math.round(val * 100);
    const isHighlight = letter !== "0";

    return `
      <tr class="hover:bg-[#F3F8FA] transition ${isHighlight ? 'bg-[#FFE14F]/15' : ''}">
        <td class="py-2.5 px-3 font-mono font-bold ${isHighlight ? 'text-[#192853]' : 'text-[#7287A5]'}">${au}</td>
        <td class="py-2.5 px-3 text-[#192853] font-sans font-medium">${meta.name}</td>
        <td class="py-2.5 px-3 text-[#4A5F82] italic text-[11px]">${meta.muscle}</td>
        <td class="py-2.5 px-3 text-center">
          <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold ${pillClass}">${letter}</span>
        </td>
        <td class="py-2.5 px-3">
          <div class="flex items-center gap-2">
            <div class="clinical-progress-track w-16">
              <div class="clinical-progress-fill bg-[#192853]" style="width: ${pct}%"></div>
            </div>
            <span class="text-[11px] text-[#4A5F82] font-mono tabular-nums">${pct}%</span>
          </div>
        </td>
        <td class="py-2.5 px-3 text-[#4A5F82] max-w-xs text-[11px] font-sans leading-relaxed">${meta.clinical_meaning}</td>
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
  if (progContainer) progContainer.classList.remove("hidden");
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
  tr.className = "hover:bg-[#F3F8FA] transition";
  tr.innerHTML = `
    <td class="py-2.5 px-3 font-medium text-[#192853] truncate max-w-[140px] font-mono text-[11px]">${item.image_name}</td>
    <td class="py-2.5 px-3 text-center">
      <span class="px-2 py-0.5 rounded text-[10px] font-medium ${item.face_detected ? 'bg-[#FEF9C3] text-[#854D0E] border border-[#FDE047]' : 'bg-rose-50 text-rose-700 border border-rose-200'}">
        ${item.face_detected ? 'TERDETEKSI' : 'NIHIL'}
      </span>
    </td>
    <td class="py-2.5 px-3">
      <span class="px-2 py-0.5 rounded text-[10px] font-bold ${getBadgeClass(item.distress_level)}">${item.distress_level}</span>
    </td>
    <td class="py-2.5 px-3 font-mono tabular-nums text-[11px]">
      <span class="px-1.5 py-0.5 rounded font-sans font-medium ${getBadgeClass(dass.depression.level)}">${dass.depression.level || '-'}</span>
      <span class="text-[#7287A5] text-[10px] ml-1">(${Math.round((dass.depression.score || 0) * 100)}%)</span>
    </td>
    <td class="py-2.5 px-3 font-mono tabular-nums text-[11px]">
      <span class="px-1.5 py-0.5 rounded font-sans font-medium ${getBadgeClass(dass.anxiety.level)}">${dass.anxiety.level || '-'}</span>
      <span class="text-[#7287A5] text-[10px] ml-1">(${Math.round((dass.anxiety.score || 0) * 100)}%)</span>
    </td>
    <td class="py-2.5 px-3 font-mono tabular-nums text-[11px]">
      <span class="px-1.5 py-0.5 rounded font-sans font-medium ${getBadgeClass(dass.stress.level)}">${dass.stress.level || '-'}</span>
      <span class="text-[#7287A5] text-[10px] ml-1">(${Math.round((dass.stress.score || 0) * 100)}%)</span>
    </td>
    <td class="py-2.5 px-3 font-mono tabular-nums text-[11px] text-[#192853] font-semibold">${emo.valence !== undefined ? emo.valence.toFixed(2) : '-'}</td>
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
