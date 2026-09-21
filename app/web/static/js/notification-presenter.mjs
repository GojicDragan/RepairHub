/** UI-Verhalten ohne DOM, HTML, Bootstrap oder Browser-Globals. */
export class NotificationPresenter {
  constructor(view) {
    this.view = view;
    this.dismissed = false;
  }

  dismiss() {
    // Mehrfach ausgelöste Ereignisse dürfen Entfernen und Fokuswechsel nicht wiederholen.
    if (this.dismissed) return;
    this.dismissed = true;
    // Vor dem Entfernen Fokusverlust für Tastaturbedienung vermeiden.
    this.view.focusReturnTarget();
    this.view.remove();
  }
}
