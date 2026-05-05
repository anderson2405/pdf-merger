# PDF Merger

PDFs per Drag & Drop zusammenführen und komprimieren – lokal oder online deploybar.

## Lokal starten

**Voraussetzungen**
- Python 3.9+
- [Ghostscript](https://www.ghostscript.com/) (`brew install ghostscript`)

```bash
pip install -r requirements.txt
python app.py
```

Öffnet automatisch http://localhost:7777 im Browser.  
Alternativ: Doppelklick auf `PDF Merger starten.command`.

## Online deployen

Die App unterstützt Deployments auf Railway, Render oder Heroku.  
Im Online-Modus wird die fertige PDF direkt als Download zurückgegeben (kein lokaler Speicherpfad nötig).

### Railway / Render

1. Repo auf GitHub pushen
2. Neues Projekt aus dem GitHub-Repo erstellen
3. Umgebungsvariable setzen: `LOCAL_MODE=false`
4. Ghostscript installieren – z. B. über eine `nixpacks.toml`:

```toml
[phases.setup]
nixPkgs = ["ghostscript"]
```

### Heroku

```bash
heroku create
heroku buildpacks:add heroku/python
heroku config:set LOCAL_MODE=false
git push heroku main
```

Ghostscript via Buildpack hinzufügen:
```bash
heroku buildpacks:add --index 1 https://github.com/dokku/heroku-buildpack-ghostscript
```

## Umgebungsvariablen

| Variable     | Standard | Beschreibung                                      |
|--------------|----------|---------------------------------------------------|
| `LOCAL_MODE` | `true`   | `false` = Online-Modus, PDF als Download          |
| `PORT`       | `7777`   | Port des Servers                                  |
