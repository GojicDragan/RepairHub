/** Speichern, Änderungsvergleich und Fehlerzustand ohne DOM oder Flask. */
export class RepairFormPresenter {
  constructor(view, source, original = null) {
    Object.assign(this, {view, source, original});
    this.busy = false;
  }

  canSubmit(values) {
    const names = Object.keys(values);
    // false ist ein gültiger Erledigungszustand, kein leeres Pflichtfeld.
    return !this.busy && names.length > 0 && names.every(name =>
      typeof values[name] === 'boolean' || String(values[name]).trim().length > 0
    ) && (this.original === null || this.hasChanges(values));
  }

  hasChanges(values) {
    // Auch vorübergehend leere Entwürfe beim Speichern eines anderen Formulars erhalten.
    return Object.keys(values).some(name =>
      String(values[name]).trim() !== String(this.original?.[name] ?? '').trim()
    );
  }

  async submit(values) {
    if (!this.canSubmit(values)) return;
    this.busy = true;
    this.view.busy(true);
    this.view.errors({});
    try {
      const result = await this.source.save(values);
      if (result.ok) this.view.saved(result.body);
      else if (result.status === 422) this.view.errors(result.body.errors);
      else this.view.failed(result.body?.error);
    } catch {
      this.view.failed();
    } finally {
      this.busy = false;
      this.view.busy(false);
    }
  }
}
