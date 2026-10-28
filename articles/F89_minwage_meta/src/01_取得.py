"""これまでの看板記事（F01・F15・F17・F26）の結果ファイルを集める。
同じリポジトリの隣のフォルダにあればそこから、なければ GitHub から取る。"""
import shutil
import requests
from common import RAW, ROOT

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {
    "F01_twfe.csv": "F01_minimum_wage_did/results/twfe.csv",
    "F01_did.csv": "F01_minimum_wage_did/results/did.csv",
    "F01_robustness.csv": "F01_minimum_wage_did/results/robustness.csv",
    "F01_first_stage.csv": "F01_minimum_wage_did/results/first_stage.csv",
    "F01_panel.csv": "F01_minimum_wage_did/data/panel.csv",
    "F15_estimates.json": "F15_border_minwage/results/estimates.json",
    "F15_robustness.csv": "F15_border_minwage/results/robustness.csv",
    "F17_main.json": "F17_minwage_causal_forest/results/main.json",
    "F17_robustness.csv": "F17_minwage_causal_forest/results/robustness.csv",
    "F26_past_flagships.csv": "F26_power_simulation/results/past_flagships.csv",
    "F26_mde_grid.csv": "F26_power_simulation/results/mde_grid.csv",
}

RAW.mkdir(parents=True, exist_ok=True)
for name, rel in FILES.items():
    local = ROOT.parent / rel
    if local.exists():
        shutil.copy(local, RAW / name)
    else:
        r = requests.get(BASE + rel, timeout=60)
        r.raise_for_status()
        (RAW / name).write_bytes(r.content)
    print("ok", name)
