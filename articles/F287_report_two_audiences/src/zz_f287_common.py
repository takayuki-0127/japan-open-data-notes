"""F287 共通：架空の会社「みどり堂（架空）」の合成データ、3つのレポートの生成、測り方。

- データは乱数で合成（種を固定）。実在の会社・顧客のデータは使わない。
- レポートは「ブロック」（見出し・本文・含む事実・表示する数字の数）の列として作る。
"""
import numpy as np
import pandas as pd
import re

DEPTS = ["文具", "書籍", "雑貨", "カフェ"]
DEPT_SHARE = np.array([0.36, 0.30, 0.22, 0.12])
DEPT_MARGIN = np.array([0.38, 0.27, 0.42, 0.62])
SEASON = np.array([1.18, 0.93, 0.92, 0.98, 1.04, 0.90, 0.95, 0.96, 1.20, 0.92, 0.88, 1.14])  # 4月始まり
MONTHS = pd.period_range("2023-04", "2026-03", freq="M")
FY25 = [m for m in MONTHS if m >= pd.Period("2025-04", "M")]
WAGE = 1100.0


def store_names(n):
    return [f"S{i+1:02d}" for i in range(n)]


def store_size(n):
    # 規模を S・M・L に3等分（店の番号順に L→M→S）
    k = int(np.ceil(n / 3))
    return {s: ("L" if i < k else "M" if i < 2 * k else "S") for i, s in enumerate(store_names(n))}


def events(n):
    """本当の動き（答え）。店の番号は店の数によらず同じ相対位置に置く。"""
    st = store_names(n)
    return {
        "cust_drop": (st[int(round(n * 7 / 12)) - 1], pd.Period("2025-07", "M"), -0.08),   # ある店の客数 −8%
        "cafe_up": (st[int(round(n * 3 / 12)) - 1], pd.Period("2025-05", "M"), 0.15),      # ある店のカフェ +15%
        "zakka_margin": ("雑貨", pd.Period("2025-10", "M"), -0.02),                         # 雑貨の粗利率 −2pt（全店）
        "price": (pd.Period("2025-04", "M"), 0.03),                                           # 全社の単価 +3%
    }


def gen(seed=287, n=12, with_events=True):
    """店×部門×月の数字を合成する。"""
    rng = np.random.default_rng(seed)
    st = store_names(n)
    size = store_size(n)
    base = {"L": 52.0, "M": 34.0, "S": 21.0}  # 月の売上（百万円）の目安
    ev = events(n)
    rows = []
    store_lvl = {s: base[size[s]] * rng.uniform(0.9, 1.1) for s in st}
    store_trend = {s: rng.normal(0.01, 0.015) for s in st}
    for s in st:
        for di, d in enumerate(DEPTS):
            dlev = store_lvl[s] * DEPT_SHARE[di] * rng.uniform(0.9, 1.1)
            for t, m in enumerate(MONTHS):
                yrs = t / 12.0
                trend = (1 + store_trend[s]) ** yrs
                cust = dlev / 1.6 * 1000 * SEASON[t % 12] * trend * np.exp(rng.normal(0, 0.035))  # 百人ではなく人
                ticket = 1600 * (1.012 ** yrs) * np.exp(rng.normal(0, 0.02))
                margin = DEPT_MARGIN[di] + rng.normal(0, 0.006)
                if with_events:
                    if m >= ev["price"][0]:
                        ticket *= 1 + ev["price"][1]
                    s1, m1, e1 = ev["cust_drop"]
                    if s == s1 and m >= m1:
                        cust *= 1 + e1
                    s2, m2, e2 = ev["cafe_up"]
                    if s == s2 and d == "カフェ" and m >= m2:
                        cust *= 1 + e2
                    d3, m3, e3 = ev["zakka_margin"]
                    if d == d3 and m >= m3:
                        margin += e3
                sales = cust * ticket / 1e6  # 百万円
                hours = sales * 1e6 / 4200 * np.exp(rng.normal(0, 0.03))
                rows.append((s, size[s], d, str(m), t, cust, sales, sales * margin, hours))
    df = pd.DataFrame(rows, columns=["store", "size", "dept", "month", "t", "cust", "sales", "gp", "hours"])
    return df


def plan_of(df):
    """FY2025 の計画：前年同月の売上 ×1.02、営業利益は前年同月 ×1.02（作成者が置いた計画）。"""
    return 1.02


def kpis(df):
    """全社・部門・店・店×部門の月次の KPI 表を作る。"""
    fixed_per_store = 1.0  # 百万円/月（その他の経費）
    g = {}
    co = df.groupby("month").agg(sales=("sales", "sum"), gp=("gp", "sum"), cust=("cust", "sum"), hours=("hours", "sum"))
    co["op"] = co.gp - co.hours * WAGE / 1e6 - fixed_per_store * df.store.nunique()
    g["co"] = co
    g["dept"] = df.groupby(["dept", "month"]).agg(sales=("sales", "sum"), gp=("gp", "sum"), cust=("cust", "sum"))
    st = df.groupby(["store", "month"]).agg(sales=("sales", "sum"), gp=("gp", "sum"), cust=("cust", "sum"), hours=("hours", "sum"))
    g["store"] = st
    g["sd"] = df.groupby(["store", "dept", "month"]).agg(sales=("sales", "sum"))
    g["size"] = df.groupby("store")["size"].first()
    return g


def yoy(series_now, series_prev):
    return (series_now / series_prev - 1) * 100


def month_view(g, m, bands, rule="rel"):
    """月 m の数字をまとめる（レポートに載せる値）。bands は偶然の幅（前年比の pt、90%の半幅）。"""
    m = pd.Period(m, "M")
    py = str(m - 12); pm = str(m - 1); ms = str(m); nx = str(m + 1)
    co = g["co"]
    v = {}
    v["co_sales"] = co.loc[ms, "sales"]; v["co_sales_py"] = co.loc[py, "sales"]
    v["co_sales_yoy"] = yoy(v["co_sales"], v["co_sales_py"])
    v["co_sales_plan"] = (v["co_sales"] / (v["co_sales_py"] * 1.02) - 1) * 100
    v["co_op"] = co.loc[ms, "op"]; v["co_op_plan"] = (co.loc[ms, "op"] / (co.loc[py, "op"] * 1.02) - 1) * 100
    v["co_cust_yoy"] = yoy(co.loc[ms, "cust"], co.loc[py, "cust"])
    tk_now = co.loc[ms, "sales"] / co.loc[ms, "cust"]; tk_py = co.loc[py, "sales"] / co.loc[py, "cust"]
    v["co_ticket_yoy"] = yoy(tk_now, tk_py)
    v["co_gpr"] = co.loc[ms, "gp"] / co.loc[ms, "sales"] * 100
    v["co_gpr_py"] = co.loc[py, "gp"] / co.loc[py, "sales"] * 100
    # 部門
    dep = {}
    for d in DEPTS:
        x = g["dept"].loc[(d, ms)]; xp = g["dept"].loc[(d, py)]
        gy = yoy(x.sales, xp.sales); gpr = x.gp / x.sales * 100; gprp = xp.gp / xp.sales * 100
        dep[d] = dict(sales=x.sales, yoy=gy, gpr=gpr, gpr_d=gpr - gprp,
                      out=bool(abs(gy - (v["co_sales_yoy"] if rule == "rel" else 0)) > bands["dept_sales"] or abs(gpr - gprp) > bands["dept_gpr"]))
    v["dept"] = dep
    # 店
    sto = {}
    for s in g["size"].index:
        x = g["store"].loc[(s, ms)]; xp = g["store"].loc[(s, py)]
        sy = yoy(x.sales, xp.sales); cy = yoy(x.cust, xp.cust)
        lp = x.sales * 1e6 / x.hours
        wd = min(DEPTS, key=lambda d: yoy(g["sd"].loc[(s, d, ms)].sales, g["sd"].loc[(s, d, py)].sales))
        wdy = yoy(g["sd"].loc[(s, wd, ms)].sales, g["sd"].loc[(s, wd, py)].sales)
        sto[s] = dict(sales=x.sales, yoy=sy, cust_yoy=cy, ticket_yoy=yoy(x.sales / x.cust, xp.sales / xp.cust),
                      lp=lp, worst=wd, worst_yoy=wdy, size=g["size"][s],
                      out=bool(abs(cy - (v["co_cust_yoy"] if rule == "rel" else 0)) > bands["store_cust"] or abs(sy - (v["co_sales_yoy"] if rule == "rel" else 0)) > bands["store_sales"]))
    # 同じ規模の中での順位（売上前年比）
    for sz in ["L", "M", "S"]:
        mem = [s for s in sto if sto[s]["size"] == sz]
        ordr = sorted(mem, key=lambda s: -sto[s]["yoy"])
        for i, s in enumerate(ordr):
            sto[s]["rank"] = i + 1; sto[s]["nsize"] = len(mem)
    v["store"] = sto
    # 来月の見通し（前年同月 × 直近3か月の前年比の平均）
    last3 = [str(m - k) for k in range(3)]
    gr = np.mean([co.loc[x, "sales"] / co.loc[str(pd.Period(x, "M") - 12), "sales"] for x in last3])
    v["next_sales"] = co.loc[str(m + 1 - 12), "sales"] * gr if str(m + 1 - 12) in co.index else np.nan
    return v


# ---------------- レポートの文を作る ----------------
def f1(x):
    return f"{x:+.1f}"


def blk(sec, text, facts=(), heading=False):
    t2 = re.sub(r"S\d{2}", "S", text)  # 店の番号は数字に数えない
    nums = len(re.findall(r"[+\-−]?\d+(?:[.,]\d+)*", t2))
    return dict(sec=sec, text=text, facts=set(facts), heading=heading, nums=nums, chars=len(text))


def decisions(v):
    outs = [s for s, x in v["store"].items() if x["out"]]
    od = [d for d, x in v["dept"].items() if x["out"]]
    items = []
    for d in od:
        items.append(f"{d}部門の粗利率（前年差{f1(v['dept'][d]['gpr_d'])}pt）の原因を仕入れ担当が確認し、来月の会議で値付けの見直し案を出す")
    for s in outs:
        items.append(f"{s}の客数（前年比{f1(v['store'][s]['cust_yoy'])}%）について、店長と地域の担当が理由を確認する")
    if not items:
        items.append("幅の外の動きはなく、今月決めることはない")
    return items


def todo(v, s):
    x = v["store"][s]
    if x["out"] and x["cust_yoy"] < 0:
        return f"客数が前年より{abs(x['cust_yoy']):.1f}%少ない。来店の多い土日の品出しと、会員へのお知らせの回数を見直す"
    if x["worst_yoy"] < -5:
        return f"{x['worst']}の売上が前年比{f1(x['worst_yoy'])}%。売り場の場所と品ぞろえを、同じ規模の店の上位と比べる"
    return "大きな動きはない。人時売上高を同じ規模の店の平均に近づけるよう、シフトの組み方を続ける"


def worst_word(x):
    """前年比がマイナスなら「いちばん落ちた部門」、プラスなら「いちばん伸びが小さい部門」。"""
    return "いちばん落ちた部門" if x["worst_yoy"] < 0 else "いちばん伸びが小さい部門"


def report_C(v, m, summary_first=False):
    """共通版：全社→部門→店→店×部門→見通し→対応→前月の結果。すべての数字を同じ形で並べる。"""
    B = []
    B.append(blk("全社", f"# みどり堂（架空） 月次レポート {m}（共通版）", heading=True))
    if summary_first:
        # 要約を先に置く共通版（レビュー後に足した比べる相手）：経営の問いの答えになる行を冒頭にまとめる
        od0 = [d for d in DEPTS if v["dept"][d]["out"]]
        os0 = [s for s in v["store"] if v["store"][s]["out"]]
        B.append(blk("要約", "## 要約", heading=True))
        B.append(blk("要約", f"偶然の幅の外の部門：{'、'.join(od0) if od0 else 'なし'}。偶然の幅の外の店：{'、'.join(os0) if os0 else 'なし'}。", ["out_depts", "out_stores"]))
        B.append(blk("要約", "決めること：" + "。".join(decisions(v)) + "。", ["decisions"]))
        B.append(blk("要約", f"来月の売上は約{v['next_sales']:.0f}百万円の見込み。先月決めた確認は、担当から報告を受けた。", ["next_month", "last_action"]))
    B.append(blk("全社", "## 1. 全社", heading=True))
    B.append(blk("全社", f"売上は{v['co_sales']:.1f}百万円で、前年同月比{f1(v['co_sales_yoy'])}%、計画比{f1(v['co_sales_plan'])}%。", ["co_sales_plan"]))
    B.append(blk("全社", f"客数は前年同月比{f1(v['co_cust_yoy'])}%、客単価は{f1(v['co_ticket_yoy'])}%。", ["co_factor"]))
    B.append(blk("全社", f"粗利率は{v['co_gpr']:.1f}%（前年{v['co_gpr_py']:.1f}%）。営業利益は{v['co_op']:.1f}百万円で、計画比{f1(v['co_op_plan'])}%。", ["co_op_plan"]))
    B.append(blk("部門", "## 2. 部門別", heading=True))
    for d in DEPTS:
        x = v["dept"][d]
        B.append(blk("部門", f"{d}：売上{x['sales']:.1f}百万円、前年比{f1(x['yoy'])}%、粗利率{x['gpr']:.1f}%（前年差{f1(x['gpr_d'])}pt）、判定は{'幅の外' if x['out'] else '幅の中'}。"))
    od = [d for d in DEPTS if v["dept"][d]["out"]]
    if not summary_first:
        B.append(blk("部門", f"偶然の幅の外の部門：{'、'.join(od) if od else 'なし'}。", ["out_depts"]))
    B.append(blk("店", "## 3. 店別（規模ごと）", heading=True))
    for sz in ["L", "M", "S"]:
        for s, x in v["store"].items():
            if x["size"] != sz:
                continue
            B.append(blk("店", f"{s}（規模{sz}）：売上{x['sales']:.1f}百万円、前年比{f1(x['yoy'])}%、客数{f1(x['cust_yoy'])}%、客単価{f1(x['ticket_yoy'])}%、人時売上高{x['lp']:,.0f}円、規模内{x['rank']}位/{x['nsize']}店、判定は{'幅の外' if x['out'] else '幅の中'}。",
                         [f"{s}:sales_yoy", f"{s}:cust_yoy", f"{s}:labor_prod", f"{s}:peer_rank", f"{s}:outside"]))
    os_ = [s for s in v["store"] if v["store"][s]["out"]]
    if not summary_first:
        B.append(blk("店", f"偶然の幅の外の店：{'、'.join(os_) if os_ else 'なし'}。", ["out_stores"]))
    B.append(blk("店×部門", "## 4. 店×部門の前年比", heading=True))
    for s, x in v["store"].items():
        B.append(blk("店×部門", f"{s}：{worst_word(x)}は{x['worst']}（前年比{f1(x['worst_yoy'])}%）。", [f"{s}:worst_dept"]))
    if not summary_first:
        B.append(blk("見通し", "## 5. 来月の見通し", heading=True))
        B.append(blk("見通し", f"来月の売上は、前年同月×直近3か月の前年比で約{v['next_sales']:.0f}百万円の見込み。", ["next_month"]))
    B.append(blk("対応", "## 6. 対応すること", heading=True))
    if not summary_first:
        B.append(blk("対応", "全社：" + "。".join(decisions(v)) + "。", ["decisions"]))
    for s in v["store"]:
        B.append(blk("対応", f"{s}：{todo(v, s)}。", [f"{s}:todo"]))
    B.append(blk("前月", "## 7. 先月の対応の結果", heading=True))
    if not summary_first:
        B.append(blk("前月", "全社：先月決めた確認は、担当から報告を受けた。", ["last_action"]))
    for s in v["store"]:
        B.append(blk("前月", f"{s}：先月やったことの結果は、今月の数字（上の表）で確認。", [f"{s}:last_result"]))
    return B


def report_E(v, m):
    """経営向け：結論→KPI→例外→見通し→決めること→先月の結果。店・部門は幅の外だけ。"""
    B = []
    B.append(blk("結論", f"# みどり堂（架空） {m} 経営向け", heading=True))
    B.append(blk("結論", "## 結論", heading=True))
    B.append(blk("結論", f"売上は計画比{f1(v['co_sales_plan'])}%、営業利益は計画比{f1(v['co_op_plan'])}%。", ["co_sales_plan", "co_op_plan"]))
    B.append(blk("結論", f"前年比{f1(v['co_sales_yoy'])}%の内訳は、客数{f1(v['co_cust_yoy'])}%・客単価{f1(v['co_ticket_yoy'])}%。", ["co_factor"]))
    od = [d for d in DEPTS if v["dept"][d]["out"]]
    os_ = [s for s in v["store"] if v["store"][s]["out"]]
    B.append(blk("例外", "## 偶然の幅の外の動き", heading=True))
    t = "部門：" + ("、".join(f"{d}（粗利率 前年差{f1(v['dept'][d]['gpr_d'])}pt）" for d in od) if od else "部門：なし") + "。"
    B.append(blk("例外", t, ["out_depts"]))
    t = "店：" + ("、".join(f"{s}（客数{f1(v['store'][s]['cust_yoy'])}%）" for s in os_) if os_ else "店：なし") + "。"
    B.append(blk("例外", t, ["out_stores"]))
    B.append(blk("決める", "## 決めること", heading=True))
    B.append(blk("決める", "。".join(decisions(v)) + "。", ["decisions"]))
    B.append(blk("見通し", "## 来月の見通し", heading=True))
    B.append(blk("見通し", f"来月の売上は約{v['next_sales']:.0f}百万円の見込み（前年同月×直近3か月の前年比）。", ["next_month"]))
    B.append(blk("前月", "## 先月決めたことの結果", heading=True))
    B.append(blk("前月", "先月決めた確認は、担当から報告を受けた。", ["last_action"]))
    return B


def report_S(v, m, s):
    """現場向け：店ごとに1枚。"""
    x = v["store"][s]
    B = []
    B.append(blk("自店", f"# {s} 店長向け {m}", heading=True))
    B.append(blk("自店", "## 今月の自店", heading=True))
    B.append(blk("自店", f"売上は前年比{f1(x['yoy'])}%（客数{f1(x['cust_yoy'])}%・客単価{f1(x['ticket_yoy'])}%）。判定は{'偶然の幅の外' if x['out'] else '偶然の幅の中'}。",
                 [f"{s}:sales_yoy", f"{s}:cust_yoy", f"{s}:outside"]))
    B.append(blk("自店", f"人時売上高は{x['lp']:,.0f}円。同じ規模の{x['nsize']}店の中で売上前年比は{x['rank']}位。", [f"{s}:labor_prod", f"{s}:peer_rank"]))
    B.append(blk("自店", f"{worst_word(x)}は{x['worst']}（前年比{f1(x['worst_yoy'])}%）。", [f"{s}:worst_dept"]))
    B.append(blk("やる", "## 今月やること", heading=True))
    B.append(blk("やる", todo(v, s) + "。", [f"{s}:todo"]))
    B.append(blk("前月", "## 先月やったことの結果", heading=True))
    B.append(blk("前月", "先月やったことの結果は、上の客数と部門の数字で確認する。", [f"{s}:last_result"]))
    return B


Q_EXEC = ["co_sales_plan", "co_op_plan", "co_factor", "out_stores", "out_depts", "next_month", "decisions", "last_action"]


def q_store(s):
    return [f"{s}:{k}" for k in ["sales_yoy", "cust_yoy", "worst_dept", "peer_rank", "outside", "labor_prod", "todo", "last_result"]]


def read_cost(B, facts, mode="linear"):
    """問いの事実をすべて見つけるまでに読む文字数。見つからない事実があれば None。"""
    need = set(facts)
    have = set().union(*[b["facts"] for b in B])
    if not need <= have:
        return None
    if mode == "linear":
        pos = 0
        left = set(need)
        for b in B:
            pos += b["chars"]
            left -= b["facts"]
            if not left:
                return pos
        return None
    # 見出しを先に読み、事実のある節だけ読む
    head = sum(b["chars"] for b in B if b["heading"])
    secs = {b["sec"] for b in B if b["facts"] & need}
    body = sum(b["chars"] for b in B if (not b["heading"]) and b["sec"] in secs)
    return head + body


def answered_within(B, facts, cap):
    """先頭から cap 字で切ったとき、答えの事実が残っている問いの数。"""
    pos = 0
    kept = set()
    for b in B:
        pos += b["chars"]
        if pos > cap:
            break
        kept |= b["facts"]
    return sum(1 for f in facts if f in kept)


def noise_share(B, facts):
    """表示した数字のうち、問いの答えになる事実を含まないブロックの数字の割合。"""
    need = set(facts)
    tot = sum(b["nums"] for b in B if not b["heading"])
    useless = sum(b["nums"] for b in B if (not b["heading"]) and not (b["facts"] & need))
    return useless / tot if tot else np.nan


def text_of(B):
    return "\n".join(b["text"] for b in B)
