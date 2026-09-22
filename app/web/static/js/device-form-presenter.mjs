export function deviceFormComplete(values) {
  return ['name', 'manufacturer', 'model'].every(name => typeof values[name] === 'string' && values[name].trim().length > 0);
}

/** Koordiniert AJAX-Speichern; Eingabewerte bleiben bei Fehlern in der View erhalten. */
export class DeviceFormPresenter {
  constructor(view, source, original = null) {
    Object.assign(this, {view, source});
    this.original = original === null ? null : {...original};
    this.busy = false;
  }

  // Wie der Server Rand-Leerzeichen ignorieren; Gross-/Kleinschreibung und
  // Leerzeichen innerhalb eines Werts bleiben echte Änderungen.
  canSubmit(values) {
    return !this.busy && deviceFormComplete(values) && (this.original === null ||
      ['name', 'manufacturer', 'model'].some(name => values[name].trim() !== this.original[name].trim()));
  }

  async submit(values) {
    // Auch programmgesteuertes Absenden darf den deaktivierten Button nicht umgehen.
    if (!this.canSubmit(values)) return;
    this.busy = true;
    this.view.busy(true);
    this.view.errors({});
    try {
      const result = await this.source.save(values);
      if (result.status === 422) this.view.errors(result.body.errors);
      else if (result.status === 401) this.view.expired();
      else if (!result.ok) this.view.failed(result.body?.error);
      else {
        // Der Server normalisiert die Werte; erst ein Erfolg verschiebt die Vergleichsbasis.
        this.original = {...result.body.device};
        this.view.saved(result.body);
      }
    } catch (error) {
      this.view.failed();
    } finally {
      this.busy = false;
      this.view.busy(false);
    }
  }
}
