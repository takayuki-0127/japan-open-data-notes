"""data/raw の表を CSV にする。
- data/national.csv：年×所有の関係（総数・持ち家・借家）×世帯人員（総数・1〜6人以上）の 総数・水準以上・水準未満
- data/pref.csv：年×都道府県の 総数・水準以上・水準未満
"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
SIZES = ["総数", "1人", "2人", "3人", "4人", "5人", "6人以上"]


def z(s):
    return re.sub(r"[\s　]", "", str(s))


def num(v):
    return pd.to_numeric(str(v).replace(",", "").strip(), errors="coerce")


def old_national(path, year):
    d = pd.read_excel(path, header=None)
    rows, tenure, k = [], None, 0
    for i in range(23, len(d)):
        lab = z(d.iloc[i, 7])
        if lab in ("主世帯総数", "持ち家", "借家"):
            tenure, k = {"主世帯総数": "総数", "持ち家": "持ち家", "借家": "借家"}[lab], 0
        elif tenure and re.match(r"^[１-６1-6]", lab):
            k += 1
        else:
            tenure = None if lab not in ("nan",) else tenure
            continue
        rows.append(dict(year=year, tenure=tenure, size=SIZES[k], total=num(d.iloc[i, 10]), above=num(d.iloc[i, 11]), below=num(d.iloc[i, 12])))
    return rows


def new_table(path, year, c_lv, c_reg, c_ten, c_size, c_val):
    d = pd.read_excel(path, header=None)
    nat, pref = [], []
    for i in range(len(d)):
        if str(d.iloc[i, c_lv]).strip() != "a":
            continue
        reg, ten, size = str(d.iloc[i, c_reg]), z(d.iloc[i, c_ten]), z(d.iloc[i, c_size])
        vals = dict(total=num(d.iloc[i, c_val]), above=num(d.iloc[i, c_val + 1]), below=num(d.iloc[i, c_val + 2]))
        code = reg[:5]
        tmap = {"0_総数": "総数", "1_持ち家": "持ち家", "2_借家": "借家"}
        if code == "00000" and ten in tmap:
            s = SIZES[int(size.split("_")[0])]
            nat.append(dict(year=year, tenure=tmap[ten], size=s, **vals))
        elif code.endswith("000") and code != "00000" and ten == "0_総数" and size == "0_総数":
            pref.append(dict(year=year, pref=int(code[:2]), **vals))
    return nat, pref


def old_pref(path, year):
    d = pd.read_excel(path, header=None)
    out = []
    for i in range(len(d)):
        cells = [v for v in d.iloc[i].tolist() if str(v) != "nan"]
        if not cells:
            continue
        m = re.match(r"^(\d{2})[\s　]", str(cells[0]))
        if m and len(cells) > 4:
            nums = [num(v) for v in cells[2:5]]
            out.append(dict(year=year, pref=int(m.group(1)), total=nums[0], above=nums[1], below=nums[2]))
    return [r for r in out if r["pref"] <= 47][:47]


def main():
    nat = old_national(RAW / "h2008_t57_tenure_size_japan.xls", 2008) + old_national(RAW / "h2013_t68_tenure_size_japan.xls", 2013)
    pref = old_pref(RAW / "h2008_t12_pref.xls", 2008) + old_pref(RAW / "h2013_t12_pref.xls", 2013)
    n, p = new_table(RAW / "h2018_t76_1_tenure_size.xlsx", 2018, 4, 5, 7, 9, 10); nat += n; pref += p
    n, p = new_table(RAW / "h2023_t75_1_tenure_size.xlsx", 2023, 0, 1, 2, 3, 4); nat += n; pref += p
    nat = pd.DataFrame(nat); pref = pd.DataFrame(pref)
    assert nat.groupby("year").size().eq(21).all(), nat.groupby("year").size()
    assert pref.groupby("year").size().eq(47).all(), pref.groupby("year").size()
    nat.to_csv(DATA / "national.csv", index=False)
    pref.sort_values(["year", "pref"]).to_csv(DATA / "pref.csv", index=False)
    print(nat[nat["size"] == "総数"])


if __name__ == "__main__":
    main()
