"""F121 は新しいデータを取らない。これまでの記事（F01・F15・F17・F26・F89）の data/ と results/ を data/raw/ にコピーして使う。
元ファイル（GitHub: takayuki-0127/japan-open-data-notes/articles/）
- F01_minimum_wage_did/data/panel.csv            -> F01_panel.csv
- F15_border_minwage/data/pairs.csv, muni.csv    -> F15_pairs.csv, F15_muni.csv
- F17_minwage_causal_forest/data/f17_panel.csv   -> F17_panel.csv
- F26_power_simulation/results/past_flagships.csv-> F26_past_flagships.csv
- F89_minwage_meta/data/estimates_common_unit.csv, constants.json, results/summary.json
"""
from common import RAW
need=['F01_panel.csv','F15_pairs.csv','F15_muni.csv','F17_panel.csv','F26_past_flagships.csv','estimates_common_unit.csv','constants.json','F89_summary.json']
miss=[n for n in need if not (RAW/n).exists()]
print('missing:',miss or 'none')
