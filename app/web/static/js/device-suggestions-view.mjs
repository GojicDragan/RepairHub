import { DeviceSuggestionsPresenter } from './device-suggestions-presenter.mjs';

/** Humble Objects kapseln Fetch, native Eingaben und die markeneigene Vorschlagsliste. */
export function mountDeviceSuggestions(root) {
  for (const form of root.querySelectorAll('[data-device-form]')) {
    for (const field of form.querySelectorAll('[data-suggestion-field]')) {
      const input = field.querySelector('input');
      const list = field.querySelector('[data-suggestions]');
      const status = field.querySelector('[data-suggestion-status]');
      const popup = field.querySelector('[data-suggestion-popup]');
      let controller;
      const source = {
        cancel() { controller?.abort(); },
        async load(term, manufacturer) {
          controller = new AbortController();
          const url = new URL(form.dataset.suggestionsUrl, location.href);
          url.search = new URLSearchParams({field: input.name, term, manufacturer});
          const response = await fetch(url, {
            headers: {Accept: 'application/json'},
            signal: AbortSignal.any([controller.signal, AbortSignal.timeout(5000)])
          });
          if (!response.ok) throw new Error('suggestions_failed');
          return (await response.json()).items;
        }
      };
      const view = {
        close() {
          popup.hidden = true;
          list.hidden = true;
          list.replaceChildren();
          input.setAttribute('aria-expanded', 'false');
          input.removeAttribute('aria-activedescendant');
          status.textContent = '';
        },
        loading() { popup.hidden = false; status.textContent = form.dataset.suggestionsLoading; },
        failed() { popup.hidden = false; status.textContent = form.dataset.suggestionsFailure; },
        show(items) {
          popup.hidden = false;
          const fragment = root.createDocumentFragment();
          items.forEach((value, index) => {
            const option = root.createElement('li');
            option.id = `${list.id}-${index}`;
            option.setAttribute('role', 'option');
            option.setAttribute('aria-selected', 'false');
            // Auch gespeicherte Vorschläge sind Benutzereingaben, kein HTML.
            option.textContent = value;
            // Fokus bleibt im Eingabefeld; Auswahl löst kein vorzeitiges Blur aus.
            option.addEventListener('mousedown', event => event.preventDefault());
            option.addEventListener('click', () => presenter.select(index));
            fragment.append(option);
          });
          list.replaceChildren(fragment);
          list.hidden = items.length === 0;
          input.setAttribute('aria-expanded', String(items.length > 0));
          status.textContent = items.length ? form.dataset.suggestionsFound : form.dataset.suggestionsEmpty;
        },
        highlight(index) {
          [...list.children].forEach((option, position) => option.setAttribute('aria-selected', String(position === index)));
          input.setAttribute('aria-activedescendant', list.children[index].id);
          list.children[index].scrollIntoView({block: 'nearest'});
        },
        choose(value) {
          input.value = value;
          input.dispatchEvent(new Event('change', {bubbles: true}));
        }
      };
      // Browser-Timer über Funktionen injizieren: Als Presenter-Methode aufgerufen
      // hätten native Timer sonst einen falschen this-Kontext (Illegal invocation).
      const presenter = new DeviceSuggestionsPresenter(view, source, (fn, delay) => setTimeout(fn, delay), timer => clearTimeout(timer));
      input.setAttribute('role', 'combobox');
      input.setAttribute('aria-autocomplete', 'list');
      input.setAttribute('aria-controls', list.id);
      input.setAttribute('aria-expanded', 'false');
      input.setAttribute('autocomplete', 'off');
      const refresh = () => presenter.change(input.value, form.elements.manufacturer.value);
      input.addEventListener('input', refresh);
      input.addEventListener('focus', refresh);
      input.addEventListener('blur', () => presenter.close());
      input.addEventListener('keydown', event => {
        // Enter während einer IME-Zeicheneingabe bestätigt noch keinen Vorschlag.
        if (!event.isComposing && presenter.key(event.key)) event.preventDefault();
      });
      if (input.name === 'model') {
        // Ein Herstellerwechsel darf keine bereits geladenen fremden Modelle anbieten.
        form.elements.manufacturer.addEventListener('input', () => presenter.close());
        form.elements.manufacturer.addEventListener('change', () => presenter.close());
      }
      form.addEventListener('submit', () => presenter.close());
      form.addEventListener('reset', () => presenter.close());
      window.addEventListener('pagehide', () => presenter.close());
    }
  }
}
