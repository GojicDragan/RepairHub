# T09 – Persönliche API-Keys und lesende REST-API

## Schlüssel im Frontend verwalten

Nach der Anmeldung **API access / API-Zugriff** in der Navigation öffnen
(`/account/api-key`). Dort lässt sich ein persönlicher Schlüssel generieren,
ersetzen oder widerrufen. Er wird ausschliesslich in der Antwort auf das
Generieren angezeigt. Jetzt kopieren und vertraulich aufbewahren; ein späterer
Seitenaufruf kann ihn nicht erneut anzeigen.

Pro Konto ist höchstens ein Schlüssel aktiv. Ersetzen oder Widerrufen sperrt den
bisherigen Schlüssel sofort. Die Erzeugung verwendet 256 zufällige Bits aus
Pythons `secrets`; PostgreSQL speichert ausschliesslich dessen SHA-256-Hash,
Erstellungszeit und die Bindung an die bestätigte Identität. SHA-256 ist hier für
zufällige Schlüssel vorgesehen, nicht für benutzergewählte Passwörter.

Es gibt keinen separaten Token-Abruf mehr. `POST /api/auth/token` wurde entfernt.
API-Keys bleiben bis zum Widerruf gültig; die bisherige Variable
`API_TOKEN_TTL_SECONDS` entfällt. Passwort-Reset, Kontosperre oder Entzug der
Bestätigung machen bestehende Keys ebenfalls ungültig. Browser-Abmeldung allein
widerruft einen API-Key nicht. Die Verwaltung benötigt eine bestätigte Sitzung
und CSRF; die Seite verwendet `Cache-Control: no-store`, speichert Schlüssel
weder in Sitzung noch Flash-Meldungen und funktioniert auch ohne JavaScript.

## Authentifizierung

Für jeden API-Aufruf ausschliesslich diesen Header senden:

```http
Authorization: Bearer rh_<persönlicher-schlüssel>
```

`Bearer` beschreibt die Header-Syntax, nicht einen zusätzlichen kurzlebigen
Token. Benutzername und Passwort werden nicht übergeben. Die Identität wird aus
dem Schlüssel ermittelt. Browsercookies, URL-Parameter und `X-API-Key` werden
nicht als API-Authentifizierung akzeptiert. Übermittelte Benutzernamen oder
Eigentümer-IDs können keine fremden Daten freischalten. Produktion verwendet HTTPS.

## Reparaturen auflisten

```http
GET /api/repairs?limit=20&offset=0
Authorization: Bearer rh_<persönlicher-schlüssel>
```

Beispielantwort:

```json
{
  "items": [{
    "id": 42,
    "device": {"id": 7, "name": "Radio"},
    "description": "Power supply failed",
    "status": "open",
    "created_at": "2026-09-22T10:00:00+00:00"
  }],
  "total": 1,
  "offset": 0,
  "limit": 20,
  "snapshot": 42,
  "next_offset": null
}
```

Neueste Fälle zuerst. `limit` liegt zwischen 1 und 60 (Standard 20), `offset`
ist eine nichtnegative Ganzzahl (Standard 0). Für die Folgeseite den gelieferten
`next_offset` und denselben `snapshot` mitsenden. Der Snapshot begrenzt die obere
Fall-ID; neu angelegte Fälle verschieben so die bestehenden Fenster nicht.
`next_offset: null` kennzeichnet das Ende. Er ist kein Datenbank-Snapshot;
Bearbeitungen bereits vorhandener Fälle bleiben sichtbar. Liste, Gesamtzahl und
Snapshot enthalten bei persönlichen Schlüsseln ausschliesslich eigene Fälle;
beim Systemschlüssel alle Fälle. Eine leere Liste liefert 200.
Die Liste enthält eine Übersicht; vollständige Schritte, Teile und Kosten stehen
im Detail-Endpunkt.

## Einzelne Reparatur lesen

```http
GET /api/repairs/42
Authorization: Bearer rh_<persönlicher-schlüssel>
```

```json
{
  "id": 42,
  "device": {"id": 7, "name": "Radio"},
  "description": "Power supply failed",
  "status": "open",
  "created_at": "2026-09-22T10:00:00+00:00",
  "steps": [{"id": 3, "description": "Check cable", "completed": true}],
  "parts": [{"id": 5, "name": "Cable", "quantity": 3, "unit_price": "15.00", "total": "45.00"}],
  "work": {"hours": "2.00", "hourly_rate": "80.00"},
  "costs": {"currency": "CHF", "labor": "160.00", "parts": "45.00", "total": "205.00"}
}
```

Die Detailantwort enthält alle Schritte und Teile. IDs und Mengen sind
JSON-Ganzzahlen, Erledigung ein Boolean, Dezimalwerte Strings mit zwei
Nachkommastellen. Datum ist ISO 8601 mit Zeitzone; Statuswerte bleiben `open`,
`in_progress`, `completed`. Schlüssel und Statuswerte sind sprachunabhängig.
Die Kostenberechnung entspricht exakt der Browseransicht (`Decimal`,
`ROUND_HALF_UP`). Separat gerundete Teilbeträge müssen in Grenzfällen nicht zur
aus ungerundeten Grundlagen berechneten Gesamtsumme addierbar sein.

## Fehler

| Situation | Status |
| --- | --- |
| Fehlender, falscher, ersetzter oder widerrufener Schlüssel | 401 |
| Persönlicher Key: gesperrtes/unbestätigtes Konto oder Passwort-Reset | 401 |
| Unbekannte Reparatur; bei persönlichen Keys auch fremde Reparatur | 404 |
| Ungültige/mehrfach übergebene Seitenparameter | 400 |
| POST/PUT/PATCH/DELETE an Listen- oder Detail-Endpunkt | 405 |

Fehler sind JSON ohne Login-Weiterleitung:

```json
{"error": {"status": 401, "title": "Login required", "message": "Please log in to access this resource."}}
```

Lesbare Meldungen folgen `Accept-Language`, Deutsch oder Englisch mit englischem
Fallback. 401 enthält `WWW-Authenticate: Bearer`, 405 enthält `Allow`.
HEAD prüft denselben Schlüssel wie GET; OPTIONS gibt nur erlaubte Methoden aus.
API-Antworten einschliesslich Fehler verwenden `Cache-Control: no-store`.
Nginx und Anwendung protokollieren keine Authorization-Header, Bodies oder
Querystrings. CORS-Zugriff fremder Webseiten ist nicht freigegeben.

## Curl

```bash
APP_ORIGIN=https://lab19.ifalabs.org
IFS= read -r -s -p 'API key: ' API_KEY; echo
printf 'Authorization: Bearer %s\n' "$API_KEY" \
  | curl --fail-with-body --silent --show-error --header @- \
      "$APP_ORIGIN/api/repairs?limit=20"
printf 'Authorization: Bearer %s\n' "$API_KEY" \
  | curl --fail-with-body --silent --show-error --header @- \
      "$APP_ORIGIN/api/repairs/42"
unset API_KEY
```

Lokal lautet die Origin standardmässig `http://127.0.0.1:8080`. Das Beispiel gibt
den Schlüssel nicht als Prozessargument weiter.

## Architektur und Migration

Frameworkfreie Benutzer-Slices `create_api_key`, `get_api_key`, `revoke_api_key`
und `authenticate_api_key` besitzen eigene Ports/DTOs. Der injizierte Adapter
`app.adapters.users.api_keys` kapselt Zufall, Hashing und technische
Identitätspersistenz. `app.bootstrap` verdrahtet Web, API und Adapter.
`repairs.list_repairs` und `repairs.get_repair` bleiben die gemeinsamen
Anwendungsfälle für Browser und API. Keine direkten Datenbank- oder Kostenaufrufe
in den Routen. Migration `0005_api_keys` ergänzt drei nullable Identitätsspalten
und einen eindeutigen Hash-Constraint; bestehende Benutzer/Fälle bleiben erhalten.

## Zentraler System-Leseschlüssel und Deployment

Benutzerentscheidung: `API_SMOKE_KEY` ist ein administrativer **Leseschlüssel**.
`GET /api/repairs` liefert damit Fälle aller Benutzer, weiterhin mit begrenzten
Listenfenstern (`limit`, `offset`, `snapshot`). `GET /api/repairs/{id}` liefert
die Details jedes vorhandenen Falls samt Kosten. Schreibzugriffe bleiben 405;
der Schlüssel erzeugt keine Browsersitzung und keine Benutzerrolle. Persönliche
Frontend-Schlüssel bleiben auf die eigenen Daten beschränkt.

Unter **Settings → Environments → production → Secrets** nur `API_SMOKE_KEY`
als zufälligen Systemschlüssel hinterlegen:

```bash
python3 -c 'import secrets; print("rh_" + secrets.token_urlsafe(32))'
```

Authentifizierung: `Authorization: Bearer <API_SMOKE_KEY>`. Kein Benutzername
ist erforderlich. `API_SMOKE_USERNAME`, `API_SMOKE_REPAIR_ID`,
`API_SMOKE_PASSWORD` und `API_TOKEN_TTL_SECONDS` werden nicht mehr benötigt.
Keinen persönlichen Frontend-Schlüssel als Systemschlüssel wiederverwenden.

Die Pipeline übernimmt das Secret in die geschützte App-Laufzeitvariable
`API_SMOKE_KEY`. Ohne gesetzten Wert ist der Systemzugang deaktiviert;
persönliche Schlüssel funktionieren weiter. Der Schlüssel benötigt das Format
`rh_` plus 43 URL-sichere Zeichen. Im Prozess wird sein SHA-256-Hash konstantzeitig
verglichen; er wird weder im Frontend angezeigt noch einem Konto zugeordnet.
Rotation erfolgt durch Ändern des GitHub-Secrets und erneute Auslieferung;
das neue App-Environment ersetzt den vorherigen Schlüssel.

Ansible prüft die Liste und, falls vorhanden, den ersten Fall samt CHF-Kosten.
Eine leere Datenbank ist gültig. Kein Prüfkonto, keine feste Fall-ID und keine
CLI-Provisionierung sind nötig. Runtime und Prüfschlüssel werden mit restriktiven
Dateirechten und `no_log` geschützt; ein kompatibler Rollback stellt beide
vorherigen Werte wieder her. Unveränderte Releases erzeugen keine Key-Änderungen.
