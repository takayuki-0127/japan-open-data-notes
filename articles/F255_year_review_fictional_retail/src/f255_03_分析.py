# F255 03 分析：1年分（F246〜F253）の振り返りを数字で行う
#  A. 素朴なやり方と採用したやり方の比較（各回の結果から）
#  B. 同じ「偶然の幅」を何度測ったか、値はそろっていたか
#  C. コードの点検：前の回への依存・同じ処理の繰り返し・版の固定
#  D. 予算の答え合わせ（1回）と、モデルの順位
#  E. 頑健性：比べる相手を変えても結論が変わらないか
import json, re
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
IN = HERE / "data" / "in"
RES = HERE / "results"
RES.mkdir(exist_ok=True)
N = pd.read_csv(HERE / "data/processed/numbers.csv").set_index("id")["値"]
ARTS = ["F246", "F247", "F248", "F249", "F250", "F251", "F252", "F253"]
Z95, Z90 = 1.959964, 1.644854

# ---------------- A
A = pd.DataFrame([
    ["F247", "データを整える", "全店売上の正解とのずれ", "どの手当てもしない", "8つの手当て", N.D247_naive_allsales, N.D247_ok_allsales, "低い方が良い", "%"],
    ["F248", "月次レポート", "店の例外のうち、本当に差がある店の割合", "前年比の上下5店", "今月3σか3か月続けて1σ", N.R248_top5_true, N.R248_rule_true, "高い方が良い", "%"],
    ["F249", "ダッシュボード", "差のない店×月に色がつく割合", "決めた線（±3pt）", "偶然の幅（95%）", N.V249_fixed_false, N.V249_band_false, "低い方が良い", "%"],
    ["F251", "販促の効果", "黒字の販促が赤字に見えた割合（20通り）", "前年比の差", "合成対照", N["P251_neg_前年比の差"] / 20 * 100, N["P251_neg_合成対照"] / 20 * 100, "低い方が良い", "%"],
    ["F252", "予算", "80%の幅に実際が入った割合", "ETS の区間", "業界の外れ＋自社の揺れ", N.F252_cov_ets, N.F252_cov_borrow, "80%に近い方が良い", "%"],
    ["F253", "データの品質", "入れた汚れを見つけた割合", "決めた範囲だけ", "ありえない形8つ", N.Q253_fixed, N.Q253_detect, "高い方が良い", "%"],
], columns=["回", "仕事", "ものさし", "素朴なやり方", "採用したやり方", "素朴", "採用", "向き", "単位"])
A.to_csv(RES / "A_before_after.csv", index=False, encoding="utf-8-sig")

# ---------------- B 偶然の幅（95% に直してそろえる）
B = pd.DataFrame([
    ["全社・月・売上の前年比", "F246", 95, N.N246_company_month_sales, "期間中ずっと営業の20店、36か月"],
    ["全社・月・売上の前年比", "F248", 95, N.N248_company_month_sales, "全店の売上（K10）、24か月"],
    ["全社・月・売上の前年比", "F249", 95, N.N249_company_month_sales, "全社、24か月"],
    ["全社・月・売上の前年比", "F250", 90, N.N250_company_month_sales90, "既存店、2026年3月だけ"],
    ["1店・月・売上の前年比", "F246", 95, N.N246_store_month_sales, "1店、36か月"],
    ["1店・月・売上の前年比", "F248", 95, N.N248_store_month_sales, "1店、24か月"],
    ["1店・月・売上の前年比", "F249", 95, N.N249_store_month_sales, "店×月の『全社との差』（中身が少し違う）"],
    ["1店・月・売上の前年比", "F250", 90, N.N250_store_month_sales90, "2026年3月、店ごとの幅の中央値"],
], columns=["量", "回", "幅の取り方（%）", "書いた値", "中身"])
B["95%に直した値"] = B.apply(lambda r: r["書いた値"] * (Z95 / Z90 if r["幅の取り方（%）"] == 90 else 1), axis=1)
Bs = B.groupby("量")["95%に直した値"].agg(["min", "max"])
Bs["最大÷最小"] = Bs["max"] / Bs["min"]
B.to_csv(RES / "B_noise_bands.csv", index=False, encoding="utf-8-sig")

# ---------------- C コードの点検
rows = []
for a in ARTS:
    src = {p.name: p.read_text(encoding="utf-8") for p in sorted((IN / a / "src").glob("*.py"))}
    code = "\n".join(src.values())
    req = (IN / a / "requirements.txt").read_text(encoding="utf-8")
    req_lines = [l for l in req.splitlines() if l.strip() and not l.strip().startswith("#")]
    rows.append(dict(
        回=a, スクリプト=len(src), 行数=sum(len(t.splitlines()) for t in src.values()),
        F246に依存_フォルダ名=int("F246_kpi_definitions" in code), F246に依存_コミットか関数=int(("3006b82" in code) or bool(re.search(r"\bgen\(", code))),
        F247に依存_フォルダ名=int("F247_data_mart" in code), F247に依存_コミットか関数=int(("e8ba90f" in code) or ("build_mart_pd" in code)),
        合成データを作り直す=int(bool(re.search(r"\bgen\(", code))) if a != "F246" else 1,
        乱数の種20通り=int(bool(re.search(r"range\(\s*20\s*\)|SEEDS|seeds", code))),
        偶然の幅を計算=int(bool(re.search(r"1\.96|1\.6449|1\.645|quantile\(\s*0\.0?5|percentile", code))),
        版の固定=sum("==" in l for l in req_lines), 版の下限だけ=sum((">=" in l) and ("==" not in l) for l in req_lines),
    ))
C = pd.DataFrame(rows)
C.to_csv(RES / "C_code_audit.csv", index=False, encoding="utf-8-sig")
# 2つの数え方（フォルダ名・コミットか関数名）が、その回より後の回で一致するか（自分の回は数えない）
later246 = C[C.回 > "F246"]; later247 = C[C.回 > "F247"]
dep_agree = bool((later246.F246に依存_フォルダ名 == later246.F246に依存_コミットか関数).all()
                 and (later247.F247に依存_フォルダ名 == later247.F247に依存_コミットか関数).all())
audit254 = None
p254 = IN / "F254/results/A_audit.json"
if p254.exists():
    audit254 = json.loads(p254.read_text(encoding="utf-8"))

# ---------------- D 予算の答え合わせ（モデルの順位）
D = pd.DataFrame([
    ["季節ナイーブ", 2.52, N["F252_check_季節ナイーブ"]],
    ["季節ナイーブ＋伸び＋暦（予算に使った形）", 1.38, N.F252_check_diff],
    ["ETS", 1.43, N.F252_check_ETS],
    ["SARIMA", 1.14, N.F252_check_SARIMA],
], columns=["モデル", "過去の1年合計の外れ（MAPE %, F252 の表）", "2026年4〜8月の差（%）"])
D["過去の順位"] = D.iloc[:, 1].rank().astype(int)
D["答え合わせの順位"] = D.iloc[:, 2].abs().rank().astype(int)
D.to_csv(RES / "D_budget_check_rank.csv", index=False, encoding="utf-8-sig")
# 過去の MAPE は F252 の main.json の値と照合する
f252 = json.loads((IN / "F252/results/main.json").read_text(encoding="utf-8"))
mape = f252["A_annual_mape"]["全社|足し上げ"]
assert abs(mape["季節ナイーブ"] - 2.52) < 1e-9 and abs(mape["ETS"] - 1.43) < 1e-9 and abs(mape["SARIMA"] - 1.14) < 1e-9 and abs(mape["季節ナイーブ＋伸び＋暦"] - 1.38) < 1e-9

# ---------------- E 頑健性：比べる相手を変える
f249 = pd.read_csv(IN / "F249/results/D_noise_flags_20seeds.csv", encoding="utf-8-sig")
def g249(line, col="郊外（設定上の差なし）に色がつく割合"):
    return f249[(f249.KPI == "売上の前年比の全社との差") & (f249["粒度"] == "店×月") & (f249["線"] == line)][col].iloc[0] * 100
f248 = json.loads((IN / "F248/results/main.json").read_text(encoding="utf-8"))["B"]
f253 = json.loads((IN / "F253/results/summary.json").read_text(encoding="utf-8"))
f252c = f252["C_coverage"]
cov = {(r["method"], r["model"]): r["covered"] for r in f252c}
E = pd.DataFrame([
    ["F248", "採用の代わりに『今月3σだけ』", "本当に差がある割合", f248["今月 3σ 超え"]["本当に差がある割合"] * 100, "見つけた割合は51%に下がる"],
    ["F248", "採用の代わりに『今月1.96σ』", "本当に差がある割合", f248["今月 1.96σ 超え"]["本当に差がある割合"] * 100, "上下5店（6%）よりは良い"],
    ["F249", "偶然の幅を90%（1.64σ）に", "差のない店×月に色", g249("偶然の幅（1.64σ）"), "決めた線（37%）よりずっと少ない"],
    ["F249", "偶然の幅を99%（2.58σ）に", "差のない店×月に色", g249("偶然の幅（2.58σ）"), ""],
    ["F251", "合成対照の代わりに差の差", "赤字に見えた割合", N["P251_neg_差の差"] / 20 * 100, "前年比の差（35%）よりずっと少ない"],
    ["F252", "ETS の代わりに SARIMA の区間", "80%の幅に入った割合", cov[("①モデルの区間", "SARIMA")], "モデルの区間はどちらも80%に届かない"],
    ["F252", "業界の外れだけ（自社の揺れなし）", "80%の幅に入った割合", cov[("③'業界の外れだけ", "季節ナイーブ＋伸び")], ""],
    ["F253", "線を1.3倍に下げる", "汚れのない月の誤報（1か月）", f253["pos3_fa_T13"]["abc"], "決めた範囲だけは誤報0（見つけるのは49%）"],
], columns=["回", "変えたこと", "ものさし", "値", "メモ"])
E.to_csv(RES / "E_alt_choices.csv", index=False, encoding="utf-8-sig")

main = dict(
    A=A.set_index("回")[["素朴", "採用"]].round(4).to_dict("index"),
    B_range=Bs.round(4).to_dict("index"),
    C=dict(articles=len(C), scripts=int(C.スクリプト.sum()), lines=int(C.行数.sum()),
           regen_synthetic=int(C.合成データを作り直す.sum()), seeds20=int(C.乱数の種20通り.sum()),
           noise_band_code=int(C.偶然の幅を計算.sum()), pinned=int(C.版の固定.sum()), floor_only=int(C.版の下限だけ.sum()),
           depends_F246=int(later246.F246に依存_コミットか関数.sum()), depends_F247=int(later247.F247に依存_コミットか関数.sum()),
           dep_methods_agree=dep_agree),
    F254_audit=audit254,
    D=D.to_dict("records"),
    explain_per_month=dict(raw_moved=N.R248_raw_moved, raw_explained=N.R248_raw_explain, market_explained=N.R248_mkt_explain),
)
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
print(A[["回", "素朴", "採用"]].to_string()); print(B.to_string()); print(Bs); print(C.to_string()); print(D.to_string()); print(E.to_string())
print("依存の2つの数え方が一致", dep_agree)
