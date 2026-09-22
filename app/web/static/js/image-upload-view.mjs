import { ImageUploadPresenter } from './image-upload-presenter.mjs';

/** Nur Galerie ersetzen: Entwürfe der übrigen Reparaturformulare bleiben erhalten. */
export function mountImageUploads(root) {
  // Ausgetauschte Galerieformulare sollen mitsamt ihrem Presenter freigegeben werden können.
  const presenters = new WeakMap();
  function presenter(form) {
    if (presenters.has(form)) return presenters.get(form);
    const section = form.closest('[data-image-gallery]');
    const deleting = form.hasAttribute('data-image-delete');
    // Löschen verwendet denselben Anfrageablauf, benötigt aber keine Dateiauswahl.
    const available = () => deleting || Boolean(form.elements.image.files.length);
    const view = {
      hasFile: available,
      enabled(value) { form.querySelector('[type=submit]').disabled = !value; },
      message(value) { section.querySelector('[data-image-message]').textContent = value; },
      failed(message) { view.message(message || (deleting ? section.dataset.deleteFailure : section.dataset.failure)); },
      expired() { view.message(section.dataset.expired); },
      saved(result) {
        section.outerHTML = result.html;
        initialise();
        root.querySelector('[data-image-message]').textContent = result.message;
        root.querySelector('#image-file').focus();
      },
    };
    const instance = new ImageUploadPresenter(view, {
      async upload() {
        const response = await fetch(form.action, {
          method: 'POST', body: new FormData(form),
          headers: {Accept: 'application/json', 'X-CSRFToken': form.elements.csrf_token.value},
          signal: AbortSignal.timeout(60000),
        });
        const body = await response.json();
        return {ok: response.ok, status: response.status, body};
      },
    });
    presenters.set(form, instance);
    return instance;
  }
  function initialise() {
    for (const form of root.querySelectorAll('[data-image-form], [data-image-delete]')) {
      presenter(form).update(form.hasAttribute('data-image-delete') || Boolean(form.elements.image.files.length));
    }
  }
  root.addEventListener('change', event => {
    const form = event.target.closest('[data-image-form], [data-image-delete]');
    if (form) presenter(form).update(form.hasAttribute('data-image-delete') || Boolean(form.elements.image.files.length));
  });
  // Ereignisse am stabilen Vorfahren behandeln: Auch neu gerenderte Formulare funktionieren.
  root.addEventListener('submit', event => {
    const form = event.target.closest('[data-image-form], [data-image-delete]');
    if (!form) return;
    event.preventDefault();
    presenter(form).submit(form.hasAttribute('data-image-delete') || Boolean(form.elements.image.files.length));
  });
  // Pagination bleibt bewusst eine normale Navigation; jedes Fenster ist auf 24 Bilder begrenzt.
  initialise();
}
