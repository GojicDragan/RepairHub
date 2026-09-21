import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NotificationPresenter } from '../../../app/web/static/js/notification-presenter.mjs';

test('Schliessen gibt Fokus zurück und entfernt die Meldung genau einmal', () => {
  const calls = [];
  const presenter = new NotificationPresenter({
    focusReturnTarget: () => calls.push('focus'),
    remove: () => calls.push('remove'),
  });
  assert.deepEqual(calls, []);
  presenter.dismiss();
  presenter.dismiss();
  assert.deepEqual(calls, ['focus', 'remove']);
});
