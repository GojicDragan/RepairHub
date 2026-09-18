# RepairHub

RepairHub wird eine Webanwendung zur Verwaltung privater Reparaturfälle für
Haushaltsgeräte und Elektronik. Geplant sind Benutzerkonten, eigene Geräte und
Reparaturfälle, Schritte, Ersatzteilpositionen, Kostenschätzungen in CHF und eine
authentifizierte, lesende REST-API.

**Stand: T01 – Umsetzung vorbereitet.** Die Verzeichnisse unter `app/` enthalten
nur Paketbeschreibungen. Es gibt noch keinen startbaren Webserver, keine
Datenbankmodelle, Pipeline oder Bereitstellung. Diese entstehen ab T02 gemäss
[Implementierungsplan](AGENTS.md).

## Entwicklungsumgebung vorbereiten

Die geprüfte Basis verwendet Python **3.13.15** und uv **0.12.16**. `uv` verwaltet
die lokale Umgebung; direkte Versionen stehen in `pyproject.toml`, sämtliche
aufgelösten Abhängigkeiten mit Prüfsummen in `uv.lock`.

Mit vorhandenem Python und pip lässt sich uv isoliert installieren:

```bash
python3 -m pip install --user 'uv==0.12.16'
```

Danach muss `uv` im `PATH` verfügbar sein. Auf verwalteten Systemen alternativ
die [offizielle uv-Installation](https://docs.astral.sh/uv/getting-started/installation/)
für diese Version verwenden. Die System-Python-Installation nicht überschreiben.

Im Projektverzeichnis:

```bash
uv python install 3.13.15
uv sync --locked
uv lock --check
uv pip check
uv run --locked ruff check .
uv run --locked ruff format --check .
```

Die Installation erzeugt die ignorierte `.venv/`. Die genannten Projektbefehle
wurden in T01 geprüft; Details und Grenzen stehen im
[Arbeitsnachweis](docs/work-log.md). Funktionstests folgen mit ihrer Implementierung
ab T02. `pytest` findet derzeit keine Tests; das gilt nicht als bestandener Testlauf.
Start-, Migrations- und Deploymentbefehle werden erst nach deren Umsetzung ergänzt.

`.env.example` enthält ausschliesslich Platzhalter für die spätere Konfiguration.
T01 liest diese Werte noch nicht. Geheimnisse, TLS-Dateien, Datenbanksicherungen
und lokale Prüfergebnisse bleiben ausserhalb der versionierten Quellen und Images.

## Struktur und nächste Schritte

| Pfad | Verantwortung / Stand |
| --- | --- |
| `app/web`, `app/api` | Getrennte Präsentationskomponenten, bisher nur Paketmarker |
| `app/services/{users,devices,repairs,parts,costs}` | Fünf getrennte Fachkomponenten, bisher nur Paketmarker |
| `app/data` | Grenze für Modelle, Abfragen und Transaktionen, bisher nur Paketmarker |
| `tests` | Prüfplanung; automatische Tests ab T02 |
| `docs/architecture.md` | Verbindliche Abhängigkeiten, Schnittstellenplanung und Ausbau der Struktur |
| `docs/requirements.md` | Zuordnung aller Ziele und Anforderungen zu Tasks |
| `docs/decisions.md` | Quellenprüfung, Versionswahl, Begründungen und offene Angaben |
| `docs/work-log.md` | Tatsächlich ausgeführte Prüfungen und deren Ergebnisse |
| `Diagramme/Kapitel4` | Bestehender Architekturentwurf, unverändert erhalten |

T02 erstellt zuerst das minimale Flask-Gerüst und die Pipeline
**Test → Build → Security → Deploy**, mit GitHub Actions → Ansible → Docker
Compose. Die drei Dienste `nginx`, `app` und `db` führen den modularen Monolithen
aus. T03–T10 vervollständigen Infrastruktur und Muss-Funktionen; T11–T13 behandeln
Betrieb, Gesamtabnahme und Abgabe. Suche/Filter, Statuskennzahlen, Bilder und
PDF-Berichte bleiben separate Kann-Ziele und sind nicht umgesetzt.

Repository: [GojicDragan/RepairHub](https://github.com/GojicDragan/RepairHub).
Vorhandene Branches sind `main` und
`1-bestand-prüfen-und-umsetzung-vorbereiten`. Die verbindliche Zuordnung von
Integrations- und Produktionsbranch, Zielhosts, Domain, Zugängen und Abgabetermin
ist noch offen. Diese Angaben blockieren nur die davon abhängigen späteren Schritte.

Ein späteres Quellcode-ZIP aus dem geprüften Commit erzeugen, beispielsweise mit
`git archive`, statt den gesamten Arbeitsordner einschliesslich lokaler Daten zu
komprimieren. Vor Commit und Abgabe die Dateiliste prüfen; Ignore-Regeln entfernen
keine bereits versionierten Geheimnisse. In T01 wurde weder committed noch publiziert.
