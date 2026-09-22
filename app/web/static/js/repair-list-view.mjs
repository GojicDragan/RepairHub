import { mountVirtualLists } from './virtual-list-view.mjs';

/** Reparaturzeilen sind ein reiner DOM-Adapter für dieselbe virtuelle Liste wie Geräte. */
export function mountRepairLists(root) {
  mountVirtualLists(root, {
    selector: '[data-repair-list]', rowsSelector: '[data-repair-rows]',
    itemAttribute: 'data-repair-id', namespace: 'repairs',
    renderRow(root, section, repair) {
      const row = root.createElement('li');
      row.className = 'device-row repair-row';
      row.dataset.repairId = repair.id;
      const link = root.createElement('a');
      link.className = 'repair-card';
      link.dataset.action = 'view';
      link.href = repair.url;
      const copy = root.createElement('div');
      copy.className = 'device-row-copy';
      const label = root.createElement('span');
      label.className = 'field-hint';
      label.textContent = `${repair.label} · ${repair.device_name}`;
      const title = root.createElement('h2');
      // Fehlertexte sind Nutzereingaben und werden niemals als HTML interpretiert.
      title.textContent = repair.description;
      title.title = repair.description;
      const status = root.createElement('span');
      status.className = `repair-status repair-status-${repair.status}`;
      status.textContent = repair.status_label;
      copy.append(label, title);
      link.append(copy, status);
      row.append(link);
      return row;
    }
  });
}
