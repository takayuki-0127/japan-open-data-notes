"""04 報告：毎月のチェックの結果を「1枚のチェック表」にする見本（2025年12月）。

- 確定：F247 の mart（確定）の2025年12月に、汚れを4つ入れたもの（見本のため。どれを入れたかは reports/dq_2025-12_見本_answer.json）
- 速報：締め5日の速報（data/versions/、02_整形.py）の2025年12月に、同じ汚れを入れたもの
- 出力：reports/dq_2025-12_{確定,速報}_見本.{md,html}・_flags.csv。図5は確定の HTML を画像にしたもの（05_図.py）
会社・数字はすべて架空（合成データ）。
"""
import json, pathlib, sys, warnings
import numpy as np
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dq_check as q
warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
REP = ROOT / "reports"; REP.mkdir(exist_ok=True)
MONTH = "2025-12"
summ = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
NAME = pd.read_csv(ROOT / "data" / "in" / "dim_store.csv", encoding="utf-8-sig").set_index("store_id").store_name.str.replace("サンプルマート", "").str.replace("（架空）", "")


def plant(cur, cat):
    """見本の汚れ：14店の廃棄を1か月千円で、05店の12/9を前日の写し、11店の12/16を2回足し込み、03店の12/22の人時を10倍、20店の12/12〜13の行なし"""
    cur = cur.copy(); cat = cat.copy()
    k = cur.store_id == 14; cur.loc[k, "waste"] /= 1000; cat.loc[cat.store_id == 14, "waste"] /= 1000
    a, b = (cur.store_id == 5) & (cur.biz_date == "2025-12-09"), (cur.store_id == 5) & (cur.biz_date == "2025-12-08")
    cols = [c for c in cur.columns if c not in ("biz_date", "store_id")]; cur.loc[a, cols] = cur.loc[b, cols].values
    ca, cb = (cat.store_id == 5) & (cat.biz_date == "2025-12-09"), (cat.store_id == 5) & (cat.biz_date == "2025-12-08")
    cat.loc[ca, ["sales", "gross_profit_before_waste", "waste"]] = cat.loc[cb, ["sales", "gross_profit_before_waste", "waste"]].values
    k = (cur.store_id == 11) & (cur.biz_date == "2025-12-16")
    cur.loc[k, ["receipts", "member_receipts", "items", "sales", "gross_profit_before_waste"]] *= 2
    cat.loc[(cat.store_id == 11) & (cat.biz_date == "2025-12-16"), ["sales", "gross_profit_before_waste"]] *= 2
    k = (cur.store_id == 3) & (cur.biz_date == "2025-12-22"); cur.loc[k, ["labor_hours", "labor_cost"]] *= 10
    d = (cur.store_id == 20) & cur.biz_date.isin(pd.to_datetime(["2025-12-12", "2025-12-13"]))
    dc = (cat.store_id == 20) & cat.biz_date.isin(pd.to_datetime(["2025-12-12", "2025-12-13"]))
    cur = cur[~d]; cat = cat[~dc]
    cur["gross_profit"] = cur.gross_profit_before_waste - cur.waste
    return cur, cat


ANSWER = [{"店": "郊外14店", "汚れ": "廃棄を1か月ずっと千円で入力（÷1000）"}, {"店": "都市05店", "日": "12/9", "汚れ": "前の日（12/8）の写し"},
          {"店": "郊外11店", "日": "12/16", "汚れ": "POS を2回足し込み（売上・客数・点数が2倍）"}, {"店": "都市03店", "日": "12/22", "汚れ": "人時が10倍"},
          {"店": "地方20店", "日": "12/12〜13", "汚れ": "行がない（2日）"}]


def fmt(v, metric):
    if pd.isna(v):
        return "—"
    if metric in ("売上", "廃棄", "部門の合計÷店の売上"):
        return f"{v / 1e4:,.1f}万円" if abs(v) >= 1e4 else f"{v:,.0f}円"
    if metric in ("一品単価", "時給"):
        return f"{v:,.0f}円"
    if metric in ("廃棄率",):
        return f"{v * 100:.2f}%"
    if metric in ("買上点数",):
        return f"{v:.2f}点"
    if metric in ("人時",):
        return f"{v:,.0f}時間"
    return f"{v:,.0f}"


def runs(f):
    """同じ店・チェック・列で続いた日を1行にまとめる"""
    out = []
    for (chk, sid, met, sev), gg in f.groupby(["check", "store_id", "metric", "重さ"], sort=False):
        gg = gg.sort_values("biz_date"); d = pd.to_datetime(gg.biz_date)
        grp = (d.diff().dt.days != 1).cumsum()
        for _, h in gg.groupby(grp.values):
            d0, d1 = pd.Timestamp(h.biz_date.iloc[0]), pd.Timestamp(h.biz_date.iloc[-1])
            out.append(dict(重さ=sev, check=chk, チェック=h["チェック"].iloc[0], 店=NAME.get(sid, sid), 日=(f"{d0.month}/{d0.day}" if d0 == d1 else f"{d0.month}/{d0.day}〜{d1.month}/{d1.day}（{len(h)}日）"),
                            列=met, 値=fmt(h.value.median(), met) if len(h) > 1 else fmt(h.value.iloc[0], met),
                            ふだん=fmt(h.ref.median(), met), 比=("—" if h.ratio.isna().all() else f"{h.ratio.median():.3g}倍"), 次にやること=h["次にやること"].iloc[0]))
    return pd.DataFrame(out)


def md_table(df, cols):
    s = "| " + " | ".join(cols) + " |\n|" + "|".join(["---"] * len(cols)) + "|\n"
    for _, r in df.iterrows():
        s += "| " + " | ".join(str(r[c]) for c in cols) + " |\n"
    return s


def build(cur, cat, hist, hcat, st, mode, stem):
    f, info = q.run_checks(cur, cat, hist, hcat, st, MONTH, mode=mode)
    f.to_csv(REP / f"{stem}_flags.csv", index=False, encoding="utf-8-sig")
    s = q.summary(f, info, MONTH, len(cur), mode)
    R = runs(f)
    R["_o"] = R["重さ"].map({"A": 0, "B": 1, "保留": 2}); R = R.sort_values(["_o", "check", "店"]).drop(columns="_o")
    cnt = []
    for k, (nm, sev, act) in q.CHECKS.items():
        x = f[f.check == k]
        cnt.append(dict(ID=k, チェック=nm, 重さ=sev if not (mode == "速報" and k == "Q02") else "A（未着は保留）", 件数=len(x),
                        店日=int(x[["store_id", "biz_date"]].drop_duplicates().shape[0]), 店=int(x.store_id.nunique())))
    cnt = pd.DataFrame(cnt)
    fa = summ["clean_flags_per_month"]
    lines = R[R["重さ"] != "保留"]
    pend = R[R["重さ"] == "保留"]
    nA = (R["重さ"] == "A").sum(); nB = (R["重さ"] == "B").sum()
    head = (f"# データ品質チェック {MONTH[:4]}年{int(MONTH[5:])}月（{mode}・見本）\n\n"
            f"サンプルマート（架空）・店×日 {len(cur):,} 行・部門 {len(cat):,} 行。src/dq_check.py で作成。**会社・数字はすべて架空の合成データ。見本のため汚れを入れてある。**\n\n"
            f"## 判定：{s['verdict']}\n\n"
            f"- 確かめること：{nA + nB} 件（A：数字が確実に壊れている {nA} 件、B：ふだんと大きく違う {nB} 件）"
            + (f"、保留（未着）：{len(pend)} 件" if len(pend) else "") + "\n"
            f"- A の店×日は、直すまで月の数字から外して表示する（レポートの「載せなかったもの」に書く）。B は店に確かめてから出す\n"
            f"- 汚れのない月でも、このチェックは1か月に平均 {summ['clean_store_days_per_month']:.1f} 店×日 鳴る（ふだんとの比 {fa['Q06']:.2f} 件・中の関係 {fa['Q07']:.2f} 件。20通り×24か月で測った）\n")
    body = "\n## チェックごとの件数\n\n" + md_table(cnt, ["ID", "チェック", "重さ", "件数", "店日", "店"])
    body += "\n## 確かめる一覧（続いた日は1行にまとめた）\n\n" + md_table(lines, ["重さ", "チェック", "店", "日", "列", "値", "ふだん", "比", "次にやること"])
    if len(pend):
        pp = pend.groupby("店").size().rename("件数").reset_index()
        body += f"\n## 保留（未着）：{len(pend)} 件・{pend['店'].nunique()} 店\n\n確定（翌月20日）でもう一度チェックし、まだ欠けていれば再送を頼む。\n\n" + md_table(pp, ["店", "件数"])
    nr = info["参照なしの店"]; nl = info["1年前の参照なしの店"]
    body += ("\n## 判定しなかったもの\n\n"
             f"- ふだんとの比（Q06）・中の関係（Q07）の参照がない店：{', '.join(NAME[i] for i in nr) if nr else 'なし'}（開店から8週未満）\n"
             f"- 1年前の参照がなく、前の8週だけで判定した店：{', '.join(NAME[i] for i in nl) if nl else 'なし'}（開店から1年未満。年末の動きで鳴りやすい）\n")
    md = head + body
    (REP / f"{stem}.md").write_text(md, encoding="utf-8")
    html = to_html(head, cnt, lines, pend, nr, nl, s, mode)
    (REP / f"{stem}.html").write_text(html, encoding="utf-8")
    return f, s, R


def to_html(head, cnt, lines, pend, nr, nl, s, mode):
    def tbl(df, cols, cls=""):
        h = "<table class='%s'><tr>" % cls + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
        for _, r in df.iterrows():
            sev = str(r.get("重さ", ""))
            h += f"<tr class='s{sev[:1]}'>" + "".join(f"<td>{r[c]}</td>" for c in cols) + "</tr>"
        return h + "</table>"
    nA = (lines["重さ"] == "A").sum(); nB = (lines["重さ"] == "B").sum()
    fa = summ["clean_store_days_per_month"]
    v = "要確認" if nA + nB else ("保留あり" if len(pend) else "合格")
    return f"""<!doctype html><html lang="ja"><meta charset="utf-8"><title>データ品質チェック {MONTH}</title>
<style>body{{font-family:'Noto Sans CJK JP','Noto Sans JP',sans-serif;margin:24px;color:#1f2933;width:1180px}}h1{{font-size:22px;margin:0 0 4px}}
.sub{{color:#52606d;font-size:12px}}.verdict{{display:inline-block;padding:6px 14px;border-radius:6px;font-weight:700;font-size:18px;margin:10px 0;background:#fde8e8;color:#9b1c1c}}
.kpi{{display:flex;gap:12px;margin:8px 0 14px}}.kpi div{{border:1px solid #d9e2ec;border-radius:6px;padding:8px 12px;font-size:12px;color:#52606d}}.kpi b{{display:block;font-size:20px;color:#1f2933}}
table{{border-collapse:collapse;font-size:12px;margin:6px 0 14px;width:100%}}th,td{{border-bottom:1px solid #e4e7eb;padding:4px 6px;text-align:left;vertical-align:top}}th{{background:#f5f7fa}}
th{{white-space:nowrap}}td:nth-child(1),td:nth-child(3),td:nth-child(4),td:nth-child(6),td:nth-child(7),td:nth-child(8){{white-space:nowrap}}tr.sA td:first-child{{color:#9b1c1c;font-weight:700}}tr.sB td:first-child{{color:#b45309;font-weight:700}}h2{{font-size:15px;margin:14px 0 2px;border-left:4px solid #3e4c59;padding-left:6px}}
.note{{font-size:11px;color:#616e7c}}table.small{{width:auto}}</style>
<h1>データ品質チェック {MONTH[:4]}年{int(MONTH[5:])}月（{mode}・見本）</h1>
<div class="sub">サンプルマート（架空）｜会社・数字はすべて架空の合成データ。見本のため汚れを入れてある｜src/dq_check.py</div>
<div class="verdict">判定：{v}</div>
<div class="kpi"><div>A 数字が確実に壊れている<b>{nA} 件</b></div><div>B ふだんと大きく違う<b>{nB} 件</b></div><div>保留（未着）<b>{len(pend)} 件</b></div><div>汚れのない月の目安<b>{fa:.1f} 店×日/月</b></div></div>
<h2>確かめる一覧</h2>{tbl(lines, ["重さ", "チェック", "店", "日", "列", "値", "ふだん", "比", "次にやること"])}
<h2>チェックごとの件数</h2>{tbl(cnt, ["ID", "チェック", "重さ", "件数", "店日", "店"], "small")}
<div class="note">判定しなかったもの：参照なし（開店8週未満）{len(nr)} 店／1年前の参照なし（前の8週だけで判定）{', '.join(NAME[i] for i in nl) if nl else 'なし'}。
A の店×日は直すまで月の数字から外し、B は店に確かめてから出す。</div></html>"""


fsd, cat, st = q.load_mart(ROOT / "data" / "in")
cur, cc, h, hc = q.split_month(fsd, cat, MONTH)
c1, k1 = plant(cur, cc)
fk, sk, Rk = build(c1, k1, h, hc, st, "確定", f"dq_{MONTH}_確定_見本")
V = ROOT / "data" / "versions"
sf = pd.read_csv(V / "fact_store_day_d5.csv.gz", parse_dates=["biz_date"]); sc = pd.read_csv(V / "fact_store_day_category_d5.csv.gz", parse_dates=["biz_date"])
scur, scc, _, _ = q.split_month(sf, sc, MONTH)
c2, k2 = plant(scur, scc)
fs, ss, Rs = build(c2, k2, h, hc, st, "速報", f"dq_{MONTH}_速報_見本")
(REP / f"dq_{MONTH}_見本_answer.json").write_text(json.dumps(dict(answer=ANSWER, 確定=sk, 速報=ss), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps(sk, ensure_ascii=False, default=str)); print(json.dumps(ss, ensure_ascii=False, default=str))
print(Rk.to_string())
