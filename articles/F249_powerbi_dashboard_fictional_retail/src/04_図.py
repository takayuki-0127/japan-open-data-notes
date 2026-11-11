"""04 図：静的な HTML のダッシュボード（Power BI と同じ設計）を作って画面を撮り、レイアウトを確かめ、図1〜6を作る。

- 会社・数字は架空（サンプルマート（架空）、合成データ）。
- dashboard/dashboard.html は1ファイルで動く（外部のライブラリなし）。?p=1〜3 でページを切り替える。
"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True); P = ROOT / "powerbi" / "data"
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8984", "axes.labelcolor": "#2b2b2b", "xtick.color": "#52514e", "ytick.color": "#52514e"})
BLUE, ORANGE, PURPLE, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#5b4fc4", "#a3a29d", "#0b0b0b", "#52514e"
CNT = json.load(open(pathlib.Path(__file__).resolve().parents[1] / "results" / "H_package_counts.json"))
NOTE = "サンプルマート（架空）・合成データ。会社も数字も実在しません。"

E = pd.read_csv(RES / "expected_values.csv", encoding="utf-8-sig").set_index(["範囲", "期間", "メジャー"]).期待値
NZ = pd.read_csv(P / "ref_noise_band.csv", encoding="utf-8-sig")
FM = pd.read_csv(P / "fact_store_month.csv", encoding="utf-8-sig")
ST = pd.read_csv(P / "dim_store.csv", encoding="utf-8-sig")
CAT = pd.read_csv(P / "dim_category.csv", encoding="utf-8-sig")


def band(level, grain, kpi):
    return float(NZ[(NZ.level == level) & (NZ.grain == grain) & (NZ.KPI == kpi)].band_ratio.iloc[0])


def e(scope, per, m):
    return float(E[(scope, per, m)])


def dashboard_data():
    FY, M = "FY2025", "2026-03"
    cards = [  # (名前, メジャー, 単位, 良い向き, 幅のKPI名, 段, 説明)
        ("既存店売上", "既存店売上_前年比_曜日補正", "%", 1, "売上", "売上", f"曜日補正後｜{e('全社', FY, '既存店売上') / 1e8:.1f}億円"),
        ("客数", "既存店客数_前年比", "%", 1, "客数", "売上＝客数×", "レシートの枚数"),
        ("買上点数", "既存店買上点数_前年比", "%", 1, "買上点数", "×点数×", f"1回 {e('全社', FY, '既存店買上点数'):.2f}点"),
        ("一品単価", "既存店一品単価_前年比", "%", 0, "一品単価", "×単価", f"{e('全社', FY, '既存店一品単価'):.0f}円｜物価が中心"),
        ("粗利率（廃棄後）", "既存店粗利率_廃棄後_前年差", "pt", 1, "粗利率（廃棄後）", "粗利", f"{e('全社', FY, '既存店粗利率_廃棄後') * 100:.2f}%"),
        ("廃棄率", "既存店廃棄率_前年差", "pt", -1, "廃棄率", "粗利", f"{e('全社', FY, '既存店廃棄率') * 100:.2f}%｜上がると悪い"),
        ("人時粗利", "既存店人時粗利_前年比", "%", 1, "人時粗利", "人", f"{e('全社', FY, '既存店人時粗利'):,.0f}円／人時"),
    ]
    out = {"asof": "2026年3月（FY2025 の12か月目）・確定値", "band_cm": band("全社", "月", "売上")}
    out["kgi"] = {"fy": e("全社", FY, "既存店営業利益_前年比"), "m": e("全社", M, "既存店営業利益_前年比"),
                  "band_fy": band("全社", "12か月", "営業利益"), "band_m": band("全社", "月", "営業利益"),
                  "lv_fy": e("全社", FY, "既存店営業利益"), "lv_fy0": e("全社", FY, "既存店営業利益_前年")}
    out["cards"] = [{"name": n, "fy": e("全社", FY, k), "m": e("全社", M, k), "unit": u, "good": g,
                     "band_fy": band("全社", "12か月", b), "band_m": band("全社", "月", b), "tier": t, "lv": lv} for n, k, u, g, b, t, lv in cards]
    months = pd.period_range("2024-04", "2026-03", freq="M").strftime("%Y-%m")
    out["trend"] = [{"ym": m, "raw": e("全社", m, "既存店売上_前年比"), "adj": e("全社", m, "既存店売上_前年比_曜日補正")} for m in months]
    out["bridge"] = {"op0": e("全社", FY, "既存店営業利益_前年"), "op1": e("全社", FY, "既存店営業利益"), "sales": e("全社", FY, "橋_売上の伸び"),
                     "margin": e("全社", FY, "橋_廃棄前の粗利率"), "waste": e("全社", FY, "橋_廃棄"), "labor": e("全社", FY, "橋_人件費"), "other": e("全社", FY, "橋_その他経費")}
    ac = [("既存店売上（曜日補正）", "既存店売上_前年比_曜日補正", "%", 1, "売上"), ("客数", "既存店客数_前年比", "%", 1, "客数"),
          ("廃棄率の前年差", "既存店廃棄率_前年差", "pt", -1, "廃棄率"), ("人時粗利", "既存店人時粗利_前年比", "%", 1, "人時粗利"),
          ("営業利益", "既存店営業利益_前年比", "%", 1, "営業利益")]
    out["area_cols"] = [{"name": n, "key": k, "unit": u, "good": g, "band": band("地域", "12か月", b)} for n, k, u, g, b in ac]
    out["areas"] = [{"area": a, **{k: e(a, FY, k) for _, k, *_ in ac}} for a in ("都市", "郊外", "地方")]
    co = e("全社", FY, "既存店売上_前年比_曜日補正")
    fm = FM[(FM.month_start >= "2025-04-01") & (FM.month_start <= "2026-03-01")].groupby("store_id").is_existing.sum()
    stores = []
    for _, r in ST.sort_values(["area_order", "store_id"]).iterrows():
        n = int(fm.get(r.store_id, 0))
        if n == 0:
            continue
        sc = f"店{r.store_id:02d}"
        stores.append({"id": int(r.store_id), "label": f"{r.area}{r.store_id:02d}", "area": r.area, "n": n, "full": n == 12,
                       "dev": e(sc, FY, "既存店売上_前年比_曜日補正") - co, "waste": e(sc, FY, "既存店廃棄率_前年差"), "lhgp": e(sc, FY, "既存店人時粗利_前年比")})
    out["stores"] = stores
    out["band_store"] = {"sales": band("1店", "12か月", "売上"), "waste": band("1店", "12か月", "廃棄率"), "lhgp": band("1店", "12か月", "人時粗利"),
                         "op": band("1店", "12か月", "営業利益")}
    out["band_store_m"] = {"waste": band("1店", "月", "廃棄率")}
    full = [s for s in stores if s["full"]]
    fid = max(full, key=lambda s: s["waste"])["id"]; sc = f"店{fid:02d}"
    tree = [("既存店売上（曜日補正）", "既存店売上_前年比_曜日補正", "%", 1, "売上"), ("客数", "既存店客数_前年比", "%", 1, "客数"),
            ("買上点数", "既存店買上点数_前年比", "%", 1, "買上点数"), ("一品単価", "既存店一品単価_前年比", "%", 0, "一品単価"),
            ("粗利率（廃棄後）", "既存店粗利率_廃棄後_前年差", "pt", 1, "粗利率（廃棄後）"), ("廃棄率", "既存店廃棄率_前年差", "pt", -1, "廃棄率"),
            ("人時粗利", "既存店人時粗利_前年比", "%", 1, "人時粗利"), ("営業利益（参考）", "既存店営業利益_前年比", "%", 1, None)]
    st_row = ST.set_index("store_id").loc[fid]
    rural = [s["waste"] for s in full if s["area"] == "地方"]
    opv = e(sc, FY, "既存店営業利益_前年比")
    out["focus"] = {"id": fid, "label": f"{st_row.store_name}",
                    "trend": [{"ym": m, "waste": e(sc, m, "既存店廃棄率_前年差")} for m in months],
                    "tree": [{"name": n, "v": e(sc, FY, k), "co": e("全社", FY, k), "unit": u, "good": g,
                              "band": None if b is None else band("1店", "12か月", b)} for n, k, u, g, b in tree],
                    "note": (f"廃棄率の前年差 {e(sc, FY, '既存店廃棄率_前年差') * 100:+.2f}pt は幅（±{band('1店', '12か月', '廃棄率') * 100:.2f}pt）の外。"
                             f"地方の店は12か月そろった{len(rural)}店すべてが +{min(rural) * 100:.2f}〜+{max(rural) * 100:.2f}pt で、店だけの問題ではなさそう（推測）。"
                             f"営業利益の前年比 {opv * 100:+.0f}% は前年の利益が小さいためで、店の評価には人時粗利と廃棄率を使う（F246 の決めごと）。")}
    cats = []
    for cid, nm in CAT.set_index("category_id").category.items():
        if nm == "日用品":
            pass
        cats.append({"name": nm, "waste0": e(f"部門{cid}", "FY2024", "部門_既存店廃棄率"), "waste1": e(f"部門{cid}", "FY2025", "部門_既存店廃棄率"),
                     "gpm0": e(f"部門{cid}", "FY2024", "部門_既存店粗利率_廃棄後"), "gpm1": e(f"部門{cid}", "FY2025", "部門_既存店粗利率_廃棄後")})
    out["cats"] = cats
    return out


def build_html(data):
    t = (ROOT / "src" / "dashboard_template.html").read_text(encoding="utf-8")
    html = t.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    (ROOT / "dashboard" / "dashboard.html").write_text(html, encoding="utf-8")
    return ROOT / "dashboard" / "dashboard.html"


LAYOUT_JS = """() => {
  const vw = window.innerWidth, vh = window.innerHeight, pg = document.querySelector('.page.on');
  const r = el => el.getBoundingClientRect();
  const inView = el => { const b = r(el); return b.top >= -1 && b.left >= -1 && b.bottom <= vh + 1 && b.right <= vw + 1; };
  const kgi = pg.querySelector('[data-test=kgi]'), kpis = [...pg.querySelectorAll('[data-test=kpi]')];
  let over = 0, minFont = 99;
  for (const e of pg.querySelectorAll('h1,h3,.v,.lv,.chip,.band,.mon,td,th,.note,text')) {
    if (!e.getClientRects().length) continue;
    if (e.tagName !== 'text' && e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflow !== 'visible') over++;
    const fs = parseFloat(getComputedStyle(e).fontSize); const sc = e.tagName === 'text' ? (r(e.ownerSVGElement).width / e.ownerSVGElement.viewBox.baseVal.width) : 1;
    const t = (document.querySelector('.canvas').style.transform.match(/scale\\(([^)]+)\\)/) || [0, 1])[1];
    minFont = Math.min(minFont, fs * sc * (e.tagName === 'text' ? 1 : +t));
  }
  // 箱からはみ出す文字（カードの右端を越える子）
  let clip = 0;
  for (const c of pg.querySelectorAll('.card')) { const cb = r(c); for (const k of c.children) { if (r(k).right > cb.right + 1) clip++; } }
  const colored = pg.querySelectorAll('.chip.good,.chip.bad,.chip.neu,td.good,td.bad,td.neu').length;
  return {vw, vh, hscroll: document.documentElement.scrollWidth > vw + 1,
          kgi_in_first_view: kgi ? inView(kgi) : null, kpi_in_first_view: kpis.filter(inView).length, kpi_total: kpis.length,
          kgi_top_left: kgi ? (r(kgi).left < vw * 0.3 && r(kgi).top < vh * 0.35) : null,
          text_overflow: over, clipped_children: clip, min_font_px: Math.round(minFont * 10) / 10, colored_marks: colored,
          page_height: document.documentElement.scrollHeight};
}"""


def screenshots_and_layout(path):
    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for pnum, out in [(1, FIG / "fig2_dashboard_exec.png"), (2, FIG / "fig4_dashboard_store_drill.png"), (3, RES / "screenshot_p3_category.png")]:
            pg = b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
            pg.goto(path.as_uri() + f"?p={pnum}"); pg.wait_for_timeout(300); pg.screenshot(path=str(out)); pg.close()
        for name, vp in [("Power BI の画面 1280×720", (1280, 720)), ("ノートPC 1366×768", (1366, 768)), ("大きい画面 1920×1080", (1920, 1080)),
                         ("小さいノート 1024×640", (1024, 640)), ("スマートフォン 390×844", (390, 844))]:
            for pnum in (1, 2, 3):
                pg = b.new_page(viewport={"width": vp[0], "height": vp[1]}, device_scale_factor=1)
                pg.goto(path.as_uri() + f"?p={pnum}"); pg.wait_for_timeout(200)
                r = pg.evaluate(LAYOUT_JS); r.update({"画面": name, "ページ": pnum}); rows.append(r)
                if name.startswith("スマート") and pnum == 1:
                    pg.screenshot(path=str(RES / "screenshot_p1_phone.png"), full_page=True)
                pg.close()
        b.close()
    df = pd.DataFrame(rows); df.to_csv(RES / "F_layout_checks.csv", index=False, encoding="utf-8-sig")
    return df


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)


def box(ax, x, y, w, h, title, body, fc="#eef4fc", ec=BLUE, ts=11, bs=8.8, gap=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h - 0.16, title, ha="center", va="top", fontsize=ts, weight="bold", color=INK)
    gap = gap or (0.52 if "\n" not in title else 0.85)
    ax.text(x + w / 2, y + h - gap, body, ha="center", va="top", fontsize=bs, color=MUTED, linespacing=1.5)


def fig1():
    fig, ax = plt.subplots(figsize=(13, 6.6)); ax.set_xlim(0, 13); ax.set_ylim(0, 6.9); ax.axis("off")
    ax.text(0.1, 6.75, "誰が見て、何を決めるか → ページ・KPI・粒度・色の決め方", fontsize=13.5, weight="bold", va="top")
    cols = [("① 経営", "社長・経営企画／月1回の会議", "決めること：予算の見直し、\n力を入れる地域、値上げ・人の配置の方針",
             "KGI：営業利益（既存店）\nKPI ツリーの7つ：客数・点数・単価\n粗利率・廃棄率・人時粗利 ほか", "全社・月と12か月", "全社の偶然の幅\n（月 売上 ±1.3%、12か月 ±0.4%）"),
            ("② 地域・店", "地域の責任者・店長／月1回＋週", "決めること：どの店に行くか、\n発注・値引き・シフトの見直し",
             "全社との差（売上）、廃棄率、人時粗利\n店の営業利益は並べない\n（1店・12か月でも幅 ±29%）", "店・12か月が主、\n月は推移だけ", "1店・12か月の幅\n（売上 ±2.0%、廃棄率 ±0.05pt）"),
            ("③ 部門", "商品部・部門担当／月1回", "決めること：値入れ、発注の量、\n値引きの時間",
             "部門の廃棄率・粗利率（廃棄後）\n前年との並び", "部門・12か月", "まだ測っていない\n→ 色は向きだけ")]
    rows = ["見る人／頻度", "決めること", "並べる KPI", "粒度", "色の判定"]
    for i, (t, who, dec, kpi, gr, col) in enumerate(cols):
        x = 2.1 + i * 3.6
        ax.add_patch(FancyBboxPatch((x, 5.65), 3.35, 0.62, boxstyle="round,pad=0.02,rounding_size=0.08", fc=[INK, "#2b2b2b", "#52514e"][i], ec="none"))
        ax.text(x + 1.675, 5.96, t, ha="center", va="center", color="white", fontsize=12.5, weight="bold")
        for j, txt in enumerate([who, dec, kpi, gr, col]):
            y = 5.3 - j * 1.02
            ax.add_patch(FancyBboxPatch((x, y - 0.82), 3.35, 0.86, boxstyle="round,pad=0.02,rounding_size=0.06",
                                        fc=["#f6f6f4", "#eef4fc", "#f6f6f4", "#f6f6f4", "#fff4ec"][j], ec="none"))
            ax.text(x + 1.675, y - 0.39, txt, ha="center", va="center", fontsize=8.9, color=INK if j in (1, 4) else MUTED, linespacing=1.4)
    for j, r in enumerate(rows):
        ax.text(1.95, 5.3 - j * 1.02 - 0.39, r, ha="right", va="center", fontsize=10, weight="bold", color=MUTED)
    ax.text(0.1, 0.05, "①の地域の表から②へ、②の廃棄から③へドリルスルー。3秒の決めごと：左上に KGI、その右に KPI ツリーの順でカード。色は「偶然の幅の外」だけにつける（良い＝青、悪い＝橙、物価＝紫、幅の内＝灰）。\n" + NOTE,
            fontsize=8.8, color=MUTED, va="bottom")
    save(fig, "fig1_design.png")


def fig3():
    d = pd.read_csv(RES / "D_noise_flags_20seeds.csv", encoding="utf-8-sig")
    grains = ["店×日", "店×週", "店×月", "地域×月", "店×12か月"]
    fig, axs = plt.subplots(2, 2, figsize=(12.5, 7.2), sharey=True)
    for i, kpi in enumerate(["売上の前年比の全社との差", "廃棄率の前年差"]):
        for j, line in enumerate(["決めた線（売上3pt・廃棄率0.1pt）", "偶然の幅（1.96σ）"]):
            ax = axs[i, j]; x = np.arange(len(grains))
            q = d[(d.KPI == kpi) & (d.線 == line)].set_index("粒度").reindex(grains)
            fa = q["郊外（設定上の差なし）に色がつく割合"] * 100; hit = q["地方（設定上の差あり）に正しい向きの色がつく割合"] * 100
            ax.bar(x - 0.19, fa, 0.36, color=ORANGE, label="誤報：差のない郊外の店に色がつく割合")
            ax.bar(x + 0.19, hit, 0.36, color=BLUE, label="検出：差のある地方の店に正しい向きの色がつく割合")
            for k in range(len(grains)):
                ax.text(x[k] - 0.19, fa.iloc[k] + 1.5, f"{fa.iloc[k]:.0f}", ha="center", fontsize=8.8, color=ORANGE)
                ax.text(x[k] + 0.19, hit.iloc[k] + 1.5, f"{hit.iloc[k]:.0f}", ha="center", fontsize=8.8, color=BLUE)
            ax.set_xticks(x); ax.set_xticklabels(grains); ax.set_ylim(0, 112); ax.axhline(5, color=GRAY, lw=0.8, ls=":")
            if j == 0:
                ax.set_ylabel("%（20通りの平均）")
            bandtxt = "" if j == 0 else "　幅：" + "・".join(f"{g} {v * 100:.{2 if i else 1}f}" for g, v in zip(grains, q.偶然の幅))
            ax.set_title(f"{'売上（全社との差）' if i == 0 else '廃棄率（前年差）'} × {'決めた線 ' + ('3pt' if i == 0 else '0.1pt') if j == 0 else '偶然の幅（±1.96σ）'}"
                         + ("\n" + bandtxt.strip("　") + ("pt" if True else "") if j == 1 else "\n "), loc="left", fontsize=10.5, weight="bold")
    axs[0, 0].legend(loc="upper right", fontsize=8.6, frameon=False)
    fig.text(0.01, -0.02, "設定で分かっている差：地方の店は客数が年 −2.5%（売上は全社より下）、FY2025 に廃棄が1.25倍（廃棄率は上）。郊外の店は全社との差がほぼない。"
             "FY2025 の既存店。点線は5%。\n" + NOTE, fontsize=8.6, color=MUTED, va="top")
    fig.tight_layout(); save(fig, "fig3_noise_flags.png")


def fig5():
    fig, ax = plt.subplots(figsize=(13, 6.8)); ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")
    ax.text(0.1, 6.85, "Power BI に渡すもの（powerbi/）― .pbix は自動では作っていない", fontsize=13.5, weight="bold", va="top")
    gray, blue, orange = ("#f6f6f4", GRAY), ("#eef4fc", BLUE), ("#fff4ec", ORANGE)
    box(ax, 0.2, 4.55, 2.5, 1.8, "dim_date", "1,461 日\nym・month_start・fy\n曜日・祝日・チラシ\nday_weight（曜日の重み）", *blue)
    box(ax, 0.2, 2.4, 2.5, 1.8, "dim_store", "24 店（架空）\narea（都市・郊外・地方）\nsize・開店日・閉店日\n→ RLS をかける表", *blue)
    box(ax, 0.2, 0.55, 2.5, 1.5, "dim_category", "7 部門", *blue)
    box(ax, 3.5, 4.75, 2.9, 1.6, "fact_store_day", "店×日 32,325 行\n売上・客数・点数・粗利\n廃棄・人時・人件費", *gray)
    box(ax, 3.5, 2.85, 2.9, 1.6, "fact_store_month", "店×月 1,062 行\nその他の経費・既存店の印\n（month_start で日付に）", *gray)
    box(ax, 3.5, 0.55, 2.9, 2.0, "fact_store_day_category\nfact_member_month", "店×日×部門 226,275 行\n店×月の会員 1,062 行", *gray)
    for y in (5.5, 3.6, 1.5):
        ax.annotate("", xy=(3.45, y), xytext=(2.75, y), arrowprops=dict(arrowstyle="-", color=MUTED, lw=1.2))
    ax.text(3.1, 0.25, "線＝1対多（次元→事実の一方向）", fontsize=8.5, color=MUTED, ha="center")
    box(ax, 7.0, 3.55, 2.8, 2.8, f"measures.dax（{CNT['measures']}本）", "基本の合計\n既存店（当月・前年同月の同じ店）\n前年比・前年差・曜日補正\n営業利益の分け方（橋）\n偶然の幅・色（条件付き書式）\n364日前の日次", *orange)
    box(ax, 7.0, 0.55, 2.8, 2.65, "ref_noise_band\nsec_user_area", "偶然の幅の表（F246＋この回）\n1店・全社・地域 × 日・週・月・12か月\n\nRLS：地域の責任者\n（架空のメール → 地域）", *orange)
    box(ax, 10.3, 4.1, 2.5, 2.25, "そのほかのファイル", "powerquery.m（読み込み）\ntheme.json（色・文字）\nlayout_spec.md（3ページの配置）\nrls.md（役割の定義）\nbuild_steps.md（手順）", *gray)
    box(ax, 10.3, 0.55, 2.5, 3.2, "確かめる表", f"expected_values.csv\n（{CNT['expected_rows']:,} 行：範囲×期間×メジャー）\n\nPower BI で組み立てたあと\nカードの値がこの表と\n同じになるかを見る", fc="#f2f8f2", ec="#1baf7a")
    ax.text(0.2, -0.15, NOTE + " RLS のメールアドレスは example.com の架空のもの。", fontsize=8.6, color=MUTED)
    save(fig, "fig5_powerbi_package.png")


def fig6(lay, nmeas):
    cmp_ = pd.read_csv(RES / "B_check_sql_vs_pandas.csv", encoding="utf-8-sig")
    bf = pd.read_csv(RES / "C_band_flags_fy2025.csv", encoding="utf-8-sig")
    fig, axs = plt.subplots(1, 3, figsize=(14.5, 4.9), gridspec_kw={"width_ratios": [1.05, 1.35, 1]})
    ax = axs[0]
    q = cmp_[cmp_.メジャー == "既存店売上_前年比_曜日補正"]
    for sc, c in zip(["全社", "都市", "郊外", "地方"], [INK, BLUE, GRAY, ORANGE]):
        z = q[q.範囲 == sc]; ax.scatter(z.期待値 * 100, z.SQL * 100, s=16, color=c, label=sc, alpha=0.85)
    lim = [q.期待値.min() * 100 - 0.5, q.期待値.max() * 100 + 0.5]; ax.plot(lim, lim, color=MUTED, lw=0.8)
    ax.set_xlabel("pandas（%）"); ax.set_ylabel("SQL（%）"); ax.legend(fontsize=8.5, frameon=False)
    ax.set_title(f"① メジャーの値：pandas と SQL\n{len(cmp_):,} 個の値、相対差は最大 {cmp_.相対差.max():.0e}", loc="left", fontsize=10.5, weight="bold")
    ax.text(0.02, 0.02, "例：既存店売上の前年比（曜日補正）\n月と FY、全社と3地域", transform=ax.transAxes, fontsize=8.3, color=MUTED)
    ax = axs[1]; ax.axis("off")
    ax.set_title("② 画面の大きさを変えたとき（HTML 版、3ページ）", loc="left", fontsize=10.5, weight="bold")
    scr = list(dict.fromkeys(lay.画面)); checks = ["横ずれ\nなし", "KGI が\n見える", "KPI 7枚\nが見える", "文字の\nはみ出し\nなし", "最小の\n文字"]
    for i, s in enumerate(scr):
        z = lay[lay.画面 == s]; p1 = z[z.ページ == 1].iloc[0]
        vals = [(~z.hscroll).all(), bool(p1.kgi_in_first_view), int(p1.kpi_in_first_view) == int(p1.kpi_total),
                (z.text_overflow.sum() + z.clipped_children.sum()) == 0, z.min_font_px.min()]
        ax.text(0.0, 0.83 - i * 0.16, s, fontsize=9, transform=ax.transAxes, va="center")
        for k, v in enumerate(vals):
            x = 0.37 + k * 0.135
            if k < 4:
                ok = bool(v); txt = "○" if ok else ("×" if k != 2 else f"{int(p1.kpi_in_first_view)}/7")
                ax.text(x, 0.83 - i * 0.16, txt, fontsize=11, color=BLUE if ok else ORANGE, ha="center", va="center", transform=ax.transAxes, weight="bold")
            else:
                ax.text(x, 0.83 - i * 0.16, f"{v:.1f}px", fontsize=9, color=ORANGE if v < 9 else INK, ha="center", va="center", transform=ax.transAxes)
    for k, c in enumerate(checks):
        ax.text(0.37 + k * 0.135, 0.97, c, fontsize=7.8, ha="center", va="center", color=MUTED, transform=ax.transAxes)
    ax.text(0.0, 0.0, "見える＝最初の画面（スクロールなし）に収まる。スマートフォンは縦に並べる版で、\n図を出していた最初の版は最小の文字が 2.9〜5.4px → 図を外した。橙は直したいところ。", fontsize=8.2, color=MUTED, transform=ax.transAxes)
    ax = axs[2]
    g = bf.groupby("倍率")[["色がつく店"]].sum().reset_index(); tot = bf.groupby("倍率").既存店の数.sum().iloc[0]
    fixed = bf.groupby("倍率")["色がつく店（決めた線3pt）"].sum().iloc[0]
    labels = ["決めた線\n3pt"] + [f"幅\n{k}σ" for k in g.倍率]; vals = [fixed] + list(g.色がつく店)
    bars = ax.bar(range(len(vals)), vals, color=[ORANGE, GRAY, INK, GRAY], width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 2, f"{v}（{v / tot * 100:.0f}%）", ha="center", fontsize=9)
    ax.set_xticks(range(len(vals))); ax.set_xticklabels(labels); ax.set_ylabel("色がつく店×月（FY2025、計）")
    ax.set_title(f"③ 線の引き方：店×月の売上（全社との差）\n既存店の店×月 {tot} のうち", loc="left", fontsize=10.5, weight="bold")
    fig.text(0.01, -0.04, NOTE + " ①②は DAX ではなく、同じ定義の pandas・SQL・HTML で確かめたもの（Power BI そのものでは動かしていない）。", fontsize=8.6, color=MUTED)
    fig.tight_layout(); save(fig, "fig6_checks.png")


def main():
    data = dashboard_data()
    json.dump(data, open(RES / "G_dashboard_data.json", "w"), ensure_ascii=False, indent=1)
    path = build_html(data)
    lay = screenshots_and_layout(path)
    print(lay[["画面", "ページ", "hscroll", "kgi_in_first_view", "kpi_in_first_view", "text_overflow", "clipped_children", "min_font_px", "colored_marks", "page_height"]].to_string())
    fig1(); fig3(); fig5(); fig6(lay, None)
    print("focus", data["focus"]["label"], data["focus"]["note"])


if __name__ == "__main__":
    main()
