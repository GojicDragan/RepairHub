/** Eingabepause und explizites Anwenden ohne DOM- oder Timer-Abhängigkeit. */
export class ListFilterPresenter {
  constructor(view, schedule, cancel) {
    Object.assign(this, {view, schedule, cancel});
    this.timer = null;
  }

  changed() {
    this.cancelPending();
    // Während der Eingabepause dürfen alte Suchantworten die Liste nicht aktualisieren.
    this.view.pending();
    this.timer = this.schedule(() => this.apply(), 300);
  }

  apply() {
    this.cancelPending();
    this.view.apply();
  }

  cancelPending() {
    if (this.timer !== null) this.cancel(this.timer);
    this.timer = null;
  }
}
