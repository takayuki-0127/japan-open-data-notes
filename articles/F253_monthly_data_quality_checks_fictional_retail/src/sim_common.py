"""03・04 で使う共通の部品：乱数の種ごとの合成データ（F246 の gen）と、汚れの入れ方。会社・数字はすべて架空（合成データ）。"""
import importlib.util, pathlib, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

ROOT = pathlib.Path(__file__).resolve().parents[1]
MONTHS = pd.period_range("2024-04", "2026-03", freq="M").strftime("%Y-%m").tolist()   # FY2024・FY2025 の24か月
SEEDS = list(range(20))
POS_S = ["receipts", "member_receipts", "items", "sales", "gross_profit_before_waste"]   # POS から来る列（店）
POS_C = ["sales", "gross_profit_before_waste"]                                         # POS から来る列（部門）
TYPES = ["欠測：行がない", "欠測：空の値", "欠測：0で入る", "欠測：途中までしか入らない",
         "桁ずれ：廃棄を千円で入力（1か月）", "桁ずれ：人時が10倍", "桁ずれ：店の売上だけ10倍",
         "重複：同じ行が2回", "重複：前の日の写し", "重複：2回足し込み"]


def load_gen():
    s = importlib.util.spec_from_file_location("f246gen", ROOT / "data" / "f246" / "src" / "02_整形.py")
    g = importlib.util.module_from_spec(s); s.loader.exec_module(g)
    return g


def gen_mart(g, seed):
    """F246 の gen(seed) を mart の形（F247 の列名）にする"""
    cal, fsd, fsdc, fmm, ec = g.gen(seed)
    fsd = fsd.rename(columns={"date": "biz_date"}).drop(columns=["flyer", "other_cost"])
    fsdc = fsdc.rename(columns={"date": "biz_date"})
    return fsd, fsdc


def inject(cur, cat, rng, stores, types=TYPES):
    """その月の cur（店×日）・cat（店×日×部門）に、types の汚れを1つずつ別の店に入れる。返り値：(cur, cat, truth)
    truth は汚れごとの「触れた店×日」（見つけたかどうかの判定に使う）。"""
    cur = cur.copy(); cat = cat.copy()
    days = sorted(cur.biz_date.unique())
    pick = rng.choice(stores, size=len(types), replace=False)
    truth, add_rows, drop_idx, drop_cidx = [], [], [], []
    for t, s in zip(types, pick):
        d = pd.Timestamp(days[rng.integers(1, len(days) - 3)])
        ks = (cur.store_id == s) & (cur.biz_date == d)
        kc = (cat.store_id == s) & (cat.biz_date == d)
        touch = [d]
        if t == "欠測：行がない":
            k = int(rng.integers(1, 4)); dd = [d + pd.Timedelta(days=i) for i in range(k)]; touch = dd
            drop_idx += cur.index[(cur.store_id == s) & cur.biz_date.isin(dd)].tolist()
            drop_cidx += cat.index[(cat.store_id == s) & cat.biz_date.isin(dd)].tolist()
        elif t == "欠測：空の値":
            col = ["labor_hours", "waste", "items"][int(rng.integers(0, 3))]
            cur.loc[ks, col] = np.nan
        elif t == "欠測：0で入る":
            cur.loc[ks, POS_S] = 0; cat.loc[kc, POS_C] = 0
        elif t == "欠測：途中までしか入らない":
            f = rng.uniform(0.3, 0.7); cur.loc[ks, POS_S] *= f; cat.loc[kc, POS_C] *= f
            cur.loc[ks, ["receipts", "member_receipts", "items"]] = cur.loc[ks, ["receipts", "member_receipts", "items"]].round()
        elif t == "桁ずれ：廃棄を千円で入力（1か月）":
            cur.loc[cur.store_id == s, "waste"] /= 1000; cat.loc[cat.store_id == s, "waste"] /= 1000
            touch = [pd.Timestamp(x) for x in days]
        elif t == "桁ずれ：人時が10倍":
            cur.loc[ks, ["labor_hours", "labor_cost"]] *= 10
        elif t == "桁ずれ：店の売上だけ10倍":
            cur.loc[ks, "sales"] *= 10
        elif t == "重複：同じ行が2回":
            add_rows.append(cur.loc[ks])
        elif t == "重複：前の日の写し":
            p = d - pd.Timedelta(days=1); touch = [d, p]
            kp = (cur.store_id == s) & (cur.biz_date == p)
            cols = [c for c in cur.columns if c not in ("biz_date", "store_id")]
            cur.loc[ks, cols] = cur.loc[kp, cols].values
            kcp = (cat.store_id == s) & (cat.biz_date == p)
            cat.loc[kc, ["sales", "gross_profit_before_waste", "waste"]] = cat.loc[kcp, ["sales", "gross_profit_before_waste", "waste"]].values
        elif t == "重複：2回足し込み":
            cur.loc[ks, POS_S] *= 2; cat.loc[kc, POS_C] *= 2
        truth.append(dict(type=t, store_id=int(s), dates=touch))
    cur = cur.drop(index=drop_idx); cat = cat.drop(index=drop_cidx)
    if add_rows:
        cur = pd.concat([cur] + add_rows)
    cur["gross_profit"] = cur.gross_profit_before_waste - cur.waste
    return cur, cat, truth


def eligible_stores(hist, cur, m0):
    """汚れを入れる店：その月に営業していて、1年前と8週前の参照がそろう店"""
    s_now = set(cur.store_id.unique())
    ly = hist[(hist.biz_date >= m0 - pd.Timedelta(days=364 + 56)) & (hist.biz_date < m0 - pd.Timedelta(days=364))].groupby("store_id").size()
    return sorted(s for s in s_now if ly.get(s, 0) == 56)
