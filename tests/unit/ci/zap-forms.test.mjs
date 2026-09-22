import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const source = readFileSync('scripts/ci/zap_forms.js', 'utf8');
const nonce = Buffer.from(JSON.stringify('a'.repeat(40))).toString('base64url');
const token = `${nonce}.abcdef.${'b'.repeat(27)}`;
const field = (value) => `<input id="csrf_token" name="csrf_token" type="hidden" value="${value}">`;

function fixture(overrides = {}) {
    const stats = [];
    const context = vm.createContext({ Java: { type: (name) => name.endsWith('HttpSender')
        ? { ACTIVE_SCANNER_INITIATOR: 2 } : { incCounter: (key) => stats.push(key) } } });
    vm.runInContext(source, context);
    const state = { body: `<h1>Login</h1>${field(token)}`, initiator: 2, rule: '40018',
        method: 'POST', scheme: 'https', host: 'nginx', port: 8443, path: '/login',
        status: 200, contentType: 'text/html; charset=utf-8', ...overrides };
    const message = {
        getRequestHeader: () => ({ getHeader: () => state.rule, getMethod: () => state.method,
            getURI: () => ({ getScheme: () => state.scheme, getHost: () => state.host,
                getPort: () => state.port, getPath: () => state.path }) }),
        getResponseHeader: () => ({ getStatusCode: () => state.status,
            getHeader: () => state.contentType, setContentLength: (n) => { state.length = n; } }),
        getResponseBody: () => ({ toString: () => state.body, length: () => state.body.length }),
        setResponseBody: (body) => { state.body = body; },
    };
    return { context, state, stats, run: () => context.responseReceived(message, state.initiator, {}) };
}

test('only signed timestamp and signature are normalized; session nonce stays visible', () => {
    const { context } = fixture();
    assert.equal(context.normalizeCsrf(field(token)), field(token));
    const otherTime = `${nonce}.ghijkl.${'c'.repeat(27)}`;
    assert.equal(context.normalizeCsrf(field(token)), context.normalizeCsrf(field(otherTime)));
    const otherSession = Buffer.from(JSON.stringify('d'.repeat(40))).toString('base64url');
    assert.notEqual(context.normalizeCsrf(field(token)), context.normalizeCsrf(field(token.replace(nonce, otherSession))));
});

test('SQL-dependent data and XSS payloads remain distinguishable', () => {
    const { context } = fixture();
    const normal = field(token) + '<p>No records</p>';
    const injected = field(token) + '<p>Private account data</p><script>alert(1)</script>';
    assert.notEqual(context.normalizeCsrf(normal), context.normalizeCsrf(injected));
    assert.ok(context.normalizeCsrf(injected).endsWith('<p>Private account data</p><script>alert(1)</script>'));
});

test('no general token, reflection or arbitrary hidden-field removal', () => {
    const { context } = fixture();
    for (const body of [token, field('invalid-token'), field(token).replace('type="hidden"', 'type="text"'),
        field(token).replace('name="csrf_token"', 'name="password"'), '<p>' + token + '</p>']) {
        assert.equal(context.normalizeCsrf(body), body);
    }
});

test('only isolated SQL-rule responses are changed, with measurable valid POST coverage', () => {
    const f = fixture(); f.run();
    assert.equal(f.state.body, `<h1>Login</h1>${field(token)}`);
    f.state.body = `<h1>Login</h1>${field(`${nonce}.ghijkl.${'c'.repeat(27)}`)}`;
    f.run();
    assert.equal(f.state.body, `<h1>Login</h1>${field(token)}`);
    assert.deepEqual(f.stats, ['repairhub.csrf.post.login', 'repairhub.csrf.post.login', 'repairhub.csrf.normalized']);
    assert.equal(f.state.length, f.state.body.length);
});

for (const overrides of [{ initiator: 1 }, { rule: '40012' }, { rule: null },
    { host: 'production.invalid' }, { port: 443 }, { scheme: 'http' }, { path: '/devices' },
    { status: 400 }, { status: 500 }, { contentType: 'application/json' }]) {
    test(`preserves all responses outside the exact comparison scope: ${JSON.stringify(overrides)}`, () => {
        const f = fixture(overrides); const before = f.state.body; f.run();
        assert.equal(f.state.body, before); assert.deepEqual(f.stats, []);
    });
}

function senderFixture(overrides = {}) {
    const state = { body: `csrf_token=${token}&identity=person%27+OR+1%3D1&password=synthetic`,
        method: 'POST', cookie: 'session=original-scanned-session', path: '/login',
        host: 'nginx', scheme: 'https', port: 8443, rule: '40018', status: 200,
        html: field(`${nonce}.ghijkl.${'c'.repeat(27)}`), initiator: 2, ...overrides };
    const stats = []; const calls = [];
    function HttpSender(initiator) {
        calls.push(['sender', initiator]);
        this.setUseCookies = (enabled) => calls.push(['cookies', enabled]);
        this.sendAndReceive = (message, redirects) => {
            calls.push(['send', message, redirects]);
            if (state.fail) throw new Error('synthetic-private-input');
        };
    }
    HttpSender.ACTIVE_SCANNER_INITIATOR = 2; HttpSender.MANUAL_REQUEST_INITIATOR = 3;
    const context = vm.createContext({ Java: { type: (name) => name.endsWith('HttpSender')
        ? HttpSender : { incCounter: (key) => stats.push(key) } } });
    vm.runInContext(source, context);
    const uri = () => ({ getScheme: () => state.scheme, getHost: () => state.host,
        getPort: () => state.port, getPath: () => state.path, setQuery: (v) => { state.refreshQuery = v; } });
    const request = { getURI: uri, getMethod: () => state.method,
        getHeader: (name) => name === 'Cookie' ? state.cookie : state.rule,
        setContentLength: (n) => { state.length = n; } };
    const refreshHeaders = { Cookie: state.cookie, 'X-ZAP-Scan-ID': state.rule, 'Content-Type': 'application/x-www-form-urlencoded' };
    const refresh = { getRequestHeader: () => ({ getURI: uri,
        setMethod: (m) => { state.refreshMethod = m; },
        setHeader: (k, v) => { refreshHeaders[k] = v; }, setContentLength: () => {} }),
        setRequestBody: (b) => { state.refreshBody = b; },
        getResponseHeader: () => ({ getStatusCode: () => state.status }),
        getResponseBody: () => state.html };
    const message = { getRequestHeader: () => request, cloneRequest: () => refresh,
        getRequestBody: () => ({ toString: () => state.body, length: () => state.body.length }),
        setRequestBody: (b) => { state.body = b; } };
    return { state, stats, calls, refreshHeaders, run: () => context.sendingRequest(message, state.initiator, {}) };
}

for (const path of ['/register', '/login', '/confirm', '/reset']) {
    test(`refreshes ${path} with the attack's own cookie and preserves all attack input`, () => {
        const f = senderFixture({ path }); const original = f.state.body; f.run();
        assert.equal(f.state.body, original.replace(token, `${nonce}.ghijkl.${'c'.repeat(27)}`));
        assert.equal(f.state.cookie, 'session=original-scanned-session');
        assert.equal(f.refreshHeaders.Cookie, f.state.cookie);
        assert.equal(f.state.refreshMethod, 'GET'); assert.equal(f.state.refreshBody, '');
        assert.equal(f.state.refreshQuery, null); assert.equal(f.refreshHeaders['X-ZAP-Scan-ID'], null);
        assert.deepEqual(f.calls[0], ['sender', 3]); assert.deepEqual(f.calls[1], ['cookies', false]);
        assert.equal(f.calls[2][2], false); // Keine Weiterleitung ausserhalb des isolierten Ziels.
        assert.deepEqual(f.stats, ['repairhub.csrf.refreshed']);
        assert.equal(f.state.length, f.state.body.length);
    });
}

for (const overrides of [{ rule: '20012' }, { initiator: 3 }, { method: 'GET' },
    { cookie: '' }, { body: 'identity=person&password=synthetic' }, { body: 'csrf_token=&identity=person' },
    { body: 'csrf_token=%3Cscript%3Ealert%281%29%3C%2Fscript%3E&identity=person' },
    { body: 'csrf_token=invalid-token&identity=person' },
    { host: 'production.invalid' }, { path: '/other' }]) {
    test(`does not repair intended CSRF attacks or unrelated requests: ${JSON.stringify(overrides)}`, () => {
        const f = senderFixture(overrides); const original = f.state.body; f.run();
        assert.equal(f.state.body, original); assert.deepEqual(f.calls, []); assert.deepEqual(f.stats, []);
    });
}

for (const overrides of [{ status: 400 }, { html: '<h1>Invalid request</h1>' }]) {
    test(`does not override cookies or fabricate tokens when refresh is rejected: ${JSON.stringify(overrides)}`, () => {
        const f = senderFixture(overrides); const original = f.state.body; f.run();
        assert.equal(f.state.body, original); assert.deepEqual(f.stats, []);
        assert.equal(f.state.cookie, 'session=original-scanned-session');
    });
}

test('script failures increment a blocking counter without echoing private input', () => {
    const f = senderFixture({ fail: true });
    assert.throws(f.run, /RepairHub CSRF refresh failed/);
    assert.deepEqual(f.stats, ['repairhub.csrf.errors']);
});

test('comparison errors also block without leaking the underlying response', () => {
    const f = fixture({ contentType: { toString() { throw new Error('synthetic-private-response'); } } });
    assert.throws(f.run, /RepairHub CSRF comparison failed/);
    assert.deepEqual(f.stats, ['repairhub.csrf.errors']);
});
