import { VirtualListPresenter, ROW_HEIGHT, restoreScrollTop } from './virtual-list-presenter.mjs';

/** Humble Object: Datenfenster in eine feste, begrenzte Anzahl DOM-Zeilen übersetzen. */
export function mountVirtualLists(root, {selector, rowsSelector, itemAttribute, namespace, renderRow}) {
  for (const section of root.querySelectorAll(selector)) {
    const viewport = section.querySelector('[data-list-viewport]');
    const rows = section.querySelector(rowsSelector);
    const before = section.querySelector('[data-spacer-before]');
    const after = section.querySelector('[data-spacer-after]');
    const status = section.querySelector('[data-list-status]');
    const retry = section.querySelector('[data-list-retry]');
    const total = Number(section.dataset.total);
    const offset = Number(section.dataset.offset);
    // Tab- und benutzergebunden: keine Listendaten speichern oder fremde Listen übernehmen.
    const positionKey = `repairhub:${namespace}:scroll:${section.dataset.owner}:${location.pathname}${location.search}`;
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
        // Bestehende Filter (z.B. device_id) beim Fensterwechsel beibehalten.
        for (const [key, value] of Object.entries({offset: start, limit, snapshot})) url.searchParams.set(key, value);
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
        const focusedId = active?.closest(`[${itemAttribute}]`)?.getAttribute(itemAttribute);
        const focusedAction = active?.dataset.action;
        const fragment = root.createDocumentFragment();
        for (const [index, item] of page.items.entries()) {
          const row = renderRow(root, section, item);
          row.setAttribute('aria-posinset', page.offset + index + 1);
          row.setAttribute('aria-setsize', page.total);
          fragment.append(row);
        }
        // Ersetzen statt Anhängen: auch nach tausenden Datensätzen bleiben höchstens 60 Zeilen.
        rows.replaceChildren(fragment);
        // Platzhalter bilden die ausgelassenen Zeilen ab und erhalten die Gesamthöhe.
        before.style.height = `${page.offset * height}px`;
        after.style.height = `${Math.max(0, page.total - page.offset - page.items.length) * height}px`;
        viewport.scrollTop = scrollTop;
        // Ersetzte DOM-Knoten verlieren den Tastaturfokus. Nach Möglichkeit dieselbe
        // Aktion fokussieren, andernfalls den Scrollbereich, ohne die Position zu verändern.
        if (focused) {
          const target = rows.querySelector(`[${itemAttribute}="${focusedId}"] [data-action="${focusedAction || 'view'}"]`);
          (target || viewport).focus({preventScroll: true});
        }
        status.textContent = '';
        retry.hidden = true;
        viewport.setAttribute('aria-busy', 'false');
      }
    };
    const presenter = new VirtualListPresenter(view, source, total, Number(section.dataset.snapshot));
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
