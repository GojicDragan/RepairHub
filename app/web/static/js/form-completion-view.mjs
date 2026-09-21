import { FormCompletionPresenter } from './form-completion-presenter.mjs';

/** Humble Object: übersetzt nur DOM-Werte, Ereignisse und den Zustand der Buttons. */
export class FormCompletionView {
  constructor(form) {
    this.form = form;
    this.touched = new Set();
    this.fields = [...form.querySelectorAll('[data-required-input]')];
    this.buttons = [...form.querySelectorAll('[type="submit"]')];
  }

  readRequiredFields() {
    return this.fields.map(field => ({
      name: field.name,
      matches: field.dataset.matchField,
      minimumLength: Number(field.dataset.minLength || 0),
      value: field.value,
      password: field.type === 'password',
      feedback: this.form.hasAttribute('data-validate-email') && field.type === 'email',
      touched: this.touched.has(field),
      // Der Browser prüft die Syntax; übersetzte Meldungen erscheinen im eigenen Design.
      valid: !this.form.hasAttribute('data-validate-email') ||
        field.type !== 'email' || field.validity.valid,
    }));
  }

  setFieldErrors(errors) {
    this.fields.forEach((field, index) => {
      const container = field.closest('.form-field');
      for (const message of container.querySelectorAll('[data-field-error]')) {
        message.hidden = message.dataset.fieldError !== errors[index];
      }
      field.classList.toggle('has-field-error', errors[index] !== null);
      // Eine bestandene Browserprüfung hebt noch keinen serverseitigen Fehler auf.
      const invalid = errors[index] !== null || container.querySelector('[data-server-error]') !== null;
      field.setAttribute('aria-invalid', String(invalid));
    });
  }

  setSubmitEnabled(enabled) {
    for (const button of this.buttons) button.disabled = !enabled;
  }

  bind(update) {
    const window = this.form.ownerDocument.defaultView;
    // Browser-Popups erst deaktivieren, wenn die eigene Fehleranzeige angebunden ist.
    if (this.form.hasAttribute('data-validate-email')) this.form.noValidate = true;
    this.form.addEventListener('focusout', event => {
      this.touched.add(event.target);
      update();
    });
    this.form.addEventListener('input', update);
    this.form.addEventListener('change', update);
    this.form.addEventListener('focusin', update);
    this.form.addEventListener('reset', () => {
      this.touched.clear();
      // Das reset-Ereignis kommt vor dem Zurücksetzen der Werte durch den Browser.
      window.queueMicrotask(update);
    });
    this.form.addEventListener('submit', event => {
      if (!update()) event.preventDefault();
    });

    // Manche Passwortmanager befüllen Felder ohne input/change-Ereignis. Auch
    // diese Werte abgleichen; beim Verlassen pausieren, auch im Zurück/Vorwärts-Cache.
    let timer;
    const start = () => {
      update();
      if (timer !== undefined) return;
      timer = window.setInterval(() => {
        if (!this.form.ownerDocument.hidden) update();
      }, 500);
    };
    window.addEventListener('pageshow', start);
    window.addEventListener('pagehide', () => {
      window.clearInterval(timer);
      timer = undefined;
    });
    start();
  }
}

export function mountFormCompletion(root) {
  for (const form of root.querySelectorAll('[data-form-completion]')) {
    const view = new FormCompletionView(form);
    const presenter = new FormCompletionPresenter(view);
    view.bind(() => presenter.update());
  }
}
