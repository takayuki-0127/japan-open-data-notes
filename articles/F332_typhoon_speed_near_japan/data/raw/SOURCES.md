# data/raw の出典

取得日：2026-11-16（`src/01_fetch.py` で取得）

| ファイル | 内容 | URL |
|---|---|---|
| bst_all.zip | 気象庁 RSMC Tokyo「ベストトラック」（1951年〜、台風ごとの中心位置・中心気圧・階級。中に bst_all.txt） | https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/Besttracks/bst_all.zip |

- 使った列：時刻（YYMMDDHH）、階級（2 熱帯低気圧、3〜5 台風の強さ、6 温帯低気圧、9 台風の強さ以上）、緯度・経度（0.1度単位）、中心気圧。
- 年は2けたのため、51以上を1900年代、50以下を2000年代とした。2026年は途中のため使っていない。
