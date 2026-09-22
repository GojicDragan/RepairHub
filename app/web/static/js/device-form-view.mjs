import { DeviceFormPresenter } from './device-form-presenter.mjs';

/** Humble Object: Formularwerte, Fokus und übersetzte Meldungen an den DOM binden. */
export function mountDeviceForms(root) {
  for (const form of root.querySelectorAll('[data-device-form]')) {
    // Nach JS-Anbindung erscheinen auch Pflichtfeldfehler im eigenen Design.
    form.noValidate = true;
    const fields = ['name', 'manufacturer', 'model'];
    const status = form.querySelector('[data-save-status]');
    const link = form.querySelector('[data-saved-link]');
    const login = form.querySelector('[data-login-link]');
    const values = () => Object.fromEntries(fields.map(name => [name, form.elements[name].value]));
    const updateButton = () => {
      form.querySelector('[type="submit"]').disabled = !presenter.canSubmit(values());
    };
    const view = {
      busy(value) {
        updateButton();
        form.setAttribute('aria-busy', String(value));
        for (const name of fields) form.elements[name].readOnly = value;
      },
      errors(errors) {
        status.textContent = '';
        link.hidden = true;
        login.hidden = true;
        for (const name of fields) {
          form.querySelector(`[data-error-for="${name}"]`).textContent = errors[name] || '';
          form.elements[name].classList.toggle('is-invalid', Boolean(errors[name]));
          form.elements[name].setAttribute('aria-invalid', String(Boolean(errors[name])));
        }
        const first = fields.find(name => errors[name]);
        if (first) form.elements[first].focus();
      },
      expired() { status.textContent = form.dataset.expired; login.hidden = false; },
      failed(message) { status.textContent = message || form.dataset.failure; },
      saved(result) {
        status.textContent = result.message;
        link.href = result.url;
        link.hidden = false;
        // Weitere Speicheraktionen bearbeiten das eben erstellte Gerät statt Duplikate anzulegen.
        form.action = result.edit_url;
        form.dataset.saved = 'true';
        for (const name of fields) form.elements[name].value = result.device[name];
      }
    };
    const source = {
      async save(values) {
        const response = await fetch(form.action, {
          method: 'POST',
          signal: AbortSignal.timeout(20000),
          headers: {Accept: 'application/json', 'Content-Type': 'application/json',
                    'X-CSRFToken': form.elements.csrf_token.value},
          body: JSON.stringify(values)
        });
        const body = await response.json();
        return {status: response.status, ok: response.ok, body};
      }
    };
    // Nach einem serverseitigen Formularfehler stehen in den Inputs bereits die
    // abgelehnten Eingaben; die Vergleichsbasis kommt separat vom gespeicherten Gerät.
    const original = form.dataset.editing === 'true'
      ? Object.fromEntries(fields.map(name => [name, form.elements[name].dataset.originalValue]))
      : null;
    const presenter = new DeviceFormPresenter(view, source, original);
    form.addEventListener('input', updateButton);
    // Autocomplete setzt den Wert programmatisch und meldet ihn über change.
    form.addEventListener('change', updateButton);
    form.addEventListener('focusin', updateButton);
    form.addEventListener('reset', () => queueMicrotask(updateButton));
    window.addEventListener('pageshow', updateButton);
    updateButton();
    form.addEventListener('submit', event => {
      event.preventDefault();
      presenter.submit(values());
    });
  }
}
