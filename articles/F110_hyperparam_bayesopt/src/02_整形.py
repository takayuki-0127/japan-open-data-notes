"""F110 整形：学習・検証・テストの分け方を確かめて results/data_summary.json に書く
- 地価：20km 四方のブロック単位で 60%・20%・20%（同じブロックの地点は同じ側に入る）
- 電力：学習 2016/4〜2022/3、検証 2022/4〜2024/3、テスト 2024/4〜（時間の順に分ける）"""
import json
from common import *
out = {}
for name, ld in [("land", load_land), ("power", load_power)]:
    D = ld(); out[name] = {k: int(len(v[1])) for k, v in D.items()}
json.dump(out, open(RES / "data_summary.json", "w"), indent=1)
print(out)
