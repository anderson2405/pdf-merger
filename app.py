#!/usr/bin/env python3
import os
import subprocess
import tempfile
import threading
import webbrowser
from pathlib import Path
from flask import Flask, request, jsonify

app = Flask(__name__)

GS_PATH = subprocess.run(['which', 'gs'], capture_output=True, text=True).stdout.strip() or 'gs'

HTML = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PDF Merger</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: #f2f2f7;
    min-height: 100vh;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 48px 16px;
  }

  .card {
    background: #fff;
    border-radius: 14px;
    padding: 32px;
    width: 100%;
    max-width: 500px;
    box-shadow: 0 1px 4px rgba(0,0,0,.08), 0 4px 24px rgba(0,0,0,.04);
  }

  h1 { font-size: 18px; font-weight: 600; color: #111; letter-spacing: -.3px; }
  .subtitle { font-size: 13px; color: #999; margin-top: 4px; margin-bottom: 24px; }

  /* Drop zone */
  .drop-zone {
    border: 1.5px dashed #d0d0d0;
    border-radius: 10px;
    padding: 36px 20px;
    text-align: center;
    cursor: pointer;
    transition: border-color .15s, background .15s;
  }
  .drop-zone:hover, .drop-zone.over { border-color: #555; background: #fafafa; }
  .drop-icon { font-size: 28px; margin-bottom: 8px; }
  .drop-text { font-size: 14px; color: #666; line-height: 1.5; }
  .drop-text b { color: #111; font-weight: 500; text-decoration: underline; cursor: pointer; }
  input[type=file] { display: none; }

  /* File list */
  .section { margin-top: 20px; }
  .label { font-size: 11px; font-weight: 600; color: #aaa; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 8px; }

  .file-item {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 9px 10px;
    background: #f7f7f7;
    border-radius: 7px;
    margin-bottom: 5px;
    cursor: grab;
    user-select: none;
    transition: background .2s, border-color .2s;
    border: 1.5px solid transparent;
  }
  .file-item:hover { background: #f0f0f0; }
  .file-item.dragging { opacity: .3; }
  .file-item.drop-target { outline: 2px solid #555; outline-offset: -2px; }
  .file-item.valid {
    background: #f0fdf4;
    border-color: #86efac;
  }
  .file-item.valid .fname { color: #166534; }
  .file-item.valid .num { color: #4ade80; }
  .file-item.valid .fsize { color: #86efac; }
  .file-item.valid .handle { color: #86efac; }

  .handle { color: #ccc; font-size: 14px; flex-shrink: 0; }
  .num { font-size: 11px; color: #bbb; width: 14px; text-align: right; flex-shrink: 0; }
  .fname { flex: 1; font-size: 13px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .fsize { font-size: 12px; color: #bbb; flex-shrink: 0; }
  .rm { background: none; border: none; color: #ccc; font-size: 18px; cursor: pointer; line-height: 1; padding: 0 2px; flex-shrink: 0; }
  .rm:hover { color: #e44; }

  /* Output section */
  .radio-row { display: flex; align-items: center; gap: 7px; font-size: 14px; color: #333; cursor: pointer; margin-bottom: 7px; }

  .custom-path-row {
    display: none;
    align-items: center;
    gap: 8px;
    margin-top: 6px;
    padding: 9px 11px;
    background: #f7f7f7;
    border-radius: 7px;
    border: 1.5px solid #e0e0e0;
  }
  .custom-path-row.visible { display: flex; }
  .custom-path-text {
    flex: 1;
    font-size: 13px;
    color: #555;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .custom-path-text.placeholder { color: #bbb; }
  .pick-btn {
    background: none;
    border: 1px solid #d0d0d0;
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 12px;
    color: #555;
    cursor: pointer;
    font-family: inherit;
    white-space: nowrap;
    transition: background .1s, border-color .1s;
    flex-shrink: 0;
  }
  .pick-btn:hover { background: #ececec; border-color: #bbb; }

  input[type=text] {
    width: 100%;
    padding: 9px 11px;
    border: 1.5px solid #e0e0e0;
    border-radius: 7px;
    font-size: 13px;
    color: #333;
    font-family: inherit;
    outline: none;
    transition: border-color .15s;
    margin-top: 4px;
  }
  input[type=text]:focus { border-color: #555; }

  .filename-row { display: flex; align-items: center; gap: 6px; }
  .filename-row input { flex: 1; margin-top: 0; }
  .ext { font-size: 14px; color: #999; flex-shrink: 0; }

  /* Merge button */
  .btn {
    width: 100%;
    margin-top: 24px;
    padding: 13px;
    background: #111;
    color: #fff;
    border: none;
    border-radius: 9px;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
    font-family: inherit;
    transition: background .15s;
    letter-spacing: -.1px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    min-height: 50px;
  }
  .btn:hover:not(:disabled) { background: #333; }
  .btn:disabled { background: #ccc; cursor: not-allowed; }

  /* Spinner */
  .spinner {
    width: 18px;
    height: 18px;
    border: 2px solid rgba(255,255,255,.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin .6s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Result */
  .result { margin-top: 14px; }
  .result-box {
    padding: 12px 14px;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.5;
    word-break: break-all;
  }
  .result-box.err { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }

  /* Success overlay */
  .success-overlay {
    display: none;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 20px 14px;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 8px;
    text-align: center;
    animation: fadeIn .3s ease;
  }
  .success-overlay.visible { display: flex; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

  .checkmark-wrap {
    width: 44px;
    height: 44px;
  }
  .checkmark-circle {
    stroke-dasharray: 166;
    stroke-dashoffset: 166;
    stroke-width: 2;
    stroke: #16a34a;
    fill: none;
    animation: stroke .4s cubic-bezier(.65,0,.45,1) .1s forwards;
  }
  .checkmark-check {
    stroke-dasharray: 48;
    stroke-dashoffset: 48;
    stroke-width: 3;
    stroke: #16a34a;
    fill: none;
    stroke-linecap: round;
    stroke-linejoin: round;
    animation: stroke .3s cubic-bezier(.65,0,.45,1) .5s forwards;
  }
  @keyframes stroke { to { stroke-dashoffset: 0; } }

  .success-text { font-size: 14px; font-weight: 500; color: #166534; }
  .success-path { font-size: 12px; color: #4ade80; color: #15803d; word-break: break-all; }
</style>
</head>
<body>
<div class="card">
  <h1>PDF Zusammenführen</h1>
  <p class="subtitle">PDFs hinzufügen, Reihenfolge festlegen, zusammenführen und komprimieren.</p>

  <div class="drop-zone" id="dz">
    <div class="drop-icon">📄</div>
    <p class="drop-text">PDFs hier ablegen<br>oder <b id="pickBtn">Dateien auswählen</b></p>
    <input type="file" id="fi" accept=".pdf" multiple>
  </div>

  <div class="section" id="listSection" style="display:none">
    <div class="label" id="listLabel"></div>
    <div id="listItems"></div>
  </div>

  <div class="section">
    <div class="label">Ausgabeordner</div>
    <label class="radio-row">
      <input type="radio" name="out" value="downloads" checked> Downloads
    </label>
    <label class="radio-row">
      <input type="radio" name="out" value="custom"> Anderer Pfad
    </label>
    <div class="custom-path-row" id="customPathRow">
      <span class="custom-path-text placeholder" id="customPathText">Noch kein Ordner gewählt</span>
      <button class="pick-btn" id="folderPickBtn" type="button">Auswählen…</button>
    </div>
  </div>

  <div class="section">
    <div class="label">Dateiname</div>
    <div class="filename-row">
      <input type="text" id="fname" value="Zusammengeführt">
      <span class="ext">.pdf</span>
    </div>
  </div>

  <button class="btn" id="mergeBtn">Zusammenführen &amp; Komprimieren</button>

  <div id="result"></div>
</div>

<script>
  let files = [];
  let dragSrc = null;
  let selectedFolder = null;

  const dz = document.getElementById('dz');
  const fi = document.getElementById('fi');

  document.getElementById('pickBtn').addEventListener('click', () => fi.click());

  dz.addEventListener('dragenter', e => { e.preventDefault(); });
  dz.addEventListener('dragover', e => {
    e.preventDefault();
    if (dragSrc === null) dz.classList.add('over');
  });
  dz.addEventListener('dragleave', () => dz.classList.remove('over'));
  dz.addEventListener('drop', e => {
    e.preventDefault();
    dz.classList.remove('over');
    if (dragSrc !== null) return;
    const added = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
    addFiles(added);
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
    const sec = document.getElementById('listSection');
    const lbl = document.getElementById('listLabel');
    const items = document.getElementById('listItems');
    if (!files.length) { sec.style.display = 'none'; return; }

    sec.style.display = 'block';
    lbl.textContent = files.length + ' Datei' + (files.length !== 1 ? 'en' : '');
    items.innerHTML = '';

    files.forEach((f, i) => {
      const size = f.size > 1048576
        ? (f.size / 1048576).toFixed(1) + ' MB'
        : (f.size / 1024).toFixed(0) + ' KB';

      const el = document.createElement('div');
      el.className = 'file-item' + (newIndices.includes(i) ? ' valid' : '');
      el.draggable = true;
      el.dataset.i = i;
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

      items.appendChild(el);
    });
  }

  function esc(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // Output type toggle
  document.querySelectorAll('input[name=out]').forEach(r => {
    r.addEventListener('change', () => {
      const row = document.getElementById('customPathRow');
      row.classList.toggle('visible', r.value === 'custom');
    });
  });

  // Native folder picker
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
    } catch(e) { /* user cancelled */ }
    btn.textContent = 'Auswählen…';
    btn.disabled = false;
  });

  // Merge
  document.getElementById('mergeBtn').addEventListener('click', async () => {
    if (!files.length) { alert('Bitte mindestens eine PDF-Datei hinzufügen.'); return; }

    const outputType = document.querySelector('input[name=out]:checked').value;
    if (outputType === 'custom' && !selectedFolder) {
      alert('Bitte zuerst einen Ausgabeordner auswählen.');
      return;
    }

    const btn = document.getElementById('mergeBtn');
    const resultEl = document.getElementById('result');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Verarbeite…';
    resultEl.innerHTML = '';

    const fd = new FormData();
    files.forEach(f => fd.append('files', f));
    fd.append('output_type', outputType);
    fd.append('custom_path', selectedFolder || '');
    fd.append('filename', document.getElementById('fname').value.trim() || 'Zusammengeführt');

    try {
      const r = await fetch('/merge', { method: 'POST', body: fd });
      const d = await r.json();
      if (d.success) {
        const sz = d.size > 1048576 ? (d.size/1048576).toFixed(1)+' MB' : (d.size/1024).toFixed(0)+' KB';
        resultEl.innerHTML = `
          <div class="success-overlay visible">
            <div class="checkmark-wrap">
              <svg viewBox="0 0 52 52" width="44" height="44">
                <circle class="checkmark-circle" cx="26" cy="26" r="25"/>
                <polyline class="checkmark-check" points="14,26 22,34 38,18"/>
              </svg>
            </div>
            <div class="success-text">Fertig! Gespeichert als <strong>${esc(d.path.split('/').pop())}</strong></div>
            <div class="success-path">${esc(d.path)} &nbsp;·&nbsp; ${sz}</div>
          </div>`;
      } else {
        resultEl.innerHTML = `<div class="result-box err">Fehler: ${esc(d.error)}</div>`;
      }
    } catch(e) {
      resultEl.innerHTML = `<div class="result-box err">Fehler: ${esc(e.message)}</div>`;
    }

    btn.disabled = false;
    btn.innerHTML = 'Zusammenführen &amp; Komprimieren';
  });
</script>
</body>
</html>"""


@app.route('/')
def index():
    return HTML


@app.route('/pick-folder')
def pick_folder():
    script = 'POSIX path of (choose folder with prompt "Ausgabeordner wählen")'
    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    if result.returncode == 0:
        return jsonify({'path': result.stdout.strip()})
    return jsonify({'path': None})


@app.route('/merge', methods=['POST'])
def merge():
    files = request.files.getlist('files')
    output_type = request.form.get('output_type', 'downloads')
    custom_path = request.form.get('custom_path', '').strip()
    filename = request.form.get('filename', 'Zusammengeführt').strip() or 'Zusammengeführt'

    if not filename.endswith('.pdf'):
        filename += '.pdf'

    if output_type == 'downloads':
        output_dir = str(Path.home() / 'Downloads')
    else:
        output_dir = custom_path or str(Path.home() / 'Downloads')

    output_dir = os.path.expanduser(output_dir)
    if not os.path.isdir(output_dir):
        return jsonify({'success': False, 'error': f'Ordner nicht gefunden: {output_dir}'})

    output_path = os.path.join(output_dir, filename)

    with tempfile.TemporaryDirectory() as tmp:
        input_files = []
        for i, f in enumerate(files):
            path = os.path.join(tmp, f'{i:04d}_{f.filename}')
            f.save(path)
            input_files.append(path)

        if not input_files:
            return jsonify({'success': False, 'error': 'Keine Dateien empfangen.'})

        cmd = [
            GS_PATH, '-dBATCH', '-dNOPAUSE', '-dQUIET',
            '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.5',
            '-dPDFSETTINGS=/ebook',
            f'-sOutputFile={output_path}',
        ] + input_files

        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return jsonify({'success': False, 'error': result.stderr or 'Ghostscript-Fehler'})

    size = os.path.getsize(output_path)
    return jsonify({'success': True, 'path': output_path, 'size': size})


if __name__ == '__main__':
    def open_browser():
        import time
        time.sleep(0.6)
        webbrowser.open('http://localhost:7777')

    threading.Thread(target=open_browser, daemon=True).start()
    print('PDF Merger läuft → http://localhost:7777')
    app.run(port=7777, debug=False)
