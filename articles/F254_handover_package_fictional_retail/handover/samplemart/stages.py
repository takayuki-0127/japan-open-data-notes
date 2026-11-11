"""段（ステージ）の表：どの回の、どのスクリプトを、どの順に流すか。

- target "report"：mart と月次レポートを作るのに要る段だけ（F246 → F247 → F248）
- target "all"   ：F246〜F251 の README の「再現手順」を、その順のまま全部
どちらも、前の回の成果物は GitHub から取らずに、この作業の中で作り直したもの（隣のフォルダ）を使う。
そのために、GitHub から取りに行く「01_取得.py」の代わりに、隣のフォルダから写す段（prefill_*）を前に置く。
"""
import pathlib, re, shutil

REPORT_ARTS = ["F246_kpi_definitions_fictional_retail", "F247_data_mart_fictional_retail",
               "F248_monthly_report_template_fictional_retail"]


def articles(cfg, target):
    return cfg["source"]["articles"] + (cfg["source"]["extra_articles"] if target == "all" else [])


def readme_steps(art_dir):
    t = (art_dir / "README.md").read_text(encoding="utf-8")
    m = re.search(r"## 再現手順\s*\n```[^\n]*\n(.*?)```", t, re.S)
    return [l.split("#")[0].split()[1] for l in m.group(1).splitlines() if l.strip().startswith("python ")]


# ---------------------------------------------------------------- 隣のフォルダから写す段
def _copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)


def prefill_f247(arts, cfg):
    """F247 の 01_取得.py は F246 のデータを GitHub（コミット 3006b82）から取る。代わりに、いま作り直した F246 の data/ を写す。"""
    src = arts / "F246_kpi_definitions_fictional_retail" / "data"
    dst = arts / "F247_data_mart_fictional_retail" / "data" / "truth"
    n = 0
    for f in ["dim_store.csv", "dim_category.csv", "dim_date.csv", "fact_store_day.csv.gz",
              "fact_store_day_category.csv.gz", "fact_member_month.csv", "fact_ec_day.csv"]:
        _copy(src / f, dst / f); n += 1
    return f"F246 の data/ から {n} ファイルを F247 の data/truth/ に写した"


def prefill_mart_user(name):
    """F250・F251 の 01_取得.py は F247 の mart と F246 の合成コードを GitHub から取る（無いときだけ）。先に隣から写しておく。"""
    def f(arts, cfg):
        a = arts / name
        mart = arts / "F247_data_mart_fictional_retail" / "mart"
        for fn in ["dim_store.csv", "dim_category.csv", "dim_date.csv", "store_month.csv",
                   "fact_store_day.csv.gz", "fact_store_day_category.csv.gz"]:
            _copy(mart / fn, a / "data" / "mart" / fn)
        f246 = arts / "F246_kpi_definitions_fictional_retail"
        _copy(f246 / "src" / "02_整形.py", a / "data" / "f246" / "src" / "02_整形.py")
        for fn in ["calendar_daily.csv.gz", "sales_monthly_6types.csv", "kakei_items.csv"]:
            _copy(f246 / "data" / "raw" / fn, a / "data" / "f246" / "data" / "raw" / fn)
        return f"{name[:4]}：隣の F247 の mart と F246 の合成コードを data/ に写した"
    return f


PREFILL = {"F247_data_mart_fictional_retail": ("prefill", prefill_f247, "F246 の作り直したデータを F247 の正解に写す"),
           "F250_sales_drop_explanation_fictional_retail": ("prefill", prefill_mart_user("F250_sales_drop_explanation_fictional_retail"), "mart を隣から写す"),
           "F251_promo_effect_fictional_retail": ("prefill", prefill_mart_user("F251_promo_effect_fictional_retail"), "mart を隣から写す")}
# 01_取得.py を飛ばす回（prefill が代わりをする）
SKIP_01 = {"F247_data_mart_fictional_retail"}

# target "report" で流すスクリプト（それ以外の段は、図・頑健性・SQL の照合など）
REPORT_STEPS = {
    "F246_kpi_definitions_fictional_retail": [("src/02_整形.py", "合成データ（seed 0）を data/ に"),
                                              ("src/03_分析.py", "偶然の幅・曜日の効果（20通りの作り直し）")],
    "F247_data_mart_fictional_retail": [("src/02_整形.py", "現場から届くファイル（汚れ入り）を合成"),
                                        ("src/03_整える.py", "SQL で staging→mart→テスト")],
    "F248_monthly_report_template_fictional_retail": [("src/01_取得.py", "F246・F247 の成果物を data/in/ に写す"),
                                                      ("src/02_整形.py", "計画と、締めの日ごとの店×月"),
                                                      ("src/03_レポート.py", "12か月×速報・確定の月次レポート")],
}


def plan(cfg, target):
    out = []
    for a in articles(cfg, target):
        if a in PREFILL:
            label, fn, what = PREFILL[a]
            out.append({"article": a, "label": label, "func": fn, "what": what})
        if target == "report":
            steps = REPORT_STEPS[a]
        else:
            steps = [(s, "README の再現手順") for s in readme_steps_cached(cfg, a)]
        for s, what in steps:
            if a in SKIP_01 and s.endswith("01_取得.py"):
                continue
            out.append({"article": a, "label": pathlib.Path(s).stem, "script": s, "what": what})
    return out


_README = {}


def set_repo(repo):
    _README["repo"] = repo


def readme_steps_cached(cfg, a):
    return readme_steps(_README["repo"] / "articles" / a)
