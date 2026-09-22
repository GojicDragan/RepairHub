import { mountVirtualLists } from './virtual-list-view.mjs';

/** Gerätezeilen darstellen; Scrollen und Zustand sind für alle Listen gemeinsam. */
export function mountDeviceLists(root) {
  mountVirtualLists(root, {selector: '[data-device-list]', rowsSelector: '[data-device-rows]', itemAttribute: 'data-device-id', namespace: 'devices', renderRow(root, section, device) {
          const row = root.createElement('li');
          row.className = 'device-row';
          row.dataset.deviceId = device.id;
          const copy = root.createElement('div');
          copy.className = 'device-row-copy';
          const link = root.createElement('a');
          link.className = 'device-name';
          link.dataset.action = 'view';
          // Den Pfad erweitern, ohne den Suchbegriff in die Geräte-ID einzubauen.
          const detailUrl = new URL(section.dataset.url, location.href);
          detailUrl.pathname += `/${device.id}`;
          link.href = detailUrl.href;
          // Gerätetexte sind Benutzereingaben: niemals als HTML in den DOM einsetzen.
          link.textContent = device.name;
          link.title = device.name;
          const description = root.createElement('p');
          description.textContent = `${device.manufacturer} · ${device.model}`;
          description.title = description.textContent;
          const edit = root.createElement('a');
          edit.className = 'btn btn-outline-secondary btn-sm';
          edit.dataset.action = 'edit';
          const editUrl = new URL(detailUrl);
          editUrl.pathname += '/edit';
          edit.href = editUrl.href;
          edit.textContent = section.dataset.editLabel;
          edit.setAttribute('aria-label', `${section.dataset.editLabel}: ${device.name}`);
          copy.append(link, description);
          row.append(copy, edit);
    return row;
  }});
}
