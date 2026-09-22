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

import { mountRepairForms } from './repair-form-view.mjs';
mountRepairForms(document);

import { mountRepairLists } from './repair-list-view.mjs';
mountRepairLists(document);

import { mountImageUploads } from './image-upload-view.mjs';
mountImageUploads(document);
