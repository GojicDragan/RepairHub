import test from 'node:test';
import assert from 'node:assert/strict';
import { RepairFormPresenter } from '../../../app/web/static/js/repair-form-presenter.mjs';

function setup(response, original = null) {
  const events = [];
  const view = Object.fromEntries(['busy', 'errors', 'failed', 'saved', 'expired'].map(name => [name, value => events.push([name, value])]));
  const source = {async save() { if (response instanceof Error) throw response; return response; }};
  return {presenter: new RepairFormPresenter(view, source, original), events};
}

test('Empty and unchanged forms cannot submit; explicit false is a valid completion state', () => {
  const {presenter} = setup({}, {description:'Cable', completed:false});
  assert.equal(presenter.canSubmit({description:' ', completed:true}), false);
  assert.equal(presenter.canSubmit({description:' Cable ', completed:false}), false);
  assert.equal(presenter.canSubmit({description:'Cable', completed:true}), true);
  assert.equal(presenter.canSubmit({description:'New cable', completed:false}), true);
  assert.equal(presenter.hasChanges({description:'', completed:false}), true);
  assert.equal(presenter.hasChanges({description:' Cable ', completed:false}), false);
});

test('Status changes allow reopening and prevent duplicate pending submissions', async () => {
  let finish, calls = 0;
  const {presenter, events} = setup({}, {status:'completed'});
  presenter.source.save = () => {calls++; return new Promise(resolve => {finish = resolve;});};
  const pending = presenter.submit({status:'in_progress'});
  await presenter.submit({status:'open'});
  assert.equal(calls, 1);
  finish({ok:true,body:{html:'rendered'}}); await pending;
  assert.deepEqual(events.at(-1), ['busy', false]);
});

test('Validation and network failures preserve retry capability', async () => {
  for (const response of [{ok:false,status:422,body:{errors:{description:'Invalid'}}}, new Error('offline')]) {
    const {presenter, events} = setup(response);
    await presenter.submit({description:'Cable'});
    assert.equal(presenter.canSubmit({description:'Cable'}), true);
    assert.equal(events.at(-2)[0], response instanceof Error ? 'failed' : 'errors');
  }
});


test('Expired sessions offer authentication without discarding the draft', async () => {
  const {presenter, events} = setup({ok:false,status:401,body:{error:'Expired'}});
  await presenter.submit({description:'Keep this draft'});
  assert.equal(events.at(-2)[0], 'expired');
  assert.equal(events.at(-1)[0], 'busy');
  assert.equal(presenter.canSubmit({description:'Keep this draft'}), true);
});
