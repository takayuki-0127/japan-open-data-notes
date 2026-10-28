"""02_整形：2000年国勢調査（旧市町村）と廃置分合の記録から、旧→新の対応表と長期パネルを作る。

入力
  data/raw/f94_raw.json          … 01_取得 で保存（廃置分合CSV＋2000年国勢調査 第1表×47都道府県）
  data/ssds_present_boundary.csv … 社会・人口統計体系（現在の境域に組み替えた人口、F40 と同じ）
出力
  data/old_units_2000.csv   … 2000年10月1日時点の市町村（政令市は市単位、東京23区は区単位）
  data/merger_events.csv    … 2000-10-02〜2020-10-01 の廃置分合のうち、境域・コードが変わるもの
  data/crosswalk_2000_2020.csv … 旧コード→2020年のコード（連鎖をたどったもの）
  results/validation.json   … 対応表の検算
"""
import io
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = json.load(open(ROOT / "data/raw/f94_raw.json", encoding="utf-8"))

# ---------------------------------------------------------------- 1. 2000年の旧市町村
rows = []
CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
for pref, tab in RAW["census2000_t1"].items():
    pref_done = False
    for r in tab["rows"]:
        if not r:
            continue
        # 表によって列の位置が違う（福井県は7桁コードの列がない）ので、名前の列を探して位置を合わせる
        j = next((i for i, x in enumerate(r[:12]) if isinstance(x, str) and CJK.search(x)
                  and i >= 2 and isinstance(r[i + 3] if i + 3 < len(r) else None, (int, float))), None)
        if j is None:
            continue
        name = r[j].replace("\u3000", "").strip()
        c3 = r[j - 1].strip() if isinstance(r[j - 1], str) else None
        if name.endswith(("都", "道", "府", "県")) and c3 and len(c3) == 2 and not pref_done:
            code, pref_done = f"{int(pref):02d}000", True
        elif c3 and re.fullmatch(r"\d{3}", c3):
            code = f"{int(pref):02d}{c3}"
        else:
            code = None
        rows.append(dict(pref=int(pref), code=code, name=name,
                         pop2000=r[j + 3], pop1995=r[j + 4], area=r[j + 7]))
cen = pd.DataFrame(rows)
cen = cen[cen.code.notna()]
pref_tot = cen[cen.code.str[2:] == "000"].drop_duplicates("pref").set_index("pref").pop2000

def unit_type(row):
    c, n = row["code"], row["name"]
    if c[2:] == "000" or n in ("市部", "郡部", "特別区部", "人口集中地区"):
        return "agg"
    if n.endswith(("郡", "支庁", "振興局")):
        return "agg"
    tail = int(c[2:])
    if c[:2] == "13" and 101 <= tail <= 123:
        return "ward23"
    if 100 <= tail <= 199 and n.endswith("区"):
        return "ward"           # 政令市の区（市の行で数える）
    if 100 <= tail <= 199 and n.endswith("市"):
        return "seirei"         # 政令市（市全体）
    return "muni"

cen["type"] = cen.apply(unit_type, axis=1)
old = cen[cen.type.isin(["muni", "seirei", "ward23"])].copy()
old = old.drop_duplicates("code")
chk = old.groupby("pref").pop2000.sum().sub(pref_tot).abs().max()
old[["pref", "code", "name", "type", "pop2000", "pop1995", "area"]].to_csv(
    ROOT / "data/old_units_2000.csv", index=False)

# ---------------------------------------------------------------- 2. 廃置分合の記録
m = pd.read_csv(io.StringIO(RAW["merger_csv"]), dtype=str)
m.columns = ["code", "pref", "gun", "gunk", "name", "namek", "date", "reason"]
m["reason"] = m.reason.str.replace("\r", "")
CODE = re.compile(r"\((\d{5})\)")

events = []  # (date, kind, olds, new, text)
SPLITS = {}
for (date, reason), g in m.groupby(["date", "reason"], sort=False):
    rowcodes = list(dict.fromkeys(g.code))
    for line in reason.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "が合併し" in line and "を新設" in line:
            head, tail = line.split("が合併し", 1)
            olds = CODE.findall(head)
            newc = CODE.findall(tail)
            if newc:
                new = newc[0]
            else:
                cand = [c for c in rowcodes if c not in olds and c[2:] != "000"]
                newname = re.search(r"、(.+?)を新設", tail).group(1)
                # 名前を引き継ぐ新設（例：一関市(03209)…が合併し、一関市を新設）はコードも引き継ぐ
                same = [c for c in olds if re.search(r"(^|、)" + re.escape(newname) + r"\(" + c, head)]
                new = same[0] if same else (cand[0] if cand else None)
            events.append((date, "新設合併", olds, new, line))
        elif "に編入し、" in line:
            # 分割して2つの市町村に編入（上九一色村の1件）。大字の数で多い側に寄せ、按分は 03_分析 の頑健性で扱う
            cs = CODE.findall(line)
            events.append((date, "分割編入", [cs[0]], cs[-1], line))
            SPLITS[cs[0]] = cs[1:]
        elif "に編入" in line:
            head, tail = line.split("が", 1) if line.count("が") == 1 else line.rsplit("が", 1)
            olds = CODE.findall(head)
            new = CODE.findall(tail)[-1]
            events.append((date, "編入合併", olds, new, line))
        elif "政令指定都市" in line and "への" in line:
            cs = CODE.findall(line)
            events.append((date, "政令市移行", [cs[0]], cs[1], line))
        elif "市制施行" in line or "町制施行" in line:
            cs = CODE.findall(line)
            if len(cs) >= 2:
                events.append((date, "市制・町制", [cs[0]], cs[-1], line))
        elif "区域変更" in line and "が" in line:
            head, tail = line.split("が", 1)
            for o, n in zip(CODE.findall(head), CODE.findall(tail)):
                if o != n:
                    events.append((date, "コード変更", [o], n, line))
        elif "名称変更" in line and len(set(CODE.findall(line))) == 2:
            cs = CODE.findall(line)
            events.append((date, "コード変更", [cs[0]], cs[-1], line))

ev = pd.DataFrame(events, columns=["date", "kind", "olds", "new", "text"])
mask = (ev.kind == "編入合併") & ev.text.str.contains("大字")
ev.loc[mask, "olds"] = ev.loc[mask, "olds"].apply(lambda o: [c for c in o if c not in SPLITS])
ev = ev.assign(_k=ev.olds.str.join(";")).drop_duplicates(subset=["date", "text", "_k"]).drop(columns="_k").sort_values("date").reset_index(drop=True)
ev["n_old"] = ev.olds.str.len()
ev.assign(olds=ev.olds.str.join(";")).to_csv(ROOT / "data/merger_events.csv", index=False)

# ---------------------------------------------------------------- 3. 連鎖をたどって 2000→2020
succ = {}
for r in ev.itertuples():
    for o in r.olds:
        if o != r.new:
            succ[o] = (r.new, r.date, r.kind)

ssds_codes = pd.read_csv(ROOT / "data/ssds_present_boundary.csv", dtype={"code": str}).code.unique()
SEIREI = sorted(c for c in ssds_codes if c[:2] != "13" and 100 <= int(c[2:]) <= 199)

def to_city(c):
    """政令市の区のコード（例：京都市右京区 26108）を市のコード（26100）に寄せる"""
    if c[:2] != "13" and 101 <= int(c[2:]) <= 199 and c not in SEIREI:
        return max(x for x in SEIREI if x[:2] == c[:2] and x <= c)
    return c

def resolve(c):
    path = [c]
    while c in succ and len(path) < 20:
        c = to_city(succ[c][0])
        path.append(c)
    return c, path

ssds = pd.read_csv(ROOT / "data/ssds_present_boundary.csv", dtype={"code": str})
s20 = ssds[ssds.year == 2020].set_index("code")
cw = []
for r in old.itertuples():
    new, path = resolve(r.code)
    merged_kinds = [succ[p][2] for p in path[:-1]]
    cw.append(dict(code2000=r.code, name2000=r.name, code2020=new,
                   n_steps=len(path) - 1,
                   merged=any(k in ("新設合併", "編入合併") for k in merged_kinds),
                   path=">".join(path)))
cw = pd.DataFrame(cw)
# 合併に関わった 2020 年の単位（吸収した側を含む）
grp = cw.groupby("code2020").agg(n_old=("code2000", "size"), any_merged=("merged", "any"))
cw = cw.merge(grp, left_on="code2020", right_index=True)
cw["unchanged"] = (cw.n_old == 1) & (~cw.any_merged)
cw.to_csv(ROOT / "data/crosswalk_2000_2020.csv", index=False)

# ---------------------------------------------------------------- 4. 検算
agg = old.merge(cw[["code2000", "code2020"]], left_on="code", right_on="code2000") \
         .groupby("code2020").pop2000.sum()
s05 = ssds[ssds.year == 2005].set_index("code").A1101
ratio = (s05.reindex(agg.index) / agg)
val = dict(
    old_units=int(len(old)),
    old_units_by_type=old.type.value_counts().to_dict(),
    pref_total_max_abs_diff=float(chk),
    events=int(len(ev)), events_by_kind=ev.kind.value_counts().to_dict(),
    new_units=int(agg.size),
    new_units_in_ssds2020=int(agg.index.isin(s20.index).sum()),
    ssds2020_units=int(len(s20)),
    ssds_units_without_old=sorted(set(s20.index) - set(agg.index)),
    old_units_not_in_ssds=sorted(set(agg.index) - set(s20.index)),
    pop2000_total=int(old.pop2000.sum()),
    ratio_ssds2005_to_agg2000_median=float(ratio.median()),
    ratio_outside_0p8_1p2=int(((ratio < 0.8) | (ratio > 1.2)).sum()),
    unchanged_units_2000=int(cw.unchanged.sum()),
    merged_old_units=int((~cw.unchanged).sum()),
)
(ROOT / "results").mkdir(exist_ok=True)
val["splits"] = SPLITS
val["zero_pop_2000"] = old.loc[old.pop2000.fillna(0) <= 0, "name"].tolist()
json.dump(val, open(ROOT / "results/validation.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(val, ensure_ascii=False, indent=1))
