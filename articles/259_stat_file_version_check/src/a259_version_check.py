"""259 統計表を定期的に取り直すとき、何で「変わった」を見つけるか

SSDSE-B（都道府県×12年×109項目）の2024・2025・2026年版を、5つの点検で比べる。
  C1 ファイルのハッシュ（md5）
  C2 行数・列数
  C3 列の並び（項目コードと項目名。1列目の版名は除く）
  C4 キー（年度×地域コード）の重複・欠け
  C5 前に保存したファイルと重なる年の値の差（セルごとに完全一致か）
本物の版どうしの比較（前年の版と比べる）に加えて、保存した2026年版と「同じ版を取り直したファイル」に黙った変化を1つずつ入れた8つの場面でも、どの点検が反応するかを数える。
"""
import hashlib, io, json
import numpy as np
import pandas as pd
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, read_raw, save, plt

ED = {y: DATA / f"SSDSE-B-{y}.csv" for y in (2024, 2025, 2026)}


def load_bytes(b):
    codes, names, body = read_raw(io.BytesIO(b)) if isinstance(b, bytes) else read_raw(b)
    return codes, names, body


def parse(b, enc="cp932"):
    d = pd.read_csv(io.BytesIO(b), encoding=enc, header=None, dtype=str, keep_default_na=False)
    codes, names = list(d.iloc[0]), list(d.iloc[1])
    body = d.iloc[2:].reset_index(drop=True)
    body.columns = ["year"] + codes[1:]
    return codes, names, body


def checks(prev_b, new_b, new_enc="cp932"):
    """前の版（bytes）と新しい版（bytes）に5つの点検をかけ、反応したかと中身を返す"""
    out = {}
    out["C1_hash"] = hashlib.md5(prev_b).hexdigest() != hashlib.md5(new_b).hexdigest()
    try:
        pc, pn, pb = parse(prev_b)
        nc, nn, nb = parse(new_b, new_enc)
    except Exception as e:  # 読めないこと自体が異常
        return {k: True for k in ("C1_hash", "C2_shape", "C3_schema", "C4_keys", "C5_values")} | {"note": f"読めない: {e.__class__.__name__}"}
    out["C2_shape"] = pb.shape != nb.shape
    out["C3_schema"] = (pc[1:] != nc[1:]) or (pn[1:] != nn[1:])
    key = nb[["year", "Code"]]
    yrs = sorted(nb["year"].unique())
    expect = len(yrs) * nb["Code"].nunique()
    out["C4_keys"] = bool(key.duplicated().any()) or len(key) != expect or nb["Code"].nunique() != 47
    # C5：前の版と重なる年・同じ項目コード（コードで突き合わせる。列の並びには頼らない）
    m = pb.merge(nb, on=["year", "Code"], suffixes=("_p", "_n"))
    items = [c for c in pc[3:] if c in nc[3:]]
    changed = []
    for c in items:
        a = pd.to_numeric(m[c + "_p"], errors="coerce").to_numpy()
        b = pd.to_numeric(m[c + "_n"], errors="coerce").to_numpy()
        diff = ~((a == b) | (np.isnan(a) & np.isnan(b)))
        for i in np.where(diff)[0]:
            changed.append({"item": c, "name": nn[nc.index(c)], "year": m["year"].iloc[i], "Code": m["Code"].iloc[i],
                            "prev": a[i], "new": b[i]})
    lost = len(pb[pb["year"].isin(nb["year"].unique())]) - len(m)  # 重なる年なのに新しい版で消えた行
    out["C5_values"] = len(changed) > 0 or lost > 0
    out["n_changed_cells"] = len(changed)
    out["n_lost_rows"] = int(lost)
    out["n_overlap_cells"] = int(len(m) * len(items))
    out["_changed"] = changed
    return out


raw = {y: ED[y].read_bytes() for y in ED}
summary = {}

# --- 本物の版どうし ---
real = {}
for a, b in [(2024, 2025), (2025, 2026)]:
    r = checks(raw[a], raw[b])
    real[f"{a}→{b}"] = r
    summary[f"real_{a}_{b}"] = {k: v for k, v in r.items() if not k.startswith("_")}
pc, pn, _ = parse(raw[2024]); nc, nn, _ = parse(raw[2025])
summary["first_col_header"] = {y: parse(raw[y])[0][0] for y in ED}
ch = pd.DataFrame(real["2024→2025"]["_changed"])
ch["rel"] = (ch["new"] / ch["prev"] - 1)
ch.to_csv(RES / "real_changes_2024_2025.csv", index=False)
by_item = ch.groupby(["item", "name"]).agg(cells=("rel", "size"), max_abs_rel=("rel", lambda s: float(s.abs().max())),
                                           years=("year", lambda s: ",".join(sorted(s.unique())))).reset_index()
by_item.to_csv(RES / "real_changes_by_item.csv", index=False)
summary["real_2024_2025_by_item"] = by_item.to_dict("records")
summary["real_2024_2025_by_year"] = ch.groupby("year").size().to_dict()
summary["real_2024_2025_max_abs_diff"] = float((ch["new"] - ch["prev"]).abs().max())

# --- 保存してある2026年版と、あとで同じ版を取り直したファイルを比べる。取り直したファイルに「黙った変化」を1つずつ入れる ---
codes, names, body = parse(raw[2026])


def to_bytes(codes, names, body, enc="cp932"):
    head = pd.DataFrame([codes, names])
    b2 = body.copy(); b2.columns = list(range(b2.shape[1])); head.columns = b2.columns
    buf = io.StringIO()
    pd.concat([head, b2]).to_csv(buf, header=False, index=False, lineterminator="\r\n")
    return buf.getvalue().encode(enc)


base_b = to_bytes(codes, names, body)
summary["roundtrip_identical"] = base_b == raw[2026]
rng = np.random.default_rng(259)
scen = {}
# S0 何も変えずに保存し直す（同じ中身・同じ文字コード）
scen["S0 同じ中身をもう一度取る"] = base_b
# S1 文字コードだけ UTF-8 に（中身は同じ）
scen["S1 文字コードだけ変わる"] = to_bytes(codes, names, body, "utf-8")
# S2 過去の年の1セルだけ改訂
b2 = body.copy(); i = int(np.where(b2["year"] == "2019")[0][rng.integers(0, 47)])
b2.loc[i, "F3101"] = str(int(b2.loc[i, "F3101"]) + 7)
scen["S2 過去の1セルだけ直る"] = to_bytes(codes, names, b2)
# S3 1つの列の単位が変わる（人→千人）
b3 = body.copy(); b3["A4101"] = (pd.to_numeric(b3["A4101"]) / 1000).round(3).map(lambda v: f"{v:g}")
scen["S3 1列の単位が変わる"] = to_bytes(codes, names, b3)
# S4 2つの列の並びが入れ替わる（コードと値ごと）
c4 = codes.copy(); n4 = names.copy(); b4 = body.copy()
j, k = codes.index("E2401"), codes.index("E2501")
c4[j], c4[k] = c4[k], c4[j]; n4[j], n4[k] = n4[k], n4[j]
cols = list(b4.columns); cols[j], cols[k] = cols[k], cols[j]; b4 = b4[cols]; b4.columns = ["year"] + c4[1:]
scen["S4 列の並びが入れ替わる"] = to_bytes(c4, n4, b4)
# S5 1行（ある県のある年）が抜ける
b5 = body.drop(index=int(rng.integers(0, len(body)))).reset_index(drop=True)
scen["S5 1行が抜ける"] = to_bytes(codes, names, b5)
# S6 項目名だけ言い換え（コード・値は同じ）
n6 = names.copy(); n6[codes.index("H5610")] = "1人1日当たりのごみ排出量"
scen["S6 項目名だけ変わる"] = to_bytes(codes, n6, body)
# S7 列の並びが入れ替わり、コード行はそのまま（値だけずれる）
b7 = body.copy(); b7[["E2401", "E2501"]] = b7[["E2501", "E2401"]].to_numpy()
scen["S7 値だけ隣の列とずれる"] = to_bytes(codes, names, b7)

rows = []
for name, nb_ in scen.items():
    enc = "utf-8" if name.startswith("S1") else "cp932"
    r = checks(raw[2026], nb_, enc)
    rows.append({"場面": name} | {k: r[k] for k in ("C1_hash", "C2_shape", "C3_schema", "C4_keys", "C5_values")}
                | {"変わったセル": r["n_changed_cells"], "消えた行": r["n_lost_rows"]})
for lab, key in [("本物 2024年版→2025年版", "2024→2025"), ("本物 2025年版→2026年版", "2025→2026")]:
    r = real[key]
    rows.insert(0 if key == "2024→2025" else 1, {"場面": lab} | {k: r[k] for k in ("C1_hash", "C2_shape", "C3_schema", "C4_keys", "C5_values")}
                | {"変わったセル": r["n_changed_cells"], "消えた行": r["n_lost_rows"]})
M = pd.DataFrame(rows)
M.to_csv(RES / "scenario_matrix.csv", index=False)
summary["scenarios"] = M.to_dict("records")
# 過去の年の中身が本当に変わった場面（＝知らせてほしい場面）
truth = {"本物 2024年版→2025年版": True, "本物 2025年版→2026年版": False, "S0 同じ中身をもう一度取る": False,
         "S1 文字コードだけ変わる": False, "S2 過去の1セルだけ直る": True, "S3 1列の単位が変わる": True,
         "S4 列の並びが入れ替わる": False, "S5 1行が抜ける": True, "S6 項目名だけ変わる": False, "S7 値だけ隣の列とずれる": True}
M["中身が変わった"] = M["場面"].map(truth)
acc = {}
for c in ("C1_hash", "C2_shape", "C3_schema", "C4_keys", "C5_values"):
    hit = M[c] & M["中身が変わった"]; fa = M[c] & ~M["中身が変わった"]
    acc[c] = {"見つけた": int(hit.sum()), "中身が変わった場面": int(M["中身が変わった"].sum()), "空振り": int(fa.sum()),
              "変わっていない場面": int((~M["中身が変わった"]).sum())}
summary["accuracy"] = acc
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))

# --- 図1：場面×点検の表 ---
lab = {"C1_hash": "C1 ハッシュ", "C2_shape": "C2 行数・列数", "C3_schema": "C3 列の並び", "C4_keys": "C4 キー", "C5_values": "C5 重なる年の値"}
fig, ax = plt.subplots(figsize=(10.5, 5.6))
cs = list(lab)
for i, r in M.iterrows():
    for j, c in enumerate(cs):
        v = bool(r[c]); t = bool(r["中身が変わった"])
        col = (BLUE if t else ORANGE) if v else ("#f2d4c8" if t else "#f4f4f2")
        ax.add_patch(plt.Rectangle((j, -i), 0.96, -0.9, color=col))
        ax.text(j + 0.48, -i - 0.45, "反応" if v else "−", ha="center", va="center", fontsize=10, color="white" if v else INK)
    ax.text(-0.1, -i - 0.45, r["場面"] + ("  ●" if r["中身が変わった"] else ""), ha="right", va="center", fontsize=10)
for j, c in enumerate(cs):
    ax.text(j + 0.48, 0.25, lab[c], ha="center", va="bottom", fontsize=10)
ax.set_xlim(-2.7, 5); ax.set_ylim(-len(M) - 0.1, 0.9); ax.axis("off")
ax.set_title("どの点検が反応したか（●＝過去の年の中身が本当に変わった場面）\n青＝正しく反応　橙＝空振り　薄い橙＝見落とし", loc="left", fontsize=12)
save(fig, "a259_matrix.png")

# --- 図2：本物の改訂（2024年版→2025年版）---
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw={"width_ratios": [1.4, 1]})
bi = by_item.sort_values("cells")
axes[0].barh(bi["name"], bi["cells"], color=BLUE)
for y_, v in enumerate(bi["cells"]):
    axes[0].text(v + 1, y_, f"{v}", va="center", fontsize=9)
axes[0].set_xlabel("値が変わったセルの数")
axes[0].set_title("2024年版→2025年版で値が変わった項目", loc="left", fontsize=11)
by = ch.groupby("year").size()
axes[1].bar(by.index, by.values, color=BLUE)
for x_, v in zip(by.index, by.values):
    axes[1].text(x_, v + 2, f"{v}", ha="center", fontsize=9)
axes[1].set_title("変わったセルの年度", loc="left", fontsize=11)
axes[1].set_ylabel("セル数")
fig.suptitle(f"重なる11年度分 {real['2024→2025']['n_overlap_cells']:,} セルのうち {len(ch)} セル（{len(ch)/real['2024→2025']['n_overlap_cells']*100:.2f}%）が変わっていた。変化は最大 {ch['rel'].abs().max()*100:.2f}%",
             x=0.0, ha="left", fontsize=11)
fig.tight_layout()
save(fig, "a259_real_changes.png", y=-0.04)

# --- 図3：毎月（毎年）取り直す手順 ---
steps = [("1 取る", "ファイルを日付つきの名前で保存。上書きしない"),
         ("2 ハッシュ", "前回と同じなら終わり。違えば先へ（新しい版では毎回違う）"),
         ("3 形と列", "行数・列数、項目コードと項目名の並びを前回と照合"),
         ("4 キー", "年度×地域コードに重複・欠けがないか"),
         ("5 重なる年の値", "前の版と同じ年・同じコードの値を1セルずつ照合"),
         ("6 記録", "変わったセルを一覧に残し、使う側に知らせる")]
fig, ax = plt.subplots(figsize=(10.5, 3.9)); ax.axis("off")
for i, (h, t) in enumerate(steps):
    y0 = 1 - i * 0.165
    ax.add_patch(plt.Rectangle((0, y0 - 0.13), 0.2, 0.13, color=BLUE if i in (4,) else LIGHT, transform=ax.transAxes))
    ax.text(0.1, y0 - 0.065, h, ha="center", va="center", fontsize=11, color="white" if i == 4 else INK, transform=ax.transAxes)
    ax.text(0.23, y0 - 0.065, t, ha="left", va="center", fontsize=11, transform=ax.transAxes)
ax.set_title("統計表を定期的に取り直す6つの手順（過去の値の変化を空振りなしで全部見つけたのは5だけ）", loc="left", fontsize=12)
save(fig, "a259_steps.png")
print(json.dumps({k: summary[k] for k in ("first_col_header", "accuracy", "real_2024_2025_by_year", "roundtrip_identical")}, ensure_ascii=False))
print(M.to_string())
