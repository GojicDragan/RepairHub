import { DeviceListPresenter, ROW_HEIGHT, restoreScrollTop } from './device-list-presenter.mjs';

/** Humble Object: Datenfenster in eine feste, begrenzte Anzahl DOM-Zeilen übersetzen. */
export function mountDeviceLists(root) {
  for (const section of root.querySelectorAll('[data-device-list]')) {
    const viewport = section.querySelector('[data-list-viewport]');
    const rows = section.querySelector('[data-device-rows]');
    const before = section.querySelector('[data-spacer-before]');
    const after = section.querySelector('[data-spacer-after]');
    const status = section.querySelector('[data-list-status]');
    const retry = section.querySelector('[data-list-retry]');
    const total = Number(section.dataset.total);
    const offset = Number(section.dataset.offset);
    // Tab- und benutzergebunden: keine Gerätedaten speichern oder fremde Listen übernehmen.
    const positionKey = `repairhub:devices:scroll:${section.dataset.owner}:${location.pathname}${location.search}`;
    let savedPosition = null;
    try { savedPosition = JSON.parse(sessionStorage.getItem(positionKey)); } catch { /* Speicher kann gesperrt sein. */ }
    const rememberPosition = () => {
      try { sessionStorage.setItem(positionKey, JSON.stringify(viewport.scrollTop)); } catch { /* Scrollen bleibt ohne Speicher nutzbar. */ }
    };
    let controller;
    const source = {
      async load(start, limit, snapshot) {
        controller?.abort();
        controller = new AbortController();
        const url = new URL(section.dataset.url, location.href);
        url.search = new URLSearchParams({offset: start, limit, snapshot});
        const response = await fetch(url, {headers: {Accept: 'application/json'}, signal: AbortSignal.any([controller.signal, AbortSignal.timeout(20000)])});
        if (!response.ok) throw new Error('load_failed');
        return response.json();
      }
    };
    const view = {
      idle() { status.textContent = ""; retry.hidden = true; viewport.setAttribute("aria-busy", "false"); },
      loading() { status.textContent = section.dataset.loading; retry.hidden = true; viewport.setAttribute('aria-busy', 'true'); },
      failed() { status.textContent = section.dataset.failure; retry.hidden = false; viewport.setAttribute('aria-busy', 'false'); },
      render(page, height) {
        const scrollTop = viewport.scrollTop;
        const active = root.activeElement;
        const focused = rows.contains(active);
        const focusedId = active?.closest('[data-device-id]')?.dataset.deviceId;
        const focusedAction = active?.dataset.action;
        const fragment = root.createDocumentFragment();
        for (const [index, device] of page.items.entries()) {
          const row = root.createElement('li');
          row.className = 'device-row';
          row.dataset.deviceId = device.id;
          row.setAttribute('aria-posinset', page.offset + index + 1);
          row.setAttribute('aria-setsize', page.total);
          const copy = root.createElement('div');
          copy.className = 'device-row-copy';
          const link = root.createElement('a');
          link.className = 'device-name';
          link.dataset.action = 'view';
          link.href = `${section.dataset.url}/${device.id}`;
          // Gerätetexte sind Benutzereingaben: niemals als HTML in den DOM einsetzen.
          link.textContent = device.name;
          link.title = device.name;
          const description = root.createElement('p');
          description.textContent = `${device.manufacturer} · ${device.model}`;
          description.title = description.textContent;
          const edit = root.createElement('a');
          edit.className = 'btn btn-outline-secondary btn-sm';
          edit.dataset.action = 'edit';
          edit.href = `${section.dataset.url}/${device.id}/edit`;
          edit.textContent = section.dataset.editLabel;
          edit.setAttribute('aria-label', `${section.dataset.editLabel}: ${device.name}`);
          copy.append(link, description);
          row.append(copy, edit);
          fragment.append(row);
        }
        // Ersetzen statt Anhängen: auch nach tausenden Datensätzen bleiben höchstens 60 Zeilen.
        rows.replaceChildren(fragment);
        // Platzhalter bilden die ausgelassenen Zeilen ab und erhalten die Gesamthöhe.
        before.style.height = `${page.offset * height}px`;
        after.style.height = `${Math.max(0, page.total - page.offset - page.items.length) * height}px`;
        viewport.scrollTop = scrollTop;
        if (focused) {
          const target = rows.querySelector(`[data-device-id="${focusedId}"] [data-action="${focusedAction || 'view'}"]`);
          (target || viewport).focus({preventScroll: true});
        }
        status.textContent = '';
        retry.hidden = true;
        viewport.setAttribute('aria-busy', 'false');
      }
    };
    const presenter = new DeviceListPresenter(view, source, total, Number(section.dataset.snapshot));
    viewport.classList.add('is-virtual');
    before.style.height = `${offset * ROW_HEIGHT}px`;
    after.style.height = `${Math.max(0, total - offset - rows.children.length) * ROW_HEIGHT}px`;
    // Erst mit vollständiger virtueller Höhe kann der Browser eine tiefe Position
    // wiederherstellen, ohne sie auf die kurze serverseitige Startliste zu begrenzen.
    viewport.scrollTop = restoreScrollTop(savedPosition, offset, total, viewport.clientHeight);
    section.querySelector('[data-list-pagination]').hidden = true;
    let scheduled = false;
    viewport.addEventListener('scroll', () => {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(() => { scheduled = false; presenter.update(viewport.scrollTop); });
    });
    retry.addEventListener('click', () => presenter.retry());
    presenter.update(viewport.scrollTop);
    // Vor der Detailnavigation sichern; pagehide deckt zusätzlich andere Rückwege ab.
    section.addEventListener('click', rememberPosition, {capture: true});
    window.addEventListener('pagehide', () => { rememberPosition(); controller?.abort(); });
    window.addEventListener('pageshow', () => presenter.update(viewport.scrollTop));
  }
}
