# K-T05 – PDF-Reparaturbericht

Auf jeder eigenen Reparaturdetailseite steht «PDF-Bericht herunterladen» zur
Verfügung. `GET /repairs/{id}/report.pdf` liefert einen Download namens
`repair-{id}.pdf`. Der Ablauf funktioniert mit und ohne JavaScript.

Der Bericht enthält Gerät, Hersteller, Modell, Erstellungszeitpunkt, aktuellen
Status, Fehlerbeschreibung, sämtliche Reparaturschritte mit Erledigungszustand,
sämtliche Ersatzteilpositionen, Arbeitsstunden, Stundensatz und die geschätzten
Kosten in CHF. Er ist ausdrücklich keine Rechnung. Deutsch wird wie in der
Oberfläche über Accept-Language ausgewählt; Englisch ist der Fallback. Zeitangaben
sind als UTC gekennzeichnet. Die Schrittfolge ist der aktuelle dokumentierte
Stand, keine nachträglich erfundene Änderungshistorie.

## Architektur und Sicherheit

Der vorhandene Slice `get_repair` liefert mit `complete=True` dieselbe vollständige
und autorisierte Auskunft wie für die lesende API. Die Browser-Pagination begrenzt
den Bericht nicht. Gerätedetails stammen aus dem vorhandenen Geräte-Leseslice.
Es entsteht keine neue fachliche Regel und deshalb kein duplizierter Export-Slice
mit eigener Eigentumsprüfung oder Kostenformel. `app.web.documents.repair_pdf`
formatiert ausschliesslich bereits autorisierte DTOs. Die Kosten kommen unverändert
aus der gemeinsamen Domain-Berechnung; SQL/ORM und Speicherzugriff bleiben ausserhalb
der Präsentation. Weder eine neue Migration noch ein Garage-Objekt ist erforderlich.

Eine Browsersitzung ist erforderlich. Fremde und unbekannte Fälle ergeben 404;
ohne Sitzung folgt die Anmeldung. Persönliche/System-API-Keys schalten den
Browserdownload nicht frei. Downloads verwenden `no-store`, `nosniff` und einen
festen serverseitigen Dateinamen. Der PDF-Inhalt entsteht im Arbeitsspeicher und
wird nicht öffentlich zwischengespeichert.

Benutzereingaben werden vor der ReportLab-Paragraph-Darstellung escaped. Sie können
keine Bilder, Links, XML-Tags oder externen Ressourcen in den Renderer einschleusen.
PDFs enthalten keine aktiven Formular-/JavaScript-Funktionen. Lange Texte werden
umgebrochen, statt stillschweigend abgeschnitten. Der vollständige Bericht wächst
mit dem Umfang des Falls; sehr grosse Fälle benötigen entsprechend mehr Ressourcen.

## Gestaltung und Bibliothek

ReportLab 5.0.1 übernimmt PDF-Erzeugung und Platypus-Seitenlayout. Die mitgelieferte
Bitstream-Vera-Schrift wird eingebettet; deutsche Umlaute sind geprüft. Beliebige
Schriftsysteme und Emoji sind nicht durch diese Schrift abgedeckt. Die bestehende
Marke erscheint als RepairHub-Wortmarke, Dunkelgrün, Rostorange und helle Kostenfläche.
A4, wiederholte Kopf-/Fusszeilen und Seitenzahlen sowie wiederholte Tabellenköpfe
unterstützen mehrseitige Berichte. Schrittlabel bleiben beim folgenden Text.

Quellen: [ReportLab Platypus](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/),
[Paragraph-Markup](https://docs.reportlab.com/reportlab/userguide/ch6_paragraphs/).
`pypdf` ist nur eine Entwicklungsabhängigkeit für Inhaltsprüfungen, kein Bestandteil
der produktiven PDF-Erzeugung. Es sind keine zusätzlichen Environment-Variablen,
Secrets oder Systempakete nötig.
