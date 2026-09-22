import { mountFormCompletion } from './form-completion-view.mjs';
import { mountNotifications } from './notification-view.mjs';

// Module werden nach dem Parsen des Dokuments ausgeführt.
mountNotifications(document);

mountFormCompletion(document);

import { mountDeviceLists } from './device-list-view.mjs';
import { mountDeviceForms } from './device-form-view.mjs';
mountDeviceLists(document);
mountDeviceForms(document);

import { mountDeviceSuggestions } from './device-suggestions-view.mjs';
mountDeviceSuggestions(document);
