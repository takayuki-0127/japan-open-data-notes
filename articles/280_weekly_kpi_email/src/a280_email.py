"""週次 KPI のメールを作り、ファイルに書き出す（送らない）。送る前の確認（数字がそろったか）もここで行う。"""
import io, json, re, duckdb, pandas as pd, matplotlib.pyplot as plt
from email.message import EmailMessage
from email import policy
from email.parser import BytesParser
from email.utils import make_msgid, formatdate
from common import DATA, SQL, RES, ROOT, BLUE, GRAY, tsql_to_duckdb
df = pd.read_csv(DATA / "weekly_kpi.csv")
expected = "2025-12-29"  # 2026-01-05（月）に送る、前の週
# 1) 送る前の確認（T-SQL の文を DuckDB で動かす。DECLARE の変数は値に置き換える）
q = (SQL / "01_freshness.sql").read_text()
q = re.sub(r"DECLARE @expected_week DATE = '([\d-]+)';", "", q).replace("@expected_week", f"DATE '{expected}'").replace("dbo.", "")
con = duckdb.connect(); con.register("weekly_kpi", df.assign(week_start=pd.to_datetime(df.week_start).dt.date))
status_ok = con.execute(tsql_to_duckdb(q)).fetchone()
part = df[df.week_start != expected]  # 最後の週がまだ入っていない状態
con.register("weekly_kpi", part.assign(week_start=pd.to_datetime(part.week_start).dt.date))
status_wait = con.execute(tsql_to_duckdb(q)).fetchone()
assert status_ok[2] == "OK" and status_wait[2] == "WAIT"
# 2) 中身：KPI ごとに今週・前週比・4週平均比
w = df.pivot(index="week_start", columns="kpi", values="value").sort_index()
cur, prev, avg4 = w.iloc[-1], w.iloc[-2], w.iloc[-5:-1].mean()
rows = [(k, cur[k], (cur[k] / prev[k] - 1) * 100, (cur[k] / avg4[k] - 1) * 100) for k in w.columns]
# 3) 小さな推移の図（12週、売上）を PNG にしてメールに埋め込む
fig, ax = plt.subplots(figsize=(4.2, 1.3), dpi=110)
s = w["売上（百万円）"].iloc[-12:]; ax.plot(range(12), s.values, color=BLUE, lw=2); ax.scatter([11], [s.values[-1]], color=BLUE, s=18)
ax.set_axis_off(); buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight"); plt.close(fig); png = buf.getvalue()
cid = "<sparkline-2025-12-29@example.invalid>"  # 毎回同じ名前にする
def arrow(x): return ("▲", "#3aa07a") if x > 0 else ("▼", "#eb6834")
trs = "".join(
    f'<tr><td style="padding:6px 10px;border-bottom:1px solid #e3e2de">{k}</td>'
    f'<td style="padding:6px 10px;border-bottom:1px solid #e3e2de;text-align:right;font-weight:bold">{v:,.1f}</td>'
    f'<td style="padding:6px 10px;border-bottom:1px solid #e3e2de;text-align:right;color:{arrow(d1)[1]}">{arrow(d1)[0]} {d1:+.1f}%</td>'
    f'<td style="padding:6px 10px;border-bottom:1px solid #e3e2de;text-align:right;color:{arrow(d4)[1]}">{arrow(d4)[0]} {d4:+.1f}%</td></tr>'
    for k, v, d1, d4 in rows)
top = max(rows, key=lambda r: abs(r[3]))
html = f"""<div style="font-family:sans-serif;max-width:560px;color:#0b0b0b">
<p style="font-size:15px;margin:0 0 8px"><b>週次 KPI（{expected} の週）</b></p>
<p style="margin:0 0 12px">いちばん大きく動いたのは<b>{top[0]}</b>で、4週平均より {top[3]:+.1f}% でした。</p>
<table style="border-collapse:collapse;font-size:13px;width:100%">
<tr style="background:#2a78d6;color:#ffffff"><th style="padding:6px 10px;text-align:left">KPI</th><th style="padding:6px 10px;text-align:right">今週</th><th style="padding:6px 10px;text-align:right">前週比</th><th style="padding:6px 10px;text-align:right">4週平均比</th></tr>
{trs}</table>
<p style="margin:14px 0 2px;font-size:12px;color:#6b6a65">売上（百万円）の直近12週</p>
<img src="cid:{cid[1:-1]}" alt="売上の直近12週の推移" style="width:360px">
<p style="font-size:11px;color:#6b6a65">集計表の {expected} の週が4つの KPI ともそろったことを確かめてから作成しました。数字は架空です。</p></div>"""
text = f"週次 KPI（{expected} の週）\nいちばん大きく動いたのは{top[0]}で、4週平均より {top[3]:+.1f}% でした。\n\n" + "\n".join(
    f"- {k}: {v:,.1f}（前週比 {d1:+.1f}%、4週平均比 {d4:+.1f}%）" for k, v, d1, d4 in rows) + "\n\n数字は架空です。\n"
msg = EmailMessage(policy=policy.SMTP)
msg["Subject"] = f"[週次KPI] {expected} の週：{top[0]} 4週平均比 {top[3]:+.1f}%"
msg["From"] = "report@example.invalid"; msg["To"] = "team@example.invalid"; msg["Date"] = formatdate(1767567600, localtime=False)  # 2026-01-05 07:00 JST ごろ（例）
msg["Message-ID"] = "<weekly-2025-12-29@example.invalid>"
msg.set_content(text); msg.add_alternative(html, subtype="html")
msg.get_payload()[1].add_related(png, maintype="image", subtype="png", cid=cid)
def send(m, dry_run=True):
    """dry_run=True（既定）ではファイルに書くだけ。この記事では送っていない"""
    if dry_run:
        p = ROOT / "output" / "weekly_2025-12-29.eml"; p.write_bytes(m.as_bytes()); return p
    raise RuntimeError("この記事のコードでは送信しない（SMTP の設定は各自の環境で）")
p = send(msg)
# 4) 書き出したメールを読み戻して確かめる
back = BytesParser(policy=policy.default).parsebytes(p.read_bytes())
parts = [x.get_content_type() for x in back.walk()]
h = back.get_body(("html",)).get_content(); t = back.get_body(("plain",)).get_content()
cids = re.findall(r'src="cid:([^"]+)"', h); att = [x["Content-ID"].strip("<>") for x in back.walk() if x.get_content_type() == "image/png"]
nums = lambda s: sorted(re.findall(r"[+-]?\d[\d,]*\.\d", s))
res = {"freshness_full": list(map(str, status_ok)), "freshness_missing_last_week": list(map(str, status_wait)),
       "parts": parts, "size_kb": round(p.stat().st_size / 1024, 1), "cid_refs_resolved": set(cids) <= set(att) and len(cids) == 1,
       "numbers_text_equal_html": nums(t) == nums(re.sub("<[^>]+>", " ", h)), "n_numbers": len(nums(t)),
       "style_tags": h.count("<style"), "inline_style_attrs": h.count('style="'), "subject": back["Subject"]}
json.dump(res, open(RES / "email_checks.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(res, ensure_ascii=False, indent=1))
(ROOT / "output" / "preview.html").write_text(h.replace(f"cid:{cids[0]}", "sparkline.png"), encoding="utf-8")
(ROOT / "output" / "sparkline.png").write_bytes(png)
