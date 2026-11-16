"""02 整形：各回の報道発表の PDF の表（都市部・都市部近郊・地方・総計、総数・再配達数・再配達率）を取り出す。
PDF は pdftotext（poppler-utils）で文字にする。同じ時期の値が複数の回に出るときは、その時期の回の値を優先する。"""
import pathlib, re, subprocess, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AREA = {"都市部": "都市部", "都市部近郊": "都市部近郊", "地方": "地方", "総計": "総計", "総計(参考)": "総計(参考)"}


def text(f):
    t = subprocess.run(["pdftotext", "-layout", str(f), "-"], capture_output=True, text=True).stdout
    return unicodedata.normalize("NFKC", t)


def periods(line):
    out = []
    for era, y, m in re.findall(r"(平成|令和|H|R)\s*(\d+)\s*[/年]\s*(\d+)\s*[/月]\s*1\s*日?", line):
        base = 1988 if era in ("平成", "H") else 2018
        out.append(f"{base + int(y)}-{int(m):02d}")
    return out


def main():
    rows = []
    for f in sorted(RAW.glob("press_*.pdf")):
        rel = f.name.split("_")[1]
        t = text(f)
        ps = []
        six = "6社" in t or "６社" in t
        for line in t.splitlines():
            if "調査期間" in line and periods(line):
                ps = periods(line)          # 表のすぐ上の「調査期間」の行の時期を使う
                continue
            m = re.match(r"^\s*(都\s*市\s*部\s*近\s*郊|都\s*市\s*部|地\s*方|総\s*計\s*\(\s*参\s*考\s*\)|総\s*計)\s+(.*)$", line)
            if not m:
                continue
            name = re.sub(r"\s", "", m.group(1))
            groups = re.findall(r"([\d,]{5,})\s+([\d,]{3,})\s+([\d.]+)\s*%", m.group(2))
            for i in range(min(len(groups), len(ps))):
                tot, red, rate = groups[i]
                base = "3社" if (not six or name == "総計(参考)") else "6社"
                area = "総計" if name == "総計(参考)" else name
                rows.append((rel, ps[i], base, area, int(tot.replace(",", "")), int(red.replace(",", "")),
                             float(rate.rstrip("%")), int(ps[i] == rel)))
    d = pd.DataFrame(rows, columns=["release", "period", "base", "area", "total", "redelivered", "rate_pub", "own"])
    d["rate"] = 100 * d.redelivered / d.total
    d = d[d.period.str[-2:].isin(["04", "10"])]            # 再配達の調査は4月と10月だけ（ほかの表の行を除く）
    d.to_csv(ROOT / "data" / "all_rows.csv", index=False)
    # その時期の回の値を優先し、なければいちばん新しい回の値
    d = d.sort_values(["base", "area", "period", "own", "release"], ascending=[True, True, True, False, False])
    u = d.drop_duplicates(["base", "area", "period"]).sort_values(["base", "area", "period"])
    u.to_csv(ROOT / "data" / "series.csv", index=False)
    print(u.pivot_table(index="period", columns=["base", "area"], values="rate").round(1).to_string())
    bad = d[(d.rate - d.rate_pub).abs() > 0.06]
    print("公表の率と計算した率の差が0.06ポイントを超える行", len(bad))
    print(bad.to_string())


if __name__ == "__main__":
    main()
