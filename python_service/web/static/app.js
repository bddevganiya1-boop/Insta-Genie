// Insta Genie Client-Side Automation Controller

let currentDraft = null;

document.addEventListener("DOMContentLoaded", () => {
  initSystem();
  setupEventListeners();
});

// -----------------------------------------------------------------------------
// System Initialization
// -----------------------------------------------------------------------------
async function initSystem() {
  addLog("Initializing Insta Genie Agent UI...", "info");
  
  try {
    const [statusRes, accountRes, schedRes] = await Promise.all([
      fetch("/api/status").then(r => r.json()),
      fetch("/api/account").then(r => r.json()).catch(() => null),
      fetch("/api/scheduler").then(r => r.json()).catch(() => null)
    ]);

    // Update connection status
    const statusPill = document.getElementById("connection-status");
    const statusLabel = statusPill.querySelector(".status-label");
    
    if (statusRes.dry_run) {
      statusPill.className = "status-pill online";
      statusLabel.textContent = "Safe Mock Mode (Active)";
      addLog("System running in DRY_RUN safe testing mode.", "warning");
    } else {
      statusPill.className = "status-pill online";
      statusLabel.textContent = "Live Connected";
      addLog("System connected to live Meta Graph API & Cloudflare.", "success");
    }

    // Update account card
    if (accountRes) {
      document.getElementById("account-username").textContent = `@${accountRes.username || 'instagenie_demo'}`;
      document.getElementById("account-followers").textContent = `${Number(accountRes.followers_count || 14200).toLocaleString()} followers`;
      document.getElementById("ig-preview-handle").textContent = accountRes.username || 'instagenie_demo';
      document.getElementById("ig-caption-handle").textContent = accountRes.username || 'instagenie_demo';
      if (accountRes.profile_picture_url) {
        document.getElementById("account-avatar").src = accountRes.profile_picture_url;
        document.getElementById("ig-preview-avatar").src = accountRes.profile_picture_url;
      }
    }

    // Update Scheduler UI
    if (schedRes) {
      updateSchedulerUI(schedRes);
    }

  } catch (err) {
    addLog(`System check error: ${err.message}`, "error");
  }
}

// -----------------------------------------------------------------------------
// Event Handlers
// -----------------------------------------------------------------------------
function setupEventListeners() {
  // Topic Chips
  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const cleanTopic = chip.textContent.replace(/^[^\w]+/, "").trim();
      document.getElementById("topic-input").value = cleanTopic;
      chip.style.transform = "scale(0.95)";
      setTimeout(() => chip.style.transform = "", 150);
    });
  });

  // Buttons
  document.getElementById("btn-generate-draft").addEventListener("click", handleGenerateDraft);
  document.getElementById("btn-1click-publish").addEventListener("click", handle1ClickPublish);
  document.getElementById("btn-publish-draft").addEventListener("click", handlePublishCurrentDraft);
  document.getElementById("btn-copy-caption").addEventListener("click", handleCopyCaption);
  document.getElementById("btn-clear-logs").addEventListener("click", () => {
    document.getElementById("terminal-logs").innerHTML = "";
  });

  // Scheduler Switch
  document.getElementById("scheduler-toggle").addEventListener("change", handleToggleScheduler);
}

// -----------------------------------------------------------------------------
// Draft Generation Flow
// -----------------------------------------------------------------------------
async function handleGenerateDraft() {
  const topicInput = document.getElementById("topic-input");
  const topic = topicInput.value.trim();
  const tone = document.getElementById("tone-select").value;

  if (!topic) {
    alert("Please enter a post topic or click one of the quick suggestions.");
    topicInput.focus();
    return;
  }

  showLoader(true, "Drafting copy with Llama 3 & rendering 8K artwork with FLUX.1...");
  addLog(`[AGENT] Drafting content for topic: "${topic}"...`, "info");

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, tone })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Generation failed");
    }

    const data = await res.json();
    currentDraft = data;

    // Update UI elements
    renderPreview(data);
    document.getElementById("btn-publish-draft").style.display = "inline-flex";
    document.getElementById("publication-banner").style.display = "none";

    addLog(`[WORKERS_AI] Generated copy & image successfully in ${data.elapsed_seconds}s!`, "success");

  } catch (err) {
    addLog(`[ERROR] Generation error: ${err.message}`, "error");
    alert(`Generation Error: ${err.message}`);
  } finally {
    showLoader(false);
  }
}

// -----------------------------------------------------------------------------
// 1-Click Autonomous Flow
// -----------------------------------------------------------------------------
async function handle1ClickPublish() {
  const topicInput = document.getElementById("topic-input");
  const topic = topicInput.value.trim();
  const tone = document.getElementById("tone-select").value;

  if (!topic) {
    alert("Please enter a post topic first.");
    topicInput.focus();
    return;
  }

  showLoader(true, "Autonomous Cycle: Generating AI assets & publishing to Instagram...");
  addLog(`[PIPELINE] Starting end-to-end publishing cycle for: "${topic}"`, "info");

  try {
    const res = await fetch("/api/run-pipeline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, tone, auto_publish: true })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Pipeline failed");
    }

    const data = await res.json();
    addLog(`[META_GRAPH_API] Post published! ID: ${data.published?.published_media_id}`, "success");
    addLog(`[INSTAGRAM] Permalink: ${data.published?.permalink}`, "success");

    // Display banner
    showPublicationSuccess(data.published);

    // Also fetch and show draft content in preview
    if (data.draft) {
      renderPreview(data.draft);
    }

  } catch (err) {
    addLog(`[ERROR] Pipeline failed: ${err.message}`, "error");
    alert(`Publishing Error: ${err.message}`);
  } finally {
    showLoader(false);
  }
}

// -----------------------------------------------------------------------------
// Publish Current Draft
// -----------------------------------------------------------------------------
async function handlePublishCurrentDraft() {
  if (!currentDraft) return;

  showLoader(true, "Publishing draft directly to Instagram...");
  addLog("[META_GRAPH_API] Uploading image and creating media container...", "info");

  try {
    const res = await fetch("/api/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        caption: currentDraft.full_caption,
        image_base64: currentDraft.image_base64
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Publish failed");
    }

    const result = await res.json();
    addLog(`[SUCCESS] Published to Instagram! ID: ${result.published_media_id}`, "success");
    showPublicationSuccess(result);

  } catch (err) {
    addLog(`[ERROR] Publish draft failed: ${err.message}`, "error");
    alert(`Publish Error: ${err.message}`);
  } finally {
    showLoader(false);
  }
}

// -----------------------------------------------------------------------------
// Scheduler Control
// -----------------------------------------------------------------------------
async function handleToggleScheduler(e) {
  const enabled = e.target.checked;
  addLog(`[SCHEDULER] Toggling autopilot to: ${enabled ? 'ENABLED' : 'DISABLED'}`, "info");

  try {
    const res = await fetch("/api/scheduler/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled, interval_hours: 6 })
    });
    const data = await res.json();
    updateSchedulerUI(data);
    addLog(`[SCHEDULER] Autopilot is now ${data.is_running ? 'ACTIVE' : 'STOPPED'}`, "success");
  } catch (err) {
    addLog(`[ERROR] Scheduler update failed: ${err.message}`, "error");
  }
}

function updateSchedulerUI(sched) {
  document.getElementById("scheduler-toggle").checked = sched.is_running;
  document.getElementById("sched-status").textContent = sched.is_running ? "Active (Every 6h)" : "Inactive";
  document.getElementById("sched-status").style.color = sched.is_running ? "#10b981" : "#94a3b8";
  document.getElementById("sched-next").textContent = sched.next_run_time ? new Date(sched.next_run_time).toLocaleTimeString() : "--";
}

// -----------------------------------------------------------------------------
// UI Utilities
// -----------------------------------------------------------------------------
function renderPreview(data) {
  if (data.image_base64) {
    document.getElementById("ig-post-image").src = data.image_base64;
  }
  document.getElementById("ig-caption-hook").textContent = data.hook || "";
  document.getElementById("ig-caption-body").textContent = data.body || "";

  // Hashtags
  const tagsContainer = document.getElementById("ig-hashtags");
  tagsContainer.innerHTML = "";
  (data.hashtags || []).forEach(tag => {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = tag.startsWith("#") ? tag : `#${tag}`;
    tagsContainer.appendChild(span);
  });
}

function showPublicationSuccess(published) {
  const banner = document.getElementById("publication-banner");
  document.getElementById("pub-id").textContent = published.published_media_id || "18029384729182391";
  const link = document.getElementById("pub-link");
  link.href = published.permalink || "https://instagram.com";
  banner.style.display = "flex";
}

function showLoader(visible, text = "") {
  const loader = document.getElementById("image-loader");
  if (text) {
    loader.querySelector("p").textContent = text;
  }
  loader.style.display = visible ? "flex" : "none";
}

function handleCopyCaption() {
  if (!currentDraft && !document.getElementById("ig-caption-body").textContent) {
    alert("Generate a post first to copy its caption!");
    return;
  }
  const fullText = currentDraft?.full_caption || 
    `${document.getElementById("ig-caption-hook").textContent}\n\n${document.getElementById("ig-caption-body").textContent}`;
  
  navigator.clipboard.writeText(fullText).then(() => {
    const btn = document.getElementById("btn-copy-caption");
    const oldText = btn.textContent;
    btn.textContent = "✓ Copied!";
    setTimeout(() => btn.textContent = oldText, 2000);
  });
}

function addLog(message, type = "info") {
  const terminal = document.getElementById("terminal-logs");
  const now = new Date().toTimeString().split(" ")[0];
  const div = document.createElement("div");
  div.className = `log-line ${type}`;
  div.textContent = `[${now}] ${message}`;
  terminal.appendChild(div);
  terminal.scrollTop = terminal.scrollHeight;
}
