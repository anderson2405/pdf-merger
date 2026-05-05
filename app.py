#!/usr/bin/env python3
import io
import os
import re
import shutil
import subprocess
import tempfile
import threading
import webbrowser
import zipfile
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_file
import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()

app = Flask(__name__)

GS_PATH = subprocess.run(['which', 'gs'], capture_output=True, text=True).stdout.strip() or 'gs'
LOCAL_MODE = os.environ.get('LOCAL_MODE', 'true').lower() == 'true'
PORT = int(os.environ.get('PORT', 7777))


@app.route('/')
def index():
    return render_template('index.html', local_mode=LOCAL_MODE)


@app.route('/impressum')
def impressum():
    return render_template('impressum.html')


@app.route('/datenschutz')
def datenschutz():
    return render_template('datenschutz.html')


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
    filename = (request.form.get('filename') or 'Zusammengeführt').strip()
    if not filename.endswith('.pdf'):
        filename += '.pdf'

    with tempfile.TemporaryDirectory() as tmp:
        input_files = []
        for i, f in enumerate(files):
            path = os.path.join(tmp, f'{i:04d}_{f.filename}')
            f.save(path)
            input_files.append(path)

        if not input_files:
            return jsonify({'success': False, 'error': 'Keine Dateien empfangen.'})

        output_path = os.path.join(tmp, filename)
        cmd = [
            GS_PATH, '-dBATCH', '-dNOPAUSE', '-dQUIET',
            '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.5',
            '-dPDFSETTINGS=/ebook',
            f'-sOutputFile={output_path}',
        ] + input_files

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            return jsonify({'success': False, 'error': proc.stderr or 'Ghostscript-Fehler'})

        if LOCAL_MODE:
            output_type = request.form.get('output_type', 'downloads')
            custom_path = (request.form.get('custom_path') or '').strip()
            output_dir = str(Path.home() / 'Downloads') if output_type == 'downloads' else (custom_path or str(Path.home() / 'Downloads'))
            output_dir = os.path.expanduser(output_dir)

            if not os.path.isdir(output_dir):
                return jsonify({'success': False, 'error': f'Ordner nicht gefunden: {output_dir}'})

            final_path = os.path.join(output_dir, filename)
            shutil.copy(output_path, final_path)
            return jsonify({'success': True, 'path': final_path, 'size': os.path.getsize(final_path)})

        # Online mode: return file as download
        with open(output_path, 'rb') as f:
            data = io.BytesIO(f.read())

    data.seek(0)
    return send_file(data, as_attachment=True, download_name=filename, mimetype='application/pdf')


@app.route('/convert', methods=['POST'])
def convert():
    files = request.files.getlist('files')
    quality = min(100, max(60, int(request.form.get('quality', 85))))

    if not files:
        return jsonify({'success': False, 'error': 'Keine Dateien empfangen.'})

    with tempfile.TemporaryDirectory() as tmp:
        converted = []
        for f in files:
            stem = re.sub(r'\.(heic|heif)$', '', f.filename, flags=re.IGNORECASE)
            out_name = stem + '.jpg'
            out_path = os.path.join(tmp, out_name)
            try:
                img = Image.open(f.stream)
                img = img.convert('RGB')
                img.save(out_path, 'JPEG', quality=quality, optimize=True)
                converted.append((out_name, out_path))
            except Exception as e:
                return jsonify({'success': False, 'error': f'{f.filename}: {e}'})

        if LOCAL_MODE:
            output_type = request.form.get('output_type', 'downloads')
            custom_path = (request.form.get('custom_path') or '').strip()
            output_dir = str(Path.home() / 'Downloads') if output_type == 'downloads' else (custom_path or str(Path.home() / 'Downloads'))
            output_dir = os.path.expanduser(output_dir)

            if not os.path.isdir(output_dir):
                return jsonify({'success': False, 'error': f'Ordner nicht gefunden: {output_dir}'})

            for name, path in converted:
                shutil.copy(path, os.path.join(output_dir, name))

            return jsonify({'success': True, 'count': len(converted), 'folder': output_dir})

        # Online: single file → JPEG, multiple → ZIP
        if len(converted) == 1:
            name, path = converted[0]
            with open(path, 'rb') as f:
                data = io.BytesIO(f.read())
            data.seek(0)
            return send_file(data, as_attachment=True, download_name=name, mimetype='image/jpeg')

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for name, path in converted:
                zf.write(path, name)
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name='bilder.zip', mimetype='application/zip')


if __name__ == '__main__':
    if LOCAL_MODE:
        threading.Thread(target=lambda: (
            __import__('time').sleep(0.6),
            webbrowser.open(f'http://localhost:{PORT}')
        ), daemon=True).start()
        print(f'PDF Merger läuft → http://localhost:{PORT}')

    app.run(host='0.0.0.0', port=PORT, debug=False)
