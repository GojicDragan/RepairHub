// ZAP-HTTP-Sender: CSRF-Tokens mit dem passenden Cookie laden und volatile
// Tokenmetadaten nur für SQL-Vergleiche vereinheitlichen. Keine Regeln ausblenden.
// Die Vereinheitlichung verändert keine Anwendungsausgabe.
var HttpSender = Java.type('org.parosproxy.paros.network.HttpSender');
var Stats = Java.type('org.zaproxy.zap.utils.Stats');
// ZAP kann Tokens aus verglichenen Antworten erneut senden. Deshalb einen
// echten signierten Wert je Nonce behalten, niemals einen ungültigen Platzhalter.
// Der Cache lebt nur im Scannerprozess (maximal 20 Minuten), nicht in der App.
var canonicalTokens = Object.create(null);

function sendingRequest(msg, initiator, helper) {
    try { refreshCsrf(msg, initiator); }
    catch (error) {
        Stats.incCounter('repairhub.csrf.errors');
        throw new Error('RepairHub CSRF refresh failed');
    }
}

function refreshCsrf(msg, initiator) {
    if (initiator !== HttpSender.ACTIVE_SCANNER_INITIATOR) return;
    var request = msg.getRequestHeader();
    if (!isForm(request) || String(request.getMethod()) !== 'POST') return;
    // Die CSRF-Prüfregel muss absichtlich fehlende/ungültige Tokens testen können.
    if (String(request.getHeader('X-ZAP-Scan-ID')) === '20012') return;
    var body = String(msg.getRequestBody());
    // Keine in dieses Feld injizierten Payloads durch ein gültiges Token ersetzen.
    if (!/(^|&)csrf_token=[A-Za-z0-9_-]{56}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}(&|$)/.test(body)) return;
    if (!request.getHeader('Cookie')) return;

    // ZAPs globale Tokenzuordnung kann bei gleichen signierten Tokens auf ein
    // GET mit einem anderen Cookie zeigen. Frisch laden, aber mit genau dem
    // Cookie dieses Angriffs; Cookies und Nutzereingaben niemals überschreiben.
    var refresh = msg.cloneRequest();
    var header = refresh.getRequestHeader();
    header.setMethod('GET');
    header.getURI().setQuery(null);
    header.setHeader('X-ZAP-Scan-ID', null);
    header.setHeader('Content-Type', null);
    refresh.setRequestBody('');
    header.setContentLength(0);
    var sender = new HttpSender(HttpSender.MANUAL_REQUEST_INITIATOR);
    sender.setUseCookies(false);
    sender.sendAndReceive(refresh, false);
    if (refresh.getResponseHeader().getStatusCode() !== 200) return;
    var match = /<input\b(?=[^>]*\sname="csrf_token")(?=[^>]*\stype="hidden")[^>]*\svalue="([A-Za-z0-9_-]{56}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27})"/.exec(String(refresh.getResponseBody()));
    if (!match) return;
    msg.setRequestBody(body.replace(/(^|&)csrf_token=[^&]*/, '$1csrf_token=' + match[1]));
    request.setContentLength(msg.getRequestBody().length());
    Stats.incCounter('repairhub.csrf.refreshed');
}

function isForm(request) {
    var uri = request.getURI();
    return String(uri.getScheme()) === 'https' && String(uri.getHost()) === 'nginx'
        && uri.getPort() === 8443 && /^\/(register|login|confirm|reset)$/.test(String(uri.getPath()));
}

function responseReceived(msg, initiator, helper) {
    try { compareResponse(msg, initiator); }
    catch (error) {
        Stats.incCounter('repairhub.csrf.errors');
        throw new Error('RepairHub CSRF comparison failed');
    }
}

function compareResponse(msg, initiator) {
    if (initiator !== HttpSender.ACTIVE_SCANNER_INITIATOR) return;
    var request = msg.getRequestHeader();
    if (String(request.getHeader('X-ZAP-Scan-ID')) !== '40018') return;
    if (!isForm(request)) return;
    var response = msg.getResponseHeader();
    if (response.getStatusCode() !== 200 || !String(response.getHeader('Content-Type')).startsWith('text/html')) return;
    var path = String(request.getURI().getPath());
    if (String(request.getMethod()) === 'POST') Stats.incCounter('repairhub.csrf.post.' + path.slice(1));

    var original = String(msg.getResponseBody());
    // Flask-WTF signiert dieselbe Sitzungsnonce bei jeder Antwort erneut.
    // Nur Zeitstempel/Signatur eines korrekt geformten Hidden-Felds ersetzen;
    // die Nonce bleibt stehen, damit Sitzungswechsel weiterhin sichtbar sind.
    var normalized = normalizeCsrf(original);
    if (normalized !== original) {
        msg.setResponseBody(normalized);
        response.setContentLength(msg.getResponseBody().length());
        Stats.incCounter('repairhub.csrf.normalized');
    }
}

function normalizeCsrf(body) {
    return body.replace(
        /(<input\b(?=[^>]*\sname="csrf_token")(?=[^>]*\stype="hidden")[^>]*\svalue=")([A-Za-z0-9_-]{56})\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27}("[^>]*>)/g,
        function (field, prefix, nonce, suffix) {
            var token = field.slice(prefix.length, field.length - suffix.length);
            if (!canonicalTokens[nonce]) canonicalTokens[nonce] = token;
            return prefix + canonicalTokens[nonce] + suffix;
        }
    );
}
