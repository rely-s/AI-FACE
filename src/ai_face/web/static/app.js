/**
 * AI-FACE Clinical Web Platform - Interactive ES6 Application
 */

// Global State
let clinicalInfo = null;
let currentSelectedFile = null;
let batchFiles = [];
let batchResults = [];
let liveStream = null;
let liveInterval = null;
let liveShowEmotions = false;
let liveStartTime = null;

// Initialize on Load
document.addEventListener("DOMContentLoaded", async () => {
  lucide.createIcons();
  await loadClinicalInfo();
});

// Navigation Tab Switcher
function switchTab(tabName) {
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".nav-tab").forEach(el => {
    el.classList.remove("active", "bg-emerald-600", "text-white");
    el.classList.add("text-slate-300");
  });

  const activeContent = document.getElementById(`tab-content-${tabName}`);
  const activeBtn = document.getElementById(`tab-btn-${tabName}`);
  if (activeContent) activeContent.classList.remove("hidden");
  if (activeBtn) {
    activeBtn.classList.add("active", "bg-emerald-600", "text-white");
    activeBtn.classList.remove("text-slate-300");
  }

  // If leaving live camera tab, stop camera to release resources
  if (tabName !== "live" && liveStream) {
    stopCamera();
  }

  lucide.createIcons();
}

// Load metadata dictionary
async function loadClinicalInfo() {
  try {
    const res = await fetch("/api/v1/clinical/info");
    clinicalInfo = await res.json();
  } catch (err) {
    console.error("Failed to load clinical info metadata:", err);
  }
}

// Helper: Badge classes
function getBadgeClass(level) {
  const l = (level || "").toLowerCase();
  if (l.includes("normal") || l === "low") return "badge-normal";
  if (l.includes("mild")) return "badge-mild";
  if (l.includes("moderate")) return "badge-moderate";
  if (l.includes("extremely")) return "badge-extremely-severe";
  if (l.includes("severe") || l === "high") return "badge-severe";
  return "badge-normal";
}

function getAUIntensityLetter(score) {
  if (score >= 0.85) return "E";
  if (score >= 0.70) return "D";
  if (score >= 0.50) return "C";
  if (score >= 0.30) return "B";
  if (score >= 0.10) return "A";
  return "0";
}

// =========================================================================
// TAB 1: LIVE WEBCAM MONITORING
// =========================================================================

async function startCamera() {
  const video = document.getElementById("webcam-video");
  const placeholder = document.getElementById("camera-placeholder");
  const btnStart = document.getElementById("btn-start-camera");
  const btnStop = document.getElementById("btn-stop-camera");
  const overlay = document.getElementById("live-annotated-overlay");

  try {
    liveStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false
    });
    video.srcObject = liveStream;
    placeholder.classList.add("hidden");
    overlay.classList.remove("hidden");

    btnStart.classList.add("hidden");
    btnStop.classList.remove("hidden");

    liveStartTime = Date.now();
    document.getElementById("live-subject-id").textContent = "SUBJ-" + Math.random().toString(36).substring(2, 6).toUpperCase();

    // Start frame loop at ~10-15 Hz (every 100ms)
    liveInterval = setInterval(captureAndSendLiveFrame, 100);
  } catch (err) {
    alert("Tidak dapat mengakses kamera webcam: " + err.message);
  }
}

function stopCamera() {
  if (liveInterval) clearInterval(liveInterval);
  if (liveStream) {
    liveStream.getTracks().forEach(track => track.stop());
    liveStream = null;
  }
  const video = document.getElementById("webcam-video");
  video.srcObject = null;
  document.getElementById("camera-placeholder").classList.remove("hidden");
  const overlay = document.getElementById("live-annotated-overlay");
  overlay.classList.add("hidden");
  overlay.src = "";

  document.getElementById("btn-start-camera").classList.remove("hidden");
  document.getElementById("btn-stop-camera").classList.add("hidden");
}

function toggleLiveEmotions() {
  liveShowEmotions = !liveShowEmotions;
  const btn = document.getElementById("live-emotion-toggle");
  if (liveShowEmotions) {
    btn.innerHTML = `<i data-lucide="toggle-right" class="w-4 h-4 text-emerald-400"></i> Mode Ekspresi Lengkap (ON)`;
    btn.className = "text-xs px-3 py-1.5 rounded-lg font-medium border flex items-center gap-1.5 transition border-emerald-500 bg-emerald-950/40 text-emerald-300";
  } else {
    btn.innerHTML = `<i data-lucide="toggle-left" class="w-4 h-4"></i> Mode Klinis Murni (Ekspresi OFF)`;
    btn.className = "text-xs px-3 py-1.5 rounded-lg font-medium border flex items-center gap-1.5 transition border-slate-700 bg-slate-800 text-slate-300 hover:border-emerald-500";
  }
  lucide.createIcons();
}

async function captureAndSendLiveFrame() {
  const video = document.getElementById("webcam-video");
  const canvas = document.getElementById("capture-canvas");
  if (!video || video.readyState !== 4) return;

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob(async (blob) => {
    if (!blob) return;
    const formData = new FormData();
    formData.append("file", blob, "live_frame.jpg");
    formData.append("show_emotions", liveShowEmotions ? "true" : "false");

    try {
      const res = await fetch("/api/v1/analyze/frame", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) return;
      const data = await res.json();
      updateLiveDashboard(data);
    } catch (err) {
      // frame dropped, ignore silently
    }
  }, "image/jpeg", 0.75);
}

function updateLiveDashboard(data) {
  // Update HUD overlay image
  if (data.annotated_image_base64) {
    document.getElementById("live-annotated-overlay").src = data.annotated_image_base64;
  }

  // Update uptime
  if (liveStartTime) {
    const elapsed = ((Date.now() - liveStartTime) / 1000).toFixed(1);
    document.getElementById("live-uptime").textContent = elapsed + "s";
  }

  // Update distress level badge
  const distBadge = document.getElementById("live-distress-badge");
  const distLvl = data.distress_level || "NO_FACE";
  distBadge.textContent = distLvl;
  distBadge.className = `text-xs font-bold px-2 py-0.5 rounded mt-1 inline-block ${getBadgeClass(distLvl)}`;

  // Update DASS-3
  if (data.dass_clinical_assessment) {
    const dass = data.dass_clinical_assessment;
    // Depression
    document.getElementById("live-dep-score").textContent = Math.round(dass.depression.score * 100) + "%";
    const depLvl = document.getElementById("live-dep-level");
    depLvl.textContent = dass.depression.level;
    depLvl.className = `text-[11px] font-bold px-1.5 py-0.5 rounded ${getBadgeClass(dass.depression.level)}`;
    document.getElementById("live-dep-bar").style.width = Math.min(100, Math.round(dass.depression.score * 100)) + "%";

    // Anxiety
    document.getElementById("live-anx-score").textContent = Math.round(dass.anxiety.score * 100) + "%";
    const anxLvl = document.getElementById("live-anx-level");
    anxLvl.textContent = dass.anxiety.level;
    anxLvl.className = `text-[11px] font-bold px-1.5 py-0.5 rounded ${getBadgeClass(dass.anxiety.level)}`;
    document.getElementById("live-anx-bar").style.width = Math.min(100, Math.round(dass.anxiety.score * 100)) + "%";

    // Stress
    document.getElementById("live-str-score").textContent = Math.round(dass.stress.score * 100) + "%";
    const strLvl = document.getElementById("live-str-level");
    strLvl.textContent = dass.stress.level;
    strLvl.className = `text-[11px] font-bold px-1.5 py-0.5 rounded ${getBadgeClass(dass.stress.level)}`;
    document.getElementById("live-str-bar").style.width = Math.min(100, Math.round(dass.stress.score * 100)) + "%";
  }

  // Update Active Action Units
  const aus = data.facs_action_units || {};
  const activeContainer = document.getElementById("live-active-aus");
  const activeList = Object.entries(aus).filter(([k, v]) => v >= 0.1);

  if (activeList.length === 0) {
    activeContainer.innerHTML = `<span class="text-xs text-slate-500 italic">Otot wajah santai / netral (Semua Level 0)</span>`;
  } else {
    activeContainer.innerHTML = activeList.map(([au, val]) => {
      const letter = getAUIntensityLetter(val);
      const meta = (clinicalInfo?.facs_metadata || {})[au] || {};
      return `<span class="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200" title="${meta.name || ''} - ${meta.clinical_meaning || ''}">
        <span class="text-cyan-400 font-bold">${au}</span> [${letter}]
      </span>`;
    }).join("");
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
  btnAnalyze.disabled = false;

  // Show dropzone preview
  const dropZone = document.getElementById("drop-zone");
  dropZone.innerHTML = `
    <i data-lucide="check-circle-2" class="w-8 h-8 mx-auto text-emerald-400 mb-1"></i>
    <p class="text-xs font-semibold text-white truncate max-w-xs mx-auto">${file.name}</p>
    <p class="text-[10px] text-slate-400 mt-0.5">${(file.size / 1024).toFixed(1)} KB</p>
    <button type="button" class="mt-2 text-[11px] text-emerald-400 hover:underline">Ganti Foto</button>
  `;
  lucide.createIcons();
}

async function uploadAndAnalyzePhoto() {
  if (!currentSelectedFile) return;

  const btn = document.getElementById("btn-analyze-photo");
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Menganalisis...`;
  lucide.createIcons();

  const showEmotions = document.getElementById("photo-show-emotions").checked;
  const formData = new FormData();
  formData.append("file", currentSelectedFile);
  formData.append("show_emotions", showEmotions ? "true" : "false");

  try {
    const res = await fetch("/api/v1/analyze/photo", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Gagal menganalisis foto: " + (await res.text()));
    const data = await res.json();
    renderPhotoResults(data);
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4"></i> Analisis Wajah Pasien`;
    lucide.createIcons();
  }
}

function renderPhotoResults(data) {
  document.getElementById("photo-empty-state").classList.add("hidden");
  const container = document.getElementById("photo-result-container");
  container.classList.remove("hidden");

  // Previews
  const origPreview = document.getElementById("photo-original-preview");
  const annotPreview = document.getElementById("photo-annotated-preview");
  origPreview.src = URL.createObjectURL(currentSelectedFile);
  annotPreview.src = data.annotated_image_base64 || origPreview.src;

  // DASS Cards
  if (data.dass_clinical_assessment) {
    const dass = data.dass_clinical_assessment;
    // Depression
    document.getElementById("photo-dep-score").textContent = Math.round(dass.depression.score * 100) + "%";
    const depB = document.getElementById("photo-dep-badge");
    depB.textContent = dass.depression.level;
    depB.className = `text-xs font-bold px-2 py-0.5 rounded ${getBadgeClass(dass.depression.level)}`;

    // Anxiety
    document.getElementById("photo-anx-score").textContent = Math.round(dass.anxiety.score * 100) + "%";
    const anxB = document.getElementById("photo-anx-badge");
    anxB.textContent = dass.anxiety.level;
    anxB.className = `text-xs font-bold px-2 py-0.5 rounded ${getBadgeClass(dass.anxiety.level)}`;

    // Stress
    document.getElementById("photo-str-score").textContent = Math.round(dass.stress.score * 100) + "%";
    const strB = document.getElementById("photo-str-badge");
    strB.textContent = dass.stress.level;
    strB.className = `text-xs font-bold px-2 py-0.5 rounded ${getBadgeClass(dass.stress.level)}`;
  }

  // Populate 31 FACS Table
  populateAUTable(data.facs_action_units || {});
}

function populateAUTable(facsAUs) {
  const tbody = document.getElementById("au-table-body");
  const metadata = clinicalInfo?.facs_metadata || {};

  const rows = Object.entries(facsAUs).map(([au, val]) => {
    const meta = metadata[au] || { name: "Action Unit", muscle: "-", region: "-", clinical_meaning: "-" };
    const letter = getAUIntensityLetter(val);
    const pct = Math.round(val * 100);
    const activeColor = letter !== "0" ? "text-cyan-400 font-bold" : "text-slate-500";

    return `
      <tr class="hover:bg-slate-800/40 transition">
        <td class="py-2.5 px-3 font-bold ${activeColor}">${au}</td>
        <td class="py-2.5 px-3 text-slate-200">${meta.name}</td>
        <td class="py-2.5 px-3 text-slate-400 italic">${meta.muscle}</td>
        <td class="py-2.5 px-3 text-center">
          <span class="px-2 py-0.5 rounded ${letter !== '0' ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30' : 'text-slate-500'}">${letter}</span>
        </td>
        <td class="py-2.5 px-3">
          <div class="flex items-center gap-2">
            <div class="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div class="h-full bg-cyan-500" style="width: ${pct}%"></div>
            </div>
            <span class="text-[11px] text-slate-400 font-mono">${pct}%</span>
          </div>
        </td>
        <td class="py-2.5 px-3 text-slate-400 max-w-xs text-[11px]">${meta.clinical_meaning}</td>
      </tr>
    `;
  });

  tbody.innerHTML = rows.join("");
}

function filterAUTable() {
  const query = (document.getElementById("au-search").value || "").toLowerCase();
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

  countEl.textContent = `${batchFiles.length} foto terpilih`;
  btnProcess.disabled = batchFiles.length === 0;
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

  btnProcess.disabled = true;
  btnDownload.disabled = true;
  progContainer.classList.remove("hidden");
  batchResults = [];
  tbody.innerHTML = "";

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
      console.error("Batch file error:", file.name, e);
    }

    const pct = Math.round(((i + 1) / batchFiles.length) * 100);
    progBar.style.width = pct + "%";
    progPct.textContent = pct + "%";
    progText.textContent = `Memproses ${i + 1} / ${batchFiles.length}...`;
  }

  btnProcess.disabled = false;
  btnDownload.disabled = batchResults.length === 0;
  progText.textContent = `Selesai! Berhasil memproses ${batchResults.length} foto.`;
}

function appendBatchRow(item) {
  const tbody = document.getElementById("batch-table-body");
  const dass = item.dass_clinical_assessment || { depression: {}, anxiety: {}, stress: {} };
  const emo = item.emotions || {};

  const tr = document.createElement("tr");
  tr.className = "hover:bg-slate-800/40 transition";
  tr.innerHTML = `
    <td class="py-2.5 px-3 font-semibold text-slate-200 truncate max-w-[140px]">${item.image_name}</td>
    <td class="py-2.5 px-3 text-center">
      <span class="px-2 py-0.5 rounded text-[11px] ${item.face_detected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}">${item.face_detected ? 'Ya' : 'Tidak'}</span>
    </td>
    <td class="py-2.5 px-3">
      <span class="px-2 py-0.5 rounded text-[11px] ${getBadgeClass(item.distress_level)}">${item.distress_level}</span>
    </td>
    <td class="py-2.5 px-3">
      <span class="px-2 py-0.5 rounded text-[11px] ${getBadgeClass(dass.depression.level)}">${dass.depression.level || '-'}</span>
      <span class="text-slate-500 text-[10px] ml-1">(${Math.round((dass.depression.score || 0) * 100)}%)</span>
    </td>
    <td class="py-2.5 px-3">
      <span class="px-2 py-0.5 rounded text-[11px] ${getBadgeClass(dass.anxiety.level)}">${dass.anxiety.level || '-'}</span>
      <span class="text-slate-500 text-[10px] ml-1">(${Math.round((dass.anxiety.score || 0) * 100)}%)</span>
    </td>
    <td class="py-2.5 px-3">
      <span class="px-2 py-0.5 rounded text-[11px] ${getBadgeClass(dass.stress.level)}">${dass.stress.level || '-'}</span>
      <span class="text-slate-500 text-[10px] ml-1">(${Math.round((dass.stress.score || 0) * 100)}%)</span>
    </td>
    <td class="py-2.5 px-3 font-mono text-[11px] text-slate-400">${emo.valence !== undefined ? emo.valence.toFixed(2) : '-'}</td>
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
  link.setAttribute("download", `batch_dass_summary_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
