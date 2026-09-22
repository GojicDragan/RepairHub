import test from 'node:test';
import assert from 'node:assert/strict';
import { ListFilterPresenter } from '../../../app/web/static/js/list-filter-presenter.mjs';
import { VirtualListPresenter } from '../../../app/web/static/js/virtual-list-presenter.mjs';

test('Typing restarts the 300ms pause; explicit apply cancels the timer', () => {
  const tasks = new Map(); let id = 0, applied = 0, paused = 0;
  const presenter = new ListFilterPresenter({pending(){paused++;},apply(){applied++;}},
    (callback, delay) => {assert.equal(delay,300); tasks.set(++id,callback); return id;},
    timer => tasks.delete(timer));
  presenter.changed(); presenter.changed(); presenter.changed();
  assert.equal(tasks.size,1); assert.equal(applied,0); assert.equal(paused,3);
  [...tasks.values()][0]();
  assert.equal(applied,1); assert.equal(tasks.size,0);
  presenter.changed(); presenter.apply();
  assert.equal(applied,2); assert.equal(tasks.size,0);
  presenter.changed(); presenter.cancelPending();
  assert.equal(tasks.size,0); assert.equal(applied,2);
});

test('Changing filters invalidates old responses before debounce and reloads empty lists', async () => {
  const requests = [], rendered = [];
  const presenter = new VirtualListPresenter({loading(){},failed(){assert.fail();},render(page){rendered.push(page);}},
    {load(offset,limit,snapshot){return new Promise(resolve => requests.push({offset,limit,snapshot,resolve}));}},100,123);
  const old = presenter.update(0);
  presenter.pause();
  requests[0].resolve({total:100,snapshot:123,items:['stale']}); await old;
  assert.equal(rendered.length,0);
  await presenter.update(112*50); assert.equal(requests.length,1);
  const fresh = presenter.reset();
  assert.equal(requests[1].offset,0); assert.equal(requests[1].snapshot,null);
  requests[1].resolve({total:0,snapshot:0,items:[]}); await fresh;
  const next = presenter.reset();
  requests[2].resolve({total:80,snapshot:150,items:[]}); await next;
  assert.equal(presenter.total,80); assert.equal(presenter.snapshot,150);
  assert.equal(rendered.length,2);
});
