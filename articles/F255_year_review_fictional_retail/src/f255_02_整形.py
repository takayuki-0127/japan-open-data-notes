# F255 02 整形：F246〜F253 の結果ファイルから、振り返りに使う数字を1つの表（data/processed/numbers.csv）にする
# 数字はすべて結果ファイルから読む（手で写さない）。各数字に「どのファイルのどこか」を付ける。
import json, csv
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
IN = HERE / "data" / "in"
OUT = HERE / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)


def J(art, rel="results/main.json"):
    return json.loads((IN / art / rel).read_text(encoding="utf-8"))


def dig(d, path):
    for k in path:
        d = d[k]
    return d


rows = []


def add(nid, art, label, value, unit, src, key):
    rows.append(dict(id=nid, 回=art, 項目=label, 値=float(value), 単位=unit, ファイル=src, 場所=key))


def jadd(nid, art, label, path, unit, rel="results/main.json", scale=1.0):
    add(nid, art, label, dig(J(art, rel), path) * scale, unit, rel, "/".join(path))


# ---- F246 KPI を決める
nz = pd.read_csv(IN / "F246/results/C_noise_by_grain.csv", encoding="utf-8-sig")
for nid, lv, gr, kpi in [("N246_store_day_sales", "1店", "日", "売上"), ("N246_store_month_sales", "1店", "月", "売上"),
                         ("N246_company_month_sales", "全社", "月", "売上"), ("N246_store_month_op", "1店", "月", "営業利益"),
                         ("N246_company_month_op", "全社", "月", "営業利益")]:
    v = nz[(nz.level == lv) & (nz.grain == gr) & (nz.KPI == kpi)]["偶然の幅（±1.96σ）"].iloc[0]
    add(nid, "F246", f"偶然の幅（95%）{lv}・{gr}・{kpi}の前年比", v, "±%", "results/C_noise_by_grain.csv", f"{lv}/{gr}/{kpi}")
jadd("K246_exist_sales", "F246", "既存店売上の前年比 FY2025", ["A_tree", "売上", "既存店_変化率"], "%", scale=100)
jadd("K246_exist_op", "F246", "既存店営業利益の前年比 FY2025", ["A_tree", "営業利益", "既存店_変化率"], "%", scale=100)

# ---- F247 データを整える
P = "すべて素朴に（上の手当てをどれもしない）"
jadd("D247_naive_allsales", "F247", "素朴に整えた全店売上の正解とのずれ", ["B", P, "全店売上_FY2025_正解とのずれ"], "%", scale=100)
jadd("D247_naive_opyoy", "F247", "素朴に整えた既存店営業利益の前年比の正解とのずれ", ["B", P, "既存店営業利益の前年比_正解とのずれ"], "pt", scale=100)
jadd("D247_ok_allsales", "F247", "正しく整えた全店売上の正解とのずれ", ["B", "正しく整えたもの", "全店売上_FY2025_正解とのずれ"], "%", scale=100)

# ---- F248 月次レポートの型
B = ["B"]
jadd("R248_top5_true", "F248", "店の例外：前年比の上下5店のうち本当に差がある割合", B + ["売上の前年比の上下5店（順位）", "本当に差がある割合"], "%", scale=100)
jadd("R248_rule_true", "F248", "店の例外：採用した選び方（3σ か 3か月1σ）のうち本当に差がある割合", B + ["採用：今月 3σ か 3か月続けて 1σ", "本当に差がある割合"], "%", scale=100)
jadd("R248_rule_found", "F248", "店の例外：採用した選び方で本当の差を見つけた割合", B + ["採用：今月 3σ か 3か月続けて 1σ", "見つけた割合"], "%", scale=100)
jadd("R248_raw_moved", "F248", "全社KPI：前年比のままの「流れが変わった」（1か月あたり）", ["C", "前年比そのまま", "流れが変わった"], "件")
jadd("R248_raw_explain", "F248", "全社KPI：前年比のまま、ツリーでまとめた後に説明すること（1か月あたり）", ["C", "前年比そのまま", "説明すること（ツリーでまとめた後）"], "件")
jadd("R248_mkt_explain", "F248", "全社KPI：市場との差＋ツリーで説明すること（1か月あたり）", ["C", "採用：市場との差（客数・既存店売上）", "説明すること（ツリーでまとめた後）"], "件")
jadd("R248_close5_noflag", "F248", "速報5日締め：予告がなければ確定で変わって見える判定（12か月計）", ["D", "5", "予告がない場合_合計"], "件")
jadd("R248_close5_after", "F248", "速報5日締め：保留と「境目」の後、予告なしで変わった判定", ["D", "5", "予告なし_合計"], "件")
w248 = pd.read_csv(IN / "F248/results/A_noise_widths.csv", encoding="utf-8-sig")
add("N248_company_month_sales", "F248", "偶然の幅（95%）全社・月・売上（全店）の前年比", w248[w248.id == "K10"]["width_1.96"].iloc[0], "±%", "results/A_noise_widths.csv", "K10/width_1.96")
add("N248_store_month_sales", "F248", "偶然の幅（95%）1店・月・売上の前年比", w248[w248.id == "S_sales"]["width_1.96"].iloc[0], "±%", "results/A_noise_widths.csv", "S_sales/width_1.96")

# ---- F249 ダッシュボード
fl = pd.read_csv(IN / "F249/results/D_noise_flags_20seeds.csv", encoding="utf-8-sig")
def fl_get(kpi, grain, line, col):
    return fl[(fl.KPI == kpi) & (fl["粒度"] == grain) & (fl["線"] == line)][col].iloc[0]
K = "売上の前年比の全社との差"; FIX = "決めた線（売上3pt・廃棄率0.1pt）"; BAND = "偶然の幅（1.96σ）"
add("V249_fixed_false", "F249", "店×月：決めた線（±3pt）で差のない郊外の店に色がつく割合", fl_get(K, "店×月", FIX, "郊外（設定上の差なし）に色がつく割合") * 100, "%", "results/D_noise_flags_20seeds.csv", f"{K}/店×月/{FIX}/郊外")
add("V249_band_false", "F249", "店×月：偶然の幅で差のない郊外の店に色がつく割合", fl_get(K, "店×月", BAND, "郊外（設定上の差なし）に色がつく割合") * 100, "%", "results/D_noise_flags_20seeds.csv", f"{K}/店×月/{BAND}/郊外")
add("V249_band_month_hit", "F249", "店×月：偶然の幅で地方の店（差あり）に正しい色がつく割合", fl_get(K, "店×月", BAND, "地方（設定上の差あり）に正しい向きの色がつく割合") * 100, "%", "results/D_noise_flags_20seeds.csv", f"{K}/店×月/{BAND}/地方")
add("V249_band_12m_hit", "F249", "店×12か月：偶然の幅で地方の店（差あり）に正しい色がつく割合", fl_get(K, "店×12か月", BAND, "地方（設定上の差あり）に正しい向きの色がつく割合") * 100, "%", "results/D_noise_flags_20seeds.csv", f"{K}/店×12か月/{BAND}/地方")
bd = pd.read_csv(IN / "F249/results/E_bands_company_area.csv", encoding="utf-8-sig")
add("N249_company_month_sales", "F249", "偶然の幅（95%）全社・月・売上の前年比", bd[(bd.level == "全社") & (bd.grain == "月") & (bd.KPI == "売上")].band.iloc[0], "±%", "results/E_bands_company_area.csv", "全社/月/売上")
add("N249_store_month_sales", "F249", "偶然の幅（95%）店×月・売上の全社との差", fl_get(K, "店×月", BAND, "偶然の幅") * 100, "±%", "results/D_noise_flags_20seeds.csv", f"{K}/店×月/偶然の幅")

# ---- F250 売上が落ちた月
jadd("E250_sales_yoy", "F250", "2026年3月 既存店売上の前年比", ["target_values", "sales_yoy"], "%", scale=100)
jadd("E250_calendar", "F250", "2026年3月 暦（曜日の並び）の寄与", ["target_values", "c_calendar"], "pt", scale=100)
jadd("E250_receipts_adj", "F250", "2026年3月 暦を除いた客数の寄与", ["target_values", "c_receipts_adj"], "pt", scale=100)
jadd("E250_chance_items", "F250", "31項目のうち偶然だけで幅の外に出る数（平均）", ["robustness", "chance_beyond_band_per_seed", "mean"], "項目")
jadd("N250_company_month_sales90", "F250", "偶然の幅（90%）全社・2026年3月・売上の前年比", ["target_band90_half", "sales_yoy"], "±%", scale=100)
jadd("N250_store_month_sales90", "F250", "偶然の幅（90%）1店・月・売上の前年比（店の中央値）", ["store_band90_half_median"], "±%", scale=100)

# ---- F251 販促の効果
for m, nm in [("M2_前年比", "前年比"), ("M3_前年比の差", "前年比の差"), ("M4_DiD", "差の差"), ("M6_合成対照", "合成対照")]:
    jadd(f"P251_bias_{nm}", "F251", f"販促：{nm}の偏り（弱い店を選んだとき、20通りの平均）", ["error_summary", f"weak_eff|{m}", "bias"], "pt", scale=100)
    jadd(f"P251_neg_{nm}", "F251", f"販促：{nm}で黒字の販促が赤字に見えた数（20通り中）", ["money_error", m, "net_neg"], "通り")
    jadd(f"P251_rbias_{nm}", "F251", f"販促：{nm}の偏り（店を無作為に選んだとき）", ["error_summary", f"random_eff|{m}", "bias"], "pt", scale=100)
jadd("P251_truth_net", "F251", "販促：答えの差し引き", ["truth", "net"], "円")

# ---- F252 予算
cov = J("F252")["C_coverage"]
def cov_get(method, model):
    return [r for r in cov if r["method"] == method and r["model"] == model][0]["covered"]
for nid, me, mo, lab in [("F252_cov_ets", "①モデルの区間", "ETS", "ETS の80%区間"), ("F252_cov_sarima", "①モデルの区間", "SARIMA", "SARIMA の80%区間"),
                         ("F252_cov_borrow", "③業界の外れ＋自社の揺れ", "季節ナイーブ＋伸び", "業界の外れ＋自社の揺れの80%幅")]:
    add(nid, "F252", f"予算：{lab}に実際が入った割合（自社の過去260回）", cov_get(me, mo), "%", "results/main.json", f"C_coverage/{me}/{mo}")
jadd("F252_check_diff", "F252", "予算の答え合わせ：2026年4〜8月の売上累計の予算との差", ["E_check", "cum5_diff_pct"], "%")
add("F252_check_lo", "F252", "予算の答え合わせ：見直しの線（下）", J("F252")["E_check"]["range5_pct"][0], "%", "results/main.json", "E_check/range5_pct/0")
add("F252_check_hi", "F252", "予算の答え合わせ：見直しの線（上）", J("F252")["E_check"]["range5_pct"][1], "%", "results/main.json", "E_check/range5_pct/1")
jadd("F252_ind_before", "F252", "業界（スーパー）の前年比：2026年3月までの12か月", ["E_check", "industry_yoy_12m_to_2026-03"], "%")
jadd("F252_ind_after", "F252", "業界（スーパー）の前年比：2026年4〜8月", ["E_check", "industry_yoy_apr_aug_2026"], "%")
jadd("F252_op_diff", "F252", "予算の答え合わせ：営業利益（4〜8月）の予算との差", ["E_check", "op5_diff_pct"], "%")
for mo in ["季節ナイーブ", "ETS", "SARIMA"]:
    jadd(f"F252_check_{mo}", "F252", f"予算の答え合わせ：{mo}で作っていた場合の差", ["E_check", "by_model_diff_pct", mo], "%")

# ---- F253 データの品質
S = "results/summary.json"
jadd("Q253_detect", "F253", "品質チェック8つで見つけた汚れの割合（4,800個）", ["detect_overall"], "%", rel=S, scale=100)
jadd("Q253_fixed", "F253", "決めた範囲だけのチェックで見つけた割合", ["fixed_range_overall"], "%", rel=S, scale=100)
jadd("Q253_clean_fa", "F253", "汚れのない月の誤報（1か月あたり店×日）", ["clean_store_days_per_month"], "件", rel=S)
jadd("Q253_partial", "F253", "見つけにくかった汚れ：途中までしか入らない", ["detect_by_type", "欠測：途中までしか入らない"], "%", rel=S, scale=100)
jadd("Q253_x13", "F253", "売上・客数・点数がそろって1.3倍になる汚れを見つけた割合", ["detect_x13_T15_abc"], "%", rel=S, scale=100)
jadd("Q253_fa_a_only", "F253", "参照を前の8週だけにしたときの誤報（売上・客数・点数、1か月）", ["pos3_fa_T15", "a"], "件", rel=S)

df = pd.DataFrame(rows)
assert df.id.is_unique
df.to_csv(OUT / "numbers.csv", index=False, encoding="utf-8")
print("数字", len(df))
