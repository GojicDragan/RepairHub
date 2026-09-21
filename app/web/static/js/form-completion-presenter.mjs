/** Formularfreigabe ohne DOM-Abhängigkeit; verbindlich validiert weiterhin der Server. */
export class FormCompletionPresenter {
  constructor(view) {
    this.view = view;
  }

  update() {
    const fields = this.view.readRequiredFields();
    const matches = field => !field.matches ||
      fields.some(other => other.name === field.matches && other.value === field.value);
    // Wie Python Unicode-Codepunkte zählen; UTF-16 würde manche Zeichen doppelt zählen.
    const longEnough = field => Array.from(field.value).length >= (field.minimumLength || 0);
    const complete = fields.length > 0 && fields.every(field => {
      const { value, password, valid = true } = field;
      // Leerzeichen können zum Passwort gehören; Zugangsdaten hier nicht normalisieren.
      return valid && (password ? value : value.trim()).length > 0 && matches(field) && longEnough(field);
    });
    this.view.setFieldErrors(fields.map(field => {
      const { value, feedback, touched, valid = true } = field;
      // Fehler erst nach dem Verlassen des Feldes anzeigen, nicht beim ersten Tippen.
      if ((!feedback && !field.matches && !field.minimumLength) || !touched) return null;
      if (field.minimumLength) return longEnough(field) ? null : 'password-length';
      if (field.matches) return matches(field) && value.length > 0 ? null : 'password-match';
      if (value.trim().length === 0) return 'required';
      return valid ? null : 'email';
    }));
    this.view.setSubmitEnabled(complete);
    return complete;
  }
}
