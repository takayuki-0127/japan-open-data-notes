/**
 * 申込シートの集計を自動にする（Google Apps Script）。
 * 前半の関数（normalizeText〜aggregate）は、スプレッドシートに触らない計算だけの関数で、Node で試験している。
 * 後半（runAggregation・installTrigger・onOpen）は SpreadsheetApp・ScriptApp を使う部分で、
 * Node の小さな模型でしか動かしていない（GAS 本体では未検証）。
 */
var CANCEL_WORDS = ['取消', '取り消し', 'キャンセル', 'cancel'];

function normalizeText(v) {
  if (v === null || v === undefined) return '';
  return String(v).normalize('NFKC').replace(/\s+/g, ' ').trim();
}

/** 人数：数字だけ・全角・「3名」「2人」を数に直す。空欄は1。読めないものは null（確認が要る行にする） */
function parseCount(v) {
  var s = normalizeText(v);
  if (s === '') return 1;
  var m = s.match(/^(\d+)\s*(名|人)?$/);
  if (!m) return null;
  var n = parseInt(m[1], 10);
  return (n >= 1 && n <= 20) ? n : null;
}

function isCancelled(v) {
  var s = normalizeText(v).toLowerCase();
  return CANCEL_WORDS.some(function (w) { return s.indexOf(w) !== -1; });
}

/** 1行を整える。空行は null */
function normalizeRow(row, rowNumber) {
  var ts = row[0], email = normalizeText(row[2]).toLowerCase(), course = normalizeText(row[3]);
  if (!email && !course && normalizeText(row[1]) === '') return null;
  return { rowNumber: rowNumber, time: new Date(ts).getTime(), name: normalizeText(row[1]), email: email,
           course: course, count: parseCount(row[4]), cancelled: isCancelled(row[5]) };
}

/**
 * 集計：同じメール×コースは、受付日時がいちばん新しい行だけを残す（取消のあとの申込し直しも、二重申込もこれで片づく）。
 * 取消の行と、人数が読めない行は集計に入れず、読めない行は review に出す。
 */
function aggregate(rows, courses) {
  var latest = {}, review = [];
  rows.forEach(function (row, i) {
    var r = normalizeRow(row, i + 2);
    if (!r) return;
    if (courses.indexOf(r.course) === -1) { review.push({ rowNumber: r.rowNumber, reason: 'コース名が一覧にない：' + r.course }); return; }
    if (!r.email) { review.push({ rowNumber: r.rowNumber, reason: 'メールが空欄' }); return; }
    var key = r.email + '|' + r.course;
    if (!latest[key] || r.time >= latest[key].time) latest[key] = r;
  });
  var out = {};
  courses.forEach(function (c) { out[c] = { applications: 0, people: 0 }; });
  Object.keys(latest).forEach(function (k) {
    var r = latest[k];
    if (r.cancelled) return;
    if (r.count === null) { review.push({ rowNumber: r.rowNumber, reason: '人数が読めない' }); return; }
    out[r.course].applications += 1; out[r.course].people += r.count;
  });
  review.sort(function (a, b) { return a.rowNumber - b.rowNumber; });
  return { summary: out, review: review };
}

// ---------- ここから下は GAS 本体では未検証 ----------
var COURSES = ['Excel入門', 'SQL入門', 'Python入門', '統計入門', 'BI入門'];

function runAggregation() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var src = ss.getSheetByName('申込');
  var values = src.getRange(2, 1, Math.max(src.getLastRow() - 1, 1), 6).getValues();
  var res = aggregate(values, COURSES);
  var dst = ss.getSheetByName('集計') || ss.insertSheet('集計');
  dst.clearContents();
  var table = [['コース', '申込件数', '人数', '集計した時刻']];
  var now = new Date();
  COURSES.forEach(function (c) { table.push([c, res.summary[c].applications, res.summary[c].people, now]); });
  dst.getRange(1, 1, table.length, 4).setValues(table);
  var rv = ss.getSheetByName('確認が要る行') || ss.insertSheet('確認が要る行');
  rv.clearContents();
  var rt = [['申込シートの行', '理由']].concat(res.review.map(function (x) { return [x.rowNumber, x.reason]; }));
  rv.getRange(1, 1, rt.length, 2).setValues(rt);
}

function installTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'runAggregation') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('runAggregation').timeBased().everyHours(1).create();
}

function onOpen() {
  SpreadsheetApp.getUi().createMenu('集計').addItem('いま集計する', 'runAggregation').addToUi();
}
