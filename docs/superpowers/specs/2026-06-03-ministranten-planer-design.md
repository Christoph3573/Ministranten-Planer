# Ministranten-Planer — Design Spec

**Datum:** 2026-06-03

## Übersicht

Web-App zur Erstellung und Verwaltung von Ministrantenplänen. Läuft auf einem Raspberry Pi, erreichbar über Cloudflare Tunnel. Kein Login erforderlich.

---

## Stack

- **Backend:** Python 3 + FastAPI
- **Datenbank:** SQLite (via SQLModel)
- **Frontend:** Vanilla HTML/CSS/JavaScript (kein Framework)
- **DOCX-Export:** python-docx
- **Deployment:** Raspberry Pi, Cloudflare Tunnel

---

## Datenmodell

### Ministrant
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | INTEGER PK | Auto-increment |
| name | TEXT | Vollständiger Name |
| aktiv | BOOLEAN | Inaktive werden beim Auto-Assign übersprungen |

### Termin
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | INTEGER PK | Auto-increment |
| datum | DATE | Datum des Termins |
| uhrzeit | TEXT | z.B. "18:00 Uhr" |
| priester | TEXT (nullable) | z.B. "Pfr. Bula" |
| ereignis | TEXT (nullable) | z.B. "Vorstellungsgottesdienst" |
| anzahl_benoetigt | INTEGER | Anzahl benötigter Ministranten |

### Zuteilung
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| termin_id | INTEGER FK | Referenz auf Termin |
| ministrant_id | INTEGER FK | Referenz auf Ministrant |

Primary Key ist (termin_id, ministrant_id).

---

## API-Endpunkte

### Ministranten (Pool)
- `GET /ministranten` — Liste aller Ministranten mit Zuteilungsanzahl
- `POST /ministranten` — Neuen Ministranten anlegen `{name, aktiv}`
- `PUT /ministranten/{id}` — Name oder aktiv-Status ändern
- `DELETE /ministranten/{id}` — Ministranten löschen (löscht auch alle bestehenden Zuteilungen via CASCADE)

### Termine
- `GET /termine` — Alle Termine mit zugeteilten Ministranten, sortiert nach Datum
- `POST /termine` — Neuen Termin anlegen `{datum, uhrzeit, priester?, ereignis?, anzahl_benoetigt}` (Wochentag wird server-seitig aus datum abgeleitet)
- `PUT /termine/{id}` — Termin bearbeiten
- `DELETE /termine/{id}` — Termin + alle Zuteilungen löschen

### Zuteilung
- `POST /termine/{id}/auto-assign` — Auto-Vorschlag: wählt die `anzahl_benoetigt` aktiven Ministranten mit den wenigsten bisherigen Zuteilungen. Bereits zugeteilte werden nicht ersetzt. Gibt die neue Gesamtzuteilung zurück (speichert direkt).
- `POST /termine/{id}/zuteilung` — Einzelnen Ministranten manuell hinzufügen `{ministrant_id}`
- `DELETE /termine/{id}/zuteilung/{ministrant_id}` — Einzelnen Ministranten aus Termin entfernen

### Export
- `GET /export/docx` — Erzeugt DOCX mit Tabelle (4 Spalten: Datum+Wochentag, Uhrzeit+Priester, Ministranten, Ereignis). Download als Datei.

---

## Frontend — Split View

### Layout
- **Top-Bar:** Titel + "Termin hinzufügen"-Button + "DOCX Export"-Button
- **Links (flex: 2):** Terminliste, scrollbar
- **Rechts (flex: 1):** Pool-Liste, scrollbar

### Terminliste (links)
Jeder Termin zeigt:
- Datum, Wochentag, Uhrzeit, Priester (falls vorhanden)
- Ereignis-Label (farbiger Badge, falls vorhanden)
- Zugeteilte Ministranten als Chips mit ✕-Button zum Entfernen
- "N fehlen"-Indikator wenn weniger als `anzahl_benoetigt` zugeteilt
- ⚡ Auto-Assign-Button (erscheint wenn noch Stellen offen)
- ✏️ Bearbeiten-Button

Termin hinzufügen/bearbeiten: Modal-Dialog mit Formular.

### Pool (rechts)
- Liste aller aktiven Ministranten, sortiert aufsteigend nach Anzahl Zuteilungen
- Badge mit Anzahl bisheriger Dienste
- Inaktive Ministranten erscheinen ausgegraut am Ende
- "+ Person"-Button zum Hinzufügen
- Klick auf Person → wird dem aktuell ausgewählten Termin hinzugefügt (falls kein Termin selektiert, passiert nichts)

### Auto-Assign-Logik
Beim Klick auf ⚡ Auto-Assign:
1. Server ermittelt wie viele Plätze noch offen sind (`anzahl_benoetigt` - bereits zugeteilte)
2. Aus allen aktiven Ministranten, die noch nicht zugeteilt sind, werden die mit den wenigsten Diensten gewählt
3. Bei Gleichstand: zufällige Auswahl
4. Zuteilung wird sofort gespeichert und UI aktualisiert

---

## DOCX-Export

Erzeugt eine Tabelle im gleichen Format wie das Original:

| Datum | Uhrzeit | Ministranten | Ereignis |
|-------|---------|--------------|---------|
| 03.01.2026 Samstag | 19:00 Uhr Pfr. Wagner | Alle | Aussendung Sternsinger |
| 09.01.2026 Freitag | 18:00 Uhr | Anna – Mirjam | |

- Datum und Wochentag in einer Zelle (Zeilenumbruch)
- Uhrzeit und Priester in einer Zelle (Zeilenumbruch)
- Ministranten mit " – " getrennt
- Header-Zeile fett
- Titelzeile über der Tabelle: "Ministrantenplan [Datum von] - [Datum bis]"

---

## Dateistruktur

```
ministranten-planer/
├── backend/
│   ├── main.py          # FastAPI app + alle Routen
│   ├── models.py        # SQLModel Datenmodelle
│   ├── database.py      # DB-Verbindung + Init
│   └── export.py        # DOCX-Export-Logik
├── frontend/
│   ├── index.html       # Single-page App
│   ├── style.css        # Styles
│   └── app.js           # Frontend-Logik
├── requirements.txt
└── README.md
```

---

## Deployment (Raspberry Pi)

- FastAPI läuft mit `uvicorn` auf Port 8000
- Statische Frontend-Dateien werden von FastAPI mitgeserved (`StaticFiles`)
- Cloudflare Tunnel leitet auf `localhost:8000`
- SQLite-Datei liegt im Projektordner (`ministranten.db`)
- Start via systemd service oder einfachem Shell-Script
