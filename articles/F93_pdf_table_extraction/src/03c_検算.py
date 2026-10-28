"""検算（表の中の決まりごと）で、読み間違いをどれだけ自動で見つけられるか。
ルール（表ごと）：
  R0 列の数     ：1行の数の個数が決まった数（T1=9, T2=16か9, T3=15, T4=5）か
  R1 足し算     ：T1 1〜3年目の合計＝3年計／T2 製造業＝その内訳の合計、各産業の合計＝調査産業計（年ごと・項目ごと）
                  ／T3 6規模の合計＝規模計（離職者数）／T4 就業者＋失業者＋非労働力＝15歳以上人口（±2、万人の概数のため）
  R2 割り算     ：T1 率＝離職者数÷就職者数（小数1桁、±tol）／T3 率＝離職者数÷就職者数（規模計）
  R3 大小・範囲 ：T2 就職者≧3年目まで≧2年目まで≧1年目まで／率は0〜100／T4 失業率の段差は±1以内
  R4 行どうし   ：T3 同じ卒業年の「1年目まで≦2年目まで≦3年目まで」（離職者数・率とも、規模ごと）
(1) 実際の読み取り結果に当てはめる：各ツールの「列の数が合った行」を正解の行に対応させ、誤りのある行のうち何割を見つけたか、
    正しい行を誤って疑った割合はどれだけか。
(2) よくある読み間違いをわざと入れて（各型×各表 1,000回、乱数固定）見つけられる割合を出す。"""
import random
from common import *
GTR = pd.read_json(GT / "ground_truth_rows.json")
TOL = 0.1

def isn(x): return x is None or (isinstance(x, float) and np.isnan(x))
def z(x): return 0.0 if isn(x) else x

def rules_row(tid, v, tol=TOL):
    """1行だけで判定できるルール。戻り値：{ルール名: 通過したか}"""
    r = {}
    ok_n = len(v) in {"T1": [9], "T2": [16, 9], "T3": [15], "T4": [5]}[tid]
    r["R0"] = ok_n
    if not ok_n: return r
    if tid == "T1":
        h, s3, a, b, c, q3, q1, q2, qq3 = v
        r["R1"] = abs(a + b + c - s3) < 1e-9
        r["R2"] = all(abs(round(x / h * 100, 1) - q) <= tol + 1e-9 for x, q in [(s3, q3), (a, q1), (b, q2), (c, qq3)]) if h else False
        r["R3"] = all(0 <= q <= 100 for q in (q3, q1, q2, qq3)) and min(v[:5]) >= 0
    if tid == "T2":
        blocks = [v[i:i + 4] for i in range(0, 16, 4)] if len(v) == 16 else [v[0:4], v[4:7], v[7:9]]
        r["R3"] = all(all(z(b[i]) >= z(b[i + 1]) for i in range(len(b) - 1)) and z(b[-1]) >= 0 for b in blocks)
    if tid == "T3":
        h, s, q = v[0], v[1], v[2]
        sz = v[3::2]
        r["R1"] = abs(sum(sz) - s) < 1e-9
        r["R2"] = abs(round(s / h * 100, 1) - q) <= tol + 1e-9 if h else False
        r["R3"] = all(0 <= x <= 100 for x in v[2::2]) and all(x >= 0 for x in v[1::2])
    if tid == "T4":
        p, e, u, n, q = v
        r["R1"] = abs(e + u + n - p) <= 2
        r["R3"] = abs(q) <= 1
    return r

MANUF = ["食料品製造業", "飲料・たばこ・飼料製造業", "繊維工業", "木材・木製品、家具・装備品製造業", "パルプ・紙・紙加工品製造、印刷・同関連業",
         "化学工業、石油製品・石炭製品製造業", "窯業・土石製品製造業", "鉄鋼業", "非鉄金属製造業", "金属製品製造業", "機械関係", "その他の製造業"]
def rules_t2_page(rows):
    """T2 のページ単位の足し算（行の並びは正解と同じ順とする）：製造業＝内訳の合計、調査産業計＝大分類の合計。
    秘匿（-）は0として足す。戻り値：各行が足し算に関わって不一致になったか（True=通過）"""
    keys = [k for k, _ in rows]; V = np.array([[z(x) for x in v] for _, v in rows], float)
    ok = np.ones(len(rows), bool)
    if V.ndim != 2: return ok
    im = keys.index("製造業"); sub = [keys.index(k) for k in MANUF if k in keys]
    big = [i for i, k in enumerate(keys) if k not in MANUF and k != "調査産業計"]
    bad1 = np.abs(V[sub].sum(0) - V[im]) > 0.5
    bad2 = np.abs(V[big].sum(0) - V[keys.index("調査産業計")]) > 0.5
    if bad1.any(): ok[[im] + sub] = False
    if bad2.any(): ok[big + [keys.index("調査産業計")]] = False
    return ok

def rules_t3_year(rows):
    """T3 の同じ卒業年の3行（1・2・3年目まで）で、離職者数と率が減っていないか。戻り値：3行とも通過なら True"""
    if len(rows) != 3 or any(len(v) != 15 for v in rows): return True
    V = np.array(rows, float)
    return bool((np.diff(V[:, 1:], axis=0) >= 0).all())

def check_gt():
    """正解の表そのものがルールを通るか（通らないルールは誤検知のもとになる）"""
    rows = []
    for r in GTR.itertuples():
        v = [np.nan if isn(x) else x for x in r.vals]
        res = rules_row(r.table, v)
        rows.append(dict(table=r.table, **{k: res.get(k, np.nan) for k in ["R0", "R1", "R2", "R3"]}))
    g = pd.DataFrame(rows)
    t2 = []
    for p in range(6):
        sub = GTR[(GTR.table == "T2") & (GTR.page == p)]
        t2 += list(rules_t2_page([(k.rsplit("_", 1)[0], v) for k, v in zip(sub.key, sub.vals)]))
    g.loc[g.table == "T2", "R1"] = np.array(t2, float)
    g[["R0", "R1", "R2", "R3"]] = g[["R0", "R1", "R2", "R3"]].astype(float)
    return g.groupby("table")[["R0", "R1", "R2", "R3"]].mean()

# ---------- (1) 実際の読み取り結果
def tok(v): return "-" if isn(v) else f"{float(v):g}"
def real_outputs(tol=TOL):
    out = []
    for f in sorted(EXT.glob("*.json")):
        ext = json.load(open(f, encoding="utf-8"))
        for tid, T in TABLES.items():
            for p in T["pages"]:
                g = GTR[(GTR.table == tid) & (GTR.page == p)]
                gv = [[np.nan if isn(x) else x for x in v] for v in g.vals]
                for r in ext[tid][str(p)]:
                    v = [x for cell in r for x in numbers(cell, signs=(tid == "T4"))]
                    if len(v) < 3: continue
                    # 正解の行に対応させる：同じ位置の値の一致が最も多い行（半分以上の一致が必要）
                    best, bi = 0, None
                    for i, w in enumerate(gv):
                        m = sum(1 for a, b in zip(v, w) if tok(a) == tok(b))
                        if m > best: best, bi = m, i
                    if bi is None or best < len(gv[bi]) / 2: continue
                    w = gv[bi]
                    wrong = len(v) != len(w) or any(tok(a) != tok(b) for a, b in zip(v, w))
                    res = rules_row(tid, v, tol)
                    flagged = not all(res.values())
                    out.append(dict(tool=f.stem, table=tid, wrong=wrong, flagged=flagged, **{k: res.get(k, np.nan) for k in ["R0", "R1", "R2", "R3"]}))
    return pd.DataFrame(out)

# ---------- (2) わざと入れる読み間違い
def corrupt(v, kind, rng):
    v = list(v); idx = [i for i, x in enumerate(v) if not isn(x)]
    if kind == "列ずれ（隣と入れ替え）":
        cand = [i for i in idx[:-1] if i + 1 in idx and v[i] != v[i + 1]]
        if not cand: return None
        i = rng.choice(cand); v[i], v[i + 1] = v[i + 1], v[i]; return v
    if kind == "列の抜け（1つ落ちて左に詰まる）":
        i = rng.choice(idx); return v[:i] + v[i + 1:]
    i = rng.choice(idx); x = v[i]
    s = f"{x:g}"
    digits = [k for k, ch in enumerate(s) if ch.isdigit()]
    if kind == "桁の落ち（1桁消える）":
        if len(digits) < 2: return None
        k = rng.choice(digits); s2 = s[:k] + s[k + 1:]
    elif kind == "数字の入れ替え（隣の2桁）":
        pairs = [k for k in digits if k + 1 in digits and s[k] != s[k + 1]]
        if not pairs: return None
        k = rng.choice(pairs); s2 = s[:k] + s[k + 1] + s[k] + s[k + 2:]
    elif kind == "似た字の誤認（3↔8・1↔7・0↔6）":
        sw = {"3": "8", "8": "3", "1": "7", "7": "1", "0": "6", "6": "0"}
        ks = [k for k in digits if s[k] in sw]
        if not ks: return None
        k = rng.choice(ks); s2 = s[:k] + sw[s[k]] + s[k + 1:]
    elif kind == "小数点・符号の落ち":
        if "." in s: s2 = s.replace(".", "")
        elif s.startswith("-"): s2 = s[1:]
        else: return None
    try: v[i] = float(s2)
    except ValueError: return None
    return v if v[i] != x else None

KINDS = ["桁の落ち（1桁消える）", "数字の入れ替え（隣の2桁）", "似た字の誤認（3↔8・1↔7・0↔6）", "小数点・符号の落ち", "列ずれ（隣と入れ替え）", "列の抜け（1つ落ちて左に詰まる）"]
def simulate(n=1000, tol=TOL, seed=SEED):
    rng = random.Random(seed); out = []
    pages = {p: GTR[(GTR.table == "T2") & (GTR.page == p)] for p in range(6)}
    for tid in TABLES:
        g = GTR[GTR.table == tid]
        for kind in KINDS:
            done = 0; tries = 0
            while done < n and tries < n * 20:
                tries += 1
                j = rng.randrange(len(g)); r = g.iloc[j]
                v = [np.nan if isn(x) else x for x in r.vals]
                c = corrupt(v, kind, rng)
                if c is None: continue
                res = rules_row(tid, c, tol)
                if tid == "T2" and all(k in res for k in ["R0"]) and res["R0"]:
                    sub = pages[r.page]; rows = [(k.rsplit("_", 1)[0], (c if k == r.key else w)) for k, w in zip(sub.key, sub.vals)]
                    res["R1"] = bool(rules_t2_page(rows)[list(sub.key).index(r.key)])
                if tid == "T3" and res.get("R0"):
                    y = r.key.split("_")[0]; sub = g[g.key.str.startswith(y + "_")]
                    rows3 = [(c if k == r.key else [np.nan if isn(x) else x for x in w]) for k, w in zip(sub.key, sub.vals)]
                    res["R4"] = rules_t3_year(rows3)
                done += 1
                out.append(dict(table=tid, kind=kind, **{k: (not res[k]) if k in res else np.nan for k in ["R0", "R1", "R2", "R3", "R4"]},
                                any=not all(res.values())))
    return pd.DataFrame(out)

if __name__ == "__main__":
    pd.set_option("display.width", 220)
    g = check_gt(); g.to_csv(RES / "rules_on_ground_truth.csv"); print("正解の表がルールを通る割合\n", g)
    # 公表された表そのものがルールを通らない行（読み取りの誤りではなく、元の表の値）
    an = [dict(table=r.table, key=r.key, vals=r.vals) for r in GTR.itertuples()
          if not all(rules_row(r.table, [np.nan if isn(x) else x for x in r.vals]).values())]
    pd.DataFrame(an).to_csv(RES / "rule_failures_in_published_table.csv", index=False); print("元の表でルールを通らない行", an)
    # ルールを1つずつ足したときの検出率（シミュレーションから）
    ro = real_outputs(); ro.to_csv(RES / "rules_on_real_outputs_rows.csv", index=False)
    s = ro.groupby("tool").apply(lambda d: pd.Series(dict(rows=len(d), wrong=d.wrong.sum(), caught=(d.wrong & d.flagged).sum(),
                                                       false_alarm=(~d.wrong & d.flagged).sum(), correct=(~d.wrong).sum())))
    s["catch_rate"] = s.caught / s.wrong.replace(0, np.nan); s["false_alarm_rate"] = s.false_alarm / s.correct.replace(0, np.nan)
    s.to_csv(RES / "rules_on_real_outputs.csv"); print(s)
    tot = ro.agg(dict(wrong="sum")); print("全ツール計 誤りのある行", int(ro.wrong.sum()), "うち検出", int((ro.wrong & ro.flagged).sum()),
                                           "正しい行の誤検知", int((~ro.wrong & ro.flagged).sum()), "/", int((~ro.wrong).sum()))
    sim = simulate(); sim.to_csv(RES / "rules_simulation_raw.csv.gz", index=False, compression="gzip")
    det = sim.groupby(["table", "kind"])[["R0", "R1", "R2", "R3", "R4", "any"]].mean()
    det.to_csv(RES / "rules_simulation_detect_rate.csv"); print(det.round(3))
    # 頑健性：割り算ルールの許容幅
    rob = []
    for tol in [0.05, 0.1, 0.2, 0.5]:
        s2 = simulate(n=400, tol=tol)
        rob.append(dict(tol=tol, detect=s2["any"].mean(), **{f"detect_{t}": s2[s2.table == t]["any"].mean() for t in TABLES}))
    rob = pd.DataFrame(rob); rob.to_csv(RES / "rules_tolerance.csv", index=False); print(rob.round(3))
