const LOCAL_MODE = document.body.dataset.localMode === 'true';

// ── Tab switching ──────────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).style.display = 'block';
  });
});

// ── Shared helpers ─────────────────────────────────────────────────────────

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtSize(bytes) {
  return bytes > 1048576
    ? (bytes / 1048576).toFixed(1) + ' MB'
    : (bytes / 1024).toFixed(0) + ' KB';
}

function showSuccess(resultEl, title, sub) {
  resultEl.innerHTML = `
    <div class="success-overlay visible">
      <svg viewBox="0 0 52 52" width="44" height="44">
        <circle class="checkmark-circle" cx="26" cy="26" r="25"/>
        <polyline class="checkmark-check" points="14,26 22,34 38,18"/>
      </svg>
      <div class="success-text">${title}</div>
      <div class="success-path">${sub}</div>
    </div>`;
}

function showError(resultEl, msg) {
  resultEl.innerHTML = `<div class="result-box err">Fehler: ${esc(msg)}</div>`;
}

// Folder picker (local only)
async function pickFolder(textEl, rowEl) {
  const btn = rowEl.querySelector('.pick-btn');
  btn.textContent = '…';
  btn.disabled = true;
  try {
    const r = await fetch('/pick-folder');
    const d = await r.json();
    if (d.path) {
      textEl.dataset.path = d.path;
      textEl.textContent = d.path;
      textEl.classList.remove('placeholder');
    }
  } catch (_) {}
  btn.textContent = 'Auswählen…';
  btn.disabled = false;
}

// File list renderer (no reorder for HEIC, reorder optional via param)
function makeFileList({ files, listSection, listLabel, listItems, newIndices = [], reorderable = false, onRemove, onReorder }) {
  if (!files.length) { listSection.style.display = 'none'; return; }
  listSection.style.display = 'block';
  listLabel.textContent = files.length + ' Datei' + (files.length !== 1 ? 'en' : '');
  listItems.innerHTML = '';

  let dragSrc = null;

  files.forEach((f, i) => {
    const el = document.createElement('div');
    el.className = 'file-item' + (newIndices.includes(i) ? ' valid' : '');
    el.draggable = reorderable;
    el.innerHTML = `
      ${reorderable ? '<span class="handle">⠿</span>' : ''}
      <span class="num">${i + 1}</span>
      <span class="fname" title="${esc(f.name)}">${esc(f.name)}</span>
      <span class="fsize">${fmtSize(f.size)}</span>
      <button class="rm" data-i="${i}">×</button>`;

    el.querySelector('.rm').addEventListener('click', e => {
      e.stopPropagation();
      onRemove(+e.target.dataset.i);
    });

    if (reorderable) {
      el.addEventListener('dragstart', e => {
        dragSrc = i; el.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
      });
      el.addEventListener('dragend', () => {
        dragSrc = null; el.classList.remove('dragging');
        listItems.querySelectorAll('.file-item').forEach(x => x.classList.remove('drop-target'));
      });
      el.addEventListener('dragover', e => {
        e.preventDefault(); e.stopPropagation();
        listItems.querySelectorAll('.file-item').forEach(x => x.classList.remove('drop-target'));
        if (dragSrc !== null && dragSrc !== i) el.classList.add('drop-target');
      });
      el.addEventListener('drop', e => {
        e.preventDefault(); e.stopPropagation();
        if (dragSrc !== null && dragSrc !== i) onReorder(dragSrc, i);
      });
    }

    listItems.appendChild(el);
  });
}

// ── PDF Tab ────────────────────────────────────────────────────────────────

(function() {
  const files = [];
  let selectedFolder = null;
  let innerDrag = false;

  const dz       = document.getElementById('pdf-dz');
  const fi       = document.getElementById('pdf-fi');
  const listSec  = document.getElementById('pdf-listSection');
  const listLbl  = document.getElementById('pdf-listLabel');
  const listEl   = document.getElementById('pdf-listItems');
  const resultEl = document.getElementById('pdf-result');
  const mergeBtn = document.getElementById('pdf-mergeBtn');

  document.getElementById('pdf-pickBtn').addEventListener('click', () => fi.click());

  dz.addEventListener('dragenter', e => e.preventDefault());
  dz.addEventListener('dragover', e => { e.preventDefault(); if (!innerDrag) dz.classList.add('over'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('over'));
  dz.addEventListener('drop', e => {
    e.preventDefault(); dz.classList.remove('over');
    if (innerDrag) return;
    addFiles(Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.pdf')));
  });
  fi.addEventListener('change', () => { addFiles(Array.from(fi.files)); fi.value = ''; });

  function addFiles(newFiles) {
    const fresh = [];
    for (const f of newFiles) {
      if (!files.some(x => x.name === f.name && x.size === f.size)) {
        fresh.push(files.length);
        files.push(f);
      }
    }
    render(fresh);
  }

  function render(newIndices = []) {
    innerDrag = false;
    makeFileList({
      files, listSection: listSec, listLabel: listLbl, listItems: listEl,
      newIndices, reorderable: true,
      onRemove: i => { files.splice(i, 1); render(); },
      onReorder: (src, dst) => {
        const moved = files.splice(src, 1)[0];
        files.splice(dst, 0, moved);
        innerDrag = false;
        render();
      }
    });
    // track when internal drag starts so drop zone ignores it
    listEl.querySelectorAll('.file-item').forEach(el => {
      el.addEventListener('dragstart', () => { innerDrag = true; });
      el.addEventListener('dragend',   () => { innerDrag = false; });
    });
  }

  if (LOCAL_MODE) {
    document.querySelectorAll('input[name="pdf-out"]').forEach(r => {
      r.addEventListener('change', () => {
        document.getElementById('pdf-customPathRow').classList.toggle('visible', r.value === 'custom');
      });
    });
    document.getElementById('pdf-folderPickBtn').addEventListener('click', () => {
      pickFolder(document.getElementById('pdf-customPathText'), document.getElementById('pdf-customPathRow'));
    });
  }

  mergeBtn.addEventListener('click', async () => {
    if (!files.length) { alert('Bitte mindestens eine PDF-Datei hinzufügen.'); return; }
    if (LOCAL_MODE) {
      const type = document.querySelector('input[name="pdf-out"]:checked').value;
      if (type === 'custom' && !document.getElementById('pdf-customPathText').dataset.path) {
        alert('Bitte zuerst einen Ausgabeordner auswählen.'); return;
      }
    }
    mergeBtn.disabled = true;
    mergeBtn.innerHTML = '<div class="spinner"></div> Verarbeite…';
    resultEl.innerHTML = '';

    const filename = document.getElementById('pdf-fname').value.trim() || 'Zusammengeführt';
    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    fd.append('filename', filename);
    if (LOCAL_MODE) {
      fd.append('output_type', document.querySelector('input[name="pdf-out"]:checked').value);
      fd.append('custom_path', document.getElementById('pdf-customPathText').dataset.path || '');
    }

    try {
      const r = await fetch('/merge', { method: 'POST', body: fd });
      if (LOCAL_MODE) {
        const d = await r.json();
        if (d.success) showSuccess(resultEl, `Fertig! <strong>${esc(d.path.split('/').pop())}</strong>`, `${esc(d.path)} · ${fmtSize(d.size)}`);
        else showError(resultEl, d.error);
      } else {
        const blob = await r.blob();
        const fn = (filename.endsWith('.pdf') ? filename : filename + '.pdf');
        triggerDownload(blob, fn);
        showSuccess(resultEl, `Fertig! <strong>${esc(fn)}</strong>`, fmtSize(blob.size));
      }
    } catch (e) { showError(resultEl, e.message); }

    mergeBtn.disabled = false;
    mergeBtn.innerHTML = 'Zusammenführen &amp; Komprimieren';
  });
})();

// ── HEIC Tab ───────────────────────────────────────────────────────────────

(function() {
  const files = [];
  let selectedFolder = null;

  const dz        = document.getElementById('heic-dz');
  const fi        = document.getElementById('heic-fi');
  const listSec   = document.getElementById('heic-listSection');
  const listLbl   = document.getElementById('heic-listLabel');
  const listEl    = document.getElementById('heic-listItems');
  const resultEl  = document.getElementById('heic-result');
  const convertBtn = document.getElementById('heic-convertBtn');
  const qualSlider = document.getElementById('heic-quality');
  const qualVal    = document.getElementById('heic-qualityVal');

  qualSlider.addEventListener('input', () => { qualVal.textContent = qualSlider.value + ' %'; });

  document.getElementById('heic-pickBtn').addEventListener('click', () => fi.click());

  dz.addEventListener('dragenter', e => e.preventDefault());
  dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('over'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('over'));
  dz.addEventListener('drop', e => {
    e.preventDefault(); dz.classList.remove('over');
    addFiles(Array.from(e.dataTransfer.files).filter(f => /\.(heic|heif)$/i.test(f.name)));
  });
  fi.addEventListener('change', () => { addFiles(Array.from(fi.files)); fi.value = ''; });

  function addFiles(newFiles) {
    const fresh = [];
    for (const f of newFiles) {
      if (!files.some(x => x.name === f.name && x.size === f.size)) {
        fresh.push(files.length);
        files.push(f);
      }
    }
    render(fresh);
  }

  function render(newIndices = []) {
    makeFileList({
      files, listSection: listSec, listLabel: listLbl, listItems: listEl,
      newIndices, reorderable: false,
      onRemove: i => { files.splice(i, 1); render(); }
    });
  }

  if (LOCAL_MODE) {
    document.querySelectorAll('input[name="heic-out"]').forEach(r => {
      r.addEventListener('change', () => {
        document.getElementById('heic-customPathRow').classList.toggle('visible', r.value === 'custom');
      });
    });
    document.getElementById('heic-folderPickBtn').addEventListener('click', () => {
      pickFolder(document.getElementById('heic-customPathText'), document.getElementById('heic-customPathRow'));
    });
  }

  convertBtn.addEventListener('click', async () => {
    if (!files.length) { alert('Bitte mindestens eine HEIC-Datei hinzufügen.'); return; }
    if (LOCAL_MODE) {
      const type = document.querySelector('input[name="heic-out"]:checked').value;
      if (type === 'custom' && !document.getElementById('heic-customPathText').dataset.path) {
        alert('Bitte zuerst einen Ausgabeordner auswählen.'); return;
      }
    }
    convertBtn.disabled = true;
    convertBtn.innerHTML = '<div class="spinner"></div> Konvertiere…';
    resultEl.innerHTML = '';

    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    fd.append('quality', qualSlider.value);
    if (LOCAL_MODE) {
      fd.append('output_type', document.querySelector('input[name="heic-out"]:checked').value);
      fd.append('custom_path', document.getElementById('heic-customPathText').dataset.path || '');
    }

    try {
      const r = await fetch('/convert', { method: 'POST', body: fd });
      if (LOCAL_MODE) {
        const d = await r.json();
        if (d.success) showSuccess(resultEl, `${d.count} Bild${d.count !== 1 ? 'er' : ''} konvertiert`, esc(d.folder));
        else showError(resultEl, d.error);
      } else {
        const blob = await r.blob();
        const fn = files.length === 1
          ? files[0].name.replace(/\.(heic|heif)$/i, '.jpg')
          : 'bilder.zip';
        triggerDownload(blob, fn);
        showSuccess(resultEl, `${files.length} Bild${files.length !== 1 ? 'er' : ''} konvertiert`, fmtSize(blob.size));
      }
    } catch (e) { showError(resultEl, e.message); }

    convertBtn.disabled = false;
    convertBtn.innerHTML = 'Zu JPEG konvertieren';
  });
})();

// ── Shared download helper ─────────────────────────────────────────────────

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
