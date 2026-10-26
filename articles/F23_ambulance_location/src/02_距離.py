"""需要点（500mメッシュの中心）から候補地までの道路距離と所要時間、直線距離を行列にする。

道路距離は OpenStreetMap の道路網をもとにした OSRM（公開デモサーバー router.project-osrm.org の table API、
自動車・渋滞なし）で、ブラウザから 50×50 ずつ取り、data/raw/f23_osrm_matrix.json に保存したもの。
取り直すときは src/osrm_fetch.js をブラウザのコンソールで実行する（数分かかる）。
出力：data/matrix.npz（road_km, road_min, line_km, snap_d, snap_c）
"""
import json

import numpy as np
import pandas as pd

from common import RAW, DATA
from opt import haversine

d = pd.read_csv(DATA / "demand.csv")
c = pd.read_csv(DATA / "candidates.csv")
js = json.load(open(RAW / "f23_osrm_matrix.json"))
road_km = np.array(js["DIST"], dtype=float) / 1000
road_min = np.array(js["DUR"], dtype=float) / 60
assert road_km.shape == (len(d), len(c)), road_km.shape
assert np.isfinite(road_km).all()
line_km = haversine(d.lat.values, d.lon.values, c.lat.values, c.lon.values)
snap_d = np.array(js["SNAPD"], dtype=float)
snap_c = np.array(js["SNAPC"], dtype=float)
np.savez_compressed(DATA / "matrix.npz", road_km=road_km, road_min=road_min, line_km=line_km,
                    snap_d=snap_d, snap_c=snap_c)
ratio = road_km / np.maximum(line_km, 0.05)
print("road/line ratio median", np.median(ratio[line_km > 1]))
print("snap distance to road (m): demand median", np.median(snap_d), "max", snap_d.max(),
      "cand max", snap_c.max())
