/** Fensterberechnung und Anfragekoordination ohne Browser- oder DOM-Abhängigkeit. */
// Muss zur festen Zeilenhöhe in app.css passen, sonst driften Platzhalter und Scrollposition.
export const ROW_HEIGHT = 112;
export const PAGE_SIZE = 20;
export const WINDOW_SIZE = 60;

export function windowStart(scrollTop, total) {
  const position = Math.min(Math.max(0, scrollTop / ROW_HEIGHT), Math.max(0, total - 1));
  // Eine Seite oberhalb vorladen; das 60er-Fenster puffert beide Scrollrichtungen.
  return Math.max(0, (Math.floor(position / PAGE_SIZE) - 1) * PAGE_SIZE);
}

/** Gespeicherte Positionen bleiben auch nach Listen- oder Grössenänderungen gültig. */
export function restoreScrollTop(saved, offset, total, viewportHeight) {
  const fallback = offset * ROW_HEIGHT;
  const top = typeof saved === 'number' && Number.isFinite(saved) && saved >= 0 ? saved : fallback;
  return Math.min(top, Math.max(0, total * ROW_HEIGHT - viewportHeight));
}

export class VirtualListPresenter {
  constructor(view, source, total, snapshot) {
    Object.assign(this, { view, source, total, snapshot });
    this.generation = 0;
    this.loaded = null;
    this.pending = null;
    this.paused = false;
  }

  async update(scrollTop) {
    if (this.paused) return;
    this.top = scrollTop;
    const start = windowStart(scrollTop, this.total);
    // Zurückscrollen ins vorhandene Fenster benötigt keinen neuen Request,
    // muss aber eine noch laufende Antwort für ein anderes Fenster entwerten.
    if (start === this.loaded && this.pending !== null) {
      ++this.generation;
      this.pending = null;
      this.view.idle();
    }
    if (start === this.loaded || start === this.pending || this.total === 0) return;
    const generation = ++this.generation;
    this.pending = start;
    this.view.loading();
    try {
      const page = await this.source.load(start, WINDOW_SIZE, this.snapshot);
      // Eine langsame ältere Antwort darf die neuere Scrollposition nicht überschreiben.
      if (generation !== this.generation) return;
      this.total = page.total;
      this.snapshot = page.snapshot;
      this.view.render(page, ROW_HEIGHT);
      this.loaded = start;
    } catch (error) {
      if (generation === this.generation) this.view.failed();
    } finally {
      if (generation === this.generation) this.pending = null;
    }
  }

  pause() {
    // Bereits beim Tippen entwerten, nicht erst nach Ablauf der Eingabepause.
    ++this.generation;
    this.pending = null;
    this.paused = true;
  }

  reset() {
    this.pause();
    this.paused = false;
    this.loaded = null;
    this.snapshot = null;
    // Auch nach einer leeren Trefferliste muss das erste neue Fenster geladen werden.
    this.total = 1;
    return this.update(0);
  }

  retry() { return this.update(this.top); }
}
