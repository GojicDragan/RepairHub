import test from 'node:test';
import assert from 'node:assert/strict';
import { ImageUploadPresenter } from '../../../app/web/static/js/image-upload-presenter.mjs';

function setup(source) {
  const state = {enabled: true, message: '', saved: null, failed: false, expired: false};
  const view = {
    enabled: value => state.enabled = value,
    message: value => state.message = value,
    hasFile: () => true,
    saved: value => state.saved = value,
    failed: () => state.failed = true,
    expired: () => state.expired = true,
  };
  return {state, presenter: new ImageUploadPresenter(view, source)};
}

test('Leere Auswahl deaktiviert den Upload und startet keine Anfrage', async () => {
  const {state, presenter} = setup({upload() { assert.fail('keine Anfrage'); }});
  presenter.update(false);
  assert.equal(state.enabled, false);
  await presenter.submit(false);
});

test('Während des Uploads keine zweite Anfrage; Erfolg erreicht die View', async () => {
  let complete, requests = 0;
  const {state, presenter} = setup({upload() {
    requests++;
    return new Promise(resolve => complete = resolve);
  }});
  const pending = presenter.submit(true);
  assert.equal(state.enabled, false);
  await presenter.submit(true);
  assert.equal(requests, 1);
  complete({ok: true, body: {message: 'saved'}});
  await pending;
  assert.deepEqual(state.saved, {message: 'saved'});
});

test('Netzwerkfehler erlauben erneutes Absenden; 401 zeigt Sitzungsfehler', async () => {
  const first = setup({upload: async () => { throw new Error(); }});
  await first.presenter.submit(true);
  assert.equal(first.state.failed, true);
  assert.equal(first.state.enabled, true);
  const second = setup({upload: async () => ({ok: false, status: 401})});
  await second.presenter.submit(true);
  assert.equal(second.state.expired, true);
});
