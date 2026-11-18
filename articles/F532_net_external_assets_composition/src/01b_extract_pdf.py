"""01b 抜き出し（run_all.sh からは呼ばない。結果は data/extracted に同梱済み）。
財務省「増減要因（試算）」の PDF（2019〜2025年末）を pdftotext -layout（poppler-utils）でテキストにし、
行の先頭の見出しの文字（「１．直接投資」「資産合計」「純資産合計」など。空白は除いて照合）で項目を決めて数字を読む。
左半分が資産、右半分が負債。数字は 前年末残高・当年末残高・前年末比・取引・為替相場変動・その他調整 の6つ（10億円）。
「▲」は負、「--」は0。注2の「対外資産…兆円のうち…兆円が外貨建て資産」も読む。
出力：data/extracted/iip_factors_YYYY.txt、data/extracted/iip_factors.csv、data/extracted/fx_denominated.csv
"""
import csv, pathlib, re, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, X = ROOT / "data" / "raw", ROOT / "data" / "extracted"
ITEMS = {"１．直接投資": "直接投資", "２．証券投資": "証券投資", "３．金融派生商品": "金融派生商品",
         "４．その他投資": "その他投資", "５．外貨準備": "外貨準備", "資産合計": "合計", "負債合計": "合計", "純資産合計": "合計"}
NUM = r"▲\s*[\d,]+|--|[\d,]+"


def nums(s):
    out = []
    for t in re.findall(NUM, s):
        t = t.replace(",", "").replace(" ", "")
        out.append(0.0 if t == "--" else (-float(t[1:]) if t.startswith("▲") else float(t)))
    return out


def main():
    X.mkdir(parents=True, exist_ok=True)
    rows, fxr = [], []
    for y in range(2019, 2026):
        txt = subprocess.run(["pdftotext", "-layout", str(RAW / f"iip_factors_{y}.pdf"), "-"], capture_output=True, text=True, check=True).stdout
        (X / f"iip_factors_{y}.txt").write_text(txt, encoding="utf-8")
        for line in txt.splitlines():
            flat = re.sub(r"[ 　]", "", line)
            for lab, item in ITEMS.items():
                if flat.startswith(lab):
                    if lab == "純資産合計":
                        side_parts = [("net", line)]
                    else:
                        # 右半分の見出しの位置で分ける（「１．直接投資」は左右に2回出る）
                        key = lab if lab not in ("資産合計",) else "資産合計"
                        right_lab = {"資産合計": "負債合計"}.get(lab, lab)
                        m = [mm.start() for mm in re.finditer(r"[ 　]*".join(right_lab), line)]
                        if lab == "資産合計":
                            cut = m[0] if m else None
                        else:
                            cut = m[1] if len(m) > 1 else None
                        left = line[:cut] if cut else line
                        right = line[cut:] if cut else ""
                        side_parts = [("assets", left)] + ([("liabilities", right)] if right else [])
                    for side, part in side_parts:
                        body = re.sub(r"^[ 　]*([１-５]．)?[^\d▲-]*", "", part)
                        v = nums(body)
                        if len(v) >= 6:
                            rows.append({"year": y, "side": side, "item": item, "prev": v[0], "curr": v[1], "change": v[2],
                                         "flow": v[3], "fx": v[4], "other": v[5]})
                    break
            m = re.search(r"対外資産([\d,\.]+)兆円のうち([\d,\.]+)兆円が外貨建て資産、同じく対外負債([\d,\.]+)兆円のうち([\d,\.]+)兆円が外貨建て負債", flat)
            if m:
                a, af, l, lf = [float(g.replace(",", "")) for g in m.groups()]
                fxr.append({"year": y, "assets_tn": a, "assets_fx_tn": af, "liab_tn": l, "liab_fx_tn": lf})
    with open(X / "iip_factors.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with open(X / "fx_denominated.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fxr[0])); w.writeheader(); w.writerows(fxr)
    print(len(rows), "rows;", len(fxr), "fx rows")


if __name__ == "__main__":
    main()
