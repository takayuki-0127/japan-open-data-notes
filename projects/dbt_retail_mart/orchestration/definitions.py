"""dbt_retail_mart を Dagster で回す定義。
- raw：架空の小売の合成データを作る（tools/generate_data.py）と、答え合わせの期待値を作る（tools/make_expected.py）
- dbt：dbt build（モデルと seed を asset、dbt のテストを asset check として扱う）
- cross_check：レポート8本を pandas で別に計算した答えと突き合わせる（ずれが1行でもあれば asset check が落ちる）
- 毎日 6:00（日本時間）の schedule と、失敗したときに target/alerts.log に書く hook

使い方（projects/dbt_retail_mart で）:
  dagster job execute -m orchestration.definitions -j daily_mart
  dagster job execute -m orchestration.definitions -j daily_mart -c orchestration/config_break.yaml   # わざと落とす
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import dagster as dg
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, DbtProject, dbt_assets

PROJECT_DIR = Path(__file__).resolve().parents[1]
TARGET = PROJECT_DIR / "target"
RAW_TABLES = ["calendar", "store", "item", "dept", "receipt", "sales_line", "returns_line"]
REPORTS = ["rpt_r1_monthly_sales", "rpt_r2_store_monthly_sales", "rpt_r3_dept_group_monthly_sales",
           "rpt_r4_comp_store_yoy", "rpt_r5_customers_ticket", "rpt_r6_store_dept_group_monthly_sales",
           "rpt_r7_kpi_summary", "rpt_r8_latest_month_daily"]

os.environ.setdefault("DBT_PROFILES_DIR", str(PROJECT_DIR))
dbt_project = DbtProject(project_dir=PROJECT_DIR, profiles_dir=PROJECT_DIR)
if not dbt_project.manifest_path.exists():
    # 手元で動かすときは、最初に dbt parse で manifest.json を作る
    subprocess.run(["dbt", "parse", "--quiet"], cwd=PROJECT_DIR, check=True,
                   env={**os.environ, "DBT_PROFILES_DIR": str(PROJECT_DIR)})


class Translator(DagsterDbtTranslator):
    """dbt の source（raw.*）を、下の raw_data が作る asset に結びつける"""

    def get_asset_spec(self, manifest, unique_id, project):
        spec = super().get_asset_spec(manifest, unique_id, project)
        props = self.get_resource_props(manifest, unique_id)
        if props["resource_type"] == "source":
            return spec.replace_attributes(key=dg.AssetKey(["raw", props["name"]]))
        return spec


@dg.multi_asset(
    specs=[dg.AssetSpec(["raw", t], group_name="raw",
                        description=f"架空の小売の合成データ（{t}）。data/<dataset>/{t}.csv.gz") for t in RAW_TABLES],
    name="raw_data",
)
def raw_data(context: dg.AssetExecutionContext):
    """合成データ（main・fixture）と、答え合わせの期待値（seeds/expected_*）を作り直す。種は 2751 で固定"""
    for script in ("generate_data.py", "make_expected.py"):
        p = subprocess.run([sys.executable, str(PROJECT_DIR / "tools" / script)], cwd=PROJECT_DIR,
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise dg.Failure(f"{script} が失敗した", metadata={"stderr": p.stderr[-2000:]})
    for t in RAW_TABLES:
        f = PROJECT_DIR / "data" / "fixture_2751" / f"{t}.csv.gz"
        yield dg.MaterializeResult(asset_key=["raw", t], metadata={"bytes_fixture": f.stat().st_size})


class DbtBuildConfig(dg.Config):
    vars_json: str = "{}"     # dbt の --vars に渡す JSON（定義の変更依頼を試すとき）
    full_refresh: bool = True


@dbt_assets(manifest=dbt_project.manifest_path, dagster_dbt_translator=Translator())
def retail_mart_dbt(context: dg.AssetExecutionContext, dbt: DbtCliResource, config: DbtBuildConfig):
    """dbt build。テストが1本でも落ちると、この段が失敗し、下流（cross_check）は動かない"""
    args = ["build"]
    if config.full_refresh:
        args.append("--full-refresh")
    v = json.loads(config.vars_json)
    if v:
        args += ["--vars", json.dumps(v, ensure_ascii=False)]
    yield from dbt.cli(args, context=context).stream()


@dg.asset(
    deps=[dg.AssetKey([r]) for r in REPORTS],
    group_name="checks",
    description="レポート8本を、pandas で別に計算した答え（答え合わせ用データ・既定の定義）と突き合わせた結果",
    check_specs=[dg.AssetCheckSpec("no_mismatch", asset="cross_check", blocking=True,
                                   description="ずれた行が0であること")],
)
def cross_check(context: dg.AssetExecutionContext):
    sys.path.insert(0, str(PROJECT_DIR / "tools"))
    import check  # tools/check.py の compare_all をそのまま使う
    res = check.compare_all(check.BASE_P, "fixture_2751")
    mismatch = sum(v[0] for v in res.values())
    rows = sum(v[1] for v in res.values())
    TARGET.mkdir(exist_ok=True)
    (TARGET / "cross_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    yield dg.MaterializeResult(metadata={"rows_compared": rows, "rows_mismatch": mismatch,
                                         "by_report": dg.MetadataValue.json(res)})
    yield dg.AssetCheckResult(check_name="no_mismatch", passed=mismatch == 0,
                              metadata={"rows_mismatch": mismatch, "rows_compared": rows})


@dg.failure_hook
def write_alert(context: dg.HookContext):
    """失敗した段の名前と時刻を target/alerts.log に1行で書き、標準エラーにも出す（手元での「知らせ」の代わり）"""
    TARGET.mkdir(exist_ok=True)
    line = f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\tFAILED\t{context.op.name}\trun={context.run_id}"
    with open(TARGET / "alerts.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print("ALERT " + line, file=sys.stderr)


daily_job = dg.define_asset_job("daily_mart", selection=dg.AssetSelection.all(), hooks={write_alert})
daily_schedule = dg.ScheduleDefinition(job=daily_job, cron_schedule="0 6 * * *",
                                       execution_timezone="Asia/Tokyo", name="daily_mart_0600_jst")

defs = dg.Definitions(
    assets=[raw_data, retail_mart_dbt, cross_check],
    jobs=[daily_job],
    schedules=[daily_schedule],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
)
