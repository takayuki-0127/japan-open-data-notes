// Code.gs を Node で読み込み、(1) 計算だけの関数の試験 (2) 小さな模型での runAggregation (3) CSV の集計 を行う
const fs = require('fs'), vm = require('vm'), path = require('path'), assert = require('assert');
const root = path.join(__dirname, '..');
const sheets = {};
const mkSheet = (name, values) => ({ name, values,
  getLastRow() { return this.values.length; },
  getRange(r, c, nr, nc) { const sh = this; return {
    getValues() { return sh.values.slice(r - 1, r - 1 + nr).map(x => x.slice(c - 1, c - 1 + nc)); },
    setValues(v) { v.forEach((row, i) => { sh.values[r - 1 + i] = row; }); } }; },
  clearContents() { this.values = []; } });
const ss = { getSheetByName: n => sheets[n] || null, insertSheet: n => (sheets[n] = mkSheet(n, [])) };
const ctx = { SpreadsheetApp: { getActiveSpreadsheet: () => ss }, ScriptApp: {}, console };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root, 'gas', 'Code.gs'), 'utf8'), ctx);

// (1) 計算だけの関数の試験
const T = [];
const t = (name, fn) => { try { fn(); T.push({ name, ok: true }); } catch (e) { T.push({ name, ok: false, err: String(e.message).slice(0, 80) }); } };
t('前後の空白を取る', () => assert.strictEqual(ctx.normalizeText('  SQL入門　'), 'SQL入門'));
t('全角の英数字を半角にそろえる', () => assert.strictEqual(ctx.normalizeText('ＳＱＬ入門'), 'SQL入門'));
t('人数：数字', () => assert.strictEqual(ctx.parseCount(3), 3));
t('人数：全角', () => assert.strictEqual(ctx.parseCount('２'), 2));
t('人数：「3名」', () => assert.strictEqual(ctx.parseCount('3名'), 3));
t('人数：空欄は1', () => assert.strictEqual(ctx.parseCount(''), 1));
t('人数：「未定」は読めない', () => assert.strictEqual(ctx.parseCount('未定'), null));
t('人数：0 や 100 は読めない扱い', () => { assert.strictEqual(ctx.parseCount(0), null); assert.strictEqual(ctx.parseCount(100), null); });
t('取消の書き方のゆれ', () => ['取消', 'キャンセル', '取り消し', ' Cancel '].forEach(w => assert.ok(ctx.isCancelled(w))));
t('空欄は取消ではない', () => assert.ok(!ctx.isCancelled('')));
t('空行は飛ばす', () => assert.strictEqual(ctx.normalizeRow(['', '', '', '', '', ''], 2), null));
const C = ['A', 'B'];
const agg = rows => ctx.aggregate(rows, C);
t('二重申込は新しい行だけ', () => { const r = agg([['2026-01-01 10:00', 'x', 'a@x.jp', 'A', 2, ''], ['2026-01-02 10:00', 'x', 'A@X.jp', 'A', 3, '']]); assert.deepStrictEqual(JSON.parse(JSON.stringify(r.summary.A)), { applications: 1, people: 3 }); });
t('取消のあとの申込し直しは数える', () => { const r = agg([['2026-01-01 10:00', 'x', 'a@x.jp', 'A', 2, '取消'], ['2026-01-03 10:00', 'x', 'a@x.jp', 'A', 1, '']]); assert.strictEqual(r.summary.A.people, 1); });
t('申込のあとの取消は数えない', () => { const r = agg([['2026-01-01 10:00', 'x', 'a@x.jp', 'A', 2, ''], ['2026-01-03 10:00', 'x', 'a@x.jp', 'A', 2, 'キャンセル']]); assert.strictEqual(r.summary.A.applications, 0); });
t('同じ人でもコースが違えば別', () => { const r = agg([['2026-01-01 10:00', 'x', 'a@x.jp', 'A', 1, ''], ['2026-01-01 11:00', 'x', 'a@x.jp', 'B', 1, '']]); assert.strictEqual(r.summary.A.applications + r.summary.B.applications, 2); });
t('一覧にないコースは確認が要る行へ', () => { const r = agg([['2026-01-01 10:00', 'x', 'a@x.jp', 'Z', 1, '']]); assert.strictEqual(r.review.length, 1); });
t('人数が読めない行は確認が要る行へ', () => { const r = agg([['2026-01-01 10:00', 'x', 'a@x.jp', 'A', '未定', '']]); assert.strictEqual(r.review.length, 1); assert.strictEqual(r.summary.A.applications, 0); });
t('メールが空欄の行は確認が要る行へ', () => { const r = agg([['2026-01-01 10:00', 'x', '', 'A', 1, '']]); assert.strictEqual(r.review.length, 1); });

// CSV の読み込み（引用符つき）
const parseCsv = s => { const out = []; let row = [], cur = '', q = false;
  for (let i = 0; i < s.length; i++) { const ch = s[i];
    if (q) { if (ch === '"') { if (s[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += ch; }
    else if (ch === '"') q = true; else if (ch === ',') { row.push(cur); cur = ''; }
    else if (ch === '\n') { row.push(cur); out.push(row); row = []; cur = ''; } else if (ch !== '\r') cur += ch; }
  if (cur !== '' || row.length) { row.push(cur); out.push(row); } return out; };

// (2) 模型での runAggregation（全部入りの申込シートで）
const all = parseCsv(fs.readFileSync(path.join(root, 'data', 'applications_all.csv'), 'utf8'));
sheets['申込'] = mkSheet('申込', all);
ctx.runAggregation();
const mock = { summary_rows: sheets['集計'].values.length, review_rows: sheets['確認が要る行'].values.length - 1,
               header: sheets['集計'].values[0].slice(0, 3) };

// (3) 場面ごとの CSV を集計
const res = {};
for (const f of fs.readdirSync(path.join(root, 'data')).filter(f => /^applications_.*\.csv$/.test(f)).sort()) {
  const v = parseCsv(fs.readFileSync(path.join(root, 'data', f), 'utf8')).slice(1);
  const r = ctx.aggregate(v, ctx.COURSES);
  res[f.replace('applications_', '').replace('.csv', '')] = { summary: r.summary, review: r.review.length };
}
fs.mkdirSync(path.join(root, 'results'), { recursive: true });
fs.writeFileSync(path.join(root, 'results', 'node_output.json'), JSON.stringify({ tests: T, mock, scenarios: res }, null, 1));
console.log('tests', T.filter(x => x.ok).length + '/' + T.length, T.filter(x => !x.ok).map(x => x.name + ':' + x.err).join(' | '), JSON.stringify(mock));
