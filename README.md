# ⛪ Ministranten-Planer

Web-App zur Erstellung von Ministrantenplänen. Termine anlegen, Ministranten aus einem Pool zuteilen (automatisch oder manuell), als DOCX exportieren.

![Split-View: Termine links, Pool rechts](docs/screenshot-placeholder.png)

---

## Features

- **Termine verwalten** — Datum, Uhrzeit, Priester, Sonderanlass, benötigte Anzahl
- **Pool verwalten** — Ministranten hinzufügen, aktivieren/deaktivieren
- **Auto-Assign** — Gleichmäßige Verteilung: wer weniger Dienste hat, wird bevorzugt
- **Manuell anpassen** — Zuteilungen per Klick ändern oder ergänzen
- **DOCX-Export** — Tabelle im gleichen Format wie der bisherige Plan

---

## Technik

| Schicht | Technologie |
|---------|-------------|
| Backend | Python · FastAPI · SQLModel |
| Datenbank | SQLite |
| Frontend | Vanilla HTML/CSS/JavaScript |
| Export | python-docx |
| Deployment | Raspberry Pi · Cloudflare Tunnel |

---

## Installation

**Voraussetzungen:** Python 3.11+, pip

```bash
# Repository klonen
git clone https://github.com/Christoph3573/Ministranten-Planer.git
cd Ministranten-Planer

# Abhängigkeiten installieren
pip install -r requirements.txt
```

---

## Starten

```bash
./start.sh
```

Die App ist dann unter **http://localhost:8000** erreichbar.

---

## Deployment auf dem Raspberry Pi

### Manuell starten

```bash
./start.sh
```

### Als systemd-Service (Autostart beim Booten)

1. Service-Datei anpassen — `User` und `WorkingDirectory` auf den eigenen Pi-Pfad setzen:

```ini
# ministranten-planer.service
[Service]
User=pi
WorkingDirectory=/home/pi/Ministranten-Planer
ExecStart=/home/pi/Ministranten-Planer/start.sh
```

2. Service installieren und aktivieren:

```bash
sudo cp ministranten-planer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ministranten-planer
sudo systemctl start ministranten-planer
```

3. Status prüfen:

```bash
sudo systemctl status ministranten-planer
```

### Cloudflare Tunnel

Tunnel auf `localhost:8000` zeigen lassen. Kein Login erforderlich — am besten nur im lokalen Netzwerk oder mit Cloudflare Access absichern.

---

## Benutzung

### Termin hinzufügen

Oben rechts auf **+ Termin** klicken. Datum, Uhrzeit und die benötigte Anzahl Ministranten eingeben. Priester und Sonderanlass sind optional.

### Ministranten zuteilen

**Automatisch:** Auf **⚡ Auto-Assign** klicken — die App wählt die Ministranten mit den wenigsten bisherigen Diensten aus.

**Manuell:** Termin in der linken Liste anklicken (wird hervorgehoben), dann eine Person aus der Pool-Liste rechts anklicken.

**Entfernen:** Auf das **✕** auf dem Namens-Chip klicken.

### Pool verwalten

Rechts oben auf **+ Person** klicken. Mit **⏸** kann eine Person temporär deaktiviert werden (wird beim Auto-Assign übersprungen).

### DOCX exportieren

Oben rechts auf **📥 DOCX Export** klicken — lädt eine `.docx`-Datei mit der kompletten Tabelle herunter.

---

## Tests ausführen

```bash
pytest tests/ -v
```

19 Tests · alle grün ✅

---

## Projektstruktur

```
ministranten-planer/
├── backend/
│   ├── main.py        # FastAPI-App + alle Routen
│   ├── models.py      # Datenmodelle (SQLModel)
│   ├── database.py    # Datenbankverbindung
│   └── export.py      # DOCX-Generierung
├── frontend/
│   ├── index.html     # Single-Page-App
│   ├── style.css      # Dark-Theme
│   └── app.js         # Frontend-Logik
├── tests/             # 19 pytest-Tests
├── requirements.txt
├── start.sh           # Startskript
└── ministranten-planer.service  # systemd-Unit
```

---

## Datenbank

Die SQLite-Datenbank (`ministranten.db`) wird automatisch beim ersten Start angelegt. Backup:

```bash
cp ministranten.db ministranten.db.backup
```
