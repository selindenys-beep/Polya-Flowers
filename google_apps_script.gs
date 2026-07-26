/**
 * Polya Flowers — приймання записів у Google Sheets.
 *
 * ЯК ВСТАНОВИТИ (одноразово, ~2 хвилини):
 *  1. Відкрий таблицю → меню «Розширення» (Extensions) → «Apps Script».
 *  2. Видали увесь код у редакторі та встав цей файл повністю.
 *  3. Заміни значення SECRET_TOKEN нижче на свій довгий випадковий рядок
 *     (те саме значення потім вкажемо у SHEETS_WEBHOOK_TOKEN застосунку).
 *  4. Натисни «Розгорнути» (Deploy) → «Новий розгорток» (New deployment) →
 *     тип «Веб-застосунок» (Web app).
 *       • Execute as: Me (твій акаунт)
 *       • Who has access: Anyone
 *  5. Скопіюй URL веб-застосунку (…/exec) і надішли його — покладемо у
 *     SHEETS_WEBHOOK_URL.
 */

const SECRET_TOKEN = 'ЗАМІНИ_МЕНЕ_НА_ДОВГИЙ_ВИПАДКОВИЙ_РЯДОК';

const SHEETS = {
  sale: {
    name: 'Продажі',
    header: ['Дата', 'ID товару', 'Опис', 'Ціна', 'Підпис', 'Посилання на пост'],
    row: function (d) {
      return [new Date(), d.product_id || '', d.description || '', d.price || '',
              d.caption || '', d.post_url || ''];
    },
  },
};

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    if (data.token !== SECRET_TOKEN) {
      return json({ ok: false, error: 'unauthorized' });
    }
    const cfg = SHEETS[data.type] || SHEETS.sale;
    const sheet = getOrCreateSheet(cfg.name, cfg.header);
    sheet.appendRow(cfg.row(data));
    return json({ ok: true });
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}

function getOrCreateSheet(name, header) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(header);
    sheet.getRange(1, 1, 1, header.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
