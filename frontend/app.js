// ── State ─────────────────────────────────────────────────────────────────────
let termine = [];
let ministranten = [];
let selectedTerminId = null;
let editingTerminId = null;

// ── Utils ─────────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ── API ───────────────────────────────────────────────────────────────────────
const api = {
  async get(path) {
    const r = await fetch(path);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async put(path, body) {
    const r = await fetch(path, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
  async delete(path) {
    const r = await fetch(path, { method: "DELETE" });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },
};

// ── Data loading ──────────────────────────────────────────────────────────────
async function loadAll() {
  [termine, ministranten] = await Promise.all([
    api.get("/termine"),
    api.get("/ministranten"),
  ]);
  renderTermine();
  renderPool();
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function renderTermine() {
  const container = document.getElementById("termine-list");
  container.innerHTML = "";

  termine.forEach(t => {
    const div = document.createElement("div");
    div.className = "termin-row" + (t.id === selectedTerminId ? " selected" : "");
    div.onclick = () => selectTermin(t.id);

    const assignedCount = t.zuteilungen.length;
    const missing = t.anzahl_benoetigt - assignedCount;
    const dateStr = new Date(t.datum + "T00:00:00").toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
    const titleStr = `${t.wochentag}, ${dateStr}`;
    const timeStr = t.uhrzeit + (t.priester ? ` · ${escapeHtml(t.priester)}` : "");

    let chipsHtml = t.zuteilungen.map(z => `
      <span class="chip">
        ${escapeHtml(z.name)}
        <span class="remove" onclick="event.stopPropagation(); removeZuteilung(${t.id}, ${z.ministrant_id})">✕</span>
      </span>`).join("");

    if (missing > 0) {
      chipsHtml += `<span class="chip-missing">+ ${missing} fehlen</span>`;
      chipsHtml += `<button class="btn-auto" onclick="event.stopPropagation(); doAutoAssign(${t.id})">⚡ Automatisch zuweisen</button>`;
    }

    div.innerHTML = `
      <div class="termin-meta">
        <div>
          <span class="termin-title">${titleStr}</span>
          <span class="termin-time">${timeStr}</span>
          ${t.ereignis ? `<span class="termin-badge">${escapeHtml(t.ereignis)}</span>` : ""}
        </div>
        <div class="termin-actions">
          <span class="termin-count">${assignedCount}/${t.anzahl_benoetigt}</span>
          <button class="btn-ghost" onclick="event.stopPropagation(); openTerminModal(${t.id})">✏️</button>
          <button class="btn-danger" onclick="event.stopPropagation(); deleteTermin(${t.id})">🗑</button>
        </div>
      </div>
      <div class="termin-chips">${chipsHtml}</div>`;
    container.appendChild(div);
  });

  const hint = document.createElement("div");
  hint.className = "add-hint";
  hint.textContent = "+ Termin hinzufügen";
  hint.onclick = () => openTerminModal();
  container.appendChild(hint);
}

function renderPool() {
  const container = document.getElementById("pool-list");
  container.innerHTML = `<div class="pool-label">Nach Diensten sortiert</div>`;

  const active = ministranten.filter(m => m.aktiv).sort((a, b) => a.anzahl_zuteilungen - b.anzahl_zuteilungen);
  const inactive = ministranten.filter(m => !m.aktiv);

  [...active, ...inactive].forEach(m => {
    const div = document.createElement("div");
    div.className = "pool-person" + (!m.aktiv ? " inactive" : "");
    div.onclick = () => m.aktiv && addZuteilungFromPool(m.id);
    div.innerHTML = `
      <span class="name">${escapeHtml(m.name)}</span>
      <div style="display:flex;gap:6px;align-items:center">
        <span class="count">${m.anzahl_zuteilungen} ×</span>
        <button class="btn-ghost" style="font-size:11px" onclick="event.stopPropagation(); toggleAktiv(${m.id}, ${!m.aktiv})">${m.aktiv ? "⏸" : "▶"}</button>
        <button class="btn-danger" onclick="event.stopPropagation(); deleteMinistrant(${m.id})">✕</button>
      </div>`;
    container.appendChild(div);
  });
}

// ── Actions ───────────────────────────────────────────────────────────────────
function selectTermin(id) {
  selectedTerminId = id;
  renderTermine();
}

async function doAutoAssign(terminId) {
  const updated = await api.post(`/termine/${terminId}/auto-assign`, {});
  termine = termine.map(t => t.id === terminId ? updated : t);
  ministranten = await api.get("/ministranten");
  renderTermine();
  renderPool();
}

async function autoAssignAll() {
  const unfinished = termine.filter(t => t.zuteilungen.length < t.anzahl_benoetigt);
  for (const t of unfinished) {
    await api.post(`/termine/${t.id}/auto-assign`, {});
  }
  await loadAll();
}

async function addZuteilungFromPool(ministrantId) {
  if (!selectedTerminId) return;
  const updated = await api.post(`/termine/${selectedTerminId}/zuteilung`, { ministrant_id: ministrantId });
  termine = termine.map(t => t.id === selectedTerminId ? updated : t);
  ministranten = await api.get("/ministranten");
  renderTermine();
  renderPool();
}

async function removeZuteilung(terminId, ministrantId) {
  const updated = await api.delete(`/termine/${terminId}/zuteilung/${ministrantId}`);
  termine = termine.map(t => t.id === terminId ? updated : t);
  ministranten = await api.get("/ministranten");
  renderTermine();
  renderPool();
}

async function deleteTermin(id) {
  if (!confirm("Termin wirklich löschen?")) return;
  await api.delete(`/termine/${id}`);
  if (selectedTerminId === id) selectedTerminId = null;
  await loadAll();
}

async function deleteMinistrant(id) {
  if (!confirm("Person wirklich löschen?")) return;
  await api.delete(`/ministranten/${id}`);
  await loadAll();
}

async function toggleAktiv(id, aktiv) {
  await api.put(`/ministranten/${id}`, { aktiv });
  ministranten = await api.get("/ministranten");
  renderPool();
}

// ── Termin Modal ──────────────────────────────────────────────────────────────
function openTerminModal(terminId = null) {
  editingTerminId = terminId;
  const t = terminId ? termine.find(x => x.id === terminId) : null;
  document.getElementById("termin-modal-title").textContent = t ? "Termin bearbeiten" : "Termin hinzufügen";
  document.getElementById("t-datum").value = t ? t.datum : "";
  document.getElementById("t-uhrzeit").value = t ? t.uhrzeit : "";
  document.getElementById("t-priester").value = t ? (t.priester || "") : "";
  document.getElementById("t-ereignis").value = t ? (t.ereignis || "") : "";
  document.getElementById("t-anzahl").value = t ? t.anzahl_benoetigt : 2;
  document.getElementById("termin-modal").classList.remove("hidden");
}

function closeTerminModal() {
  document.getElementById("termin-modal").classList.add("hidden");
  editingTerminId = null;
}

async function saveTermin() {
  const body = {
    datum: document.getElementById("t-datum").value,
    uhrzeit: document.getElementById("t-uhrzeit").value,
    priester: document.getElementById("t-priester").value || null,
    ereignis: document.getElementById("t-ereignis").value || null,
    anzahl_benoetigt: parseInt(document.getElementById("t-anzahl").value),
  };
  if (!body.datum || !body.uhrzeit) return alert("Datum und Uhrzeit sind Pflichtfelder.");
  if (editingTerminId) {
    await api.put(`/termine/${editingTerminId}`, body);
  } else {
    await api.post("/termine", body);
  }
  closeTerminModal();
  await loadAll();
}

// ── Pool Modal ────────────────────────────────────────────────────────────────
function openPoolModal() {
  document.getElementById("p-name").value = "";
  document.getElementById("p-alter").value = "";
  document.getElementById("pool-modal").classList.remove("hidden");
}

function closePoolModal() {
  document.getElementById("pool-modal").classList.add("hidden");
}

async function savePool() {
  const name = document.getElementById("p-name").value.trim();
  if (!name) return alert("Name darf nicht leer sein.");
  const alterVal = document.getElementById("p-alter").value;
  const body = { name, aktiv: true };
  if (alterVal) body.alter = parseInt(alterVal);
  await api.post("/ministranten", body);
  closePoolModal();
  ministranten = await api.get("/ministranten");
  renderPool();
}

// ── Export ────────────────────────────────────────────────────────────────────
function exportDocx() {
  window.location.href = "/export/docx";
}

// ── Close modals on overlay click ─────────────────────────────────────────────
document.getElementById("termin-modal").addEventListener("click", e => {
  if (e.target === e.currentTarget) closeTerminModal();
});
document.getElementById("pool-modal").addEventListener("click", e => {
  if (e.target === e.currentTarget) closePoolModal();
});

// ── Init ──────────────────────────────────────────────────────────────────────
loadAll();
