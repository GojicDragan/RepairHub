import test from 'node:test';
import assert from 'node:assert/strict';
import { DeviceSuggestionsPresenter } from '../../../app/web/static/js/device-suggestions-presenter.mjs';

function setup(load = async () => ['Radio', 'Radio XL']) {
  const events = []; let run;
  const view = Object.fromEntries(['close', 'loading', 'failed', 'show', 'highlight', 'choose'].map(name => [name, (...args) => events.push([name, ...args])]));
  const presenter = new DeviceSuggestionsPresenter(view, {load, cancel() {}}, fn => {run = fn;}, () => {run = null;});
  return {presenter, events, run: () => run()};
}

test('Suggestions debounce, require two characters and accept keyboard selection', async () => {
  const {presenter, events, run} = setup();
  presenter.change('a', '');
  assert.deepEqual(events, [['close']]);
  presenter.change('Ra', 'Maker');
  await run();
  assert.equal(presenter.key('ArrowDown'), true);
  assert.equal(presenter.key('Enter'), true);
  assert.deepEqual(events.at(-1), ['choose', 'Radio']);
  assert.equal(presenter.key('Enter'), false);
});

test('Late responses cannot reopen a closed or changed field', async () => {
  let resolve;
  const {presenter, events, run} = setup(() => new Promise(done => {resolve = done;}));
  presenter.change('Ra', '');
  const pending = run();
  presenter.change('Other', '');
  resolve(['Old']); await pending;
  assert.equal(events.some(event => event[0] === 'show'), false);
});

test('Arrows wrap, Escape dismisses and invalid selection does not change input', async () => {
  const {presenter, events, run} = setup();
  presenter.change('Ra', ''); await run();
  presenter.key('ArrowUp');
  assert.deepEqual(events.at(-1), ['highlight', 1]);
  presenter.key('ArrowDown');
  assert.deepEqual(events.at(-1), ['highlight', 0]);
  presenter.select(99);
  assert.equal(events.some(event => event[0] === 'choose'), false);
  presenter.key('Escape');
  assert.deepEqual(events.at(-1), ['close']);
});

test('Empty results and network failures never force a selection', async () => {
  for (const fail of [false, true]) {
    const {presenter, events, run} = setup(async () => {if (fail) throw new Error(); return [];});
    presenter.change('Unknown', ''); await run();
    assert.deepEqual(events.at(-1), fail ? ['failed'] : ['show', []]);
    assert.equal(presenter.key('Enter'), false);
  }
});
