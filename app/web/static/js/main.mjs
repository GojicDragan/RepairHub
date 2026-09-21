import { mountFormCompletion } from './form-completion-view.mjs';
import { mountNotifications } from './notification-view.mjs';

// Module werden nach dem Parsen des Dokuments ausgeführt.
mountNotifications(document);

mountFormCompletion(document);
