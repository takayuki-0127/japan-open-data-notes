"""README から特徴量（分析の単位・検出力への言及・頑健性チェックの数）と、
キーワードによる自動判定（見えなかった／言い切れない）を作り、手作業の判定と結合する。"""
import pathlib, re
import pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
man = pd.read_csv(ROOT / "data" / "coding_manual.csv")
fam = pd.read_csv(RAW / "article_family_F122.csv")
NULL_KW = ["0をまたぐ", "0と区別でき", "差は見えな", "見えなかった", "有意ではな", "有意でな", "見分けられな", "見分けにく",
           "偶然と区別", "言えない範囲", "形跡はな", "形跡は見え", "差は消え", "関係は見えず"]
UNC_KW = ["前提しだい", "仮定しだい", "手法で答え", "手法しだい", "そろわな", "逆にな", "揺れ", "で変わった", "動いた", "入れ替わ"]
UNIT = [("法人・地点など（1万以上）", ["万法人", "万地点", "万件", "万組", "万セル"]),
        ("市区町村（約1,700）", ["市区町村", "市町村"]),
        ("都道府県（47）", ["都道府県", "47県", "県別", "県ごと"]),
        ("全国の時系列", ["月次", "四半期", "週次", "時系列"])]
def section(t, head):
    m = re.search(rf"^##\s*{head}[^\n]*\n(.*?)(?=^##\s)", t, re.S | re.M)
    return m.group(1) if m else ""
rows = []
for f in sorted((RAW / "readmes").glob("F*.md"), key=lambda p: int(p.stem[1:])):
    t = f.read_text(encoding="utf-8")
    res = section(t, "主な結果") or section(t, "結果")
    title = t.splitlines()[0]
    unit = "その他"
    head = title + section(t, "手法")[:1500] + section(t, "データ")[:1500]
    for name, kws in UNIT:
        if any(k in head for k in kws):
            unit = name; break
    rob = section(t, "頑健性")
    rows.append(dict(fid=f.stem, title=title.lstrip("# ").strip(), unit=unit,
                     power=int(bool(re.search("検出力|最小検出|見つけられる大きさ", t))),
                     n_rob=len(re.findall(r"^\|", rob, re.M)),
                     kw_null=sum(res.count(k) for k in NULL_KW), kw_unc=sum(res.count(k) for k in UNC_KW),
                     readme_chars=len(t)))
feat = pd.DataFrame(rows)
df = man.merge(feat, on="fid", how="left").merge(fam, on="fid", how="left")
um = pd.read_csv(ROOT / "data" / "unit_manual_effect.csv")  # 効果の記事39本は単位を手で確かめて上書き
df = df.merge(um, on="fid", how="left"); df["unit_auto"] = df["unit"]
df["unit"] = df.unit_manual.fillna(df.unit)
df["num"] = df.fid.str[1:].astype(int)
df["broad"] = df.outcome.isin(["N", "U"]).astype(int)      # 見えなかった＋言い切れない
df["strict"] = (df.outcome == "N").astype(int)              # 見えなかった だけ
df["auto"] = ((df.kw_null >= 1) | (df.kw_unc >= 2)).astype(int)  # README の結果欄だけで判定
df.to_csv(ROOT / "data" / "articles.csv", index=False)
print(df.groupby("type")[["broad", "strict", "auto"]].mean().round(2)); print(df.unit.value_counts())
