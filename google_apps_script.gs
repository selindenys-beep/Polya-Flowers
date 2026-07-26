/**
 * Polya Flowers — універсальне приймання записів у Google Sheets.
 *
 * Тепер скрипт універсальний: додаток сам передає назву аркуша (sheet),
 * заголовки (header) і рядок (row). Тому для нових аркушів/колонок у майбутньому
 * цей скрипт міняти НЕ потрібно — лише один раз оновити зараз.
 *
 * ЯК ОНОВИТИ (одноразово, ~2 хвилини):
 *  1. Таблиця → «Розширення» (Extensions) → «Apps Script».
 *  2. Видали весь код і встав цей файл повністю.
 *  3. У рядку SECRET_TOKEN встав СВІЙ токен У ЛАПКАХ (той самий, що вже використовується).
 *  4. «Розгорнути» (Deploy) → «Керувати розгортаннями» (Manage deployments) →
 *     олівець (Edit) → Version: «New version» → «Розгорнути» (Deploy). URL лишиться той самий.
 */

const SECRET_TOKEN = 'ВСТАВ_СВІЙ_ТОКЕН_У_ЛАПКАХ';

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    if (data.token !== SECRET_TOKEN) {
      return json({ ok: false, error: 'unauthorized' });
    }
    const sheetName = data.sheet || 'Дані';
    const header = data.header || [];
    const row = data.row || [];
    const sheet = getOrCreateSheet(sheetName, header);
    sheet.appendRow(row);
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
    if (header.length) {
      sheet.appendRow(header);
      sheet.getRange(1, 1, 1, header.length).setFontWeight('bold');
      sheet.setFrozenRows(1);
    }
  }
  return sheet;
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
