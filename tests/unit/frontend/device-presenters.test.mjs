import test from 'node:test';
import assert from 'node:assert/strict';
import { DeviceListPresenter, windowStart, WINDOW_SIZE, restoreScrollTop } from '../../../app/web/static/js/device-list-presenter.mjs';
import { DeviceFormPresenter, deviceFormComplete } from '../../../app/web/static/js/device-form-presenter.mjs';

const deferred = () => { let resolve, reject; const promise = new Promise((yes,no) => {resolve=yes; reject=no;}); return {promise,resolve,reject}; };

test('Virtual windows stay bounded and support scrolling backwards', () => {
  assert.equal(WINDOW_SIZE, 60);
  assert.equal(windowStart(0, 10000), 0);
  assert.equal(windowStart(112 * 800, 10000), 780);
  assert.equal(windowStart(112 * 40, 10000), 20);
  assert.equal(windowStart(-1, 10000), 0);
});

test('A late response cannot replace the current scroll window', async () => {
  const requests = [], rendered = [];
  const view = {loading(){}, failed(){assert.fail();}, render(page){rendered.push(page);}, idle(){}};
  const source = {load(start,limit,snapshot){const d=deferred(); requests.push({start,limit,snapshot,...d});return d.promise;}};
  const presenter = new DeviceListPresenter(view,source,1000,1000);
  const first = presenter.update(0);
  const second = presenter.update(112*100);
  requests[1].resolve('new'); await second;
  requests[0].resolve('old'); await first;
  assert.deepEqual(rendered,['new']);
  assert.equal(requests[1].limit,60);
  assert.equal(requests[1].snapshot,1000);
});

test('Returning to the loaded window invalidates an in-flight request', async () => {
  const rendered = [], pending = deferred(); let count=0;
  const view = {loading(){}, failed(){assert.fail();}, render(page){rendered.push(page);}, idle(){}};
  const source = {load(){return ++count===1 ? Promise.resolve({name:'first', total:1000, snapshot:1000}) : pending.promise;}};
  const presenter = new DeviceListPresenter(view,source,1000,1000);
  await presenter.update(0);
  const next=presenter.update(112*100);
  await presenter.update(0);
  pending.resolve('stale'); await next;
  assert.deepEqual(rendered,[{name:'first', total:1000, snapshot:1000}]);
});

test('List failure preserves the window and retry requests the same position', async () => {
  let failures=0, calls=0, rendered=0;
  const presenter = new DeviceListPresenter({loading(){},failed(){failures++;},render(){rendered++;}},
    {async load(){if(++calls===1)throw new Error();return {}; }},100,100);
  await presenter.update(0); await presenter.retry();
  assert.equal(failures,1); assert.equal(rendered,1);
});

test('Save prevents concurrent submissions and retains validation errors', async () => {
  const pending = deferred(), events=[];let calls=0;
  const view={busy(v){events.push(v);},errors(e){events.push(e);},failed(){assert.fail();},saved(){assert.fail();}};
  const presenter = new DeviceFormPresenter(view,{save(){calls++;return pending.promise;}});
  const first=presenter.submit({name:'x'.repeat(121),manufacturer:'Maker',model:'R1'}); await presenter.submit({name:'duplicate',manufacturer:'Maker',model:'R1'});
  pending.resolve({status:422,ok:false,body:{errors:{name:'required'}}});await first;
  assert.equal(calls,1); assert.deepEqual(events,[true,{}, {name:'required'},false]);
});

test('Save handles success, expired sessions and network failure with retry enabled', async () => {
  for (const mode of ['success','expired','network']) {
    const events=[];
    const view={busy(v){events.push(v);},errors(){},failed(){events.push('network');},expired(){events.push('expired');},saved(){events.push('success');}};
    const source={async save(){if(mode==='network')throw new Error();return {status:mode==='expired'?401:201,ok:mode==='success',body:{}};}};
    await new DeviceFormPresenter(view,source).submit({name:'Radio',manufacturer:'Maker',model:'R1'});
    assert.deepEqual(events,[true,mode,false]);
  }
});


test('Scroll restoration validates saved positions and clamps to the current list', () => {
  assert.equal(restoreScrollTop(11235, 0, 240, 560), 11235);
  for (const invalid of [null, '100', {}, -1, NaN, Infinity]) {
    assert.equal(restoreScrollTop(invalid, 20, 240, 560), 2240);
  }
  assert.equal(restoreScrollTop(99999, 0, 100, 560), 10640);
  assert.equal(restoreScrollTop(100, 0, 0, 560), 0);
});


test('Device save requires all fields and treats whitespace as empty', async () => {
  const values = {name:'Radio', manufacturer:'Maker', model:'R1'};
  assert.equal(deviceFormComplete(values), true);
  for (const field of Object.keys(values)) {
    for (const blank of ['', '   ', undefined]) {
      const incomplete = {...values, [field]: blank};
      assert.equal(deviceFormComplete(incomplete), false);
      const presenter = new DeviceFormPresenter({}, {save(){assert.fail('Incomplete form submitted');}});
      await presenter.submit(incomplete);
    }
  }
});


test('Editing requires a real change and reverting disables saving', async () => {
  const original = {name:'Radio', manufacturer:'Maker', model:'R1'};
  const presenter = new DeviceFormPresenter({}, {save(){assert.fail();}}, original);
  assert.equal(presenter.canSubmit({...original}), false);
  assert.equal(presenter.canSubmit({...original, name:' Radio '}), false);
  assert.equal(presenter.canSubmit({...original, name:'Changed'}), true);
  assert.equal(presenter.canSubmit({...original, model:''}), false);
  assert.equal(presenter.canSubmit({...original}), false);
  await presenter.submit(original);
});

test('Only successful saves update the comparison baseline', async () => {
  const original = {name:'Radio', manufacturer:'Maker', model:'R1'};
  const changed = {...original, name:'Other radio'};
  let success = false;
  const view = {busy(){},errors(){},failed(){},saved(){}};
  const presenter = new DeviceFormPresenter(view, {async save(){
    return success ? {ok:true,status:200,body:{device:changed}} : {ok:false,status:500};
  }}, original);
  await presenter.submit(changed);
  assert.equal(presenter.canSubmit(changed), true);
  success = true;
  await presenter.submit(changed);
  assert.equal(presenter.canSubmit(changed), false);
  assert.equal(presenter.canSubmit(original), true);
});
