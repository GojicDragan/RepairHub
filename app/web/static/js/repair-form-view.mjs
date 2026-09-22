import { RepairFormPresenter } from './repair-form-presenter.mjs';

/** Delegierte DOM-Ereignisse funktionieren auch nach serverseitig gerenderten AJAX-Updates. */
export function mountRepairForms(root) {
  const container = root.querySelector('[data-repair-content]');
  if (!container) return;
  const presenters = new WeakMap();
  // Jede Erfolgsantwort ersetzt den gesamten Detailbereich. Deshalb dürfen
  // verschiedene Formulare nicht gleichzeitig konkurrierende Antworten anwenden.
  let saving = false;
  const fields = form => [...form.querySelectorAll('[data-repair-field]')];
  const read = form => Object.fromEntries(fields(form).map(field => [field.name, field.type === 'checkbox' ? field.checked : field.value]));
  const key = form => new URL(form.action).pathname;
  const updateButtons = () => {
    for (const form of container.querySelectorAll('[data-repair-form]')) {
      form.querySelector('[type="submit"]').disabled = saving || !presenterFor(form).canSubmit(read(form));
    }
  };
  function presenterFor(form) {
    if (presenters.has(form)) return presenters.get(form);
    form.noValidate = true;
    // Nach Validierungsfehlern können Eingaben vom gespeicherten Stand abweichen;
    // Änderungsvergleiche verwenden deshalb die separaten Originalwerte des Servers.
    const original = form.dataset.existing === 'true'
      ? Object.fromEntries(fields(form).map(field => [field.name, field.type === 'checkbox' ? field.dataset.original === 'true' : field.dataset.original])) : null;
    const view = {
      busy(value) {
        saving = value;
        form.setAttribute('aria-busy', String(value));
        for (const field of fields(form)) {
          if (field.type === 'checkbox' || field.tagName === 'SELECT') field.disabled = value;
          else field.readOnly = value;
        }
        updateButtons();
      },
      errors(errors) {
        form.querySelector('[data-repair-form-status]').textContent = '';
        form.querySelector('[data-repair-login]').hidden = true;
        for (const field of fields(form)) {
          const message = errors[field.name] || '';
          form.querySelector(`[data-error-for="${field.name}"]`).textContent = message;
          field.classList.toggle('is-invalid', Boolean(message));
          field.setAttribute('aria-invalid', String(Boolean(message)));
        }
        // Der Fokus führt zum ersten fehlerhaften Feld; bestehende Entwürfe bleiben erhalten.
        fields(form).find(field => errors[field.name])?.focus();
      },
      expired() {
        form.querySelector('[data-repair-form-status]').textContent = container.dataset.expired;
        form.querySelector('[data-repair-login]').hidden = false;
      },
      failed(message) { form.querySelector('[data-repair-form-status]').textContent = message || container.dataset.failure; },
      saved(result) {
        // Andere, noch nicht gespeicherte Formulare beim Aktualisieren nicht verwerfen.
        const drafts = new Map([...container.querySelectorAll('[data-repair-form]')]
          .filter(other => other !== form && presenterFor(other).hasChanges(read(other)))
          .map(other => [key(other), read(other)]));
        // Ausschliesslich eigenes, durch Jinja escapedes HTML aus derselben Origin.
        container.innerHTML = result.html;
        for (const other of container.querySelectorAll('[data-repair-form]')) {
          const draft = drafts.get(key(other));
          if (!draft) continue;
          for (const field of fields(other)) {
            if (field.type === 'checkbox') field.checked = draft[field.name];
            else field.value = draft[field.name];
          }
        }
        // Nach der Erfassung gilt die Detail-URL, ohne für jedes Speichern einen
        // zusätzlichen Eintrag in der Zurück-Navigation anzulegen.
        history.replaceState(history.state, '', result.url);
        root.title = result.title;
        const message = container.querySelector('[data-repair-message]');
        if (message) message.textContent = result.message;
        container.querySelector('h1')?.focus({preventScroll: true});
      }
    };
    const source = {
      async save(values) {
        // Werte vor dem Sperren lesen; deaktivierte Selects fehlen sonst in FormData.
        const payload = {...values, csrf_token: form.elements.csrf_token.value};
        const response = await fetch(form.action, {
          method: 'POST', headers: {Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': form.elements.csrf_token.value},
          body: JSON.stringify(payload), signal: AbortSignal.timeout(20000)
        });
        return {ok: response.ok, status: response.status, body: await response.json()};
      }
    };
    const presenter = new RepairFormPresenter(view, source, original);
    presenters.set(form, presenter);
    return presenter;
  }
  for (const event of ['input', 'change', 'focusin']) container.addEventListener(event, updateButtons);
  container.addEventListener('reset', () => queueMicrotask(updateButtons));
  container.addEventListener('submit', event => {
    const form = event.target.closest('[data-repair-form]');
    if (!form) return;
    event.preventDefault();
    if (!saving) presenterFor(form).submit(read(form));
  });
  window.addEventListener('pageshow', updateButtons);
  updateButtons();
}
