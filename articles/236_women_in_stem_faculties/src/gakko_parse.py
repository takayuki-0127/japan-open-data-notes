"""学校基本調査（文部科学省）の高等教育機関・専修学校の Excel を、年ごとに同じ形の表に直す。
2000〜2025年度で表の番号や書式が何度か変わっているので、表の番号ではなく「行の見出し」と
「計＝男＋女」の関係を手がかりに数字を拾う。"""
import re, glob, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

GU_MAJ = ["人文科学", "社会科学", "理学", "工学", "農学", "保健", "商船", "家政", "教育", "芸術", "その他"]
GJ_MAJ = ["人文", "社会", "教養", "工業", "農業", "保健", "家政", "教育", "芸術", "その他"]
S_MAJ = ["工業関係", "農業関係", "医療関係", "衛生関係", "教育・社会福祉関係", "商業実務関係", "服飾・家政関係", "文化・教養関係"]


def rows(path, sheet=0):
    """1シートを (見出しのリスト, 数値のリスト) の並びにする"""
    d = pd.read_excel(path, sheet_name=sheet, header=None)
    out = []
    for r in d.itertuples(index=False):
        lab = [re.sub(r"[\s　]", "", v) for v in r if isinstance(v, str) and v.strip()]
        lab = [x for x in lab if x not in ("―", "-", "－")]
        nums = [float(v) for v in r if isinstance(v, (int, float)) and not pd.isna(v)]
        if nums and len(lab) > 1 and re.fullmatch(r"(平成|令和)\S*年度", lab[0]):
            lab = lab[1:]                  # 2021年度以降の書式：行の頭に年度が入る
            if all(x == "計" for x in lab):
                lab = ["（年度）"]               # 年度の合計の行
        if lab or nums:
            out.append((lab, nums))
    return out


def triple(nums, start=0):
    """nums の中で最初に「a = b + c」（計・男・女）になる位置を探す"""
    for i in range(start, len(nums) - 2):
        a, b, c = nums[i:i + 3]
        if a > 0 and abs(a - (b + c)) <= 1:
            return i, (a, b, c)
    for i in range(start, len(nums) - 2):           # すべて0の行
        if nums[i:i + 3] == [0, 0, 0]:
            return i, (0.0, 0.0, 0.0)
    return None, None


def is_year_row(lab, nums):
    s = "".join(lab)
    if re.search(r"(平成|令和)\S*年度|（年度）", s):
        return True
    return (not lab) and nums and nums[0] < 100 and len(nums) > 3


def year_total(rs, second=True, which=0):
    """表の最初の「前年度・本年度」の行のうち本年度（2つ目）。which=1 なら2組目の計男女（入学者）"""
    ys = [k for k, (lab, nums) in enumerate(rs) if is_year_row(lab, nums)]
    k = ys[1] if (second and len(ys) > 1) else ys[0]
    nums = rs[k][1]
    i, t = triple(nums)
    if which == 1:
        i2, t = triple(nums, i + 3)
    return k, t


def majors(rs, MAJ, start, which=0, subs=False):
    """大分類の行（と必要なら小分類の行）を順に拾う。その他は「計−その他以外の合計」で出す"""
    res, sub, cur, nxt = {}, [], None, 0
    for lab, nums in rs[start + 1:]:
        if not nums or not lab:
            continue
        head = re.sub(r"（各種学校は.*?）", "", lab[0])
        is_major = (nxt < len(MAJ) - 1 and head == MAJ[nxt] and (len(lab) == 1 or lab[-1] in (head, "計")))
        if is_major:
            cur = head; nxt += 1
            i, t = triple(nums)
            if which == 1:
                i, t = triple(nums, i + 3)
            res[cur] = t
            continue
        if subs and cur is not None and nxt <= len(MAJ) - 1:
            i, t = triple(nums)
            if which == 1 and i is not None:
                i, t = triple(nums, i + 3)
            if t is not None:
                sub.append((cur, lab[-1], *t))
        if nxt == len(MAJ) - 1 and cur == MAJ[-2] and head in ("その他",) and False:
            pass
    return res, sub


def table_by_major(path, MAJ, sheet=0, which=0, subs=False):
    rs = rows(path, sheet)
    k, tot = year_total(rs, which=which)
    res, sub = majors(rs, MAJ, k, which=which, subs=subs)
    other = tuple(np.array(tot) - np.sum([res[m] for m in MAJ[:-1] if m in res], axis=0))
    res[MAJ[-1]] = other
    res["計"] = tot
    df = pd.DataFrame([(m, *v) for m, v in res.items()], columns=["分類", "計", "男", "女"])
    sd = pd.DataFrame(sub, columns=["分類", "小分類", "計", "男", "女"])
    # 最後の大分類（その他の直前）のあとに並ぶ「その他」ブロックの行は小分類から外す
    return df, sd


def sheet_names(path):
    return pd.ExcelFile(path).sheet_names


def find(raw, year, tab):
    f = glob.glob(str(Path(raw) / f"{year}_{tab}_*.bin"))
    return f[0] if f else None


def entrants_by_age(path):
    """大学院 年齢別入学者数：課程ごとに（入学者の計男女、社会人の計男女、年齢別の計）"""
    out = {}
    for s in sheet_names(path):
        rs = rows(path, s)
        course = None
        for k, (lab, nums) in enumerate(rs):
            s_ = "".join(lab)
            m = re.search(r"(修士|博士|専門職学位)課程", s_)
            if not nums and ("再掲" in s_ or "法科大学院" in s_ or "教職大学院" in s_):
                course = None                    # 専門職学位課程の再掲は使わない
                continue
            if m and not nums and len(s_) < 30 and "年齢別" not in s_:
                course = m.group(1); out[course] = {"ages": {}}
                continue
            if "大学院（修士課程）" in s_ and not nums:        # 2000〜2002年度は修士だけの表
                course = "修士"; out[course] = {"ages": {}}
                continue
            if course is None or not nums:
                continue
            d = out[course]
            agelab = next((x for x in lab if "歳" in x), "")
            if re.search(r"歳", agelab) and "現在" not in agelab:
                if "total" not in d:
                    # 年齢の最初の行の直前の年度の行が本年度の計
                    j = k - 1
                    while not rs[j][1]:
                        j -= 1
                    d["total"] = triple(rs[j][1])[1]
                d["ages"][agelab] = triple(nums)[1][0] if triple(nums)[1] else np.nan
            elif "社会人" in s_ and "social" not in d:
                d["social"] = triple(nums)[1]
            elif "留学生" in s_ and "intl" not in d:
                d["intl"] = triple(nums)[1]
    return out


def undergrad_by_age(path):
    """大学（学部）年齢別入学者数（2015年度〜）：最初のブロック（昼夜計）"""
    rs = rows(path, 0)
    tot, ages = None, {}
    for k, (lab, nums) in enumerate(rs):
        s_ = "".join(lab)
        if ("昼間" in s_ or "夜間" in s_) and not nums and ages:
            break
        al = next((x for x in lab if "歳" in x and "現在" not in x), None)
        if nums and al:
            if tot is None:
                j = k - 1
                while not rs[j][1]:
                    j -= 1
                tot = triple(rs[j][1])[1]
            ages[al] = triple(nums)[1]
    return tot, ages


def age_lower(lbl):
    m = re.match(r"(\d+)", lbl)
    return int(m.group(1)) if m else None
