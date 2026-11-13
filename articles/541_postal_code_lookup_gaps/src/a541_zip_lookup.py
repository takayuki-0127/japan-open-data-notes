"""541 郵便番号から都道府県・市区町村を引くと、何件が引けないのか

実データ（日本郵便の郵便番号データ 2026年10月末時点＋2023年7月〜2026年10月の削除データ）で
(1) 番号の重なり・削除のされ方、(2) 1桁の打ち間違いと隣り合う数字の入れ替えを全通り試した結果 を数え、
(3) 架空の注文 20,000件（混ぜる割合は仮定）で、引き方 A〜D ごとの「引けない」「黙って違う場所」「照合で止まる」を数える。
A 住所の番号だけ / B 事業所の個別番号も / C B＋入力の都道府県と照合 / D C＋入力の市区町村とも照合
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：日本郵便「郵便番号データ」（2026年10月末時点、削除データ 2023年7月〜2026年10月）、架空の注文は seed 541"
cur = pd.read_csv(DATA / "zip_current.csv.gz", dtype=str)
dele = pd.read_csv(DATA / "zip_deleted.csv.gz", dtype=str)
ADDR, BIZ = {}, {}
for r in cur.itertuples():
    (ADDR if r.kind == "住所" else BIZ).setdefault(r.code, set()).add((r.pref, r.city))
BOTH = {c: ADDR.get(c, set()) | BIZ.get(c, set()) for c in set(ADDR) | set(BIZ)}
out = {}

# (1) 番号の重なり
npref = {c: len({p for p, _ in s}) for c, s in ADDR.items()}
out["codes"] = {"住所の番号": len(ADDR), "事業所の番号": len(BIZ), "両方にある番号": len(set(ADDR) & set(BIZ)),
                "複数の市区町村にまたがる住所の番号": sum(len({x for x in s}) > 1 for s in ADDR.values()),
                "複数の都道府県にまたがる住所の番号": sum(v > 1 for v in npref.values())}


def status(table, code, pref, city):
    s = table.get(code)
    if not s:
        return "引けない"
    if (pref, city) in s:
        return "合う" if len(s) == 1 else "候補が複数"
    if pref in {p for p, _ in s}:
        return "市区町村が違う"
    return "都道府県が違う"


# 削除された番号が、いま引くとどうなるか（削除行ごと）
dele["now"] = [status(BOTH, r.code, r.pref, r.city) for r in dele.itertuples()]
out["deleted"] = pd.crosstab(dele.kind, dele.now).to_dict(orient="index")
out["deleted_unique_codes"] = dele.groupby("kind").code.nunique().to_dict()
hm = dele[(dele.now == "市区町村が違う")]
out["deleted_city_changed_hamamatsu_share"] = round(float(hm.city.str.startswith("浜松市").mean()), 4)

# (2) 打ち間違いを全通り（住所の番号、1つの番号に複数の場所がある場合は最初の1つを正とする）
codes = sorted(ADDR)
truth = {c: sorted(ADDR[c])[0] for c in codes}
rows = []
for c in codes:
    p, ci = truth[c]
    for i in range(7):
        for dgt in "0123456789":
            if dgt != c[i]:
                rows.append(("1桁違い", c[:i] + dgt + c[i + 1:], p, ci))
        if i < 6 and c[i] != c[i + 1]:
            rows.append(("隣の数字と入れ替え", c[:i] + c[i + 1] + c[i] + c[i + 2:], p, ci))
ty = pd.DataFrame(rows, columns=["typo", "code", "pref", "city"])
for name, tab in [("A", ADDR), ("B", BOTH)]:
    ty[name] = [status(tab, *x) for x in zip(ty.code, ty.pref, ty.city)]
tsum = (ty.groupby("typo")[["A", "B"]].agg(lambda s: s.value_counts().to_dict()))
out["typo_n"] = ty.typo.value_counts().to_dict()
out["typo"] = {t: {m: {k: int(v) for k, v in tsum.loc[t, m].items()} for m in ["A", "B"]} for t in tsum.index}
ty.groupby(["typo", "B"]).size().rename("n").reset_index().to_csv(RES / "typo_all.csv", index=False)

# (3) 架空の注文（割合は仮定）
rng = np.random.default_rng(541)
N = 20000
MIX = {"住所の番号": 0.86, "事業所の個別番号": 0.08, "削除された古い番号": 0.02, "1桁違い": 0.03, "隣の数字と入れ替え": 0.01}
kinds = rng.choice(list(MIX), size=N, p=list(MIX.values()))
bcodes = sorted(BIZ)
drows = dele[["code", "pref", "city"]].to_numpy()
recs = []
for k in kinds:
    if k == "事業所の個別番号":
        c = bcodes[rng.integers(len(bcodes))]
        p, ci = sorted(BIZ[c])[rng.integers(len(BIZ[c]))]
        recs.append((k, c, p, ci))
    elif k == "削除された古い番号":
        c, p, ci = drows[rng.integers(len(drows))]
        recs.append((k, c, p, ci))
    else:
        c = codes[rng.integers(len(codes))]
        p, ci = sorted(ADDR[c])[rng.integers(len(ADDR[c]))]
        if k != "住所の番号":
            i = int(rng.integers(6 if k == "隣の数字と入れ替え" else 7))
            if k == "1桁違い":
                d = str((int(c[i]) + int(rng.integers(1, 10))) % 10)
                c = c[:i] + d + c[i + 1:]
            else:
                c = c[:i] + c[i + 1] + c[i] + c[i + 2:]
        recs.append((k, c, p, ci))
od = pd.DataFrame(recs, columns=["kind", "code", "pref", "city"])  # pref・city は入力された（本当の）場所
od["A"] = [status(ADDR, *x) for x in zip(od.code, od.pref, od.city)]
od["B"] = [status(BOTH, *x) for x in zip(od.code, od.pref, od.city)]
od.to_csv(RES / "orders.csv", index=False)


def judge(o, tab_col, check):
    """引けない／止まる（照合で要確認）／黙って都道府県が違う／黙って市区町村が違う／通る"""
    st = o[tab_col]
    if st == "引けない":
        return "引けない"
    if check >= 1 and st == "都道府県が違う":
        return "照合で止まる"
    if check >= 2 and st == "市区町村が違う":
        return "照合で止まる"
    if st == "都道府県が違う":
        return "黙って都道府県が違う"
    if st == "市区町村が違う":
        return "黙って市区町村が違う"
    return "通る"


ORDER = ["引けない", "黙って都道府県が違う", "黙って市区町村が違う", "照合で止まる", "通る"]
meth = {"A 住所の番号だけ": ("A", 0), "B 事業所の番号も": ("B", 0), "C B＋都道府県を照合": ("B", 1), "D C＋市区町村も照合": ("B", 2)}
res = {}
for m, (col, chk) in meth.items():
    od[m] = [judge(o, col, chk) for o in od[["A", "B"]].to_dict("records")]
    res[m] = od[m].value_counts().reindex(ORDER, fill_value=0).astype(int).to_dict()
out["orders_mix"] = MIX
out["orders_kind_n"] = od.kind.value_counts().to_dict()
out["orders"] = res
out["orders_by_kind_D"] = pd.crosstab(od.kind, od["D C＋市区町村も照合"]).to_dict(orient="index")
out["orders_by_kind_B"] = pd.crosstab(od.kind, od["B"]).to_dict(orient="index")
typo_pass = od[od.kind.isin(["1桁違い", "隣の数字と入れ替え"]) & (od["D C＋市区町村も照合"] == "通る")]
out["typo_pass_all_checks"] = int(len(typo_pass))
pd.DataFrame(res).T.to_csv(RES / "orders_summary.csv")
(RES / "a541_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=int))

# 図1 打ち間違いを全通り（B：住所＋事業所で引いたとき）
cats = ["引けない", "合う", "候補が複数", "市区町村が違う", "都道府県が違う"]
LAB1 = {"合う": "同じ市区町村の別の番号"}
LAB3 = {"合う": "同じ市区町村で引ける"}
col = {"引けない": GRAY, "合う": GREEN, "候補が複数": LIGHT, "市区町村が違う": BLUE, "都道府県が違う": ORANGE}
fig, ax = plt.subplots(figsize=(8.6, 3.3))
labs = ["1桁違い", "隣の数字と入れ替え"]
for yi, t in enumerate(labs):
    left = 0
    tot = out["typo_n"][t]
    for cname in cats:
        v = out["typo"][t]["B"].get(cname, 0) / tot * 100
        ax.barh(yi, v, left=left, color=col[cname], label=LAB1.get(cname, cname) if yi == 0 else None)
        if v >= 4:
            ax.text(left + v / 2, yi, f"{v:.1f}%", ha="center", va="center", fontsize=10, color="white" if cname != "候補が複数" else INK)
        left += v
ax.set_yticks(range(2), [f"{t}\n（{out['typo_n'][t]:,}通り）" for t in labs])
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("割合（%）")
ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=9)
ax.set_title("いまある住所の番号を1か所打ち間違えると、ほかの番号に当たるのは何%か", pad=48)
save(fig, "a541_typo_all.png", SRC, y=-0.07)

# 図2 架空の注文：引き方ごと
fig, ax = plt.subplots(figsize=(8.6, 4.2))
ms = list(meth)
show = ORDER[:4]
w = 0.2
cc = [GRAY, ORANGE, BLUE, GREEN]
for i, cname in enumerate(show):
    vals = [res[m][cname] for m in ms]
    xs = np.arange(len(ms)) + (i - 1.5) * w
    ax.bar(xs, vals, w, color=cc[i], label=cname)
    for x, v in zip(xs, vals):
        ax.text(x, v + 8, f"{v}", ha="center", fontsize=8.5)
ax.set_xticks(range(len(ms)), [m.replace(" ", "\n", 1) for m in ms])
ax.set_ylabel(f"件数（架空の注文 {N:,}件のうち）")
ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.02))
ax.set_ylim(0, max(max(res[m][c] for c in show) for m in ms) * 1.25)
ax.set_title("引き方で「引けない」「黙って違う場所」「照合で止まる」の件数はどう変わるか", pad=22)
save(fig, "a541_orders_by_method.png", SRC + "。混ぜる割合は仮定（README参照）")

# 図3 削除された番号は、いま引くとどうなるか
fig, ax = plt.subplots(figsize=(8.6, 3.0))
dc = ["引けない", "合う", "候補が複数", "市区町村が違う", "都道府県が違う"]
for yi, kd in enumerate(["住所", "事業所"]):
    dd = out["deleted"][kd]
    tot = sum(dd.values())
    left = 0
    for cname in dc:
        v = dd.get(cname, 0)
        ax.barh(yi, v / tot * 100, left=left, color=col[cname], label=LAB3.get(cname, cname) if yi == 0 else None)
        if v / tot * 100 >= 4:
            ax.text(left + v / tot * 50, yi, f"{v}件", ha="center", va="center", fontsize=10, color="white" if cname != "候補が複数" else INK)
        left += v / tot * 100
ax.set_yticks(range(2), [f"{kd}の番号\n（削除 {sum(out['deleted'][kd].values()):,}行）" for kd in ["住所", "事業所"]])
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("割合（%）")
ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=9)
ax.set_title("2023年7月〜2026年10月に削除された番号を、いまのデータで引くと", pad=48)
save(fig, "a541_deleted_now.png", SRC, y=-0.08)
print(json.dumps(out, ensure_ascii=False, indent=1, default=int))
