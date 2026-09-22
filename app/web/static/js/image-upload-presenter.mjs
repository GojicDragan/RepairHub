/** Dateiauswahl und Anfragezustand; weder DOM noch fachliche Bildvalidierung. */
export class ImageUploadPresenter {
  constructor(view, source) { Object.assign(this, {view, source}); this.busy = false; }
  update(hasFile) { this.view.enabled(Boolean(hasFile) && !this.busy); }
  async submit(hasFile) {
    if (!hasFile || this.busy) return;
    this.busy = true;
    this.update(hasFile);
    this.view.message('');
    try {
      const result = await this.source.upload();
      if (result.ok) this.view.saved(result.body);
      else if (result.status === 401) this.view.expired();
      else this.view.failed(result.body?.error);
    } catch { this.view.failed(); }
    finally { this.busy = false; this.update(this.view.hasFile()); }
  }
}
