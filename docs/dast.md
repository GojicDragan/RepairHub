# ZAP: reproduzierbare Formular- und Browserprüfung

Nacharbeit vom 21. September 2026 zu T02/T04–T06; Bezug M01, M02,
N04, N08–N10 und Benutzerauftrag zur Behebung des fehlgeschlagenen DAST-Laufs.
Die Änderungen betreffen ausschliesslich den Scanner und dessen CI-Tests.
Anwendung, Datenbankzugriffe, CSRF-Schutz und Facharchitektur bleiben unverändert.

## Nachgewiesene Ursachen

Ein erneuter Lauf der bisherigen Konfiguration gegen eine wegwerfbare Instanz
reproduzierte vier HIGH-Befunde der SQL-Regel 40018 und den übersprungenen
DOM-XSS-Scan (`Failed to read marionette port`). Private Diagnosedaten wurden
nicht als CI-Artefakte veröffentlicht.

Ein gezielter Lauf von Regel 40018 mit vollständigem HTTP-Mitschnitt zeigte:

- Bei 133 Login-POSTs passte die CSRF-Nonce nicht zum mitgesendeten Sitzungscookie;
  sämtliche Antworten waren HTTP 400. Ein Reset-POST hatte dasselbe Problem.
  Diese Anfragen prüften daher nicht die eigentliche Formularverarbeitung.
- Bei den booleschen Angriffen auf `submit` unter `/confirm` und `/reset` änderte
  sich ausschliesslich die Zeile mit dem versteckten CSRF-Feld. Flask-WTF signiert
  dieselbe Sitzungsnonce mit einem neuen Zeitstempel. Regel 40018 vergleicht die
  Antworttexte nach Entfernung reflektierter Angriffswerte auf exakte Gleichheit;
  wechselnde Zeitstempel/Signaturen wurden damit als SQL-bedingte Unterschiede
  fehlinterpretiert. Die bereits vorhandenen PostgreSQL-Regressionstests prüfen
  weiterhin, dass die Eingaben keine SQL-Struktur oder fremden Daten verändern.
- Firefox konnte im read-only Scannercontainer seinen Cache nicht schreiben.
  Ein direkter WebDriver-Test mit schreibbarem `XDG_CACHE_HOME` startete erfolgreich.
  Ein Scanner-Exitcode 0 allein hatte den vorher übersprungenen DOM-Test nicht erkannt.

## Korrektur

`scripts/ci/dast.py` lädt `scripts/ci/zap_forms.js` als ZAP-HTTP-Sender-Skript.
Der Spider verarbeitet die Formulare mit einem Thread und akzeptiert Cookies.
Vor aktiven POST-Angriffen auf die vier öffentlichen Benutzerformulare lädt das
Skript das Formular mit **dem Cookie der jeweiligen Angriffsanfrage** erneut.
Nur das CSRF-Feld wird aktualisiert. Eingaben, Cookie und Angriff bleiben erhalten;
der Refresh folgt keinen Weiterleitungen und verwendet keinen globalen Cookie-Jar.
Fehlende Tokens werden nicht ergänzt, und die aktive CSRF-Regel 20012 wird nicht
verändert. Damit bleiben absichtliche CSRF-Negativtests wirksam.

Nur für Regel 40018 werden in erfolgreichen HTML-Antworten die wechselnden
Zeitstempel-/Signaturanteile des exakt bekannten versteckten CSRF-Felds für den
Vergleich vereinheitlicht: Pro Sitzungsnonce dient das erste tatsächlich vom Server
signierte Token als kanonischer Vergleichswert. ZAP kann solche Felder erneut
senden; ungültige Platzhalter würden deshalb die Formularprüfung verfälschen.
Der nur im Scanprozess gehaltene Cache überlebt den Lauf nicht. Die normale
Token-Gültigkeitsprüfung der Anwendung wird nicht verändert.
Die Sitzungsnonce, reflektierte Eingaben, Datensätze,
Fehlertexte, Statuscodes und alle anderen Felder bleiben erhalten. Andere Regeln,
Browser, passive Originalseiten und die reale Anwendung erhalten keine solche
Normalisierung. Das ist keine Alert-Unterdrückung: Regel 40018 bleibt aktiv,
mit unveränderter Stärke und Schwelle `Medium`; MEDIUM/HIGH blockieren weiterhin.

Firefox erhält einen temporären schreibbaren Cache. Read-only-Dateisystem,
Capability-Entzug, Netzwerkisolation und fehlende Hostports bleiben erhalten.

Die Abnahme verlangt zusätzlich:

- SQL-Test-POSTs mit HTTP 200 auf `/register`, `/login`, `/confirm` und `/reset`;
  dies belegt die Formularverarbeitung nach CSRF-Prüfung, keine erfolgreiche Anmeldung;
- tatsächlich ausgeführte Tokenaktualisierung und Vergleichsnormalisierung;
- keine Skriptfehler, auch wenn zuvor bereits erfolgreiche Anfragen stattfanden;
- Browserangriffe laut `domxss.gets.count` (der blosse Startzähler genügt nicht);
- abgeschlossene SQL-/DOM-XSS-Regeln laut dem Log des festgelegten ZAP-Images.
  Auch ein nur teilweise fehlgeschlagener Browserstart blockiert.

Bei fehlgeschlagenen Statistikprüfungen nennt `failed_checks` ausschliesslich
die im Plan festgelegten Prüfnamen. Unbekannte Namen und rohe Scannertexte werden
nicht übernommen. Auch ein widersprüchlicher Exitcode 0 hebt diese Fehler nicht auf.

Der veröffentlichte Bericht enthält zusätzlich die Anzahl der SQL-Testanfragen
und einen booleschen DOM-Abschlussnachweis. Rohlogs, Cookies, Formulare und
Angriffswerte bleiben temporär und werden beim Aufräumen entfernt.

## Prüfungen

```bash
uv run --locked python scripts/ci/images.py build \
  --directory artifacts/zap-fix --commit "$(git rev-parse HEAD)"
uv run --locked pytest tests/unit -q
node --test tests/unit/frontend/*.test.mjs tests/unit/ci/*.test.mjs
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python scripts/check_architecture.py
uv run --locked python scripts/ci/dast.py \
  --artifacts artifacts/zap-fix --reports reports/security/zap-fix \
  --commit "$(git rev-parse HEAD)"
```

- 414 Python-Unit-Tests bestanden, darunter 121 Tests der DAST-Steuerung.
- 45 JavaScript-Tests bestanden, darunter 32 Tests des ZAP-Skripts. Diese prüfen
  unveränderte Angriffswerte/Cookies, weiterhin sichtbare Datenunterschiede,
  ursprüngliche CSRF-Negativtests und blockierende Skriptfehler.
- Die acht bestehenden SQL-Injection-Regressionsfälle gegen echtes PostgreSQL
  erneut bestanden; CSRF blieb aktiviert. Nachweis:
  `reports/security/zap-fix/injection-regression.xml`.
- Ruff, Architekturprüfung und Actionlint bestanden.
- pip-audit, Bandit, Gitleaks sowie Trivy für App/Nginx/PostgreSQL bestanden;
  die bestehende ausdrücklich freigegebene PostgreSQL-Ausnahme bleibt unverändert.
- Gezielter SQL-Replay mit der endgültigen Tokenkanonisierung: 502 POSTs auf den vier Formularen, alle HTTP 200,
  keine Befunde von Regel 40018. Dies ist ein Diagnose-, kein vollständiger DAST-Lauf.
- Zusätzlicher isolierter Negativkontrolllauf gegen einen synthetischen Server,
  der absichtlich unterschiedliche Daten bei booleschen SQL-Eingaben ausgibt:
  Mit eingeschalteter Normalisierung fand Regel 40018 **vier HIGH-Instanzen**.
  Die Berichtsauswertung blockierte trotz Scanner-Exitcode 0. Dieser Server ist
  kein Bestandteil der Anwendung und enthielt keine echten Benutzer-/Produktionsdaten.

Geprüfter lokaler Arbeitsbaum auf Basiscommit
`65f9d9054f60c70a22749af3fc52151f397b5ad5`, kein veröffentlichter Releasecommit.
App-Image-ID: `sha256:012884a975a24a5c4ae1ad8f7e0db45863363eb8bf001a5077d3cd7b44b97a67`.

Der erste vollständige aktive Lauf auf dem neu gebauten Image bestand:
`reports/security/zap-fix/zap.json`, Scanner-Exit 0, ausschliesslich INFO-Befunde.
Regel 40018 führte 1300 Anfragen aus; DOM-XSS schloss mit 609 Anfragen ohne
Befund ab. Die anschliessend korrigierte endgültige Skriptfassung wurde ebenfalls
vollständig aktiv geprüft; ihr Ergebnis steht nachfolgend.
Eine Zwischenfassung mit ungültigen Vergleichsplatzhaltern wurde durch die
neue Formularabdeckung gesperrt: ZAP hatte diese Platzhalter wieder als Tokens
gesendet. Die anschliessende strikte Prüfung von Angriffseingaben machte diesen
Cache-Konflikt sichtbar. Der gezielte Mitschnitt bestätigte HTTP 400 statt einer
fachlichen Prüfung. Die endgültige Fassung behält echte signierte Tokens im
Vergleichscache und erzeugt keine Platzhalter mehr.
Ein zur Skriptverschärfung bewusst beendeter weiterer Zwischenlauf wurde korrekt als fehlgeschlagen
bewertet (`invalid_or_missing_report`), nicht als grüner Teilscan.

Zusätzlich startete der Browser-Test auch mit UID/GID 1001, read-only-Dateisystem,
entzogenen Capabilities und ohne Netzwerk erfolgreich. Damit wurde der Cache-Fix
auch mit einer vom Scanner-Image abweichenden Runner-UID geprüft.

## Endgültiger aktiver Nachweis

`reports/security/zap-fix-final/zap.json`: **bestanden**, Scanner-Exitcode **0**,
`failed_checks: []`, keine LOW-, MEDIUM- oder HIGH-Befunde. Die fünf verbliebenen
Regeltypen sind ausschliesslich informativ (10058, 10015, 10112, 10104, 10031).

- Regel 40018: **1300 Anfragen**, keine Befunde.
- DOM-XSS: **609 Anfragen**, regulär abgeschlossen, keine Befunde.
- Sämtliche verpflichtenden Statistikprüfungen bestanden, einschliesslich der
  vier Formularpfade, Tokenbehandlung und null Skriptfehlern.
- Alle eigenen temporären Scan-/Kontroll-/PostgreSQL-Testcontainer wurden entfernt.
  Es laufen weiterhin nur die vier vorhandenen Entwicklungsdienste.

Der Kontrolllauf wurde nach der endgültigen Tokenkanonisierung erneut ausgeführt:
Regel 40018 erkannte weiterhin vier HIGH-Instanzen. Es wurden keine Scannerregeln
abgeschaltet, Alertfilter hinzugefügt oder Befundschwellen gelockert.
Keine neuen GitHub-Variablen oder Secrets erforderlich.

## Geltungsbereich

Der Scan prüft die öffentliche Oberfläche und Benutzerformulare im eigenen
Docker-Netz. Ein grüner Lauf belegt keine authentifizierte DAST-Abdeckung der
Gerätefunktionen oder künftigen API. Diese Erweiterung bleibt offen; bestehende
Eigentums-, Integrations- und Browserprüfungen sind davon unabhängig.
Externe OAST-Rückrufe sind im internen Netz nicht verfügbar; insbesondere ist
Log4Shell-OAST damit nicht geprüft. Keine Produktionsbereitstellung oder
GitHub-Actions-Abnahme wird aus einem lokalen Scan abgeleitet.

Grundlagen: [ZAP-HTTP-Sender-Skripte](https://www.zaproxy.org/docs/desktop/addons/script-console/automation/),
[Anti-CSRF-Behandlung](https://www.zaproxy.org/docs/desktop/start/features/anticsrf/),
[aktive Scanparameter](https://www.zaproxy.org/docs/desktop/addons/automation-framework/job-ascan/),
[SQL-Regel 40018](https://www.zaproxy.org/docs/alerts/40018/),
[CSRF-Regel 20012](https://www.zaproxy.org/docs/alerts/20012/).
