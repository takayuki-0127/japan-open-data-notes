# japan-open-data-notes

日本の政府統計・オープンデータを分析して、note に書いた記事のコード・データ・図をまとめたリポジトリです。

- `articles/<番号>_<名前>/` に1記事1フォルダで置いています（README・データ・図・集計結果・コード）。各フォルダはそれだけで動きます
- 番号は note の記事の通し番号です（002〜007・017・018 は YouTube やツールの記事で、別のリポジトリにあります）
- 以前の記事で使った図は [note-figures](https://github.com/takayuki-0127/note-figures) にあります

## 看板記事
手法をくわしく見せる長めの記事です。まずはここから読んでください（下の「記事の一覧」の本数には含めていません）。

| # | 記事 | 手法 | フォルダ |
|---|---|---|---|
| F01 | 最低賃金の引き上げは、雇用を減らしたのか？ 47都道府県・18年のデータで比べると、減った形跡は見えなかった | 差の差・イベントスタディ・プラセボ・並べ替え検定・wild cluster bootstrap | [F01_minimum_wage_did](articles/F01_minimum_wage_did) |
| F02 | コロナがなかったら、赤ちゃんは何人多かったのか？ 2010年代の傾向から「なかった場合」を作ると、はっきり減ったのは2021年1月前後だけだった | 時系列の反実仮想（SARIMA・ETS・Prophet、シミュレーションによる予測区間）・バックテスト・婚姻経由の回帰 | [F02_births_counterfactual](articles/F02_births_counterfactual) |
| F03 | 地価を決めているのは何か？ 全国2.6万地点を機械学習で読むと、効いていたのは駅までの距離より「周りの駅にどれだけ人がいるか」だった | LightGBM・ランダムCVと空間ブロックCV（20km四方・都道府県）・SHAP・部分依存・残差の地図 | [F03_land_price_ml](articles/F03_land_price_ml) |
| F04 | Go To トラベルは宿泊をどれだけ増やしたのか？ ベイズで「なかった場合」を作ると、上乗せは前提しだいで4,400万〜9,000万人泊と2倍ちがった | ベイズ構造時系列（CausalImpact型、PyMC）・差の差（東京の途中参加）・合成コントロール・プラセボ | [F04_goto_causalimpact](articles/F04_goto_causalimpact) |
| F05 | 医療費の地域差は「県」と「市町村」のどちらで決まるか？ 階層ベイズモデルで分けると、6割が県の差。入院は県、外来は市町村で差がつく | 階層ベイズモデル（PyMC）・分散の分解・部分プーリング・事後予測チェック | [F05_medical_cost_hierarchical](articles/F05_medical_cost_hierarchical) |
| F06 | 高齢化は地図の上で固まっているか？ 札幌・横浜・福岡の町丁字を空間統計で見ると、20年で塊はより強くなり、横浜では都心から郊外へ移っていた | 空間自己相関（Moran's I・LISA、並べ替え検定・FDR）・面積按分・隣接の定義の感度 | [F06_aging_spatial](articles/F06_aging_spatial) |
| F07 | 新卒は何年目に辞めやすいのか？ 30年分の卒業年を生存分析で追うと、大卒の山は「1年目」から「2・3年目」へ移り、就職した年の不景気が効くのは1年目だけだった | 離散時間ハザード（集計値の二項ロジット）・卒業年コホートの残存曲線・入口と出口の景気・クラスター頑健SE | [F07_turnover_survival](articles/F07_turnover_survival) |
| F08 | 1,740市区町村を62の指標で分けると何タイプか？ 5つに分けられたが、はっきりした塊はなく、都市から過疎までの「グラデーション」を区切ったものだった | 主成分分析・UMAP・k-means／ガウス混合／ウォード法／HDBSCAN・クラスタ数の検討（シルエット・BIC）・ブートストラップ安定性 | [F08_municipal_segments](articles/F08_municipal_segments) |
| F09 | 国会で「賃上げ」はいつから語られるようになったのか？ 40年分の発言をテキスト分析すると、2022年から急に増え、話題は「春闘」から「税制・支援」に移っていた | テキストマイニング（国会会議録APIで取得・形態素解析・重み付き対数オッズ比・共起ネットワーク・LDA トピックモデル）・統計との相関 | [F09_diet_text](articles/F09_diet_text) |
| F10 | 人の流れで見ると、日本はいくつの「圏」に分かれるか？ 引っ越しをネットワーク分析すると4つに分かれ、30年で入れ替わったのは2県だけだった | ネットワーク分析（PageRank・Leiden 法のコミュニティ検出・解像度の比較・ARI／NMI での一致）・1都3県の通勤ネットワーク | [F10_mobility_network](articles/F10_mobility_network) |
| F11 | 消費増税の「駆け込み」と「反動」はどれだけだったか？ 2014年と2019年をイベントスタディで比べると、2019年は反動が小さく、軽減税率の食料は落ち込まなかった | イベントスタディ（季節・傾きの反実仮想）・偽の増税月によるプラセボ・軽減税率の差の差の差 | [F11_tax_hike_event](articles/F11_tax_hike_event) |
| F12 | 公的統計を毎月自動で更新するには？ e-Stat→DuckDB→dbtで「くらしの指標」を作ると、実質賃金は公表値と680か月すべて一致し、壊れたデータはテストで止まった | データパイプライン（e-Stat ファイル→DuckDB→dbt、テスト20本・差分チェック・再試行）・Streamlit・GitHub Actions の例 | [F12_stats_pipeline](articles/F12_stats_pipeline) |
| F13 | 失業率を来月まで予測できるか？ 4つのモデルを21年分のローリング予測で比べると、1か月先は「前月の値」に勝てず、3か月先は求人の情報で誤差が15%減った | ローリング予測（ARIMA・SARIMAX・ElasticNet・LightGBM）・ナイーブとの比較・Diebold–Mariano 検定・公表タイミングを守った特徴量・SHAP | [F13_unemployment_forecast](articles/F13_unemployment_forecast) |
| F14 | コンパクトシティの計画を作った市町村で、中心部の人口密度は保てたのか？ 似た市町村と組にして比べると、2015→20年の5年では差は見えなかった | 傾向スコアマッチング・差の差・作成時期ごとの推定（Callaway–Sant'Anna 型）・IPW・二重頑健 | [F14_compact_city_psm_did](articles/F14_compact_city_psm_did) |
| F15 | 県境をまたぐと最低賃金が違う。隣どうしの町で雇用は違ったか？ 724組を境界で比べると差は見えず、そもそも見分けられる設計ではなかった | 境界不連続デザイン（県境をはさんで接する市区町村ペア・ペア固定効果）・製造業との三重差・並べ替え検定・検出力 | [F15_border_minwage](articles/F15_border_minwage) |
| F16 | 保育所に通う子どもが増えた町で、女性は働きに出たのか？ 80の条件を機械学習で取り除いて比べると、効果はプラスだが小さく、子ども1人あたり約0.06人だった | ダブル機械学習（DML・部分線形モデル、ランダムフォレスト／LightGBM／Lasso、交差適合）・重回帰との比較・プラセボ（前の期間） | [F16_childcare_dml](articles/F16_childcare_dml) |
| F17 | 最低賃金の影響が大きかったのはどんな県か？ 因果フォレストで県ごとの効果を推定すると、違いは「見えたように見えた」が、検証すると偶然と区別できなかった | 因果フォレスト（econml CausalForestDML）・LinearDML との比較・県を外した予測での BLP／GATES・プラセボ（上がり幅のシャッフル） | [F17_minwage_causal_forest](articles/F17_minwage_causal_forest) |
| F18 | 景気は今どうなのか？ 20の月次統計から「共通の動き」を取り出してGDPを公表前に推定すると、四半期の2か月目から誤差が4割小さくなった | ダイナミックファクターモデル（月次＋四半期、状態空間・カルマンフィルタ）・疑似リアルタイムのナウキャスト・AR との比較（DM 検定） | [F18_nowcast_dfm](articles/F18_nowcast_dfm) |
| F19 | 小さな町の検診受診率は、どこまで信用できるのか？ 周りの町から情報を借りる「縮小推定」をすると、値が動くのは対象者500人未満の町で、翌年の値も少しよく当たった | 小地域推定（Fay–Herriot モデル・REML による経験ベイズ）・ファネルプロット・過分散・翌年の値での検証 | [F19_small_area_fh](articles/F19_small_area_fh) |
| F20 | 出生率は隣の町と似るのか？ 1,841の市区町村を空間回帰で分析すると、普通の回帰で見えた「所得が高い町ほど低い」は地域の固まりの見かけだった | 空間回帰（OLS 残差の Moran's I・LM 検定・空間ラグ／空間誤差モデル・直接／間接効果）・地理的加重回帰（GWR）・都道府県ダミーとの比較 | [F20_tfr_spatial_regression](articles/F20_tfr_spatial_regression) |
| F21 | 公的統計の「いつもと違う動き」を自動で見つけられるか？ 98系列を異常検知にかけると、14の出来事のうち13を見つけたが、印の半分は年表にない動きだった | 異常検知（STL 残差の頑健 z スコア・Isolation Forest・PELT による変化点検出）・出来事の年表との答え合わせ・閾値のトレードオフ | [F21_anomaly_detection](articles/F21_anomaly_detection) |
| F22 | 明日の電力需要はどこまで当てられるか？ 東京エリアを6年半分予測すると、LightGBMの誤差は2.2%で「1週間前の同じ時刻」の4分の1。外れやすいのは猛暑より「お盆」だった | 時系列の交差検証（年度ごとの拡張ウィンドウ）・ベースライン比較・LightGBM・線形回帰・誤差分析・SHAP・気温の予報誤差のシミュレーション | [F22_power_demand_forecast](articles/F22_power_demand_forecast) |
| F23 | 救急車をどこに置けば、到着が早くなるか？ 福井市の人口と道路で21か所を選び直すと、平均距離は2割縮むが、遠い地区の「5分以内」は減った | 数理最適化（p-median・最大カバー、整数計画・HiGHS）・道路距離（OSRM）・直線距離との比較・重みと候補地の感度 | [F23_ambulance_location](articles/F23_ambulance_location) |
| F25 | 経済白書41年分をAIの「文埋め込み」で読むと、政府の関心はどう移ったか？ 主役は貿易→金融→雇用・賃金と入れ替わり、2000年代は毎年話題が変わっていた | 文埋め込み（ruri-v3-30m）・KMeans と c-TF-IDF でテーマ分け・UMAP・年度間のコサイン類似度・意味検索・単語ベース（TF-IDF＋SVD）との比較 | [F25_whitepaper_embeddings](articles/F25_whitepaper_embeddings) |
| F26 | 政策の効果を見つけるには、何県・何年のデータが要るのか？ 都道府県パネルで1,000回シミュレーションすると、就業率で見つかるのは0.7ポイント以上。これまでの「差は見えなかった」の多くは、見分けられない設計だった | 検出力シミュレーション（差の差のモンテカルロ、実データにでたらめな処置）・最小検出効果・標準誤差の比較（OLS・HC1・クラスター・wild cluster bootstrap）・TWFE と Callaway–Sant'Anna | [F26_power_simulation](articles/F26_power_simulation) |
| F27 | 市区町村の死亡率の地図は、小さな町ほどぶれる。隣の町の情報を借りる空間ベイズ（BYM2）で描き直すと、地域差の9割以上は「隣と共通の差」だった | 空間ベイズ（BYM2・ICAR、PyMC）・ファネルプロット・公表のベイズ推定値との比較・事前分布／隣接／死因の頑健性 | [F27_disease_map_bym2](articles/F27_disease_map_bym2) |
| F28 | 法人は何年続くのか？ 150万法人の登記を生存分析で追うと、10年で1割が閉鎖。合同会社は株式会社より1.5倍閉鎖しやすく、その差は2〜3年目がいちばん大きかった | 生存分析（Kaplan–Meier・Cox 比例ハザード・Schoenfeld 残差・期間別ハザード比） | [F28_corporate_survival](articles/F28_corporate_survival) |
| F29 | 北陸新幹線の金沢延伸で、石川県の宿泊客はどれだけ増えたか？ 合成コントロールとその発展形で推定すると日本人の宿泊は約12%増。ただ富山はほぼ0で、新幹線のない県にも同じくらい増えた県があった | 合成コントロール・Synthetic DID・Augmented SCM（自前実装）・構造時系列との比較・空間と時間のプラセボ | [F29_shinkansen_sdid](articles/F29_shinkansen_sdid) |
| F31 | 60歳・65歳で、働く人はどれだけ減るのか？ 国勢調査20年分を回帰不連続で見ると、60歳の段差は4分の1に縮み、2015年からは65歳の段差のほうが大きくなった | 回帰不連続（年齢を走る変数に）・バンド幅と次数の感度・偽の境界（プラセボ）・都道府県別 | [F31_retirement_rdd](articles/F31_retirement_rdd) |
| F32 | 所得の高い町と低い町で、効いている要因は同じか？ 1,740市区町村を分位点回帰で分けると、大卒の割合は上の町ほど強く効き、人口密度は下の町でだけプラスだった | 分位点回帰（10〜90%点）・ブートストラップの区間・分位点の間の差の検定・予測した分布の比較 | [F32_income_quantile](articles/F32_income_quantile) |
| F33 | 人の移動は距離でどれだけ減るのか？ 37年分の都道府県間の引っ越しを重力モデルで読むと、距離が2倍で移動は34%減。普通の回帰では51%減に見え、新幹線でつながっても増えた形跡はなかった | 重力モデル（PPML、出発県×年・到着県×年の固定効果）と対数の最小二乗法の比較・期間ごとの距離の弾力性・ペアの固定効果つきの新幹線の効果とイベントスタディ | [F33_migration_gravity](articles/F33_migration_gravity) |
| F34 | 同じお金で、どの市町村が多くのサービスを出しているか？ DEAとSFAで1,740市区町村の効率を測ると、2つの手法の順位は7割ほどしか合わず、入力を職員数に変えると大きく入れ替わった | 包絡分析法（DEA：CCR・BCC・スーパー効率、自前の線形計画）・確率的フロンティア（SFA：費用関数の最尤推定）・手法間の順位比較・2段階目の回帰・出力／入力／年を変えた頑健性 | [F34_municipal_efficiency](articles/F34_municipal_efficiency) |
| F35 | 景気の「山」と「谷」をデータだけで当てられるか？ マルコフ切り替えモデルで景気動向指数を読むと、7回の後退のうち6回を±4か月以内で見つけ、その時点のデータでも山の2〜4か月後にサインが出た | マルコフ切り替えモデル（3状態：急落・後退・拡張）・景気基準日付との一致と山谷のずれ・その時点までのデータで380回推定し直したリアルタイム判定・2状態／分散の切り替え／鉱工業生産／コロナ期除外の頑健性 | [F35_business_cycle_markov](articles/F35_business_cycle_markov) |
| F36 | 全国と47都道府県の宿泊者数の予測を、足し算が合うようにそろえると？ 58系列で比べると、全国の予測は15%よく当たるようになったが、都道府県はほぼ変わらず、トップダウンは3割以上悪くなった | 階層時系列予測の整合（全国・10地方・47都道府県の58系列、ETS／ARIMA、ボトムアップ・トップダウン・OLS・WLS・MinT）・ローリング予測と段ごとの MASE・コロナ後の比較・日本人／外国人・学習期間の頑健性 | [F36_hierarchical_forecast](articles/F36_hierarchical_forecast) |
| F37 | 地価の予測に「この範囲に9割入る」を付けられるか？ コンフォーマル予測で2.6万地点を確かめると、ランダムに分けた検証では9割入ったが、場所で分けると82%に落ちた | コンフォーマル予測（分割・正規化・CQR）・ランダムCVと20kmブロックCVでの当たり方・較正用データの取り方・地域／価格帯別の当たり方・年をまたぐと崩れる確認 | [F37_conformal_land_price](articles/F37_conformal_land_price) |
| F38 | 観光客が1兆円使うと、日本全体の生産はいくら増えるのか？ 産業連関表で計算すると2.1兆円。ただ前提の置き方しだいで1.7〜2.8兆円まで変わった | 産業連関分析（レオンチェフ逆行列・競争輸入型・直接／1次／2次波及・雇用誘発）・買物代の購入者価格→生産者価格の分解・費目別の比較・2015年表／輸入の扱い／消費転換係数で前提を変えた比較 | [F38_input_output_tourism](articles/F38_input_output_tourism) |
| F39 | 物価・賃金・金利は、どれがどれを動かしているのか？ データだけで因果の向きを推定する3つの手法を比べると、そろったのは「輸入物価と物価がつながっている」ことだけで、向きは手法で逆になった | 因果探索（VAR-LiNGAM・PC アルゴリズム）とグレンジャー因果の比較・ブートストラップで矢印が出た割合・非ガウス性の確認・期間／変数／変換を変えた頑健性 | [F39_causal_discovery_macro](articles/F39_causal_discovery_macro) |
| F40 | 所得の格差は「県の間」と「県の中」のどちらにあるか？ 1,741市区町村をタイル指数で分けると半々。15年で広がった分の半分は「東京都の中」だった | 不平等指標の分解（タイル指数 T・L、ジニ係数の分解）・でたらめなグループ分けとの比較・変化の要因分解 | [F40_inequality_decomposition](articles/F40_inequality_decomposition) |
| F41 | 欠けているデータを埋めると、結論は変わるのか？ 小さい町村で値がない「持ち家率」を4通りに扱うと、係数は+0.1から−9.7まで動き、多重代入の答えは「外挿」に頼っていた | 多重代入法（連鎖方程式・ルービンのルール）・完全ケース／平均／回帰代入との比較・欠測の仕組み（MCAR・MAR・MNAR）のシミュレーション | [F41_missing_data_mi](articles/F41_missing_data_mi) |
| F42 | 季節調整を自分でやると、公表値と同じになるか？ X-13ARIMA-SEATSで鉱工業指数と労働力調査を再現すると、就業者は0.02ポイントの差でほぼ一致。鉱工業は曜日と祝日の調整を入れないと前月比の向きが4か月に1回ずれた | 季節調整の再現（X-13ARIMA-SEATS の X-11 方式を公表元の設定に合わせる：鉱工業は2曜日＋日本の祝日＋年間補正、労働力調査は管理限界9.8σ〜9.9σ）・公表の季節指数との比較・曜日／祝日の効果・STL との比較・改定のシミュレーション | [F42_seasonal_adjustment](articles/F42_seasonal_adjustment) |

## まず見てほしい記事
| # | 記事 | 見どころ |
|---|---|---|
| 029 | [コロナで東京への人の流れはどれだけ減ったか？ 合成コントロール法で「コロナがなかった東京」を作って比べた](articles/029_covid_tokyo_synth) | 合成コントロール法で「コロナがなかった東京」を作って比べる |
| 022 | [保育所を増やした県で、出生率は上がったか？ 固定効果モデルで「県の違い」と「全国の流れ」を取り除いた](articles/022_nursery_birthrate_fe) | 二方向固定効果（都道府県×年のパネル） |
| 037 | [東京の中古マンションは10年で何%上がった？ 中央値では61%、「質をそろえる」と77%だった（ヘドニック回帰）](articles/037_tokyo_condo_hedonic) | ヘドニック回帰による品質調整済み価格指数 |
| 035 | [円安は、どれくらい物価を上げるのか？ 日銀のAPIでデータを取り、VARで「伝わり方」を調べた](articles/035_yen_prices_var) | 日銀 API でデータを取得し、VAR・インパルス応答 |
| 095 | [就業者は13年で550万人増えた。増えたのは女性と65歳以上で、人口が減る分を「働く人の割合」が912万人押し上げた](articles/095_employment_growth) | 就業者の増加を「人口」と「働く人の割合」に要因分解 |
| 137 | [市区町村の歳出の4割は福祉（民生費）。12年で1.5倍になり、伸びが大きかったのは子どもと障害者福祉など](articles/137_welfare_spending) | e-Stat の CSV から必要な行を抜き出して表を作るところからコード化 |

## 記事の一覧（219本）
| # | 記事のタイトル | フォルダ |
|---|---|---|
| 000 | 女性の労働力率は何で決まる？ 全国1,739市区町村の公開データで調べてみた | [000_women_labor](articles/000_women_labor) |
| 001 | 納税者1人あたりの所得は、なぜ街によって違うのか？ 全国1,740市区町村の公開データで調べてみた | [001_income_municipal](articles/001_income_municipal) |
| 008 | 人が集まっている街は、所得が高い街か？ 全国1,740市区町村で「条件をそろえる」と答えが変わった | [008_migration_income](articles/008_migration_income) |
| 009 | 子どもが多く生まれる街は、所得が高い街か？ 年齢をそろえると関係が消えた | [009_births_income](articles/009_births_income) |
| 010 | 外国人住民が多いのは、どんな市区町村か？ 「都心」「工場の街」「農業の村」の3タイプがあった | [010_foreign_residents_income](articles/010_foreign_residents_income) |
| 011 | 「平均所得ランキング」をそのまま信じていいか？ 全国1,740市区町村で「分母」と「町の大きさ」を確かめた | [011_income_ranking](articles/011_income_ranking) |
| 012 | 東京23区の中の所得の差は何倍か？ 港区と足立区で4.5倍、差と一緒に動いていたもの | [012_tokyo23_income](articles/012_tokyo23_income) |
| 013 | 昼に人が集まる街は、所得が高い街か？ 条件をそろえても残ったが、東京23区を除くと消えた | [013_daynight_income](articles/013_daynight_income) |
| 014 | ふるさと納税で「赤字」になるのは、どんな街か？ 7割の市区町村は黒字、でも7割の人は赤字の街に住んでいる | [014_furusato_balance](articles/014_furusato_balance) |
| 015 | 財政力が強い町は、住民の所得が高い町か？ 上位には発電所・工場・空港・別荘地の町が並んだ | [015_fiscal_strength](articles/015_fiscal_strength) |
| 016 | 人口あたりの医師が多いのは、どんな市区町村か？ 上位は「医学部のある町」、医師0人の町村は29 | [016_doctors](articles/016_doctors) |
| 019 | 1,740市区町村を「似た街」に分けてみた：k-means で5つのグループ、でも境目はあいまいだった | [019_municipal_clusters](articles/019_municipal_clusters) |
| 020 | 失業率は何か月先まで予測できるか？ 自分で季節調整して SARIMA で128回予測してみた | [020_unemployment_sarima](articles/020_unemployment_sarima) |
| 021 | 福島市の桃は全国の6倍、高知市のかつおは4.5倍：家計調査で「その街らしい食卓」と似た街を探した | [021_prefcapital_food](articles/021_prefcapital_food) |
| 022 | 保育所を増やした県で、出生率は上がったか？ 固定効果モデルで「県の違い」と「全国の流れ」を取り除いた | [022_nursery_birthrate_fe](articles/022_nursery_birthrate_fe) |
| 023 | スマホでゲームや音楽を楽しむ人が多いのは、どの県か？ 社会生活基本調査で見ると「若さ」で大部分が説明できた | [023_games_music_aging](articles/023_games_music_aging) |
| 024 | ふるさと納税は一部の自治体に集中しているか？ 18年分の受入額で見ると、2019年の制度変更のあと集中はゆるんだ | [024_furusato_concentration](articles/024_furusato_concentration) |
| 025 | 外国人の宿泊はコロナ前に戻ったか？ 全国では94%、でも2019年を超えたのは9都府県だけだった | [025_inbound_recovery](articles/025_inbound_recovery) |
| 026 | 人が転入してくる年に、その県の地価は上がるか？ 都道府県×11年のパネルで確かめた | [026_migration_landprice_fe](articles/026_migration_landprice_fe) |
| 027 | YouTube などの動画サイトは誰が見ている？ 総務省の調査を年代別に見ると、60代は6年で23%→45%に倍増 | [027_video_viewers_age](articles/027_video_viewers_age) |
| 028 | 動画サイトの利用率、都道府県の差は「誤差」なのか？ ファンネルプロットで確かめると、高齢化で3割ほど説明できた | [028_video_usage_funnel](articles/028_video_usage_funnel) |
| 029 | コロナで東京への人の流れはどれだけ減ったか？ 合成コントロール法で「コロナがなかった東京」を作って比べた | [029_covid_tokyo_synth](articles/029_covid_tokyo_synth) |
| 030 | 通勤時間が長い県は、何の時間を削っているか？ 社会生活基本調査の時間配分で見ると、まず睡眠だった | [030_commute_sleep](articles/030_commute_sleep) |
| 031 | 鹿児島は焼酎、東京はワイン：家計調査の「お酒の支出」をコレスポンデンス分析で地図にした | [031_alcohol_ca](articles/031_alcohol_ca) |
| 032 | 人口が2倍の街には、飲食店も2倍あるか？ 1,741市区町村で「スケーリング則」を調べた | [032_scaling_law](articles/032_scaling_law) |
| 033 | 高校卒業後の進学率、県の差は縮まっているか？ 11年分でσ収束とβ収束を確かめた | [033_university_convergence](articles/033_university_convergence) |
| 034 | テレワークをしたことがある人は6年で4倍に。でも年収・性別・住む県で大きな差（通信利用動向調査） | [034_telework](articles/034_telework) |
| 035 | 円安は、どれくらい物価を上げるのか？ 日銀のAPIでデータを取り、VARで「伝わり方」を調べた | [035_yen_prices_var](articles/035_yen_prices_var) |
| 036 | 日銀短観の「先行き」は当たるのか？ 147四半期分の予測と実績を比べたら、製造業と非製造業で違った | [036_tankan_forecast](articles/036_tankan_forecast) |
| 037 | 東京の中古マンションは10年で何%上がった？ 中央値では61%、「質をそろえる」と77%だった（ヘドニック回帰） | [037_tokyo_condo_hedonic](articles/037_tokyo_condo_hedonic) |
| 038 | 築年数と駅からの距離で、マンションはいくら安くなる？ 23区で一番上がった区は？ 17万件の取引で調べた | [038_condo_age_station](articles/038_condo_age_station) |
| 039 | 駅の利用者はコロナ前に戻ったか？ 全国の駅別乗降客数で見ると2024年度は92%、都心の駅ほど戻りきっていない | [039_station_recovery](articles/039_station_recovery) |
| 040 | 1年で利用者が半分になった駅は本当か？ 公的データの「段差」（数え方の変更）をコードで見つけた | [040_data_breaks](articles/040_data_breaks) |
| 041 | 今の地価は、バブルのピークの何%か？ 地価公示の43年分の履歴をつないで、圏域・用途別に計算した | [041_landprice_bubble](articles/041_landprice_bubble) |
| 042 | この10年で地価が上がった場所・下がった場所：全国2万地点で見ると、同じ県の中でも「高い所ほど上がる」二極化だった | [042_landprice_polarization](articles/042_landprice_polarization) |
| 043 | 2050年に人口が半分未満になる市町村は341。将来推計を「出生・死亡」と「人の移動」に分けてみた | [043_population_2050](articles/043_population_2050) |
| 044 | 2050年の人口推計は何で決まっているのか？ ランダムフォレストで調べたら、ほぼ「今の年齢構成」だった | [044_population_rf](articles/044_population_rf) |
| 045 | 50代前半の月給は20代前半の何倍？ 都道府県で比べると男性1.5〜2.0倍。大企業の多さだけでは説明できなかった | [045_wage_curve](articles/045_wage_curve) |
| 046 | 都道府県の年収差は「職種の違い」から来ているのか？ シフト・シェア分解したら、大半は同じ職種の中の差だった | [046_wage_shiftshare](articles/046_wage_shiftshare) |
| 047 | 2022年以降、死亡数は「予想」より毎年9万〜13万人多い。ただし予想の作り方で6年の合計は8万〜47万人まで変わる | [047_excess_deaths](articles/047_excess_deaths) |
| 048 | 病院で亡くなる人の割合は2005年がピーク。折れ線回帰で「流れが変わった年」を探した | [048_place_of_death](articles/048_place_of_death) |
| 049 | 大学進学率はどこまで上がる？ S字カーブを当てはめたら、上限は「よく分からない」が答えだった | [049_university_scurve](articles/049_university_scurve) |
| 050 | 子どもはほぼ半分、学校は4分の1減。小学校の数と子どもの数を77年分比べたら、減り方は「時期」で決まっていた | [050_school_closures](articles/050_school_closures) |
| 051 | 家計の株は「売り越し」なのに400兆円増えた。資金循環統計で、買った分と値上がり分を分けてみた | [051_household_assets](articles/051_household_assets) |
| 052 | 日本の家計は「値上がりした後に買う」のか？ 投資信託は追いかけ、株は追わなかった | [052_household_flows](articles/052_household_flows) |
| 053 | 東京都の外国人は47年で7倍。国籍ごとの「住む場所の偏り」を非類似度指数で測ったら、多くは小さくなっていた | [053_tokyo_foreign_segregation](articles/053_tokyo_foreign_segregation) |
| 054 | 東京都の外国人は10年で75%増。区市ごとの伸びの差は「国籍構成」ではなく、ほぼ「地域独自」だった | [054_tokyo_foreign_growth](articles/054_tokyo_foreign_growth) |
| 055 | 日本の気温の「最高記録」は、最近30年で5回。気温が変わらなければ0.27回のはずだった | [055_temperature_records](articles/055_temperature_records) |
| 056 | 1時間に100mm以上の雨は、40年で2倍に。強い雨ほど速く増えていた | [056_heavy_rain](articles/056_heavy_rain) |
| 057 | 暑さ指数31の日は、25の日の約7倍。熱中症の救急搬送を、6都市10年分の日別データで調べた | [057_wbgt_heatstroke](articles/057_wbgt_heatstroke) |
| 058 | 「夏の初めほど熱中症になりやすい」はデータで見えるか？ 6都市10年分で確かめたら、はっきりしなかった | [058_heatstroke_season](articles/058_heatstroke_season) |
| 059 | 交通事故29万件で「死亡事故になりやすい条件」を調べた。単独事故・歩行者・深夜・カーブで高かった | [059_fatal_accidents](articles/059_fatal_accidents) |
| 060 | 人身事故は6年で25%減。それでも「75歳以上」と「自転車」が第1当事者の事故だけは増えていた | [060_accidents_change](articles/060_accidents_change) |
| 061 | 大都市圏の中古マンションは4年で約3割上昇。品質をそろえて比べると、戸建ての伸びはその半分ほどだった | [061_house_price_index](articles/061_house_price_index) |
| 062 | 同じ条件の中古マンションでも、レインズの成約価格は登記ベースの取引価格より約1割低かった | [062_contract_vs_transaction](articles/062_contract_vs_transaction) |
| 063 | 訪問介護の事業所は減っていなかった。ただ2024年の報酬改定のあと、撤退のしやすさは通所介護と比べて1.4倍になっていた | [063_home_care_entry_exit](articles/063_home_care_entry_exit) |
| 064 | 訪問介護の事業所が1つもない市区町村は、5年半で46から83に増えていた | [064_home_care_access](articles/064_home_care_access) |
| 065 | Mが1大きい地震は約9分の1しか起きない。ただし小さな地震まで数えると、この法則は崩れて見える | [065_earthquake_bvalue](articles/065_earthquake_bvalue) |
| 066 | 余震はほぼ「経過時間に反比例」して減る。東北・熊本・能登の3つの地震で、減り方の指数はどれも1.03〜1.08だった | [066_aftershock_omori](articles/066_aftershock_omori) |
| 067 | 食中毒は25年でほぼ半減。腸炎ビブリオやサルモネラは激減し、代わりにアニサキスが増え、ノロウイルスは2025年に戻ってきた | [067_food_poisoning_trend](articles/067_food_poisoning_trend) |
| 068 | 食中毒の患者の4分の1は、上位1%の大きな事件から。仕出屋とノロウイルスの事件が大きくなりやすかった | [068_food_poisoning_size](articles/068_food_poisoning_size) |
| 069 | 台風の数は75年でやや少なめに。でも日本に近づく台風の数は、ほとんど変わっていなかった | [069_typhoon_counts](articles/069_typhoon_counts) |
| 070 | 台風が最も発達する場所は北へ移ったか。1980年以降の全台風では10年で0.4度北上、強い台風に限るとはっきりしなかった | [070_typhoon_latitude](articles/070_typhoon_latitude) |
| 071 | 日曜に開いている診療所は8%。平日夜7時以降の診療は全国で4分の1、近畿では5〜7割だった | [071_clinic_hours](articles/071_clinic_hours) |
| 072 | 薬局の半分は、医療機関から50m以内にあった。産婦人科を掲げる医療機関が掲載されていない市区町村は864 | [072_pharmacy_distance](articles/072_pharmacy_distance) |
| 073 | 工場などから出る化学物質の排出は、24年で3分の1になっていた。いちばん効いたのは、続けて届け出ている事業所の削減だった | [073_prtr_decline](articles/073_prtr_decline) |
| 074 | 化学物質の排出の半分は、届け出ている事業所の上位1%から出ていた。この集中は24年間ほとんど変わっていない | [074_prtr_concentration](articles/074_prtr_concentration) |
| 075 | さくらの開花は1960〜80年代より約5日早く、かえでの紅葉は約11日遅くなっていた | [075_sakura_autumn_leaves](articles/075_sakura_autumn_leaves) |
| 076 | とのさまがえるを記録した地点は9割減。ほかの生き物の減少の多くは、観測地点そのものが減った分だった | [076_phenology_animals](articles/076_phenology_animals) |
| 077 | インフルエンザの流行の山は3シーズン続けて年内に。伝染性紅斑は2025年、マイコプラズマ肺炎は2024年に大きな流行があった | [077_infectious_peaks](articles/077_infectious_peaks) |
| 078 | インフルエンザの流行は毎シーズン沖縄が先行。本土での広がり方は年ごとに違い、手足口病は南から北へ進んでいた | [078_infectious_onset](articles/078_infectious_onset) |
| 079 | 都道府県をまたぐ引っ越しは1971年がピークで、今はその半分。それでも東京圏への転入超過は70年間ほぼ毎年続いていた | [079_migration_tokyo](articles/079_migration_tokyo) |
| 080 | 引っ越しが距離に左右される度合いは1970年までに弱まり、その後50年ほぼ同じ。東京圏へ向かう割合は西日本や中部で上がり、東北で下がった | [080_migration_gravity](articles/080_migration_gravity) |
| 081 | 在留外国人は13年で2倍の412万人に。増え方が大きかったのは、北海道・九州・沖縄だった | [081_foreign_residents_growth](articles/081_foreign_residents_growth) |
| 082 | 在留外国人が人口の1割以上の市区町村は31。技能実習・特定技能は地方に、留学は東京に多く住んでいた | [082_foreign_residents_where](articles/082_foreign_residents_where) |
| 083 | 1人1日のごみは18年で23%減った。でもリサイクル率は2010年度の20.8%をピークに下がっていた | [083_waste_recycling](articles/083_waste_recycling) |
| 084 | 町村ほど家庭ごみが多く、都市ほど事業系ごみが多い。合計はほぼ同じで、処理費は1トン6.4万円に上がっていた | [084_waste_cost](articles/084_waste_cost) |
| 085 | 食品の値上げで、米は2倍でも量は減らず、魚や果物は大きく減った。家計調査の127品目で見る | [085_food_price_quantity](articles/085_food_price_quantity) |
| 086 | 同じ値上げでも、年収の低い世帯は支出の6.3%、高い世帯は3.6%。エンゲル係数は34.9%まで上がった | [086_engel_income](articles/086_engel_income) |
| 087 | 実質賃金は1997年から18%下がった。でも1時間当たりでは3%減。物価と同じくらい「働く時間」が効いていた | [087_real_wage](articles/087_real_wage) |
| 088 | ボーナスは基本給の3倍振れる。2009年は製造業、2020年は宿泊・飲食と娯楽で大きく減った | [088_bonus_volatility](articles/088_bonus_volatility) |
| 089 | 建設躯体工事は7.9倍、一般事務は0.34倍。人手不足は職業で20倍以上の差があった | [089_job_openings_occupation](articles/089_job_openings_occupation) |
| 090 | 都道府県の求人倍率の差は50年で縮んだが、2019年から止まった。東京都は働く場所で数えると42位 | [090_job_openings_pref](articles/090_job_openings_pref) |
| 091 | 新築の家は1戸当たり97.5㎡から76.8㎡に。持家は1996年の141㎡から112㎡へ小さくなっていた | [091_housing_floor_area](articles/091_housing_floor_area) |
| 092 | 木造の割合は43%に戻った。でも住宅以外の木造は8%どまりで、伸びたのは病院・診療所と事務所だった | [092_wooden_nonresidential](articles/092_wooden_nonresidential) |
| 093 | 裸眼視力1.0未満の小学生は46年で18%→36%に倍増。高校生は7割を超えた | [093_eyesight](articles/093_eyesight) |
| 094 | 17歳の身長は1994年度が最高で、30年ほぼ横ばい。それでも中学生男子は今が一番高い | [094_height](articles/094_height) |
| 095 | 就業者は13年で550万人増えた。増えたのは女性と65歳以上で、人口が減る分を「働く人の割合」が912万人押し上げた | [095_employment_growth](articles/095_employment_growth) |
| 096 | 非正規の割合はほとんどの年齢で下がっていた。全体が横ばいに見えるのは、65歳以上の働く人が増えたから | [096_nonregular_share](articles/096_nonregular_share) |
| 097 | ドラッグストアの売上は11年で約1.9倍。伸びの中心は食品で、売上の3分の1を超えた | [097_drugstore](articles/097_drugstore) |
| 098 | 2019年より売上が多いのはスーパーやドラッグストア。でもコロナ前の伸び方には、コンビニとドラッグストアが届いていなかった | [098_retail_recovery](articles/098_retail_recovery) |
| 099 | 日本の海面は約40年で10cm上がった。でも120年で見ると、1950年頃にも今と同じくらい高い時期があった | [099_sea_level](articles/099_sea_level) |
| 100 | 日本近海の海水温は世界平均の約2倍の速さで上がっていた。同じ期間でそろえると2.0倍、最近40年は2.3倍 | [100_sea_temperature](articles/100_sea_temperature) |
| 101 | 米は1人年114.9kgから53.4kgへ半分以下に。肉は6.6倍、牛乳・乳製品は4.1倍になった60年余り | [101_food_balance](articles/101_food_balance) |
| 102 | 食料自給率73%→38%の低下、半分強は「米を食べなくなった」など食べるものの変化だった | [102_food_self_sufficiency](articles/102_food_self_sufficiency) |
| 103 | 大人の1日の歩数は20年で男性7%・女性12%減った。減ったのは20〜60代で、70歳以上はほぼ横ばい | [103_daily_steps](articles/103_daily_steps) |
| 104 | 睡眠6時間未満は50代で5割に。朝食を抜く40〜50代男性は、若いころから抜いていた世代だった | [104_sleep_breakfast](articles/104_sleep_breakfast) |
| 105 | 牛乳1Lは那覇364円・長岡214円。同じ品目の値段の都市差は、16年でははっきり縮まっていなかった | [105_price_city_gap](articles/105_price_city_gap) |
| 106 | 値上げは「幅」より「回数」が増えた。外食の値上げ頻度は2.7倍、牛乳は98.8%の市が同じ月に上げた | [106_price_increase_sync](articles/106_price_increase_sync) |
| 107 | 外国人の宿泊は2017年までは地方に広がった。でもコロナ後は東京に集まり、地方の割合は2011年並みの34% | [107_inbound_regional](articles/107_inbound_regional) |
| 108 | 宿泊者数の回復、日本人は29都道府県でまだ2019年以下。外国人は1.6倍でも、京都・東北は日本人が戻らない | [108_accommodation_recovery](articles/108_accommodation_recovery) |
| 109 | 外国人の入国は羽田と福岡が2019年の1.7倍に。成田の割合は38%から28%へ下がった | [109_immigration_airports](articles/109_immigration_airports) |
| 110 | 東南アジアは12月、欧米は4月と10月、韓国は1月。外国人が日本に来る季節は国籍で4つの形に分かれた | [110_immigration_seasons](articles/110_immigration_seasons) |
| 111 | 米の収量は涼しい夏に大きく落ちた。暑い夏ではほとんど落ちないが、2000年以降は豊作にもならなくなった | [111_rice_yield_summer](articles/111_rice_yield_summer) |
| 112 | 米の作付面積は1969年から55%減った。西日本ほど大きく減り、北海道・東北・北陸の割合は48%に | [112_rice_area](articles/112_rice_area) |
| 113 | さんまはピークの7%、するめいかは3%に。魚種別の漁獲量69年で、減り始めた年と増えた魚を探した | [113_fish_catch](articles/113_fish_catch) |
| 114 | ブリの漁獲で北海道の割合は2%→12%に。重心は0.8度北へ動いたが、海水温との年ごとの連動は弱かった | [114_yellowtail_north](articles/114_yellowtail_north) |
| 115 | 狩猟で獲られたクマは年400頭前後。出没が多い年度も増えず、岩手・群馬・福島で4割 | [115_bear_capture](articles/115_bear_capture) |
| 116 | 獣の捕獲は「狩猟」から「許可」へ。許可による捕獲は24年で9倍、わな猟の免状は銃を上回った | [116_deer_boar_capture](articles/116_deer_boar_capture) |
| 117 | 生活保護を受ける世帯は2017年度まで増え、その後は横ばい。半分は1人で暮らす高齢の方の世帯になった | [117_public_assistance_households](articles/117_public_assistance_households) |
| 118 | 生活保護の申請は2020年2月を底に増加。2020年4月は前年より25%多く、都道府県の差は少しずつ縮まった | [118_public_assistance_applications](articles/118_public_assistance_applications) |
| 119 | 空き家率20%以上の市区町村は159→215に。上がったのは住む人のいる住宅が減った所だった | [119_vacancy_rate](articles/119_vacancy_rate) |
| 120 | 賃貸用の空き家は大きな市、使い道のない空き家は小さな町に。使い道のない空き家は40年で3.1倍の386万戸 | [120_vacant_rental_unused](articles/120_vacant_rental_unused) |
| 121 | 子どもの体力は1980〜85年度が最高。その後5%落ちて横ばい、2019年度からもう一段下がった | [121_child_fitness](articles/121_child_fitness) |
| 122 | いまの70代前半の合計点は、20年前の60代後半とほぼ同じ。ただ握力や片足立ちは届いていない | [122_elderly_fitness](articles/122_elderly_fitness) |
| 123 | 辞める人が多い産業ほど入る人も多い（相関0.97）。転職で賃金が1割以上増えた人は15%から28%に | [123_turnover_rates](articles/123_turnover_rates) |
| 124 | 辞める理由の4分の3は「個人的理由」。女性の結婚・出産による離職は14%から3%に減った | [124_turnover_reasons](articles/124_turnover_reasons) |
| 125 | 昼夜間人口比率1位は千代田区の1,355。でも30年でほぼ半分に下がり、住む人が増えた | [125_daytime_population](articles/125_daytime_population) |
| 126 | 副業をする人は年収の低い人と高い人に多いU字型。正規は2.6%、役員・自営業主は9%前後 | [126_side_jobs](articles/126_side_jobs) |
| 127 | 物価が高い県は13年ずっと東京都。ただ家賃を除くと、2023年から北海道が1位になった | [127_regional_prices](articles/127_regional_prices) |
| 128 | ピアノは静岡県が100%、眼鏡枠は福井県が92%。1県に生産が集中する製造品は全体の1割 | [128_product_concentration](articles/128_product_concentration) |
| 129 | 住まいの不満、多いのは断熱・地震・高齢者への配慮。治安への不満は10年で半分に、断熱はほぼ変わらず | [129_housing_satisfaction](articles/129_housing_satisfaction) |
| 130 | 日本人観光客の日帰りは埼玉98%、和歌山51%。人数では9割が日帰りでも、お金では半分ほど | [130_tourism_daytrip](articles/130_tourism_daytrip) |
| 131 | 入院患者の平均年齢は60年で36歳から73歳に。4人に3人が65歳以上、それでも年齢ごとの入院は半分に | [131_inpatient_age](articles/131_inpatient_age) |
| 132 | 高齢者1人あたりの介護給付費は全国31.2万円。大阪府37.6万円、栃木県26.4万円で、差の3分の1は年齢構成で説明できた | [132_ltc_benefits](articles/132_ltc_benefits) |
| 133 | 私立小学校の学習費は公立の4.8倍。差の大部分は授業料や入学金で、公立中学生は塾代のほうが多かった | [133_school_expenses](articles/133_school_expenses) |
| 134 | 光化学オキシダントの環境基準は1,137局中1局しか達成していない。原因物質は減ったのに、濃度は上がって横ばい | [134_photochemical_oxidant](articles/134_photochemical_oxidant) |
| 135 | 竜巻の半分以上は8〜10月。いちばん多いのは9月の昼過ぎで、海の上の竜巻は10月に多かった | [135_tornado](articles/135_tornado) |
| 136 | 茶畑はピークから4割減。でも10aあたりの荒茶は増え、せん茶が減る一方で番茶と抹茶の原料などは増えていた | [136_tea](articles/136_tea) |
| 137 | 市区町村の歳出の4割は福祉（民生費）。12年で1.5倍になり、伸びが大きかったのは子どもと障害者福祉など | [137_welfare_spending](articles/137_welfare_spending) |
| 138 | 刑法犯は2021年までに7割減。減った分の8割は窃盗で、2022年からは自転車盗と詐欺が増えた | [138_crime](articles/138_crime) |
| 139 | 企業の研究者は12年で7.8万人増えた。増えた分の7割近くは製造業の外で、情報科学の研究者は2.1倍に | [139_researchers](articles/139_researchers) |
| 140 | 人口ピラミッドの裾がいちばん広かったのは1953年まで。1981年から0〜4歳は40〜44歳より少なくなった | [140_population_pyramid](articles/140_population_pyramid) |
| 141 | 賃上げ率の大企業と中小企業の差は2025年に1.5ポイントと、51年で最大。1990年代まではほぼ差がなかった | [141_wage_increase](articles/141_wage_increase) |
| 142 | エアコンは27年、薄型テレビは7年で広がった。家電と車の普及率のS字と、ピーク後に下がった品目 | [142_durable_goods](articles/142_durable_goods) |
| 143 | 内部留保は17年で2.2倍の555兆円。現預金の増加はその半分で、大企業では株式などの投資が増えていた | [143_retained_earnings](articles/143_retained_earnings) |
| 144 | 住宅の価格指数は3月に高く12月に低い。季節の差は2.8%で、取引件数も3月に25〜38%増えていた | [144_housing_price_seasonality](articles/144_housing_price_seasonality) |
| 145 | 訪日客の支出は「買物」から「宿泊」へ。中国は買物の割合が51%→37%、欧米は宿泊に4割以上を使っていた | [145_inbound_spending](articles/145_inbound_spending) |
| 146 | 診療所は15年で6%増。腎臓内科・糖尿病内科・美容外科を掲げる所は2倍に、小児科と外科は2割減っていた | [146_clinic_specialties](articles/146_clinic_specialties) |
| 147 | 通所介護は2015年度まで訪問介護の2倍の速さで増えた。コロナ後は逆転し、訪問介護のほうが伸びていた | [147_home_vs_day_care](articles/147_home_vs_day_care) |
| 148 | 小学校の先生の年齢構成は、「ふたコブ」からどう変わったか？ | [148_teacher_age](articles/148_teacher_age) |
| 149 | 川や海に比べて、湖だけ環境基準の達成率が低いのはなぜか？ | [149_lake_water_quality](articles/149_lake_water_quality) |
| 150 | 黄砂の観測日数は、2000年代から減ったのか？ | [150_yellow_sand](articles/150_yellow_sand) |
| 151 | 農業経営体は5年で22%減、石川県は36%減。経営主のいちばん多い年齢は70〜74歳になった | [151_farm_decline](articles/151_farm_decline) |
| 152 | スマホを9割以上が持つのは50代まで。60代は89%に迫り、70代68%・80歳以上33%で大きな段差があった | [152_smartphone_age](articles/152_smartphone_age) |
| 153 | 平均初婚年齢の上昇は2013〜14年頃に止まった。夫は31.1歳で横ばい、妻は11年で0.3歳だけ上がった | [153_first_marriage_age](articles/153_first_marriage_age) |
| 154 | 最低賃金の地域差は2014年度をピークに縮まった。最高÷最低は1.31倍から1.18倍に、それでも差額は195円ある | [154_minimum_wage_gap](articles/154_minimum_wage_gap) |
| 155 | 病床利用率は1〜2月が高い。ただ一番大きいのは12月末の落ち込みで、月末が土日でも約3ポイント下がる | [155_bed_occupancy_season](articles/155_bed_occupancy_season) |
| 156 | ネット販売の売上比率が高いのは航空運輸業の32%。全体では売上の1.2%で、電子商取引をする企業は4%のままだった | [156_ec_sales_by_industry](articles/156_ec_sales_by_industry) |
| 157 | よく出される飲み薬は1年で101億錠。子どもはアレルギーの薬が4割、40〜74歳の男性は糖尿病の薬がいちばん多かった | [157_drugs_by_sex_age](articles/157_drugs_by_sex_age) |
| 158 | サービス産業の売上は2023年3月にコロナ前を回復。宿泊業は2019年の118%まで伸びたが、飲食店は85%のままだった | [158_service_recovery](articles/158_service_recovery) |
| 159 | 1人あたり医療費は15年で42%増。ただ年齢別では10代が+87%、70代は+5%で、全体の伸びは高齢化によるところが大きかった | [159_medical_cost_by_age](articles/159_medical_cost_by_age) |
| 160 | 国内旅行は「日帰り化」していなかった。日帰りの割合は2014年の50%から2025年は46%に下がり、出張の日帰りが特に減った | [160_daytrip_share](articles/160_daytrip_share) |
| 161 | 特定健診の受診率は健保組合83%、市町村国保38%。15年で差は29ポイントから45ポイントに広がっていた | [161_health_checkup_rate](articles/161_health_checkup_rate) |
| 162 | 介護をしながら働く人は5年で18万人増えて365万人に。増えたのは50〜60代で、増加の8割は働く人の年齢構成の変化だった | [162_working_carers](articles/162_working_carers) |
| 163 | 調剤医療費の伸び、この5年は半分が薬局の技術料、4割が注射薬。内服薬は日数が3割伸びても1日の値段が2割下がった | [163_dispensing_costs](articles/163_dispensing_costs) |
| 164 | 学習塾の受講生は2018年から1割減。それでも売上はトレンド通りに伸び、支えたのは1人当たりの受講料だった | [164_juku_sales](articles/164_juku_sales) |
| 165 | 人口あたりの看護師は高知が最多で埼玉の2.1倍。上位10県はすべて中国・四国・九州だった | [165_nurses_by_pref](articles/165_nurses_by_pref) |
| 166 | 国内線の座席利用率は8月が最も高く、1月と4月が低い。季節の差は15ポイントで、2025年は年平均80%を超えた | [166_air_load_factor_season](articles/166_air_load_factor_season) |
| 167 | 医療費の中で割合が最も伸びた病気はがんなどの新生物で13.1%から15.0%に。循環器は20.8%から18.2%に下がった | [167_medical_cost_by_disease](articles/167_medical_cost_by_disease) |
| 168 | 産業廃棄物は年3.7億t。電気・水道業、農業、建設業がそれぞれ2割強で、種類では汚泥が42%を占めていた | [168_industrial_waste_by_industry](articles/168_industrial_waste_by_industry) |
| 169 | 外国人労働者は10年で2.4倍。製造業は1位のまま割合が31%から25%に下がり、医療・福祉は8.4倍、建設業は5.0倍になった | [169_foreign_workers_by_industry](articles/169_foreign_workers_by_industry) |
| 170 | 日本企業の海外現地法人は2021年度にASEANが中国を上回った。中国の現地法人で働く人は9年で4割減った | [170_overseas_affiliates_region](articles/170_overseas_affiliates_region) |
| 171 | 道路の交通量は2015→2021年度で5.6%減。高速道路は延びたのに1区間あたり11%減、大型車の割合は上がった | [171_road_traffic_change](articles/171_road_traffic_change) |
| 172 | 理容所はピークから25%減、美容所は60年で3.1倍。銭湯は84%減、クリーニングは58%減だった | [172_barber_beauty_salons](articles/172_barber_beauty_salons) |
| 173 | 家庭の光熱費の内訳で52都市を分けると3タイプ。灯油型の4都市は光熱費が都市ガス型の1.5倍だった | [173_household_energy_types](articles/173_household_energy_types) |
| 174 | 「3年で3割辞める」大卒は28年中27年で30%以上。高卒は50%から37%に下がり、1年目に辞める割合は減っていた | [174_three_year_turnover](articles/174_three_year_turnover) |
| 175 | ゴルフ場の利用者は2000年比95でコロナ前並み。ボウリング場は34まで減ったが、それでも2019年までの減り方の延長よりは多かった | [175_golf_bowling_users](articles/175_golf_bowling_users) |
| 176 | コンテナの港ランキングは15年でほとんど動かなかった。上位10港は2012年から同じ顔ぶれで、2024年の量は2019年より7%少ない | [176_container_ports](articles/176_container_ports) |
| 177 | 入院する人の割合の県差は、年齢をそろえても2.2倍残る。上位12県のうち10県が九州・四国・山口だった | [177_treatment_rate_age_adjusted](articles/177_treatment_rate_age_adjusted) |
| 178 | 産業廃棄物の再生利用率は2008年度から52〜55%で横ばい。汚泥を除けば9割近く、紙くずやばいじんは13年で10ポイント以上伸びた | [178_industrial_waste_recycling](articles/178_industrial_waste_recycling) |
| 179 | 外国人労働者の半分が技能実習の県もある。宮崎・青森・高知は全国の2.5倍で、東京は0.28倍だった | [179_technical_intern_specialization](articles/179_technical_intern_specialization) |
| 180 | 日本の輸出先、米国の割合は30年で27%から18%台に。中国は5%から17%になり、インドとベトナムが上位10か国に入った | [180_export_destination_ranking](articles/180_export_destination_ranking) |
| 181 | 鉄道の定期外はコロナ前を超えたのに、定期は2019年度の87%のまま。5年で約19億人分が戻っていなかった | [181_rail_commuter_recovery](articles/181_rail_commuter_recovery) |
| 182 | 人口あたりの病床数、最多の高知は神奈川の3倍。上位15のうち14が中国・四国・九州。差は療養と精神の病床で大きかった | [182_hospital_beds_west_east](articles/182_hospital_beds_west_east) |
| 183 | 日本の温室効果ガスは2013年度から25%減。減った量の37%は産業部門で、鉄鋼だけで16%。業務と家庭も4割近くを占めた | [183_ghg_sector_contribution](articles/183_ghg_sector_contribution) |
| 184 | 大卒の3年以内離職率、5人未満の事業所は58%、1,000人以上は24%。規模が10倍になるごとに約12ポイント下がり、差は20年縮まっていない | [184_turnover_by_firm_size](articles/184_turnover_by_firm_size) |
| 185 | 売上100億円以上の企業は全体の0.46%なのに、売上の7割を占める。上位1%では約77%、約8割の企業の売上は合わせて3% | [185_sales_concentration](articles/185_sales_concentration) |
| 186 | トラックの荷物、運送会社が運ぶ割合は1970年度の24%から67%に。距離をかけると88%で、自家用は平均20km余りの近場が中心だった | [186_truck_commercial_share](articles/186_truck_commercial_share) |
| 187 | 病院の外来患者は2025年も2019年の9割。静岡96から秋田84まで県で差があり、47都道府県のすべてがコロナ前に戻っていない | [187_outpatient_recovery_pref](articles/187_outpatient_recovery_pref) |
| 188 | 塾代のピークは中3で年34万円。通う割合は中3が79%で最も高いが、通う子1人の金額は高3の45万円が最も多い | [188_juku_cost_by_grade](articles/188_juku_cost_by_grade) |
| 189 | 家庭のCO2は北海道が全国の1.7倍。ただエネルギーが最も少ない沖縄も全国より多く、最少は九州。差を広げるのは電気のつくり方だった | [189_household_co2_region](articles/189_household_co2_region) |
| 190 | 黄砂の観測日は福岡が年7.5日で東京の9.5倍。東京で見えた日の7割は福岡でも観測、ただ最も西の那覇は福岡の半分以下だった | [190_yellow_sand_stations](articles/190_yellow_sand_stations) |
| 191 | 野菜の産地はどれだけ集中しているか。ばれいしょは北海道が8割、41品目のうち20品目は上位3県で半分以上だった | [191_vegetable_concentration](articles/191_vegetable_concentration) |
| 192 | 障害者の実雇用率、大企業と小さな企業の差は12年で縮まらず0.59→0.75ポイントに。法定雇用率が上がる年は大企業ほど達成割合が下がった | [192_disability_employment_size](articles/192_disability_employment_size) |
| 193 | 市区町村の稼ぎ頭は製造業が5割。全国では医療・福祉が最大でも、1,741市区町村のうち910で製造業が1位だった | [193_municipal_earning_industry](articles/193_municipal_earning_industry) |
| 194 | 大きな都市ほど自動車を使わない。人口10倍で分担率は23ポイント低いが、100万都市でも東京23区12%と仙台市50%の差があった | [194_city_size_car_share](articles/194_city_size_car_share) |
| 195 | 病院は35年で2割減。減った分の8割は100床未満の小さな病院で、150〜199床だけが増えていた | [195_hospital_bed_size](articles/195_hospital_bed_size) |
| 196 | 女性の小学校長は10年で19%から30%に。石川は58%、島根・長崎は12%で、10年前に女性の教頭が多かった県ほど今の女性校長が多い | [196_female_principals](articles/196_female_principals) |
| 197 | 騒音の苦情で工場は20年で4割減。代わりに建設業が6割増えて、いまは工事の音が騒音の苦情の4割を占める | [197_noise_complaints](articles/197_noise_complaints) |
| 198 | 日照時間の「晴れの県ランキング」は30年たってもほとんど入れ替わらない。山梨は39年中21年で1位、秋田は34年で下位5位 | [198_sunshine_rank](articles/198_sunshine_rank) |
| 199 | 主要147漁港の水揚げは、上位10港で半分近く。下位半分の73港は合わせて5%で、10年で大きな港への集中が進んだ | [199_fishing_ports](articles/199_fishing_ports) |
| 200 | 勤務間インターバル制度の導入は1,000人以上の企業で20%、30〜99人は6%。7年で差は4ポイントから14ポイントに広がった | [200_work_interval](articles/200_work_interval) |
| 201 | サービス業の売上は人数にほぼ比例。人が10倍の事業所は売上11.4倍、ただ葬儀や結婚式場は大きいほど1人あたりが下がる | [201_service_sales_scale](articles/201_service_sales_scale) |
| 202 | 分譲マンションの年収倍率は2024年度調査まで5倍台、2025年度は6.57倍に。購入資金は1年で37.7%増えた | [202_condo_income_ratio](articles/202_condo_income_ratio) |
| 203 | 埼玉県の観光客の3分の1は越谷市。上位5市で6割を占め、この割合は15年ほぼ変わらない | [203_saitama_tourism_concentration](articles/203_saitama_tourism_concentration) |
| 204 | HbA1c 6.5%以上の人は特定健診で7.26%。年齢をそろえても佐賀県8.72%、長野県6.34%と1.38倍の差 | [204_health_checkup_hba1c](articles/204_health_checkup_hba1c) |
| 205 | 図書館で1人が借りる本は年4.78冊。滋賀県は7.30冊、青森県と秋田県は2.74冊で2.7倍の差 | [205_library_loans](articles/205_library_loans) |
| 206 | 食品ロスは12年で182万トン減。事業系94万トン、家庭系88万トンとほぼ半々で、外食は2年続けて増加 | [206_food_loss](articles/206_food_loss) |
| 207 | 紫外線のピークは6月でなく7〜8月。那覇の7月は10.3と札幌の1.7倍 | [207_uv_index](articles/207_uv_index) |
| 208 | 牛乳の生産は1994年から29%減。ヨーグルトなどのはっ酵乳は5.5倍になり、牛乳の3分の1に | [208_milk_products](articles/208_milk_products) |
| 209 | 都道府県ランキングの1位は、10年で半分近く入れ替わる。334指標で1位が同じだったのは56% | [209_pref_rank_turnover](articles/209_pref_rank_turnover) |
| 210 | ストライキは1974年の5,211件から27件に。1976年から年11%ずつ減り、2003年からは年20〜50件台で横ばい | [210_strikes](articles/210_strikes) |
| 211 | 家賃を除いても、物価の地域差は2割しか縮まない。東京都は1位から3位に、北海道が1位に | [211_regional_price_ex_rent](articles/211_regional_price_ex_rent) |
| 212 | 労働分配率は景気後退期に上がる。14回中13回で上昇し、平均4.1ポイント | [212_labor_share_cycle](articles/212_labor_share_cycle) |
| 213 | 昭和54年以前のマンションは役員の47%が70歳以上。同じ築年を5年後に見ると、さらに高齢化していた | [213_condo_aging](articles/213_condo_aging) |
| 214 | 宿泊の季節の形で47都道府県を5つに分けると、山梨は8月に年平均の1.85倍、東京は1年中ほぼ平ら | [214_lodging_seasonality](articles/214_lodging_seasonality) |
| 215 | 医療費は23年で18兆円増えた。高齢化の分は57%、残りの多くは一人当たり医療費の伸び | [215_medical_cost_aging](articles/215_medical_cost_aging) |
| 216 | 要介護認定者は2007年度から1.6倍に。増えたのは軽い区分で、要介護5は1.16倍にとどまった | [216_care_levels](articles/216_care_levels) |
| 217 | 給食の自校方式は神奈川で87%、島根で1%。15年で39都道府県が自校方式の割合を減らした | [217_school_lunch_kitchens](articles/217_school_lunch_kitchens) |
| 218 | 食品ロスの2030年度目標、家庭系は今のペースなら届く。事業系はここ3年横ばいで、届くかは読み切れない | [218_food_loss_2030](articles/218_food_loss_2030) |
| 219 | 2025年の梅雨明けは8地方で1951年以降最も早かった。それでも76年で見ると、梅雨明けは早まっていない | [219_baiu_end_trend](articles/219_baiu_end_trend) |
| 220 | 養豚は1戸2.4頭から2,811頭に。2,000頭以上の経営が頭数の8割を持つが、ジニ係数はむしろ下がった | [220_livestock_scale](articles/220_livestock_scale) |
| 221 | 理想の子ども数と実際の差は、広がっていなかった。縮んだのは、理想が2.67人から2.25人に下がったから | [221_ideal_vs_actual_children](articles/221_ideal_vs_actual_children) |
| 222 | 労災でいちばん多いのは転倒で、16年で1.6倍に。60歳以上では死傷の4割が転倒だった | [222_falls_elderly_workers](articles/222_falls_elderly_workers) |
| 223 | ネットで買う品目の順位は、10年でほとんど入れ替わらなかった。大きく上がったのは出前で、21位から13位に | [223_online_shopping_rank](articles/223_online_shopping_rank) |
| 224 | 研究開発にお金をかける業種ほど、生産性は高い。でも同じ業種の中で研究開発を増やした年に、生産性が上がったわけではなかった | [224_rd_productivity](articles/224_rd_productivity) |
| 225 | 建設工事の受注は、3月にふつうの月の2倍入る。年度末の山をつくっているのは公共工事より民間の非製造業だった | [225_construction_orders_fiscal_yearend](articles/225_construction_orders_fiscal_yearend) |
| 226 | 円安が大きかった国の訪日客ほど、円で見た支出が増えた。国と年の違いを除くと、円安1%で支出は0.89%増えていた | [226_fx_inbound_spending](articles/226_fx_inbound_spending) |

## 共通の方針
- データは e-Stat などの公開データだけを使い、出典は各フォルダの README に書いています（政府標準利用規約 第2.0版などに沿って「〇〇をもとに作成者が加工して作成」）
- 各フォルダの `src/` のスクリプトは、フォルダの中の `data/` を読んで `figures/` と `results/` を作り直します
- 図の日本語フォントは Noto Sans CJK JP を使っています

コード：MIT License
