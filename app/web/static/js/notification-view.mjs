import { NotificationPresenter } from './notification-presenter.mjs';

/** Humble Object: nur DOM-Bindung; Entscheidungen trifft der Presenter. */
export class NotificationView {
  constructor(element, returnTarget) {
    this.element = element;
    this.returnTarget = returnTarget;
  }

  bind(onDismiss) {
    const button = this.element.querySelector('[data-dismiss-notification]');
    button.addEventListener('click', onDismiss);
    // Erst nach der Ereignisbindung anzeigen: Ohne JS bleibt die Meldung lesbar,
    // aber es erscheint kein funktionsloser Schliessbutton.
    button.hidden = false;
  }

  focusReturnTarget() {
    this.returnTarget.focus();
  }

  remove() {
    this.element.remove();
  }
}

// Einmalige Verdrahtung für die serverseitig gerenderte Seite. root hält die
// DOM-Auswahl aus dem Presenter heraus; jede Meldung erhält ihren eigenen Zustand.
export function mountNotifications(root) {
  const returnTarget = root.querySelector('#content');
  for (const element of root.querySelectorAll('[data-notification]')) {
    const view = new NotificationView(element, returnTarget);
    const presenter = new NotificationPresenter(view);
    view.bind(() => presenter.dismiss());
  }
}
