"""02 整形：saidai_02 の都府県別「死者数」表 96 枚を縦持ちにし、各表の合計行と突き合わせる。人口推計も縦持ちに。"""
import re, sys, json, pathlib
import pandas as pd
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
raw, proc = out / "data/raw", out / "data/processed"
proc.mkdir(parents=True, exist_ok=True)
PREFS = ("茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 "
         "愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 "
         "愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県").split()
COLS = ["建物倒壊", "うち屋内", "津波", "急傾斜地", "火災", "ブロック塀等", "合計", "堤防増分"]  # PDF 上の列の並び
HEAD = re.compile(r"死者数（地震動：(.+?)ケース、津波ケース(.)、(.+?)、(.+?)、早期避難率(.+?)）")
NUM = re.compile(r"約\s*([\d,]+)")
w = pd.read_csv(raw / "f292_s2_words.csv")
rows, checks = [], []
for tid, (pg, g) in enumerate(w.groupby("page", sort=True)):
    head = g[g.text.str.contains("死者数（地震動", regex=False)]
    assert len(head) == 1, pg
    meta = dict(zip(["地震動", "津波ケース", "季節時刻", "風速", "避難"], HEAD.search(head.text.iloc[0]).groups()))
    meta["風速"] = meta["風速"].replace(" ", "")
    def cells(top):
        r = g[((g.top - top).abs() < 3) & (g.x0 > 100)]
        return [(x1, int(NUM.search(t).group(1).replace(",", ""))) for x1, t in zip(r.x1, r.text) if NUM.search(t)]
    trow = g[(g.text == "合計") & (g.x0 < 100)]
    assert len(trow) == 1, pg
    tc = cells(trow.top.iloc[0])
    assert len(tc) == 8, (pg, tc)
    anchors = [x for x, _ in tc]
    tot = [v for _, v in tc]
    recs = {}
    for p in PREFS:
        pr = g[(g.text == p) & (g.x0 < 100)]
        assert len(pr) == 1, (pg, p)
        v = [0] * 8
        for x1, val in cells(pr.top.iloc[0]):
            k = min(range(8), key=lambda a: abs(anchors[a] - x1))
            assert abs(anchors[k] - x1) < 12 and v[k] == 0, (pg, p, x1, val)
            v[k] = val
        recs[p] = v
    for p, v in recs.items():
        for c, x in zip(COLS, v):
            rows.append({"table": tid, "page": pg, **meta, "pref": p, "cause": c, "deaths": x})
    sums = [sum(v[k] for v in recs.values()) for k in range(8)]
    # 行内の整合：建物倒壊＋津波＋急傾斜地＋火災＋ブロック塀等 ≒ 合計（各値が丸めてあるので緩く）
    rowbad = [p for p, v in recs.items() if abs(v[0] + v[2] + v[3] + v[4] + v[5] - v[6]) > max(60, 0.06 * v[6])]
    checks.append({"table": tid, "page": int(pg), **meta, "printed": dict(zip(COLS, tot)),
                   "sum": dict(zip(COLS, sums)), "row_inconsistent": rowbad})
d = pd.DataFrame(rows)
d.to_csv(proc / "deaths_long.csv", index=False)
(proc / "table_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=0) + "\n")
# 合計（印刷値）と都府県の足し上げのずれ（四捨五入の範囲か）
bad, worst = [], 0
for c in checks:
    for k in COLS:
        a, b = c["printed"][k], c["sum"][k]
        if a >= 1000:
            worst = max(worst, abs(a - b) / a)
            if abs(a - b) / a > 0.03:
                bad.append((c["table"], k, a, b))
print("tables", len(checks), "rows", len(d), "最大ずれ(印刷値1000以上)", round(worst, 4), "3%超", bad)
pop = pd.read_csv(raw / "f292_pop.csv")
pop["year"] = pop.year.str.replace("年", "").astype(int)
pop.to_csv(proc / "pop_long.csv", index=False)
print("pop", pop.groupby("src").year.agg(["min", "max"]).to_dict())
