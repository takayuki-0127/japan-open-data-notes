"""05 図：figures/fig1〜fig6 と、見本の月（2025年12月）の PDF。
fig2 は reports/report_202512_v1.html をブラウザ（Playwright の Chromium）で画像にしたもの。
会社・数字はすべて架空（合成データ）。
"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG, REP = ROOT / "results", ROOT / "figures", ROOT / "reports"
FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False})
BLUE, RED, GREY, DARK, ORANGE, GREEN = "#2a6fb0", "#c0504d", "#b8b8b8", "#444444", "#d98200", "#2a7d3f"
NOTE = "サンプルマート（架空）・合成データ"
MONTHS = list(pd.period_range("2025-04", "2026-03", freq="M").strftime("%Y-%m"))
ML = [f"{int(m[5:])}月" for m in MONTHS]


def foot(fig, extra=""):
    fig.text(0.01, 0.005, NOTE + ("｜" + extra if extra else ""), fontsize=8, color="#777")


# ---------------------------------------------------------------- fig1 型
def fig1():
    fig, ax = plt.subplots(figsize=(11.5, 7.2)); ax.set_xlim(0, 11); ax.set_ylim(-0.3, 6.6); ax.axis("off")
    blocks = [("1. 今月のまとめ", "3行まで。①営業利益の計画比・前年比 ②流れが変わった KPI ③店の例外", "幅の中の動きの理由、経緯の説明"),
              ("2. KPI 表", "毎月同じ11行。今月・前年比・計画比・先月までの3か月・偶然の幅・判定", "行の入れ替え、その月だけの指標"),
              ("3. 要因", "売上を客数×点数×単価に、営業利益の計画との差を4つに分ける。説明は「流れが変わった」KPI だけ、KPI ツリーの下で1回", "市場と同じ動き、上の KPI の重ねての説明"),
              ("4. 例外（店）", "真ん中の店と比べ、今月 3σ 超えか、3か月続けて 1σ 超え。同じ地域3店以上は1行。5行まで", "店の営業利益（幅 ±205%）、売上の上下5店の順位"),
              ("5. 次のアクション", "例外ごとに担当（役割）と期限。前月のアクションが続いているか", "担当のない「様子を見る」"),
              ("6. 載せなかったもの\n　 ・改訂履歴", "幅の中の KPI の名前、v1 速報 → v2 確定 の差と、出し直したかどうか", "")]
    ax.text(0.2, 6.35, "月次レポートの「型」：毎月同じ順番・同じ行、載せるものは決まりで選ぶ", fontsize=13.5, weight="bold")
    ax.text(0.2, 6.02, "載せるもの", fontsize=10, color=BLUE, weight="bold"); ax.text(7.35, 6.02, "載せないもの", fontsize=10, color=RED, weight="bold")
    for i, (h, inc, exc) in enumerate(blocks):
        y = 5.15 - i * 0.98
        ax.add_patch(FancyBboxPatch((0.2, y), 2.35, 0.7, boxstyle="round,pad=0.02", fc="#eef3f9", ec=BLUE, lw=1))
        ax.text(0.32, y + 0.33, h, va="center", fontsize=10.5, weight="bold")
        import textwrap
        ax.text(2.7, y + 0.33, "\n".join(textwrap.wrap(inc, 29)), va="center", fontsize=9.2, linespacing=1.35)
        if exc:
            ax.text(7.35, y + 0.33, "\n".join(textwrap.wrap("× " + exc, 20)), va="center", fontsize=9.2, color="#8a2f2d", linespacing=1.35)
    ax.plot([7.2, 7.2], [0.2, 6.0], color="#ddd", lw=1)
    ax.text(0.2, -0.25, "作り方：mart（F247）→ Python で KPI・判定・例外を計算 → 同じテンプレートに流し込み → HTML・PDF・Markdown・JSON を毎月出す\n版：v1 速報は翌月6日（5日までに届いた POS）、v2 確定は20日。判定が変わったときだけ出し直す",
            fontsize=9, color=DARK)
    foot(fig); fig.savefig(FIG / "fig1_template.png", dpi=150, bbox_inches="tight"); plt.close(fig)


# ---------------------------------------------------------------- fig2 見本（HTML → PNG・PDF）
def fig2():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 960, "height": 900}, device_scale_factor=1.6)
        pg.goto((REP / "report_202512_v1.html").as_uri()); pg.screenshot(path=str(FIG / "fig2_sample_report.png"), full_page=True)
        pg.pdf(path=str(REP / "report_202512_v1.pdf"), format="A4", print_background=True, scale=0.8)
        pg.goto((REP / "report_202512_v2.html").as_uri()); pg.pdf(path=str(REP / "report_202512_v2.pdf"), format="A4", print_background=True, scale=0.8)
        b.close()


# ---------------------------------------------------------------- fig3 店の例外の決まり
def fig3():
    d = json.loads((REP / "report_202512.json").read_text(encoding="utf-8"))["v2"]
    W = pd.read_csv(RES / "A_noise_widths.csv").set_index("id")
    import importlib.util
    s = importlib.util.spec_from_file_location("rep", ROOT / "src" / "03_レポート.py"); M = importlib.util.module_from_spec(s); s.loader.exec_module(M)
    I = M.load_inputs(); dev, _, _ = M.store_dev(I["final"], I["final"], "2025-12")
    fig, ax = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1.15, 1]})
    ks = [k for k, _, _ in M.SKPIS]
    devs = {M._ym("2025-12", -i): M.store_dev(I["final"], I["final"], M._ym("2025-12", -i))[0] for i in range(13)}
    flagged = {(it["store_id"], it["kpi"]) for it in M.store_exceptions(devs, "2025-12", dict(W.sigma), I["st"])}
    rng = np.random.default_rng(0)
    for i, k in enumerate(ks):
        z = dev[k] / W.loc[k, "sigma"]
        for sid, v in z.items():
            hit = (sid, k) in flagged
            ax[0].scatter(i + rng.uniform(-0.18, 0.18), v, s=34 if hit else 18, color=RED if hit else GREY, zorder=3 if hit else 2, edgecolor="white", lw=0.4)
    ax[0].axhspan(-1, 1, color="#f2f2f2", zorder=0); ax[0].axhline(3, color=RED, lw=0.8, ls="--"); ax[0].axhline(-3, color=RED, lw=0.8, ls="--")
    ax[0].text(4.45, 3.15, "3σ", color=RED, fontsize=9); ax[0].text(4.45, 1.1, "1σ", color="#888", fontsize=9)
    ax[0].set_xticks(range(len(ks))); ax[0].set_xticklabels([M.SNAME[k] for k in ks], fontsize=9.5)
    ax[0].set_ylabel("真ん中の店との差（σ の何倍か）")
    ax[0].set_title("2025年12月：21店 × 5つの KPI。赤が例外の決まりを満たしたもの", fontsize=11, loc="left")
    B = pd.read_csv(RES / "B_store_rule_summary.csv")
    y = np.arange(len(B))[::-1]
    ax[1].barh(y, B["本当に差がある割合"] * 100, color=[GREY, GREY, GREY, BLUE, RED], height=0.6)
    for yy, (_, r) in zip(y, B.iterrows()):
        ax[1].text(r["本当に差がある割合"] * 100 + 1.5, yy, "%.0f%%（1か月 %.1f 件）" % (r["本当に差がある割合"] * 100, r["行数_平均"]), va="center", fontsize=9.5)
    ax[1].set_yticks(y); ax[1].set_yticklabels(B["決まり"], fontsize=9.5); ax[1].set_xlim(0, 125); ax[1].set_xlabel("載った件のうち、本当に差がある店×KPI の割合（%）")
    ax[1].set_title("決まりごとの当たりの割合（乱数の種20通りの平均）", fontsize=11, loc="left")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); foot(fig, "件数は地域でまとめる前の店×KPI の数"); fig.savefig(FIG / "fig3_store_rule.png", dpi=150); plt.close(fig)


# ---------------------------------------------------------------- fig4 全社の KPI：流れが変わったもの
def fig4():
    KP = ["K00", "K10", "K01", "K02", "K03", "K04", "K05", "K06", "K07", "K08", "K09"]
    names = {"K00": "営業利益（全店）", "K10": "売上（全店）", "K01": "既存店売上", "K02": "客数", "K03": "買上点数", "K04": "一品単価",
             "K05": "来店頻度", "K06": "粗利率（廃棄後）", "K07": "廃棄率", "K08": "人時粗利", "K09": "人件費率"}
    G = np.zeros((len(KP), 12))
    for j, m in enumerate(MONTHS):
        J = json.loads((REP / f"report_{m.replace('-', '')}.json").read_text(encoding="utf-8"))["v2"]["J"]
        for i, k in enumerate(KP):
            G[i, j] = 0 if J[k]["flag"] == 0 else (1 if J[k]["explained_by"] else 2)
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 5.2), gridspec_kw={"width_ratios": [1.35, 1]})
    from matplotlib.colors import ListedColormap
    ax[0].imshow(G, cmap=ListedColormap(["#f3f3f3", "#f2c9a8", RED]), aspect="auto", vmin=0, vmax=2)
    ax[0].set_xticks(range(12)); ax[0].set_xticklabels(ML, fontsize=9); ax[0].set_yticks(range(len(KP))); ax[0].set_yticklabels([names[k] for k in KP], fontsize=9.5)
    ax[0].set_xticks(np.arange(-.5, 12, 1), minor=True); ax[0].set_yticks(np.arange(-.5, len(KP), 1), minor=True)
    ax[0].grid(which="minor", color="white", lw=1.5); ax[0].tick_params(which="minor", length=0)
    for sp in ax[0].spines.values():
        sp.set_visible(False)
    ax[0].set_title("FY2025 の月次レポート（確定版）：濃い赤＝説明する、薄い＝下の KPI で説明できる", fontsize=10.5, loc="left")
    C = pd.read_csv(RES / "C_company_judgment_summary.csv")
    x = np.arange(len(C))
    ax[1].bar(x - 0.18, C["流れが変わった"], 0.36, color=GREY, label="流れが変わった KPI")
    ax[1].bar(x + 0.18, C["説明すること（ツリーでまとめた後）"], 0.36, color=RED, label="説明すること（ツリーでまとめた後）")
    for xx, a, b in zip(x, C["流れが変わった"], C["説明すること（ツリーでまとめた後）"]):
        ax[1].text(xx - 0.18, a + 0.05, "%.1f" % a, ha="center", fontsize=9); ax[1].text(xx + 0.18, b + 0.05, "%.1f" % b, ha="center", fontsize=9)
    ax[1].set_xticks(x); ax[1].set_xticklabels(["前年比\nそのまま", "曜日補正", "市場との差\n（採用）"], fontsize=9.5)
    ax[1].set_ylabel("1か月あたりの数（11行のうち）"); ax[1].legend(frameon=False, fontsize=9, loc="upper right")
    ax[1].set_title("判定のしかたと、毎月説明する数（種20通りの平均）", fontsize=10.5, loc="left"); ax[1].set_ylim(0, 4.3)
    fig.tight_layout(rect=(0, 0.03, 1, 1)); foot(fig, "市場＝経済産業省「商業動態統計」スーパー販売額の前年比"); fig.savefig(FIG / "fig4_company_judgment.png", dpi=150); plt.close(fig)


# ---------------------------------------------------------------- fig5 版：速報と確定
def fig5():
    B = pd.read_csv(RES / "B_reports_fy2025.csv")
    mk = pd.read_csv(ROOT / "data" / "in" / "market_super_monthly.csv").set_index("ym")["前年比_%"]
    D = pd.read_csv(RES / "D_close_day_summary.csv")
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw={"width_ratios": [1.3, 1]})
    x = np.arange(12)
    ax[0].plot(x, B.existing_yoy, color=DARK, marker="o", label="v2 確定")
    ax[0].plot(x, B.existing_yoy_v1, color=ORANGE, marker="o", ls="--", label="v1 速報（翌月5日の締め）")
    ax[0].plot(x, mk.reindex(MONTHS).values, color=BLUE, lw=1, alpha=0.7, label="市場（スーパー販売額）")
    ax[0].set_xticks(x); ax[0].set_xticklabels(ML, fontsize=9); ax[0].set_ylabel("前年比（%）"); ax[0].axhline(0, color="#aaa", lw=0.7)
    ax[0].legend(frameon=False, fontsize=9); ax[0].set_title("既存店売上の前年比：速報は低めに出て、確定で上に直る", fontsize=10.5, loc="left")
    xx = np.arange(len(D))
    ax[1].bar(xx - 0.27, D["予告がない場合_合計"], 0.27, color=GREY, label="予告がないと「変わった」に見える判定")
    ax[1].bar(xx, D["境目と予告_合計"], 0.27, color=ORANGE, label="速報で「境目」と予告した判定")
    ax[1].bar(xx + 0.27, D["予告なし_合計"], 0.27, color=RED, label="予告なしに変わった判定")
    for i, r in D.iterrows():
        ax[1].text(i - 0.27, r["予告がない場合_合計"] + 0.4, int(r["予告がない場合_合計"]), ha="center", fontsize=9)
        ax[1].text(i + 0.27, r["予告なし_合計"] + 0.4, int(r["予告なし_合計"]), ha="center", fontsize=9, color=RED)
    ax[1].set_xticks(xx); ax[1].set_xticklabels([f"翌月{int(c)}日" for c in D["締めの日"]], fontsize=9.5); ax[1].set_ylabel("FY2025 の12か月の合計")
    ax[1].legend(frameon=False, fontsize=8.6, loc="upper right"); ax[1].set_title("締めの日と、速報→確定で判定が変わる数", fontsize=10.5, loc="left")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); foot(fig, "保留＝届いた割合 99.5% 未満の店は速報で判定しない"); fig.savefig(FIG / "fig5_versions.png", dpi=150); plt.close(fig)


# ---------------------------------------------------------------- fig6 12か月の一覧
def fig6():
    B = pd.read_csv(RES / "B_reports_fy2025.csv")
    rows = []
    for m in MONTHS:
        d = json.loads((REP / f"report_{m.replace('-', '')}.json").read_text(encoding="utf-8"))
        v1, v2 = d["v1"], d["v2"]
        roots = [k for k, j in v2["J"].items() if j["flag"] != 0 and not j["explained_by"]]
        rows.append({"op_plan": v2["PJ"]["K00"]["gap"], "flag": v2["PJ"]["K00"]["flag"], "roots": len(roots), "ex": len(v2["exceptions"]),
                     "held": len(v1["held"]), "unsure": len(v1["unsure"]), "naive": len(d["changes_naive"]), "reissue": d["reissue"]})
    R = pd.DataFrame(rows)
    fig, ax = plt.subplots(2, 1, figsize=(12, 6.2), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
    x = np.arange(12)
    cols = [RED if f < 0 else BLUE if f > 0 else GREY for f in R.flag]
    ax[0].bar(x, R.op_plan, color=cols); ax[0].axhline(0, color="#999", lw=0.7)
    W = pd.read_csv(RES / "A_noise_widths.csv").set_index("id").loc["K00", "width_1.96"]
    ax[0].axhspan(-W, W, color="#f0f0f0", zorder=0); ax[0].text(11.45, W + 1, "偶然の幅 ±%.0f%%" % W, fontsize=8.5, color="#777", ha="right")
    for xx, v in zip(x, R.op_plan):
        ax[0].text(xx, v + (1.5 if v >= 0 else -1.5), ("%+.0f" % v).replace("-", "−"), ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5)
    ax[0].set_ylim(min(R.op_plan.min() - 9, -20), max(R.op_plan.max() + 7, 20)); ax[0].set_ylabel("営業利益（全店）の計画比（%）"); ax[0].set_title("FY2025 の12か月分を同じ型で自動で作った：計画比（色つき＝幅を超えた月）と、各月のレポートに載ったもの", fontsize=10.5, loc="left")
    w = 0.2
    ax[1].bar(x - 1.5 * w, R.roots, w, color=RED, label="説明した KPI")
    ax[1].bar(x - 0.5 * w, R.ex, w, color=BLUE, label="店の例外（行）")
    ax[1].bar(x + 0.5 * w, R.held, w, color=GREY, label="速報で保留した店")
    ax[1].bar(x + 1.5 * w, R.unsure, w, color=ORANGE, label="速報で境目と予告")
    ax[1].set_xticks(x); ax[1].set_xticklabels(ML); ax[1].set_ylabel("数"); ax[1].legend(frameon=False, ncol=4, fontsize=9, loc="upper left")
    ax[1].set_ylim(0, 8)
    fig.tight_layout(rect=(0, 0.03, 1, 1)); foot(fig, "計画は架空の経営企画が置いた合成の予算"); fig.savefig(FIG / "fig6_twelve_months.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6()
    for f in sorted(FIG.glob("*.png")):
        print(f.name, f.stat().st_size)
