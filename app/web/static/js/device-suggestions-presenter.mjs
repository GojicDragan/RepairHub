/** Vorschlagsablauf ohne DOM; Freitext bleibt unabhängig von Treffern gültig. */
export class DeviceSuggestionsPresenter {
  constructor(view, source, schedule, cancel) {
    Object.assign(this, {view, source, schedule, cancel});
    this.generation = 0;
    this.items = [];
    this.active = -1;
  }

  close() {
    // Ein Abbruch allein genügt nicht: bereits empfangene Antworten dürfen
    // eine durch Blur/Escape geschlossene Vorschlagsliste nicht erneut öffnen.
    ++this.generation;
    this.cancel(this.timer);
    this.source.cancel();
    this.items = [];
    this.active = -1;
    this.view.close();
  }

  change(term, manufacturer) {
    this.close();
    if (term.trim().length < 2) return;
    const generation = this.generation;
    this.timer = this.schedule(async () => {
      this.view.loading();
      try {
        const items = await this.source.load(term, manufacturer);
        if (generation !== this.generation) return;
        this.items = items;
        this.view.show(items);
      } catch {
        if (generation === this.generation) this.view.failed();
      }
    }, 250);
  }

  key(key) {
    if (key === 'Escape') { this.close(); return true; }
    if (!this.items.length) return false;
    if (key === 'ArrowDown' || key === 'ArrowUp') {
      const step = key === 'ArrowDown' ? 1 : -1;
      this.active = this.active < 0 ? (step > 0 ? 0 : this.items.length - 1)
        : (this.active + step + this.items.length) % this.items.length;
      this.view.highlight(this.active);
      return true;
    }
    // Ohne bewusst markierten Treffer bleibt Enter das normale Formular-Absenden.
    if (key === 'Enter' && this.active >= 0) {
      this.select(this.active);
      return true;
    }
    return false;
  }

  select(index) {
    if (!Number.isInteger(index) || index < 0 || index >= this.items.length) return;
    const value = this.items[index];
    this.close();
    this.view.choose(value);
  }
}
