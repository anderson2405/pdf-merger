const LOCAL_MODE = document.body.dataset.localMode === 'true';

let files = [];
let dragSrc = null;
let selectedFolder = null;

const dz = document.getElementById('dz');
const fi = document.getElementById('fi');

document.getElementById('pickBtn').addEventListener('click', () => fi.click());

dz.addEventListener('dragenter', e => e.preventDefault());
dz.addEventListener('dragover', e => {
  e.preventDefault();
  if (dragSrc === null) dz.classList.add('over');
});
dz.addEventListener('dragleave', () => dz.classList.remove('over'));
dz.addEventListener('drop', e => {
  e.preventDefault();
  dz.classList.remove('over');
  if (dragSrc !== null) return;
  addFiles(Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.pdf')));
});

fi.addEventListener('change', () => { addFiles(Array.from(fi.files)); fi.value = ''; });

function addFiles(newFiles) {
  const freshIndices = [];
  for (const f of newFiles) {
    if (!files.some(x => x.name === f.name && x.size === f.size)) {
      freshIndices.push(files.length);
      files.push(f);
    }
  }
  render(freshIndices);
}

function render(newIndices = []) {
  const sec  = document.getElementById('listSection');
  const lbl  = document.getElementById('listLabel');
  const list = document.getElementById('listItems');

  if (!files.length) { sec.style.display = 'none'; return; }

  sec.style.display = 'block';
  lbl.textContent = files.length + ' Datei' + (files.length !== 1 ? 'en' : '');
  list.innerHTML = '';

  files.forEach((f, i) => {
    const size = f.size > 1048576
      ? (f.size / 1048576).toFixed(1) + ' MB'
      : (f.size / 1024).toFixed(0) + ' KB';

    const el = document.createElement('div');
    el.className = 'file-item' + (newIndices.includes(i) ? ' valid' : '');
    el.draggable = true;
    el.innerHTML = `
      <span class="handle">⠿</span>
      <span class="num">${i + 1}</span>
      <span class="fname" title="${esc(f.name)}">${esc(f.name)}</span>
      <span class="fsize">${size}</span>
      <button class="rm" data-i="${i}">×</button>`;

    el.querySelector('.rm').addEventListener('click', e => {
      e.stopPropagation();
      files.splice(+e.target.dataset.i, 1);
      render();
    });

    el.addEventListener('dragstart', e => {
      dragSrc = i;
      el.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    });
    el.addEventListener('dragend', () => {
      dragSrc = null;
      el.classList.remove('dragging');
      document.querySelectorAll('.file-item').forEach(x => x.classList.remove('drop-target'));
    });
    el.addEventListener('dragover', e => {
      e.preventDefault();
      e.stopPropagation();
      document.querySelectorAll('.file-item').forEach(x => x.classList.remove('drop-target'));
      if (dragSrc !== null && dragSrc !== i) el.classList.add('drop-target');
    });
    el.addEventListener('drop', e => {
      e.preventDefault();
      e.stopPropagation();
      if (dragSrc !== null && dragSrc !== i) {
        const moved = files.splice(dragSrc, 1)[0];
        files.splice(i, 0, moved);
        render();
      }
    });

    list.appendChild(el);
  });
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Output folder (local only)
if (LOCAL_MODE) {
  document.querySelectorAll('input[name=out]').forEach(r => {
    r.addEventListener('change', () => {
      document.getElementById('customPathRow').classList.toggle('visible', r.value === 'custom');
    });
  });

  document.getElementById('folderPickBtn').addEventListener('click', async () => {
    const btn = document.getElementById('folderPickBtn');
    btn.textContent = '…';
    btn.disabled = true;
    try {
      const r = await fetch('/pick-folder');
      const d = await r.json();
      if (d.path) {
        selectedFolder = d.path;
        const txt = document.getElementById('customPathText');
        txt.textContent = d.path;
        txt.classList.remove('placeholder');
      }
    } catch (_) {}
    btn.textContent = 'Auswählen…';
    btn.disabled = false;
  });
}

// Merge
document.getElementById('mergeBtn').addEventListener('click', async () => {
  if (!files.length) { alert('Bitte mindestens eine PDF-Datei hinzufügen.'); return; }

  if (LOCAL_MODE) {
    const outputType = document.querySelector('input[name=out]:checked').value;
    if (outputType === 'custom' && !selectedFolder) {
      alert('Bitte zuerst einen Ausgabeordner auswählen.');
      return;
    }
  }

  const btn = document.getElementById('mergeBtn');
  const resultEl = document.getElementById('result');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Verarbeite…';
  resultEl.innerHTML = '';

  const filename = (document.getElementById('fname').value.trim() || 'Zusammengeführt');
  const fd = new FormData();
  files.forEach(f => fd.append('files', f));
  fd.append('filename', filename);

  if (LOCAL_MODE) {
    fd.append('output_type', document.querySelector('input[name=out]:checked').value);
    fd.append('custom_path', selectedFolder || '');
  }

  try {
    const r = await fetch('/merge', { method: 'POST', body: fd });

    if (LOCAL_MODE) {
      const d = await r.json();
      if (d.success) {
        const sz = d.size > 1048576 ? (d.size/1048576).toFixed(1)+' MB' : (d.size/1024).toFixed(0)+' KB';
        showSuccess(d.path.split('/').pop(), d.path, sz);
      } else {
        resultEl.innerHTML = `<div class="result-box err">Fehler: ${esc(d.error)}</div>`;
      }
    } else {
      // Online: trigger browser download
      const blob = await r.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = filename.endsWith('.pdf') ? filename : filename + '.pdf';
      a.click();
      URL.revokeObjectURL(url);
      const sz = (blob.size / 1048576).toFixed(1) + ' MB';
      showSuccess(a.download, null, sz);
    }
  } catch (e) {
    resultEl.innerHTML = `<div class="result-box err">Fehler: ${esc(e.message)}</div>`;
  }

  btn.disabled = false;
  btn.innerHTML = 'Zusammenführen &amp; Komprimieren';
});

function showSuccess(name, path, size) {
  const resultEl = document.getElementById('result');
  const pathLine = path
    ? `<div class="success-path">${esc(path)} · ${size}</div>`
    : `<div class="success-path">${size}</div>`;
  resultEl.innerHTML = `
    <div class="success-overlay visible">
      <svg viewBox="0 0 52 52" width="44" height="44">
        <circle class="checkmark-circle" cx="26" cy="26" r="25"/>
        <polyline class="checkmark-check" points="14,26 22,34 38,18"/>
      </svg>
      <div class="success-text">Fertig! <strong>${esc(name)}</strong></div>
      ${pathLine}
    </div>`;
}
