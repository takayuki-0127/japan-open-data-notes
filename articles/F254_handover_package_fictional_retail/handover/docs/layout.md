# フォルダの構成と、回どうしのつながり

## この引き継ぎ資料（handover/）

```
handover/
├── README.md                 はじめに読む。前提・3つのコマンド・出てくるもの・困ったとき
├── run_all.py                入口。取得 → 作り直し → 照合を1回で
├── config.toml               どのリポジトリの、どのコミットを使うか（ここだけ変えればよい）
├── requirements.lock         版を固定したライブラリ（数字を元と同じにするため）
├── requirements-browser.lock 図の一部と PDF を作るときだけ（--target all）
├── samplemart/
│   ├── stages.py             段の表：どの回の、どのスクリプトを、どの順に流すか
│   ├── verify.py             照合：作り直したファイルと、コミットに入っている元のファイルを比べる
│   └── rules.py              決めごとのものさし（既存店の判定など。会社設定書の文のまま）
├── tests/
│   └── test_rules.py         既存店の判定が、4か所のコードで同じ答えか
├── docs/
│   ├── layout.md             この文書
│   ├── decisions.md          決めごとの一覧と、コードのどこに書いてあるか（暗黙の前提を書き出したもの）
│   ├── monthly_runbook.md    毎月やること（締めの日から報告まで）
│   ├── checklist.md          引き継ぎのチェックリスト（渡す側・受け取る側）
│   └── troubleshooting.md    試走で止まったところと、直し方
└── work/                     （実行すると作られる。リポジトリには入れない）
    ├── repo/                 決めたコミットの F246〜F251（sparse checkout）
    ├── logs/                 段ごとのログ
    ├── run_log.json          段ごとの成否・かかった時間
    └── verify.csv            照合の結果（ファイルごと）
```

## 回どうしのつながり（データの流れ）

```
F246 KPI を決める
  src/02_整形.py  gen(seed) ── data/（合成データ seed 0）──────────────┐
  src/03_分析.py  ── results/C_noise_by_grain.csv（偶然の幅）             │
                  ── results/D_calendar_adjust.csv（曜日の並びの効果）    │
                                                                         ▼
F247 データを整える                                          data/truth/（正解）
  src/02_整形.py  ── data/raw_synth/（現場から届くファイル、汚れ入り）
  src/03_整える.py ── mart/（store_month・fact_store_day ほか）・build_mart_pd()
                                                                         │
F248 月次レポート                                                        ▼
  src/01_取得.py  ── data/in/（F246 の results と F247 の mart を写す）
  src/02_整形.py  ── data/versions/（締めの日ごとの店×月：F247 の build_mart_pd を呼ぶ）、data/plan_fy2025.csv
  src/03_レポート.py ── reports/（12か月 × 速報 v1・確定 v2）。偶然の幅は F246 の gen を呼んで測り直す

F249 ダッシュボード／F250 悪い月の説明／F251 販促の効果
  どれも F247 の mart と、F246 の gen（乱数の種を変えた作り直し）を使う
```

- **隣のフォルダを読む**：F248 の 02・03 は、`../F247_data_mart_fictional_retail` と `../F246_kpi_definitions_fictional_retail` を直接読む（GitHub から取る逃げ道がない）。F248 のフォルダだけを渡すと止まる。run_all.py は3つを同じ親フォルダに並べるので、この問題は起きない。
- **GitHub から取る**：F247・F249・F250・F251 の `01_取得.py` は、前の回の成果物を GitHub の決まったコミット（F246 は 3006b82、F247 は e8ba90f）から取る。run_all.py は、その代わりに「いま作り直した隣のフォルダ」から写す段（stages.py の prefill）を置いている。前の回を直したとき、その直しが後の回に流れるようにするため。
- **手で書いたファイルと作られるファイルが同じフォルダにある**：F249 の `powerbi/`（layout_spec.md・rls.md・build_steps.md は手書き、ほかは 05 が作る）。生成物を消すつもりで `powerbi/` を消すと、手書きの3つも消える。run_all.py はコミットにあるファイルを消さない。
