import { test } from 'node:test';
import assert from 'node:assert/strict';
import { FormCompletionPresenter } from '../../../app/web/static/js/form-completion-presenter.mjs';

test('Required fields enable submission only when all are filled, and clearing disables it again', () => {
  let fields = [{ value: '', password: false }, { value: '', password: true }];
  let enabled;
  const presenter = new FormCompletionPresenter({
    setFieldErrors: () => {},
    readRequiredFields: () => fields,
    setSubmitEnabled: value => { enabled = value; },
  });
  assert.equal(presenter.update(), false);
  fields[0].value = 'Lea';
  presenter.update();
  assert.equal(enabled, false);
  fields[1].value = 'my password';
  assert.equal(presenter.update(), true);
  assert.equal(enabled, true);
  fields[0].value = '   ';
  presenter.update();
  assert.equal(enabled, false);
});

test('Pre-filled forms work, passwords are not trimmed, and no fields cannot enable submission', () => {
  for (const [fields, expected] of [
    [[{ value: 'lea@example.org', password: false }], true],
    [[{ value: '        ', password: true }], true],
    [[{ value: '\t ', password: false }], false],
    [[], false],
  ]) {
    const presenter = new FormCompletionPresenter({
      setFieldErrors: () => {},
    readRequiredFields: () => fields,
      setSubmitEnabled: enabled => assert.equal(enabled, expected),
    });
    assert.equal(presenter.update(), expected);
  }
});

test('A populated field must also satisfy its configured format check', () => {
  let field = { value: 'not-an-email', password: false, valid: false };
  const states = [];
  const presenter = new FormCompletionPresenter({
    setFieldErrors: () => {},
    readRequiredFields: () => [field],
    setSubmitEnabled: enabled => states.push(enabled),
  });
  presenter.update();
  field = { value: 'lea@example.org', password: false, valid: true };
  presenter.update();
  field = { value: 'lea@', password: false, valid: false };
  presenter.update();
  assert.deepEqual(states, [false, true, false]);
});

test('Branded email feedback appears after blur and clears when corrected', () => {
  const field = { value: 'invalid', valid: false, feedback: true, touched: false };
  let error;
  const presenter = new FormCompletionPresenter({
    readRequiredFields: () => [field],
    setFieldErrors: errors => { [error] = errors; },
    setSubmitEnabled: () => {},
  });
  presenter.update();
  assert.equal(error, null);
  field.touched = true;
  presenter.update();
  assert.equal(error, 'email');
  field.value = '';
  presenter.update();
  assert.equal(error, 'required');
  field.value = 'lea@example.org';
  field.valid = true;
  presenter.update();
  assert.equal(error, null);
});

test('Password confirmation must match exactly and follows edits to either field', () => {
  const password = { name: 'password', value: 'secret phrase ', password: true };
  const confirmation = { name: 'password_confirm', matches: 'password', value: 'secret phrase', password: true, touched: false };
  let errors;
  let enabled;
  const presenter = new FormCompletionPresenter({
    readRequiredFields: () => [password, confirmation],
    setFieldErrors: value => { errors = value; },
    setSubmitEnabled: value => { enabled = value; },
  });
  presenter.update();
  assert.equal(enabled, false);
  assert.equal(errors[1], null);
  confirmation.touched = true;
  presenter.update();
  assert.equal(errors[1], 'password-match');
  confirmation.value = password.value;
  presenter.update();
  assert.equal(enabled, true);
  assert.equal(errors[1], null);
  password.value = 'changed password';
  presenter.update();
  assert.equal(enabled, false);
  assert.equal(errors[1], 'password-match');
  confirmation.value = '';
  presenter.update();
  assert.equal(enabled, false);
});

test('New passwords require eight Unicode characters even when confirmation matches', () => {
  for (const [value, expected] of [
    ['1234567', false], ['12345678', true], ['🔧'.repeat(4), false], ['🔧'.repeat(8), true],
  ]) {
    let enabled;
    let errors;
    const presenter = new FormCompletionPresenter({
      readRequiredFields: () => [
        { name: 'password', value, password: true, minimumLength: 8, touched: true },
        { name: 'password_confirm', value, password: true, matches: 'password' },
      ],
      setSubmitEnabled: state => { enabled = state; },
      setFieldErrors: state => { errors = state; },
    });
    presenter.update();
    assert.equal(enabled, expected);
    assert.equal(errors[0], expected ? null : 'password-length');
  }
});
