# 索引（手法別・業務の場面別）

[README](README.md) の記事（看板記事 275本＋記事の一覧 793本）を、手法と業務の場面で引けるようにした索引です。

- 題名と手法の言葉で機械的に分けたものなので、1本が複数の区分に入ることも、うまく入らないこともあります
- 「F」で始まるのは看板記事（長めの分析。多くは公開データを使う）。数字だけの番号は、短い記事（実務の型・手法の解説など。架空のデータを使うものが多い）です
- はじめて見る方は、README の「はじめに読む10本」から読んでください

## 手法別

| 手法 | 本数 |
|---|---|
| 予測・時系列 | 149 |
| 因果推論・効果検証 | 70 |
| A/B テスト・実験 | 27 |
| 統計の考え方（検定・区間・回帰） | 322 |
| 機械学習・モデル評価 | 139 |
| 顧客分析・生存分析 | 67 |
| SQL・データ処理 | 105 |
| Excel | 13 |
| 集計の定義・KPI | 138 |
| 可視化・報告・BI | 48 |
| 保険数理・リスク | 75 |
| テキスト・ネットワーク・空間 | 33 |
| 再現性・振り返り | 100 |
| その他（記述・要因分解など） | 391 |

<details><summary><b>予測・時系列</b>（149本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F02 | コロナがなかったら、赤ちゃんは何人多かったのか？ | [F02_births_counterfactual](articles/F02_births_counterfactual) |
| F04 | Go To トラベルは宿泊をどれだけ増やしたのか？ | [F04_goto_causalimpact](articles/F04_goto_causalimpact) |
| F05 | 医療費の地域差は「県」と「市町村」のどちらで決まるか？ | [F05_medical_cost_hierarchical](articles/F05_medical_cost_hierarchical) |
| F06 | 高齢化は地図の上で固まっているか？ | [F06_aging_spatial](articles/F06_aging_spatial) |
| F11 | 消費増税の「駆け込み」と「反動」はどれだけだったか？ | [F11_tax_hike_event](articles/F11_tax_hike_event) |
| F12 | 公的統計を毎月自動で更新するには？ | [F12_stats_pipeline](articles/F12_stats_pipeline) |
| F13 | 失業率を来月まで予測できるか？ | [F13_unemployment_forecast](articles/F13_unemployment_forecast) |
| F17 | 最低賃金の影響が大きかったのはどんな県か？ | [F17_minwage_causal_forest](articles/F17_minwage_causal_forest) |
| F22 | 明日の電力需要はどこまで当てられるか？ | [F22_power_demand_forecast](articles/F22_power_demand_forecast) |
| F29 | 北陸新幹線の金沢延伸で、石川県の宿泊客はどれだけ増えたか？ | [F29_shinkansen_sdid](articles/F29_shinkansen_sdid) |
| F32 | 所得の高い町と低い町で、効いている要因は同じか？ | [F32_income_quantile](articles/F32_income_quantile) |
| F36 | 全国と47都道府県の宿泊者数の予測を、足し算が合うようにそろえると？ | [F36_hierarchical_forecast](articles/F36_hierarchical_forecast) |
| F37 | 地価の予測に「この範囲に9割入る」を付けられるか？ | [F37_conformal_land_price](articles/F37_conformal_land_price) |
| F42 | 季節調整を自分でやると、公表値と同じになるか？ | [F42_seasonal_adjustment](articles/F42_seasonal_adjustment) |
| F50 | GDPの速報は、あとでどれだけ直されるのか？ | [F50_gdp_revisions](articles/F50_gdp_revisions) |
| F52 | インフルエンザは、どの県からどの県へ広がるのか？ | [F52_influenza_spread](articles/F52_influenza_spread) |
| F55 | ベイズで出生数を予測すると、予測の幅はどう変わるのか？ | [F55_births_bsts](articles/F55_births_bsts) |
| F57 | インフルエンザの流行は、SIRモデルで再現できるか？ | [F57_flu_sir](articles/F57_flu_sir) |
| F68 | 訪日客の「来る季節」は、国によっていくつの型に分かれるか？ | [F68_inbound_seasonality_clusters](articles/F68_inbound_seasonality_clusters) |
| F71 | 都道府県の所得の差は、縮まっているのか？ | [F71_income_convergence](articles/F71_income_convergence) |
| F73 | 街の人の「景気の声」は、数字より先に動くか？ | [F73_watcher_text_tone](articles/F73_watcher_text_tone) |
| F75 | 地価の地図を「なめらかに」描くと、どこまで当たるか？ | [F75_gp_land_price](articles/F75_gp_land_price) |
| F76 | 所得が高い県は、ずっと高いままか？ | [F76_income_mobility_markov](articles/F76_income_mobility_markov) |
| F77 | 今の人の流れが続くと、都道府県の人口の分布は最後にどうなるか？ | [F77_migration_markov](articles/F77_migration_markov) |
| F78 | 産業がばらけている町は、不景気に強いのか？ | [F78_industry_portfolio](articles/F78_industry_portfolio) |
| F86 | 平均寿命はこの先どこまで延びるのか？ | [F86_lee_carter_e0](articles/F86_lee_carter_e0) |
| F92 | 電力需要の「上振れ」はどこまで見込めばよいか？ | [F92_power_quantile_forecast](articles/F92_power_quantile_forecast) |
| F97 | 「前年比+1%」は、本当に増えたと言えるのか？ | [F97_sampling_error_yoy](articles/F97_sampling_error_yoy) |
| F98 | 大きな災害のあと、宿泊客はどれくらいで戻るのか？ | [F98_disaster_lodging_recovery](articles/F98_disaster_lodging_recovery) |
| F104 | 気温と電力需要の関係を、ガウス過程の時系列で読むと？ | [F104_gp_power_temperature](articles/F104_gp_power_temperature) |
| F107 | 市区町村のつながり（隣接・通勤）を使うと、予測は良くなるか？ | [F107_gcn_municipal](articles/F107_gcn_municipal) |
| F108 | 予測モデルは、地域によって外れ方が偏っていないか？ | [F108_prediction_fairness](articles/F108_prediction_fairness) |
| F109 | どのデータを集めれば、予測は早く良くなるか？ | [F109_active_learning_land_price](articles/F109_active_learning_land_price) |
| F110 | 予測モデルの設定は、どう選ぶのが効率的か？ | [F110_hyperparam_bayesopt](articles/F110_hyperparam_bayesopt) |
| F119 | 予測した記事は、その後どれだけ当たったか？ | [F119_forecast_scorecard](articles/F119_forecast_scorecard) |
| F122 | 手法ごとに、どこでつまずいたか？ | [F122_pitfalls_from_logs](articles/F122_pitfalls_from_logs) |
| F125 | 100本を超えた看板記事で、「見えなかった」はどれくらいあったか？ | [F125_null_results_review](articles/F125_null_results_review) |
| F127 | 空き家は、人口が減った分だけ増えたのか？ | [F127_vacant_houses_decomposition](articles/F127_vacant_houses_decomposition) |
| F132 | 農家は「やめる」のか「大きくなる」のか？ | [F132_farm_size_transitions](articles/F132_farm_size_transitions) |
| F133 | 輸出先は、距離と経済規模でどこまで決まるのか？ | [F133_export_gravity](articles/F133_export_gravity) |
| F134 | 再生可能エネルギーの導入は、どこで速く進んだのか？ | [F134_renewable_diffusion](articles/F134_renewable_diffusion) |
| F135 | 雨の日は、小売の売上をどれだけ動かすのか？ | [F135_rain_retail](articles/F135_rain_retail) |
| F136 | 鉄道の利用は、コロナ前にどこまで戻ったのか？ | [F136_rail_covid_recovery](articles/F136_rail_covid_recovery) |
| F137 | 郵便物は、いつ半分になるのか？ | [F137_postal_decay](articles/F137_postal_decay) |
| F141 | 特許の出願は、どの分野で地方に広がったのか？ | [F141_ip_regional_concentration](articles/F141_ip_regional_concentration) |
| F143 | 漁獲量の減り方は、魚の種類でどう違うのか？ | [F143_fish_catch_decline](articles/F143_fish_catch_decline) |
| F146 | 統計の秘匿をノイズで置き換えると、分析の答えはどれだけ変わるか？ | [F146_dp_noise_vs_suppression](articles/F146_dp_noise_vs_suppression) |
| F150 | 季節のパターンそのものは、年々変わっているのか？ | [F150_dynamic_seasonality](articles/F150_dynamic_seasonality) |
| F151 | 47都道府県の求人倍率の「同じ動き」は、いくつに分けられるか？ | [F151_pref_hierarchical_dfm](articles/F151_pref_hierarchical_dfm) |
| F152 | 統計の速報は、確報でどれだけ直されるのか？ | [F152_revision_news_noise](articles/F152_revision_news_noise) |
| F154 | 推定の「不確かさ」は、図の形で何が読み取れるかが変わるのか？ | [F154_uncertainty_viz](articles/F154_uncertainty_viz) |
| F157 | 電力需要の予測を、1年通して運用したらどうなるか？ | [F157_power_forecast_operation](articles/F157_power_forecast_operation) |
| F158 | 地価の予測モデルは、毎年作り直す必要があるのか？ | [F158_land_price_update](articles/F158_land_price_update) |
| F159 | 出生数の予測を、毎月の速報で更新すると当たり方は変わるか？ | [F159_births_nowcast](articles/F159_births_nowcast) |
| F161 | 同じデータで記事を書き直すと、結論はどれだけ変わるか？ | [F161_rewrite_old_articles](articles/F161_rewrite_old_articles) |
| F167 | 「100年に1度の大雨」は、本当に100年に1度なのか？ | [F167_return_period_heavy_rain](articles/F167_return_period_heavy_rain) |
| F168 | 猛暑日の数は、どこまで増えたと言えるか？ | [F168_extreme_heat_trend](articles/F168_extreme_heat_trend) |
| F170 | 産業の構成比を比べるとき、割合のまま回帰してよいか？ | [F170_compositional_industry_shares](articles/F170_compositional_industry_shares) |
| F172 | 生まれる日・亡くなる日は、曜日と季節でどう偏るか？ | [F172_birth_death_calendar](articles/F172_birth_death_calendar) |
| F175 | 予測モデルの精度は、どの特徴量の「おかげ」なのか？ | [F175_r2_shapley_decomposition](articles/F175_r2_shapley_decomposition) |
| F181 | 家が建つ数は、金利と人口のどちらで決まるのか？ | [F181_housing_starts_rates_population](articles/F181_housing_starts_rates_population) |
| F185 | 宅配便の個数は、どこまで通販で説明できるのか？ | [F185_parcels_online_shopping](articles/F185_parcels_online_shopping) |
| F189 | 日本人の1日は、20年でどう変わったのか？ | [F189_time_use_composition](articles/F189_time_use_composition) |
| F191 | お金の量を増やすと、貸出は増えたのか？ | [F191_money_base_lending](articles/F191_money_base_lending) |
| F193 | インターネットの通信量は、どの時間に、どれだけ増えたのか？ | [F193_internet_traffic_decomposition](articles/F193_internet_traffic_decomposition) |
| F194 | 博物館・美術館の入館者は、コロナ前に戻ったのか？ | [F194_museum_covid_recovery](articles/F194_museum_covid_recovery) |
| F195 | 夜の明かりで、地域の経済活動はどこまで分かるか？ | [F195_night_lights_gdp](articles/F195_night_lights_gdp) |
| F199 | 季節調整のやり方で、「景気の山」の時期は変わるのか？ | [F199_seasonal_adjustment_turning_points](articles/F199_seasonal_adjustment_turning_points) |
| F200 | 200本の看板記事で使ったデータと手法は、どうつながっているか？ | [F200_method_data_network](articles/F200_method_data_network) |
| F205 | 予測モデルは、作る前に何を決め、外れをいくらと見て、いつ作り直すのか？ | [F205_power_forecast_practice_part1](articles/F205_power_forecast_practice_part1) |
| F206 | 予測は、エリアと合計をどうそろえ、どう見せ、1年回すと何が起きるのか？ | [F206_power_forecast_practice_part2](articles/F206_power_forecast_practice_part2) |
| F207 | 地価はどこで上がり、駅ができると何が起きるのか？ | [F207_landprice_series_part1](articles/F207_landprice_series_part1) |
| F208 | マンションの値段は地価とどう動き、地価の予測はどこで外れ続けるのか？ | [F208_landprice_series_part2](articles/F208_landprice_series_part2) |
| F231 | 売上の予測は、何か月先まで役に立つのか？ | [F231_sales_forecast_horizon](articles/F231_sales_forecast_horizon) |
| F232 | 店の種類ごとの予測と全体の予測を、どうそろえるか？ | [F232_hierarchical_retail_reconciliation](articles/F232_hierarchical_retail_reconciliation) |
| F235 | 在庫はどれだけ持てばよいのか？ | [F235_inventory_newsvendor](articles/F235_inventory_newsvendor) |
| F239 | 広告費は、売上にどれだけ効いているのか？ | [F239_marketing_mix_model](articles/F239_marketing_mix_model) |
| F240 | キャンペーンの効果を、比べる相手がないときにどう測るか？ | [F240_campaign_effect_no_control](articles/F240_campaign_effect_no_control) |
| F241 | 顧客はどれくらいで離れていくのか？ | [F241_customer_churn_survival](articles/F241_customer_churn_survival) |
| F242 | 毎日の KPI の「いつもと違う」を、どう自動で知らせるか？ | [F242_kpi_anomaly_alerts](articles/F242_kpi_anomaly_alerts) |
| F245 | 1つの依頼に、1時間でどこまで答えられるか？ | [F245_one_hour_request](articles/F245_one_hour_request) |
| F246 | 分析担当として最初にやること：KPI を決める（業務の再現：架空の会社で） シリーズ③の1本目。架空の食品スーパー「サン | [F246_kpi_definitions_fictional_retail](articles/F246_kpi_definitions_fictional_retail) |
| F252 | 来期の予算のための需要予測（業務の再現：架空の会社で） シリーズ③の7本目。架空の食品スーパー「サンプルマート（架空）」 | [F252_budget_forecast_fictional_retail](articles/F252_budget_forecast_fictional_retail) |
| F255 | 1年の分析業務を振り返る（業務の再現：架空の会社で） シリーズ③の10本目・最後。架空の食品スーパー「サンプルマート（架 | [F255_year_review_fictional_retail](articles/F255_year_review_fictional_retail) |
| F257 | 労働経済白書の「賃上げが広がった」は、どのデータでどこまで言えるのか？ | [F257_wage_spillover_whitepaper](articles/F257_wage_spillover_whitepaper) |
| F258 | 「実質賃金○か月連続マイナス」は、どの物価で割るかで変わるのか？ | [F258_real_wage_deflator_streak](articles/F258_real_wage_deflator_streak) |
| F259 | 需要予測の外れは、在庫と欠品のどちらに効かせるべきか？ | [F259_forecast_error_inventory_cost](articles/F259_forecast_error_inventory_cost) |
| F263 | 比べる相手がないとき、何を対照にするか？ | [F263_control_choice_nationwide_policy](articles/F263_control_choice_nationwide_policy) |
| F265 | 少子化対策の「2025年の数値目標」は、決めた時点のペースで届くと読めたのか？ | [F265_policy_targets_pace](articles/F265_policy_targets_pace) |
| F277 | 最低賃金の審議会資料にある指標で、上げ幅はどこまで説明できるか？ | [F277_minimum_wage_council_indicators](articles/F277_minimum_wage_council_indicators) |
| F278 | 「空き家が過去最多」は、住宅の数が増えた分を除くとどうか？ | [F278_vacant_record_stock_vs_rate](articles/F278_vacant_record_stock_vs_rate) |
| F293 | 毎月の数字の「おかしい」を、どう自動で見つけるか？ | [F293_monthly_anomaly_public_stats](articles/F293_monthly_anomaly_public_stats) |
| F294 | 介護の費用は、2040年度にどこまで増えるのか？ | [F294_care_cost_2040_assumptions](articles/F294_care_cost_2040_assumptions) |
| 020 | 失業率は何か月先まで予測できるか？ | [020_unemployment_sarima](articles/020_unemployment_sarima) |
| 036 | 日銀短観の「先行き」は当たるのか？ | [036_tankan_forecast](articles/036_tankan_forecast) |
| 110 | 東南アジアは12月、欧米は4月と10月、韓国は1月。外国人が日本に来る季節は国籍で4つの形に分かれた | [110_immigration_seasons](articles/110_immigration_seasons) |
| 144 | 住宅の価格指数は3月に高く12月に低い。季節の差は2.8%で、取引件数も3月に25〜38%増えていた | [144_housing_price_seasonality](articles/144_housing_price_seasonality) |
| 166 | 国内線の座席利用率は8月が最も高く、1月と4月が低い。季節の差は15ポイントで、2025年は年平均80%を超えた | [166_air_load_factor_season](articles/166_air_load_factor_season) |
| 214 | 宿泊の季節の形で47都道府県を5つに分けると、山梨は8月に年平均の1.85倍、東京は1年中ほぼ平ら | [214_lodging_seasonality](articles/214_lodging_seasonality) |
| 232 | 前年同月比と12か月移動平均は、SQL のウィンドウ関数だけで出せる。ただし月が1つ抜けると、LAG は12か月分の前年 | [232_sql_window_yoy_moving_avg](articles/232_sql_window_yoy_moving_avg) |
| 248 | 日本人の宿泊で比べると、観光客の多い宿は出張客の多い宿より季節の山が2.6倍大きい。8月は年平均の1.56倍から1.41 | [248_lodging_seasonality_purpose](articles/248_lodging_seasonality_purpose) |
| 262 | 真夏日になる最初の日は、1931〜60年と1996〜2025年の平均を比べると11日早くなった。10地点の平均で10年に | [262_first_hot_day_trend](articles/262_first_hot_day_trend) |
| 272 | 毎月の数字は、前月比・前年同月比・季節調整のどれで読むか？ | [272_seasonal_adjust_monthly](articles/272_seasonal_adjust_monthly) |
| 274 | 季節の山がいちばん大きいのは電気・情報通信機械で、3月と8月の差は42ポイント。14業種のうち8業種が3月に山を迎え、石 | [274_seasonal_amplitude_by_industry](articles/274_seasonal_amplitude_by_industry) |
| 277 | 製造業の生産の見込みは、94%の月で実績より高かった。平均の外れは−2.8%で、機械の業種ほど大きい。過去の外れの平均だ | [277_production_forecast_accuracy](articles/277_production_forecast_accuracy) |
| 278 | KPI カードの矢印は、何と比べて付けるか？ | [278_kpi_card_comparison](articles/278_kpi_card_comparison) |
| 286 | 予測モデルは、線形回帰と勾配ブースティングのどちらから始めるか？ | [286_linear_vs_gbm_first](articles/286_linear_vs_gbm_first) |
| 296 | 需要予測の当たり外れを、毎週どう見張るか？ | [296_forecast_error_control_chart](articles/296_forecast_error_control_chart) |
| 310 | Kaggle：アンサンブルは、何本混ぜると効かなくなるのか？ | [310_kaggle_ensemble_size](articles/310_kaggle_ensemble_size) |
| 361 | 予測の良し悪しは、物差しを変えるとどれだけ順位が入れ替わるのか？ | [361_forecast_metric_ranking](articles/361_forecast_metric_ranking) |
| 362 | 時系列をばらばらに分けて確かめると、予測の精度をどれだけ甘く見積もるのか？ | [362_shuffled_cv_time_series](articles/362_shuffled_cv_time_series) |
| 363 | たまにしか売れない商品の需要は、どの方法で予測するのがよいか？ | [363_intermittent_demand_methods](articles/363_intermittent_demand_methods) |
| 377 | 季節のあるデータで「施策の前後」を比べると、効果0でもどれだけ差が出るのか？ | [377_before_after_seasonal_false_effect](articles/377_before_after_seasonal_false_effect) |
| 391 | 週の波と年の波が重なる日次データは、どう分ければ元の波に戻るのか？ | [391_two_seasonalities_daily_decomposition](articles/391_two_seasonalities_daily_decomposition) |
| 394 | 似た変数を2つ入れた回帰は、係数の符号がどれくらい逆になるのか？ | [394_collinearity_sign_flips](articles/394_collinearity_sign_flips) |
| 410 | 売れ筋を A・B・C に分ける分析は、期間と区切りでどれだけ入れ替わるのか？ | [410_abc_analysis_period_cutoffs](articles/410_abc_analysis_period_cutoffs) |
| 415 | 月の途中の実績から、月末の着地をどう見込むか？ | [415_month_end_landing_forecast](articles/415_month_end_landing_forecast) |
| 430 | 同じ仕入れと販売でも、在庫の評価の方法で、月の粗利はどれだけ違うのか？ | [430_inventory_valuation_methods](articles/430_inventory_valuation_methods) |
| 432 | 死亡率の将来の下がり方を過去から延ばす方法は、正解の分かるデータでどれだけ当たるのか？ | [432_lee_carter_known_truth](articles/432_lee_carter_known_truth) |
| 435 | 対数に直して回帰した予測を元に戻すと、合計はどれだけ小さく出るのか？ | [435_log_retransformation_bias](articles/435_log_retransformation_bias) |
| 442 | 移動平均でならすと、向きが変わったことに気づくのは何日遅れるのか？ | [442_moving_average_turn_delay](articles/442_moving_average_turn_delay) |
| 448 | 曲線の次数を上げると、データの外の予測はどれだけ暴れるのか？ | [448_polynomial_degree_extrapolation](articles/448_polynomial_degree_extrapolation) |
| 460 | 予測に「答えが漏れた列」が混ざると、確かめの成績はどれだけ良く見え、本番でどれだけ落ちるのか？ | [460_target_leakage_validation](articles/460_target_leakage_validation) |
| 470 | めったに起きない出来事の予測は、正解率で測るとどれだけ良く見えるのか？ | [470_rare_event_accuracy_paradox](articles/470_rare_event_accuracy_paradox) |
| 509 | 起きる割合が学習のときから変わると、0.5で切る予測は何件を見逃すのか？ | [509_prior_shift_threshold](articles/509_prior_shift_threshold) |
| 529 | 月別の事故件数を1年分だけで見ると、季節の山は偶然と見分けられるのか？ | [529_monthly_seasonality_small_counts](articles/529_monthly_seasonality_small_counts) |
| 546 | 2つの系列のずらし幅を0〜12か月で動かして最も強い相関を選ぶと、関係がなくても相関はどれだけ高く出るのか？ | [546_lag_search_spurious_corr](articles/546_lag_search_spurious_corr) |
| 549 | 自己相関のある日次データで、ふつうのブートストラップの95%区間は、正解を何%含むのか？ | [549_block_bootstrap_coverage](articles/549_block_bootstrap_coverage) |
| 558 | 予測確率が「30%」と出た人のうち、本当に起きるのは何%なのか？ | [558_probability_calibration](articles/558_probability_calibration) |
| 576 | 時系列のデータをランダムに分けて確かめると、時間の順に分けた場合より成績はどれだけ良く見えるのか？ | [576_random_vs_time_split](articles/576_random_vs_time_split) |
| 587 | 同じテスト用データでモデルの調整を何度もくり返すと、テストの成績はどれだけ楽観的になるのか？ | [587_test_set_reuse](articles/587_test_set_reuse) |
| 588 | 散らばりが水準で変わるデータで、予測の区間を「残差の標準偏差×2」で作ると、何%の回が外れるのか？ | [588_prediction_interval_heteroscedastic](articles/588_prediction_interval_heteroscedastic) |
| 596 | 小さい契約群の実績を全体の平均とどう混ぜるか？ | [596_buhlmann_credibility](articles/596_buhlmann_credibility) |
| 618 | 起きる割合が1%のとき、ROC の AUC と PR の AUC では、予測の良し悪しの見え方はどれだけ違うのか？ | [618_roc_vs_pr_auc_imbalance](articles/618_roc_vs_pr_auc_imbalance) |
| 623 | 差分の取り込みを「更新日時が前回より後」で行うと、何件が取りこぼされるのか？ | [623_incremental_load_updated_at](articles/623_incremental_load_updated_at) |
| 636 | 件数が少なく変数が多いとき、リッジ回帰はふつうの回帰より予測の誤差をどれだけ減らすのか？ | [636_ridge_vs_ols_small_n](articles/636_ridge_vs_ols_small_n) |
| 649 | 指数平滑の α を大きくするか小さくするかで、水準が変わったときの追いつき方と平時の誤差はどう入れ替わるのか？ | [649_exp_smoothing_alpha](articles/649_exp_smoothing_alpha) |
| 659 | ARIMA の次数を AIC で選ぶと、本当の次数を何%で当て、予測はどれだけ悪くなるのか？ | [659_arima_order_selection](articles/659_arima_order_selection) |
| 660 | 回帰の「平均の区間」を新しい1件の予測の区間と取り違えると、何%の回が外れるのか？ | [660_ci_vs_prediction_interval](articles/660_ci_vs_prediction_interval) |
| 663 | ウィンドウ関数の PARTITION BY を書き忘れると、店ごとの累計や順位はどれだけ狂うのか？ | [663_window_partition_missing](articles/663_window_partition_missing) |
| 697 | ダミー変数の基準のカテゴリを変えると、係数と有意の見え方はどれだけ変わるのか？ | [697_reference_category](articles/697_reference_category) |
| 708 | 誤差に自己相関のある時系列で回帰すると、ふつうの標準誤差は何倍小さく出るのか？ | [708_autocorrelated_errors_se](articles/708_autocorrelated_errors_se) |
| 724 | 日次の売上に7日以外の幅の移動平均をかけると、曜日の波はどれだけ残るのか？ | [724_moving_avg_window_weekday](articles/724_moving_avg_window_weekday) |
| 728 | 決定木を学習データを少し入れ替えて作り直すと、最初の分かれ目の変数は何%で入れ替わるのか？ | [728_tree_instability](articles/728_tree_instability) |
| 749 | もともと定常な系列を差分にしてから予測すると、予測の誤差はどれだけ悪くなるのか？ | [749_over_differencing](articles/749_over_differencing) |
| 760 | 欠けた値を「-999」で埋めたまま回帰すると、係数はどれだけずれるのか？ | [760_sentinel_value_regression](articles/760_sentinel_value_regression) |
| 767 | カテゴリを1・2・3の数にして線形回帰に入れると、ダミー変数と比べて予測はどれだけ悪くなるのか？ | [767_label_encoding_linear](articles/767_label_encoding_linear) |
| 768 | 強く相関する変数があるとき、部分依存の図はどれだけ本当の効き方とずれるのか？ | [768_pdp_correlated_features](articles/768_pdp_correlated_features) |
| 799 | 季節の波を月のダミー変数で表すか、フーリエ項で表すかで、予測の誤差はどれだけ違うのか？ | [799_fourier_vs_dummy_seasonality](articles/799_fourier_vs_dummy_seasonality) |

</details>

<details><summary><b>因果推論・効果検証</b>（70本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F01 | 最低賃金の引き上げは、雇用を減らしたのか？ | [F01_minimum_wage_did](articles/F01_minimum_wage_did) |
| F02 | コロナがなかったら、赤ちゃんは何人多かったのか？ | [F02_births_counterfactual](articles/F02_births_counterfactual) |
| F04 | Go To トラベルは宿泊をどれだけ増やしたのか？ | [F04_goto_causalimpact](articles/F04_goto_causalimpact) |
| F11 | 消費増税の「駆け込み」と「反動」はどれだけだったか？ | [F11_tax_hike_event](articles/F11_tax_hike_event) |
| F14 | コンパクトシティの計画を作った市町村で、中心部の人口密度は保てたのか？ | [F14_compact_city_psm_did](articles/F14_compact_city_psm_did) |
| F17 | 最低賃金の影響が大きかったのはどんな県か？ | [F17_minwage_causal_forest](articles/F17_minwage_causal_forest) |
| F26 | 政策の効果を見つけるには、何県・何年のデータが要るのか？ | [F26_power_simulation](articles/F26_power_simulation) |
| F29 | 北陸新幹線の金沢延伸で、石川県の宿泊客はどれだけ増えたか？ | [F29_shinkansen_sdid](articles/F29_shinkansen_sdid) |
| F31 | 60歳・65歳で、働く人はどれだけ減るのか？ | [F31_retirement_rdd](articles/F31_retirement_rdd) |
| F33 | 人の移動は距離でどれだけ減るのか？ | [F33_migration_gravity](articles/F33_migration_gravity) |
| F39 | 物価・賃金・金利は、どれがどれを動かしているのか？ | [F39_causal_discovery_macro](articles/F39_causal_discovery_macro) |
| F46 | 雇用が増えた町に、人は集まったのか？ | [F46_bartik_iv](articles/F46_bartik_iv) |
| F48 | ガソリンが10%上がると、買う量は何%減るか？ | [F48_gasoline_elasticity](articles/F48_gasoline_elasticity) |
| F65 | 医師が多い県ほど、平均寿命は長いのか？ | [F65_doctors_life_dag](articles/F65_doctors_life_dag) |
| F73 | 街の人の「景気の声」は、数字より先に動くか？ | [F73_watcher_text_tone](articles/F73_watcher_text_tone) |
| F81 | 通勤で町の外へ出る人が多いほど、子どもは少ないのか？ | [F81_commute_gps](articles/F81_commute_gps) |
| F88 | 携帯料金の値下げは、物価をどれだけ下げたか？ | [F88_mobile_fee_rdit](articles/F88_mobile_fee_rdit) |
| F95 | 新幹線の効果は、隣の県にもこぼれたのか？ | [F95_shinkansen_spillover](articles/F95_shinkansen_spillover) |
| F98 | 大きな災害のあと、宿泊客はどれくらいで戻るのか？ | [F98_disaster_lodging_recovery](articles/F98_disaster_lodging_recovery) |
| F100 | 同じ問いを5つの手法で分析すると、答えはそろうのか？ | [F100_five_methods_one_question](articles/F100_five_methods_one_question) |
| F108 | 予測モデルは、地域によって外れ方が偏っていないか？ | [F108_prediction_fairness](articles/F108_prediction_fairness) |
| F120 | 2025年国勢調査で、記事の結論は変わったか？ | [F120_census2025_update](articles/F120_census2025_update) |
| F121 | 「最低賃金と雇用」に、4本の記事はどう答えたか？ | [F121_minwage_methods_review](articles/F121_minwage_methods_review) |
| F122 | 手法ごとに、どこでつまずいたか？ | [F122_pitfalls_from_logs](articles/F122_pitfalls_from_logs) |
| F125 | 100本を超えた看板記事で、「見えなかった」はどれくらいあったか？ | [F125_null_results_review](articles/F125_null_results_review) |
| F145 | ごみの量は、有料化のあとに減ったのか？ | [F145_waste_fee_did](articles/F145_waste_fee_did) |
| F155 | 分析の手順を変えると、答えはどこまで変わるか？ | [F155_multiverse](articles/F155_multiverse) |
| F156 | 最低賃金の効果は、地域の「賃金の低さ」で違うのか？ | [F156_minwage_bite_heterogeneity](articles/F156_minwage_bite_heterogeneity) |
| F166 | 公的統計の数字は、ベンフォードの法則に従っているか？ | [F166_benford_public_stats](articles/F166_benford_public_stats) |
| F184 | 空の便は、新幹線の開業でどれだけ減ったのか？ | [F184_air_shinkansen_did](articles/F184_air_shinkansen_did) |
| F191 | お金の量を増やすと、貸出は増えたのか？ | [F191_money_base_lending](articles/F191_money_base_lending) |
| F200 | 200本の看板記事で使ったデータと手法は、どうつながっているか？ | [F200_method_data_network](articles/F200_method_data_network) |
| F201 | 最低賃金は誰に届き、雇用をどれだけ動かしたのか？ | [F201_minimum_wage_series_part1](articles/F201_minimum_wage_series_part1) |
| F204 | 出生の支援策は、結婚・第1子・第2子のどこに効いたのか？ | [F204_births_marriage_series_part2](articles/F204_births_marriage_series_part2) |
| F207 | 地価はどこで上がり、駅ができると何が起きるのか？ | [F207_landprice_series_part1](articles/F207_landprice_series_part1) |
| F234 | 価格を1%上げると、買われる量は何%減るのか？ | [F234_price_elasticity_practice](articles/F234_price_elasticity_practice) |
| F238 | 前の期間のデータを使うと、テストはどれだけ早く終わるか？ | [F238_ab_test_cuped](articles/F238_ab_test_cuped) |
| F240 | キャンペーンの効果を、比べる相手がないときにどう測るか？ | [F240_campaign_effect_no_control](articles/F240_campaign_effect_no_control) |
| F249 | ダッシュボードを作る（業務の再現：架空の会社で） シリーズ③の続き。F246 の KPI 定義 v1 と F247 の  | [F249_powerbi_dashboard_fictional_retail](articles/F249_powerbi_dashboard_fictional_retail) |
| F251 | 販促の効果を測る（業務の再現：架空の会社で） シリーズ③の6本目。F247 の mart の架空の食品スーパー「サンプル | [F251_promo_effect_fictional_retail](articles/F251_promo_effect_fictional_retail) |
| F255 | 1年の分析業務を振り返る（業務の再現：架空の会社で） シリーズ③の10本目・最後。架空の食品スーパー「サンプルマート（架 | [F255_year_review_fictional_retail](articles/F255_year_review_fictional_retail) |
| F262 | 「出生数が過去最少」は、女性の人口の減少でどこまで説明できるか？ | [F262_births_record_low_decomposition](articles/F262_births_record_low_decomposition) |
| F263 | 比べる相手がないとき、何を対照にするか？ | [F263_control_choice_nationwide_policy](articles/F263_control_choice_nationwide_policy) |
| F270 | 「訪日客が過去最多」は、1人あたりの支出で見ても最多か？ | [F270_inbound_record_per_capita](articles/F270_inbound_record_per_capita) |
| F271 | 見られるダッシュボードと、見られないダッシュボードの違いは何か？ | [F271_dashboard_answer_cost](articles/F271_dashboard_answer_cost) |
| F276 | 地震保険の付帯率は、地震のあとにどれだけ上がって戻るのか？ | [F276_earthquake_insurance_after_quakes](articles/F276_earthquake_insurance_after_quakes) |
| F278 | 「空き家が過去最多」は、住宅の数が増えた分を除くとどうか？ | [F278_vacant_record_stock_vs_rate](articles/F278_vacant_record_stock_vs_rate) |
| 029 | コロナで東京への人の流れはどれだけ減ったか？ | [029_covid_tokyo_synth](articles/029_covid_tokyo_synth) |
| 224 | 研究開発にお金をかける業種ほど、生産性は高い。でも同じ業種の中で研究開発を増やした年に、生産性が上がったわけではなかった | [224_rd_productivity](articles/224_rd_productivity) |
| 267 | 相関を因果だと思いかけたとき、どう止めたか？ | [267_correlation_not_causation](articles/267_correlation_not_causation) |
| 268 | 差の差・回帰不連続・合成コントロールを、どう選んできたか？ | [268_causal_design_choice](articles/268_causal_design_choice) |
| 278 | KPI カードの矢印は、何と比べて付けるか？ | [278_kpi_card_comparison](articles/278_kpi_card_comparison) |
| 365 | 似た相手を選んで比べる方法は、測っていない違いがあるとどこまで外れるのか？ | [365_matching_unmeasured_confounder](articles/365_matching_unmeasured_confounder) |
| 414 | 「期首＋増加−減少＝期末」の照合は、どんな誤りを見つけ、何を見逃すのか？ | [414_roll_forward_reconciliation](articles/414_roll_forward_reconciliation) |
| 497 | 重みで偏りを直す方法は、重みが極端なとき、本当は1.0の効果をどこまで外して見積もるのか？ | [497_ipw_extreme_weights](articles/497_ipw_extreme_weights) |
| 514 | 入庫と出庫の記録が遅れて届くと、在庫が一時的にマイナスになる日は何日あるのか？ | [514_inventory_record_delay_negative](articles/514_inventory_record_delay_negative) |
| 580 | 傾向スコアで重みを付けるとき、極端な重みを切り詰めると、推定の偏りとばらつきはどう変わるのか？ | [580_ipw_weight_trimming](articles/580_ipw_weight_trimming) |
| 620 | 取引の金額の先頭の数字は、ベンフォードの法則にどれだけ従い、入力の偏りをどこまで見つけられるのか？ | [620_benford_first_digit](articles/620_benford_first_digit) |
| 640 | 傾向スコアのマッチングで、キャリパーの幅を変えると、効果の推定はどう変わるのか？ | [640_psm_caliper](articles/640_psm_caliper) |
| 646 | 差の差で、前の期間の傾きが少し違うと、効果の推定はどれだけずれ、事前の確認で何%見抜けるのか？ | [646_did_parallel_trends_violation](articles/646_did_parallel_trends_violation) |
| 647 | 回帰不連続で、境目のまわりの幅を変えると、効果の推定の偏りとばらつきはどう入れ替わるのか？ | [647_rd_bandwidth](articles/647_rd_bandwidth) |
| 648 | 効きの弱い操作変数を使うと、推定はどれだけふつうの回帰の側に引っぱられるのか？ | [648_weak_instrument](articles/648_weak_instrument) |
| 665 | 会員カードを出した客だけで客単価を見ると、店全体の客単価よりどれだけ高く出るのか？ | [665_member_card_spend_bias](articles/665_member_card_spend_bias) |
| 688 | 店の固定効果だけ入れて、年ごとの流れを入れないと、施策の効果はどれだけずれるのか？ | [688_panel_time_effects](articles/688_panel_time_effects) |
| 719 | 施策の開始時期が店ごとにずれ、効果が時間とともに大きくなるとき、ふつうの二方向固定効果の推定はどれだけずれるのか？ | [719_staggered_did_twfe](articles/719_staggered_did_twfe) |
| 720 | 2つの系列が同じ原因で動き、片方が遅れて反応するとき、グレンジャー因果の検定は何%で「因果あり」と言うのか？ | [720_granger_common_driver](articles/720_granger_common_driver) |
| 737 | 施策の効き道になる変数を回帰に入れると、施策の効果はどれだけ小さく出るのか？ | [737_mediator_adjustment](articles/737_mediator_adjustment) |
| 770 | 傾向スコアか結果のモデルのどちらかがまちがっているとき、二重に頑健な推定はどれだけずれるのか？ | [770_doubly_robust](articles/770_doubly_robust) |
| 776 | 差の差で対照を1店だけ選ぶと、施策の効果の推定はどれだけ振れるのか？ | [776_single_control_did](articles/776_single_control_did) |
| F296 | 最低賃金の差の差は、前提をどこまで確かめられるのか？ | [F296_minimum_wage_did_assumptions](articles/F296_minimum_wage_did_assumptions) |

</details>

<details><summary><b>A/B テスト・実験</b>（27本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F15 | 県境をまたぐと最低賃金が違う。隣どうしの町で雇用は違ったか？ | [F15_border_minwage](articles/F15_border_minwage) |
| F26 | 政策の効果を見つけるには、何県・何年のデータが要るのか？ | [F26_power_simulation](articles/F26_power_simulation) |
| F121 | 「最低賃金と雇用」に、4本の記事はどう答えたか？ | [F121_minwage_methods_review](articles/F121_minwage_methods_review) |
| F125 | 100本を超えた看板記事で、「見えなかった」はどれくらいあったか？ | [F125_null_results_review](articles/F125_null_results_review) |
| F156 | 最低賃金の効果は、地域の「賃金の低さ」で違うのか？ | [F156_minwage_bite_heterogeneity](articles/F156_minwage_bite_heterogeneity) |
| F164 | 図をどう作ると、読まれ方が変わったか？ | [F164_figures_and_reads](articles/F164_figures_and_reads) |
| F167 | 「100年に1度の大雨」は、本当に100年に1度なのか？ | [F167_return_period_heavy_rain](articles/F167_return_period_heavy_rain) |
| F177 | 「差がある」は、並べ替えで確かめるとどうなるか？ | [F177_permutation_tests](articles/F177_permutation_tests) |
| F198 | 調査は、何人に聞けば足りるのか？ | [F198_sample_size_planning](articles/F198_sample_size_planning) |
| F236 | A/B テストは、何人集めれば「差」が分かるのか？ | [F236_ab_test_sample_size](articles/F236_ab_test_sample_size) |
| F237 | A/B テストを途中で見ると、何がまずいのか？ | [F237_ab_test_peeking_sequential](articles/F237_ab_test_peeking_sequential) |
| F238 | 前の期間のデータを使うと、テストはどれだけ早く終わるか？ | [F238_ab_test_cuped](articles/F238_ab_test_cuped) |
| F239 | 広告費は、売上にどれだけ効いているのか？ | [F239_marketing_mix_model](articles/F239_marketing_mix_model) |
| F267 | 売上の目標を、客数と客単価の目標にどう分けるか？ | [F267_kpi_target_allocation_cvs](articles/F267_kpi_target_allocation_cvs) |
| F288 | 損害額の分布の「裾の重さ」は、データの量でどこまで見分けられるか？ | [F288_tail_heaviness_sample_size](articles/F288_tail_heaviness_sample_size) |
| 271 | A/B テストの結果を、意思決定する人にどう伝えるか？ | [271_ab_test_reporting](articles/271_ab_test_reporting) |
| 539 | 必要な人数を、過去の小さな調査のばらつきから計算すると、本番で差を見つける力はどれだけ足りなくなるのか？ | [539_pilot_sd_power_shortfall](articles/539_pilot_sd_power_shortfall) |
| 586 | 裾の重いデータで平均の差を比べると、t検定と順位の検定で検出力はどれだけ違うのか？ | [586_ttest_vs_rank_heavy_tails](articles/586_ttest_vs_rank_heavy_tails) |
| 607 | A/B テストを毎日のぞいて「差あり」が出た日に止めると、効果が0でも何%で差ありになるのか？ | [607_ab_test_peeking](articles/607_ab_test_peeking) |
| 621 | A/B テストの割り付けが 50:50 からずれていることに、何人集まれば気づけるのか？ | [621_ab_sample_ratio_mismatch](articles/621_ab_sample_ratio_mismatch) |
| 676 | ベイズの A/B テストで、事前分布を強く置くと、効果の推定と「勝つ確率」はどれだけ動くのか？ | [676_bayesian_ab_prior](articles/676_bayesian_ab_prior) |
| 677 | 多腕バンディットと固定の A/B テストでは、失う申込みの数と、正しい案を選ぶ割合はどう違うのか？ | [677_bandit_vs_ab](articles/677_bandit_vs_ab) |
| 678 | A/B テストで、前の期間の購入額を使って調整すると、必要な人数はどれだけ減るのか？ | [678_cuped_variance_reduction](articles/678_cuped_variance_reduction) |
| 679 | 層別に割り付けると、単純な無作為の割り付けよりも効果の推定のばらつきはどれだけ小さくなるのか？ | [679_stratified_randomization](articles/679_stratified_randomization) |
| 694 | A/B テストを3日だけで止めると、曜日で効き方が違うとき、効果の推定はどれだけずれるのか？ | [694_ab_weekday_imbalance](articles/694_ab_weekday_imbalance) |
| 726 | クリック率をクリック単位で数えて検定すると、ユーザー単位で割り付けた A/B テストで、効果が0でも何%で「差あり」になるのか？ | [726_ratio_metric_delta_method](articles/726_ratio_metric_delta_method) |
| 796 | 有意にならなかった結果から検出力を後で計算すると、何を言っていることになるのか？ | [796_post_hoc_power](articles/796_post_hoc_power) |

</details>

<details><summary><b>統計の考え方（検定・区間・回帰）</b>（322本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F01 | 最低賃金の引き上げは、雇用を減らしたのか？ | [F01_minimum_wage_did](articles/F01_minimum_wage_did) |
| F02 | コロナがなかったら、赤ちゃんは何人多かったのか？ | [F02_births_counterfactual](articles/F02_births_counterfactual) |
| F04 | Go To トラベルは宿泊をどれだけ増やしたのか？ | [F04_goto_causalimpact](articles/F04_goto_causalimpact) |
| F05 | 医療費の地域差は「県」と「市町村」のどちらで決まるか？ | [F05_medical_cost_hierarchical](articles/F05_medical_cost_hierarchical) |
| F06 | 高齢化は地図の上で固まっているか？ | [F06_aging_spatial](articles/F06_aging_spatial) |
| F08 | 1,740市区町村を62の指標で分けると何タイプか？ | [F08_municipal_segments](articles/F08_municipal_segments) |
| F09 | 国会で「賃上げ」はいつから語られるようになったのか？ | [F09_diet_text](articles/F09_diet_text) |
| F13 | 失業率を来月まで予測できるか？ | [F13_unemployment_forecast](articles/F13_unemployment_forecast) |
| F15 | 県境をまたぐと最低賃金が違う。隣どうしの町で雇用は違ったか？ | [F15_border_minwage](articles/F15_border_minwage) |
| F16 | 保育所に通う子どもが増えた町で、女性は働きに出たのか？ | [F16_childcare_dml](articles/F16_childcare_dml) |
| F18 | 景気は今どうなのか？ | [F18_nowcast_dfm](articles/F18_nowcast_dfm) |
| F19 | 小さな町の検診受診率は、どこまで信用できるのか？ | [F19_small_area_fh](articles/F19_small_area_fh) |
| F20 | 出生率は隣の町と似るのか？ | [F20_tfr_spatial_regression](articles/F20_tfr_spatial_regression) |
| F22 | 明日の電力需要はどこまで当てられるか？ | [F22_power_demand_forecast](articles/F22_power_demand_forecast) |
| F26 | 政策の効果を見つけるには、何県・何年のデータが要るのか？ | [F26_power_simulation](articles/F26_power_simulation) |
| F27 | 市区町村の死亡率の地図は、小さな町ほどぶれる。隣の町の情報を借りる空間ベイズ（BYM2）で描き直すと、地域差の9割以上は | [F27_disease_map_bym2](articles/F27_disease_map_bym2) |
| F31 | 60歳・65歳で、働く人はどれだけ減るのか？ | [F31_retirement_rdd](articles/F31_retirement_rdd) |
| F32 | 所得の高い町と低い町で、効いている要因は同じか？ | [F32_income_quantile](articles/F32_income_quantile) |
| F33 | 人の移動は距離でどれだけ減るのか？ | [F33_migration_gravity](articles/F33_migration_gravity) |
| F34 | 同じお金で、どの市町村が多くのサービスを出しているか？ | [F34_municipal_efficiency](articles/F34_municipal_efficiency) |
| F35 | 景気の「山」と「谷」をデータだけで当てられるか？ | [F35_business_cycle_markov](articles/F35_business_cycle_markov) |
| F39 | 物価・賃金・金利は、どれがどれを動かしているのか？ | [F39_causal_discovery_macro](articles/F39_causal_discovery_macro) |
| F41 | 欠けているデータを埋めると、結論は変わるのか？ | [F41_missing_data_mi](articles/F41_missing_data_mi) |
| F43 | 金利が上がると、何か月後に何が動くのか？ | [F43_local_projections](articles/F43_local_projections) |
| F44 | 出生率のトレンドはいつ折れたのか？ | [F44_structural_breaks](articles/F44_structural_breaks) |
| F46 | 雇用が増えた町に、人は集まったのか？ | [F46_bartik_iv](articles/F46_bartik_iv) |
| F49 | 平均寿命の県の差は、何歳の死亡で生まれているのか？ | [F49_life_expectancy_decomposition](articles/F49_life_expectancy_decomposition) |
| F50 | GDPの速報は、あとでどれだけ直されるのか？ | [F50_gdp_revisions](articles/F50_gdp_revisions) |
| F51 | 保育所の整備は、出生率に「女性の就業」を通じて効いたのか？ | [F51_childcare_mediation](articles/F51_childcare_mediation) |
| F52 | インフルエンザは、どの県からどの県へ広がるのか？ | [F52_influenza_spread](articles/F52_influenza_spread) |
| F53 | 日銀の声明文は、いつ「強気」から「弱気」に変わったか？ | [F53_boj_statement_tone](articles/F53_boj_statement_tone) |
| F54 | 働く女性の賃金は、働いている人だけを見ると高く見えるのか？ | [F54_heckman_women_wage](articles/F54_heckman_women_wage) |
| F55 | ベイズで出生数を予測すると、予測の幅はどう変わるのか？ | [F55_births_bsts](articles/F55_births_bsts) |
| F56 | 住宅価格指数を「繰り返し売買法」で作ると、ヘドニックと同じになるか？ | [F56_repeat_sales_index](articles/F56_repeat_sales_index) |
| F59 | 学力調査の県の順位は、毎年どれくらい入れ替わるのか？ | [F59_test_rank_stability](articles/F59_test_rank_stability) |
| F60 | 去年いちばん悪かった県は、今年よくなるのか？ | [F60_regression_to_mean](articles/F60_regression_to_mean) |
| F61 | 小さい町の「ランキング1位」は、なぜ毎回入れ替わるのか？ | [F61_funnel_eb_rankings](articles/F61_funnel_eb_rankings) |
| F63 | 「前年比」と「前月比」、景気の変わり目を早く見つけられるのはどちらか？ | [F63_yoy_vs_mom](articles/F63_yoy_vs_mom) |
| F65 | 医師が多い県ほど、平均寿命は長いのか？ | [F65_doctors_life_dag](articles/F65_doctors_life_dag) |
| F67 | 気温が1℃上がると、電気の使用量は何%増えるか？ | [F67_temp_power_gam](articles/F67_temp_power_gam) |
| F68 | 訪日客の「来る季節」は、国によっていくつの型に分かれるか？ | [F68_inbound_seasonality_clusters](articles/F68_inbound_seasonality_clusters) |
| F70 | 同じ数字でも、グラフの見せ方で印象はどこまで変わるのか？ | [F70_chart_honesty](articles/F70_chart_honesty) |
| F72 | 家計は、物価が何%上がると思っているのか？ | [F72_inflation_expectations_cp](articles/F72_inflation_expectations_cp) |
| F73 | 街の人の「景気の声」は、数字より先に動くか？ | [F73_watcher_text_tone](articles/F73_watcher_text_tone) |
| F74 | 観測点のない場所の気温は、どこまで当てられるか？ | [F74_temperature_kriging](articles/F74_temperature_kriging) |
| F75 | 地価の地図を「なめらかに」描くと、どこまで当たるか？ | [F75_gp_land_price](articles/F75_gp_land_price) |
| F76 | 所得が高い県は、ずっと高いままか？ | [F76_income_mobility_markov](articles/F76_income_mobility_markov) |
| F77 | 今の人の流れが続くと、都道府県の人口の分布は最後にどうなるか？ | [F77_migration_markov](articles/F77_migration_markov) |
| F78 | 産業がばらけている町は、不景気に強いのか？ | [F78_industry_portfolio](articles/F78_industry_portfolio) |
| F80 | 47都道府県×100指標を比べると、「有意な差」はいくつ偶然か？ | [F80_multiple_comparisons](articles/F80_multiple_comparisons) |
| F82 | 「年収の壁」の手前に、人はどれくらい集まっているのか？ | [F82_income_wall_bunching](articles/F82_income_wall_bunching) |
| F85 | 日本経済の「要」の産業はどれか？ | [F85_io_network](articles/F85_io_network) |
| F86 | 平均寿命はこの先どこまで延びるのか？ | [F86_lee_carter_e0](articles/F86_lee_carter_e0) |
| F88 | 携帯料金の値下げは、物価をどれだけ下げたか？ | [F88_mobile_fee_rdit](articles/F88_mobile_fee_rdit) |
| F89 | 最低賃金の効果、これまでの推定をまとめると？ | [F89_minwage_meta](articles/F89_minwage_meta) |
| F90 | 月次の統計で、四半期のGDPをどこまで当てられるか？ | [F90_midas_nowcast](articles/F90_midas_nowcast) |
| F91 | 機械学習の「何が効いているか」は、手法で答えが変わるか？ | [F91_interpretation_methods](articles/F91_interpretation_methods) |
| F92 | 電力需要の「上振れ」はどこまで見込めばよいか？ | [F92_power_quantile_forecast](articles/F92_power_quantile_forecast) |
| F95 | 新幹線の効果は、隣の県にもこぼれたのか？ | [F95_shinkansen_spillover](articles/F95_shinkansen_spillover) |
| F96 | e-Statの数万の統計表から、欲しい表をすぐ探せるか？ | [F96_estat_semantic_search](articles/F96_estat_semantic_search) |
| F97 | 「前年比+1%」は、本当に増えたと言えるのか？ | [F97_sampling_error_yoy](articles/F97_sampling_error_yoy) |
| F100 | 同じ問いを5つの手法で分析すると、答えはそろうのか？ | [F100_five_methods_one_question](articles/F100_five_methods_one_question) |
| F101 | 物価と賃金は、長い目で見ると一緒に動いているのか？ | [F101_price_wage_cointegration](articles/F101_price_wage_cointegration) |
| F102 | 円安が物価に効くのは、円安が大きいときだけか？ | [F102_fx_threshold_passthrough](articles/F102_fx_threshold_passthrough) |
| F103 | 電力需要や物価の「長い記憶」は、どれくらい続くか？ | [F103_long_memory](articles/F103_long_memory) |
| F104 | 気温と電力需要の関係を、ガウス過程の時系列で読むと？ | [F104_gp_power_temperature](articles/F104_gp_power_temperature) |
| F105 | 閉鎖を数年おきの調査でしか確かめられないと、生存曲線はどこまでずれるか？ | [F105_interval_censoring](articles/F105_interval_censoring) |
| F106 | 同じ県の会社は、同じように閉鎖しやすいのか？ | [F106_shared_frailty](articles/F106_shared_frailty) |
| F108 | 予測モデルは、地域によって外れ方が偏っていないか？ | [F108_prediction_fairness](articles/F108_prediction_fairness) |
| F109 | どのデータを集めれば、予測は早く良くなるか？ | [F109_active_learning_land_price](articles/F109_active_learning_land_price) |
| F110 | 予測モデルの設定は、どう選ぶのが効率的か？ | [F110_hyperparam_bayesopt](articles/F110_hyperparam_bayesopt) |
| F112 | 救急隊が全部出払う確率は、隊を1つ増やすとどれだけ下がるか？ | [F112_ambulance_queueing](articles/F112_ambulance_queueing) |
| F113 | 物価指数の作り方で、インフレ率はどれだけ変わるか？ | [F113_price_index_formulas](articles/F113_price_index_formulas) |
| F114 | 東京の1万円と地方の1万円は、同じ価値か？ | [F114_regional_purchasing_power](articles/F114_regional_purchasing_power) |
| F115 | 統計の公表値から、元のばらつきをどこまで復元できるか？ | [F115_grouped_income_distribution](articles/F115_grouped_income_distribution) |
| F116 | 47都道府県の指標を1つの「暮らしやすさ」にまとめると、重みでどれだけ順位が変わるか？ | [F116_composite_index_weights](articles/F116_composite_index_weights) |
| F119 | 予測した記事は、その後どれだけ当たったか？ | [F119_forecast_scorecard](articles/F119_forecast_scorecard) |
| F120 | 2025年国勢調査で、記事の結論は変わったか？ | [F120_census2025_update](articles/F120_census2025_update) |
| F121 | 「最低賃金と雇用」に、4本の記事はどう答えたか？ | [F121_minwage_methods_review](articles/F121_minwage_methods_review) |
| F122 | 手法ごとに、どこでつまずいたか？ | [F122_pitfalls_from_logs](articles/F122_pitfalls_from_logs) |
| F123 | 「場所で分けて確かめる」と、記事の結論は変わったか？ | [F123_spatial_block_cv_review](articles/F123_spatial_block_cv_review) |
| F124 | 同じデータを何本の記事で使い回したか？ | [F124_data_lineage_network](articles/F124_data_lineage_network) |
| F125 | 100本を超えた看板記事で、「見えなかった」はどれくらいあったか？ | [F125_null_results_review](articles/F125_null_results_review) |
| F126 | 暑い日の何日後まで、熱中症の搬送は増えるのか？ | [F126_heatstroke_dlnm](articles/F126_heatstroke_dlnm) |
| F127 | 空き家は、人口が減った分だけ増えたのか？ | [F127_vacant_houses_decomposition](articles/F127_vacant_houses_decomposition) |
| F128 | 家賃は、都心からの距離でどれだけ下がるのか？ | [F128_rent_distance](articles/F128_rent_distance) |
| F129 | 薬の処方量の地域差は、年齢構成でどこまで説明できるか？ | [F129_prescription_age_adjust](articles/F129_prescription_age_adjust) |
| F130 | 介護の認定率の地域差は、高齢化だけで説明できるか？ | [F130_care_certification_shrinkage](articles/F130_care_certification_shrinkage) |
| F131 | 大学に進む人が増えると、地元に残る若者は減るのか？ | [F131_univ_youth_migration](articles/F131_univ_youth_migration) |
| F132 | 農家は「やめる」のか「大きくなる」のか？ | [F132_farm_size_transitions](articles/F132_farm_size_transitions) |
| F133 | 輸出先は、距離と経済規模でどこまで決まるのか？ | [F133_export_gravity](articles/F133_export_gravity) |
| F134 | 再生可能エネルギーの導入は、どこで速く進んだのか？ | [F134_renewable_diffusion](articles/F134_renewable_diffusion) |
| F135 | 雨の日は、小売の売上をどれだけ動かすのか？ | [F135_rain_retail](articles/F135_rain_retail) |
| F136 | 鉄道の利用は、コロナ前にどこまで戻ったのか？ | [F136_rail_covid_recovery](articles/F136_rail_covid_recovery) |
| F137 | 郵便物は、いつ半分になるのか？ | [F137_postal_decay](articles/F137_postal_decay) |
| F138 | テレワークは、どの産業・地域に残ったのか？ | [F138_telework_decomposition](articles/F138_telework_decomposition) |
| F140 | 外国人の住民は、どの地域に、どの速さで増えたのか？ | [F140_foreign_residents_concentration](articles/F140_foreign_residents_concentration) |
| F141 | 特許の出願は、どの分野で地方に広がったのか？ | [F141_ip_regional_concentration](articles/F141_ip_regional_concentration) |
| F142 | 森林は、「切れる木」がどれだけ増えたのか？ | [F142_forest_age_harvest](articles/F142_forest_age_harvest) |
| F143 | 漁獲量の減り方は、魚の種類でどう違うのか？ | [F143_fish_catch_decline](articles/F143_fish_catch_decline) |
| F144 | 水道料金の差は、人口密度と水源でどこまで説明できるか？ | [F144_water_tariff_density](articles/F144_water_tariff_density) |
| F145 | ごみの量は、有料化のあとに減ったのか？ | [F145_waste_fee_did](articles/F145_waste_fee_did) |
| F146 | 統計の秘匿をノイズで置き換えると、分析の答えはどれだけ変わるか？ | [F146_dp_noise_vs_suppression](articles/F146_dp_noise_vs_suppression) |
| F147 | 集計表から「それらしい個票」を作ると、元の分析を再現できるか？ | [F147_synthetic_from_tables](articles/F147_synthetic_from_tables) |
| F150 | 季節のパターンそのものは、年々変わっているのか？ | [F150_dynamic_seasonality](articles/F150_dynamic_seasonality) |
| F151 | 47都道府県の求人倍率の「同じ動き」は、いくつに分けられるか？ | [F151_pref_hierarchical_dfm](articles/F151_pref_hierarchical_dfm) |
| F152 | 統計の速報は、確報でどれだけ直されるのか？ | [F152_revision_news_noise](articles/F152_revision_news_noise) |
| F153 | 平均でなく「分布」で比べると、地域の差は何に見えるか？ | [F153_distribution_regional](articles/F153_distribution_regional) |
| F154 | 推定の「不確かさ」は、図の形で何が読み取れるかが変わるのか？ | [F154_uncertainty_viz](articles/F154_uncertainty_viz) |
| F155 | 分析の手順を変えると、答えはどこまで変わるか？ | [F155_multiverse](articles/F155_multiverse) |
| F156 | 最低賃金の効果は、地域の「賃金の低さ」で違うのか？ | [F156_minwage_bite_heterogeneity](articles/F156_minwage_bite_heterogeneity) |
| F157 | 電力需要の予測を、1年通して運用したらどうなるか？ | [F157_power_forecast_operation](articles/F157_power_forecast_operation) |
| F158 | 地価の予測モデルは、毎年作り直す必要があるのか？ | [F158_land_price_update](articles/F158_land_price_update) |
| F159 | 出生数の予測を、毎月の速報で更新すると当たり方は変わるか？ | [F159_births_nowcast](articles/F159_births_nowcast) |
| F160 | 人口の将来推計を、自分で作るとどこまで合うか？ | [F160_cohort_projection_backtest](articles/F160_cohort_projection_backtest) |
| F161 | 同じデータで記事を書き直すと、結論はどれだけ変わるか？ | [F161_rewrite_old_articles](articles/F161_rewrite_old_articles) |
| F163 | 125本の看板記事で、いちばん効いた頑健性チェックは何だったか？ | [F163_robustness_checks_review](articles/F163_robustness_checks_review) |
| F164 | 図をどう作ると、読まれ方が変わったか？ | [F164_figures_and_reads](articles/F164_figures_and_reads) |
| F165 | データ分析の「再現できる形」は、どこまで作れたか？ | [F165_reproducibility_audit](articles/F165_reproducibility_audit) |
| F166 | 公的統計の数字は、ベンフォードの法則に従っているか？ | [F166_benford_public_stats](articles/F166_benford_public_stats) |
| F167 | 「100年に1度の大雨」は、本当に100年に1度なのか？ | [F167_return_period_heavy_rain](articles/F167_return_period_heavy_rain) |
| F168 | 猛暑日の数は、どこまで増えたと言えるか？ | [F168_extreme_heat_trend](articles/F168_extreme_heat_trend) |
| F169 | 円安と株高は、大きく動く日にだけ一緒に動くのか？ | [F169_yen_stock_copula](articles/F169_yen_stock_copula) |
| F170 | 産業の構成比を比べるとき、割合のまま回帰してよいか？ | [F170_compositional_industry_shares](articles/F170_compositional_industry_shares) |
| F171 | 人口ピラミッドの「形」は、いくつの型に分かれるか？ | [F171_pyramid_shape_fda](articles/F171_pyramid_shape_fda) |
| F172 | 生まれる日・亡くなる日は、曜日と季節でどう偏るか？ | [F172_birth_death_calendar](articles/F172_birth_death_calendar) |
| F173 | 2つの年の所得分布は、どれだけ「動いた」のか？ | [F173_income_distribution_wasserstein](articles/F173_income_distribution_wasserstein) |
| F174 | 景気の「局面」は、データから自動で見つけられるか？ | [F174_business_cycle_hmm_multiseries](articles/F174_business_cycle_hmm_multiseries) |
| F175 | 予測モデルの精度は、どの特徴量の「おかげ」なのか？ | [F175_r2_shapley_decomposition](articles/F175_r2_shapley_decomposition) |
| F176 | 白書の文章は、年々読みやすくなったのか？ | [F176_whitepaper_readability](articles/F176_whitepaper_readability) |
| F177 | 「差がある」は、並べ替えで確かめるとどうなるか？ | [F177_permutation_tests](articles/F177_permutation_tests) |
| F178 | 回帰の外れ値は、どの点がどれだけ結論を動かしているか？ | [F178_regression_influence](articles/F178_regression_influence) |
| F179 | 欠測を埋める方法で、答えはどれだけ変わるか？ | [F179_imputation_by_estimand](articles/F179_imputation_by_estimand) |
| F180 | 2つの統計の数字は、本当に同じものを測っているか？ | [F180_measurement_agreement](articles/F180_measurement_agreement) |
| F181 | 家が建つ数は、金利と人口のどちらで決まるのか？ | [F181_housing_starts_rates_population](articles/F181_housing_starts_rates_population) |
| F182 | 中古住宅は、新築の何年分の価格差で売られているか？ | [F182_condo_depreciation_curve](articles/F182_condo_depreciation_curve) |
| F183 | 車を持つ世帯は、どこで減りはじめたのか？ | [F183_car_ownership_change_points](articles/F183_car_ownership_change_points) |
| F184 | 空の便は、新幹線の開業でどれだけ減ったのか？ | [F184_air_shinkansen_did](articles/F184_air_shinkansen_did) |
| F185 | 宅配便の個数は、どこまで通販で説明できるのか？ | [F185_parcels_online_shopping](articles/F185_parcels_online_shopping) |
| F186 | 電気料金の値上がりは、家計のどこに効いたのか？ | [F186_electricity_bill_household_burden](articles/F186_electricity_bill_household_burden) |
| F187 | 子どもの身長の伸びは、いつ止まったのか？ | [F187_height_plateau_changepoint](articles/F187_height_plateau_changepoint) |
| F188 | 労働災害は、どの産業で減り、どこで減らなかったのか？ | [F188_occupational_injury_by_industry](articles/F188_occupational_injury_by_industry) |
| F189 | 日本人の1日は、20年でどう変わったのか？ | [F189_time_use_composition](articles/F189_time_use_composition) |
| F190 | 暑い夏と寒い冬に、亡くなる人はどれだけ増えるのか？ | [F190_excess_deaths_temperature](articles/F190_excess_deaths_temperature) |
| F191 | お金の量を増やすと、貸出は増えたのか？ | [F191_money_base_lending](articles/F191_money_base_lending) |
| F192 | 国債の金利は、何で動いているのか？ | [F192_jgb_yield_curve_pca](articles/F192_jgb_yield_curve_pca) |
| F193 | インターネットの通信量は、どの時間に、どれだけ増えたのか？ | [F193_internet_traffic_decomposition](articles/F193_internet_traffic_decomposition) |
| F194 | 博物館・美術館の入館者は、コロナ前に戻ったのか？ | [F194_museum_covid_recovery](articles/F194_museum_covid_recovery) |
| F195 | 夜の明かりで、地域の経済活動はどこまで分かるか？ | [F195_night_lights_gdp](articles/F195_night_lights_gdp) |
| F196 | 標本調査で、層に分けるとどれだけ精度が上がるのか？ | [F196_stratified_sampling_allocation](articles/F196_stratified_sampling_allocation) |
| F197 | 地区をまとめて選ぶと、精度はどれだけ落ちるのか？ | [F197_cluster_sampling_deff](articles/F197_cluster_sampling_deff) |
| F198 | 調査は、何人に聞けば足りるのか？ | [F198_sample_size_planning](articles/F198_sample_size_planning) |
| F199 | 季節調整のやり方で、「景気の山」の時期は変わるのか？ | [F199_seasonal_adjustment_turning_points](articles/F199_seasonal_adjustment_turning_points) |
| F200 | 200本の看板記事で使ったデータと手法は、どうつながっているか？ | [F200_method_data_network](articles/F200_method_data_network) |
| F201 | 最低賃金は誰に届き、雇用をどれだけ動かしたのか？ | [F201_minimum_wage_series_part1](articles/F201_minimum_wage_series_part1) |
| F202 | 最低賃金は「年収の壁」とどう重なり、全国一律にしたら何が起きるのか？ | [F202_minimum_wage_series_part2](articles/F202_minimum_wage_series_part2) |
| F203 | 出生率が下がったのは、結婚が減ったからか、夫婦の子どもが減ったからか？ | [F203_births_marriage_series_part1](articles/F203_births_marriage_series_part1) |
| F204 | 出生の支援策は、結婚・第1子・第2子のどこに効いたのか？ | [F204_births_marriage_series_part2](articles/F204_births_marriage_series_part2) |
| F205 | 予測モデルは、作る前に何を決め、外れをいくらと見て、いつ作り直すのか？ | [F205_power_forecast_practice_part1](articles/F205_power_forecast_practice_part1) |
| F206 | 予測は、エリアと合計をどうそろえ、どう見せ、1年回すと何が起きるのか？ | [F206_power_forecast_practice_part2](articles/F206_power_forecast_practice_part2) |
| F207 | 地価はどこで上がり、駅ができると何が起きるのか？ | [F207_landprice_series_part1](articles/F207_landprice_series_part1) |
| F208 | マンションの値段は地価とどう動き、地価の予測はどこで外れ続けるのか？ | [F208_landprice_series_part2](articles/F208_landprice_series_part2) |
| F209 | この5年の値上がりは、どの品目から来て、誰に重く、家計は何を減らしたのか？ | [F209_prices_household_series_part1](articles/F209_prices_household_series_part1) |
| F210 | 円安は品目の値段にどれだけ時間をかけて届き、物価の見通しは家計と企業でどれだけ違うのか？ | [F210_prices_household_series_part2](articles/F210_prices_household_series_part2) |
| F231 | 売上の予測は、何か月先まで役に立つのか？ | [F231_sales_forecast_horizon](articles/F231_sales_forecast_horizon) |
| F232 | 店の種類ごとの予測と全体の予測を、どうそろえるか？ | [F232_hierarchical_retail_reconciliation](articles/F232_hierarchical_retail_reconciliation) |
| F233 | 祝日・連休・天気は、売上をどれだけ動かすのか？ | [F233_calendar_weather_sales](articles/F233_calendar_weather_sales) |
| F234 | 価格を1%上げると、買われる量は何%減るのか？ | [F234_price_elasticity_practice](articles/F234_price_elasticity_practice) |
| F235 | 在庫はどれだけ持てばよいのか？ | [F235_inventory_newsvendor](articles/F235_inventory_newsvendor) |
| F236 | A/B テストは、何人集めれば「差」が分かるのか？ | [F236_ab_test_sample_size](articles/F236_ab_test_sample_size) |
| F238 | 前の期間のデータを使うと、テストはどれだけ早く終わるか？ | [F238_ab_test_cuped](articles/F238_ab_test_cuped) |
| F239 | 広告費は、売上にどれだけ効いているのか？ | [F239_marketing_mix_model](articles/F239_marketing_mix_model) |
| F240 | キャンペーンの効果を、比べる相手がないときにどう測るか？ | [F240_campaign_effect_no_control](articles/F240_campaign_effect_no_control) |
| F241 | 顧客はどれくらいで離れていくのか？ | [F241_customer_churn_survival](articles/F241_customer_churn_survival) |
| F242 | 毎日の KPI の「いつもと違う」を、どう自動で知らせるか？ | [F242_kpi_anomaly_alerts](articles/F242_kpi_anomaly_alerts) |
| F246 | 分析担当として最初にやること：KPI を決める（業務の再現：架空の会社で） シリーズ③の1本目。架空の食品スーパー「サン | [F246_kpi_definitions_fictional_retail](articles/F246_kpi_definitions_fictional_retail) |
| F250 | 売上が落ちた月に、理由を説明する（業務の再現：架空の会社で） シリーズ③の5本目。F247 の mart を使い、架空の | [F250_sales_drop_explanation_fictional_retail](articles/F250_sales_drop_explanation_fictional_retail) |
| F252 | 来期の予算のための需要予測（業務の再現：架空の会社で） シリーズ③の7本目。架空の食品スーパー「サンプルマート（架空）」 | [F252_budget_forecast_fictional_retail](articles/F252_budget_forecast_fictional_retail) |
| F255 | 1年の分析業務を振り返る（業務の再現：架空の会社で） シリーズ③の10本目・最後。架空の食品スーパー「サンプルマート（架 | [F255_year_review_fictional_retail](articles/F255_year_review_fictional_retail) |
| F257 | 労働経済白書の「賃上げが広がった」は、どのデータでどこまで言えるのか？ | [F257_wage_spillover_whitepaper](articles/F257_wage_spillover_whitepaper) |
| F259 | 需要予測の外れは、在庫と欠品のどちらに効かせるべきか？ | [F259_forecast_error_inventory_cost](articles/F259_forecast_error_inventory_cost) |
| F260 | 「100年に1度の損害」は、どの分布を仮定するかでいくら変わるのか？ | [F260_loss_distribution_return_level](articles/F260_loss_distribution_return_level) |
| F261 | 潜在成長率は、計算の仕方でどれだけ変わるのか？ | [F261_potential_growth_methods](articles/F261_potential_growth_methods) |
| F264 | 自動車の事故率は、高齢化でどこまで説明できるのか？ | [F264_auto_accident_rate_aging](articles/F264_auto_accident_rate_aging) |
| F265 | 少子化対策の「2025年の数値目標」は、決めた時点のペースで届くと読めたのか？ | [F265_policy_targets_pace](articles/F265_policy_targets_pace) |
| F266 | 「米の値段が上がった」は、どの段階で起きたのか？ | [F266_rice_price_stages](articles/F266_rice_price_stages) |
| F267 | 売上の目標を、客数と客単価の目標にどう分けるか？ | [F267_kpi_target_allocation_cvs](articles/F267_kpi_target_allocation_cvs) |
| F269 | 「価格転嫁できた企業」は、どんな企業か？ | [F269_sme_price_passthrough](articles/F269_sme_price_passthrough) |
| F272 | 火災保険料の地域差は、リスクの差にどこまで見合っているか？ | [F272_fire_insurance_rate_vs_risk](articles/F272_fire_insurance_rate_vs_risk) |
| F273 | 観光白書の「地方への分散」は、宿泊データで見えているか？ | [F273_regional_dispersion_lodging](articles/F273_regional_dispersion_lodging) |
| F274 | 「人手不足倒産が過去最多」は、会社の数と数え方をそろえても増えたのか？ | [F274_labor_shortage_bankruptcy_rate](articles/F274_labor_shortage_bankruptcy_rate) |
| F276 | 地震保険の付帯率は、地震のあとにどれだけ上がって戻るのか？ | [F276_earthquake_insurance_after_quakes](articles/F276_earthquake_insurance_after_quakes) |
| F278 | 「空き家が過去最多」は、住宅の数が増えた分を除くとどうか？ | [F278_vacant_record_stock_vs_rate](articles/F278_vacant_record_stock_vs_rate) |
| F279 | RFM で分けた顧客は、その後どう動くのか？ | [F279_rfm_segment_transitions](articles/F279_rfm_segment_transitions) |
| F281 | 食料自給率の目標と実際の差は、どこから来ているのか？ | [F281_food_self_sufficiency_target_gap](articles/F281_food_self_sufficiency_target_gap) |
| F282 | 「円安で輸出が増えた」は、数量と価格に分けるとどうか？ | [F282_yen_exports_quantity_price](articles/F282_yen_exports_quantity_price) |
| F283 | 値上げの前後で、売れ方はどう変わったか？ | [F283_price_hike_front_loading](articles/F283_price_hike_front_loading) |
| F284 | 豪雨の増え方を、火災保険の料率はどこまで追いかけているのか？ | [F284_heavy_rain_vs_fire_rates](articles/F284_heavy_rain_vs_fire_rates) |
| F285 | エネルギー基本計画の電力需要の見通しは、過去にどれだけ当たったか？ | [F285_power_demand_outlook_accuracy](articles/F285_power_demand_outlook_accuracy) |
| F286 | 「物価高で節約」は家計調査のどこに表れているか？ | [F286_household_saving_items](articles/F286_household_saving_items) |
| F288 | 損害額の分布の「裾の重さ」は、データの量でどこまで見分けられるか？ | [F288_tail_heaviness_sample_size](articles/F288_tail_heaviness_sample_size) |
| F289 | 情報通信白書のデジタル化の指標は、生産性と結びついているか？ | [F289_ict_capital_productivity](articles/F289_ict_capital_productivity) |
| F290 | アンケートの回答の偏りは、重み付けでどこまで直せるか？ | [F290_survey_weighting_limits](articles/F290_survey_weighting_limits) |
| F291 | 死亡率の改善は、年齢のどこで止まりつつあるのか？ | [F291_mortality_improvement_slowdown](articles/F291_mortality_improvement_slowdown) |
| F292 | 南海トラフの被害想定は、人口が変わるとどう動くか？ | [F292_quake_damage_population](articles/F292_quake_damage_population) |
| F295 | リスクを分けて計ると、分散効果はどれだけ効くのか？ | [F295_solvency_diversification_copula](articles/F295_solvency_diversification_copula) |
| 037 | 東京の中古マンションは10年で何%上がった？ | [037_tokyo_condo_hedonic](articles/037_tokyo_condo_hedonic) |
| 048 | 病院で亡くなる人の割合は2005年がピーク。折れ線回帰で「流れが変わった年」を探した | [048_place_of_death](articles/048_place_of_death) |
| 123 | 辞める人が多い産業ほど入る人も多い（相関0.97）。転職で賃金が1割以上増えた人は15%から28%に | [123_turnover_rates](articles/123_turnover_rates) |
| 171 | 道路の交通量は2015→2021年度で5.6%減。高速道路は延びたのに1区間あたり11%減、大型車の割合は上がった | [171_road_traffic_change](articles/171_road_traffic_change) |
| 253 | p値0.05の線を、どう扱ってきたか？ | [253_p_value_line](articles/253_p_value_line) |
| 267 | 相関を因果だと思いかけたとき、どう止めたか？ | [267_correlation_not_causation](articles/267_correlation_not_causation) |
| 268 | 差の差・回帰不連続・合成コントロールを、どう選んできたか？ | [268_causal_design_choice](articles/268_causal_design_choice) |
| 271 | A/B テストの結果を、意思決定する人にどう伝えるか？ | [271_ab_test_reporting](articles/271_ab_test_reporting) |
| 286 | 予測モデルは、線形回帰と勾配ブースティングのどちらから始めるか？ | [286_linear_vs_gbm_first](articles/286_linear_vs_gbm_first) |
| 318 | 見積もった支払備金の「幅」は、正解を何%含むのか？ | [318_reserve_interval_coverage](articles/318_reserve_interval_coverage) |
| 331 | 大きな損害だけを受け持つ「層」の見積もりは、裾の当てはめにどれだけ左右されるのか？ | [331_layer_price_tail_estimate](articles/331_layer_price_tail_estimate) |
| 332 | 免責や支払いの上限で切られたデータから、元の損害の分布は戻せるのか？ | [332_truncated_censored_loss_fit](articles/332_truncated_censored_loss_fit) |
| 334 | 要因を1つずつ見た事故率の差は、まとめて推定するとどれだけ変わるのか？ | [334_one_way_vs_glm_rating](articles/334_one_way_vs_glm_rating) |
| 347 | 災害の多い年と少ない年があるとき、件数をポアソンで見ると、備えはどれだけ足りなくなるのか？ | [347_poisson_vs_negbin_reserve](articles/347_poisson_vs_negbin_reserve) |
| 352 | 専門用語には、最初に一言の説明が付いているか？ | [352_term_first_use_gloss](articles/352_term_first_use_gloss) |
| 362 | 時系列をばらばらに分けて確かめると、予測の精度をどれだけ甘く見積もるのか？ | [362_shuffled_cv_time_series](articles/362_shuffled_cv_time_series) |
| 364 | 成績の悪かった店だけに手を打つと、何もしなくてもどれだけ「良くなって」見えるのか？ | [364_regression_to_mean_store_action](articles/364_regression_to_mean_store_action) |
| 365 | 似た相手を選んで比べる方法は、測っていない違いがあるとどこまで外れるのか？ | [365_matching_unmeasured_confounder](articles/365_matching_unmeasured_confounder) |
| 380 | ブートストラップの区間は、件数が少ない・裾が重いデータで何%当たるのか？ | [380_bootstrap_interval_coverage](articles/380_bootstrap_interval_coverage) |
| 391 | 週の波と年の波が重なる日次データは、どう分ければ元の波に戻るのか？ | [391_two_seasonalities_daily_decomposition](articles/391_two_seasonalities_daily_decomposition) |
| 392 | 「平均から3σ離れたら外れ値」は、正規でないデータで何%を外れ値と言うのか？ | [392_three_sigma_rule_non_normal](articles/392_three_sigma_rule_non_normal) |
| 393 | 説明する側の数字に測り間違いがあると、回帰の係数はどれだけ小さく出るのか？ | [393_measurement_error_attenuation](articles/393_measurement_error_attenuation) |
| 394 | 似た変数を2つ入れた回帰は、係数の符号がどれくらい逆になるのか？ | [394_collinearity_sign_flips](articles/394_collinearity_sign_flips) |
| 416 | 手元の資本と保険料の上乗せで、10年のうちに資本が尽きる確率はどう変わるのか？ | [416_ruin_probability_capital_loading](articles/416_ruin_probability_capital_loading) |
| 435 | 対数に直して回帰した予測を元に戻すと、合計はどれだけ小さく出るのか？ | [435_log_retransformation_bias](articles/435_log_retransformation_bias) |
| 446 | 指標をいくつも同時に見ると、効果が0でも何%で「差あり」が出るのか？ | [446_multiple_metrics_false_positive](articles/446_multiple_metrics_false_positive) |
| 449 | 指標の単位をそろえないまま主成分分析をすると、第1主成分はどれだけ変わるのか？ | [449_pca_units_standardization](articles/449_pca_units_standardization) |
| 450 | k-means は、丸くないまとまりや大きさの違うまとまりを、どれだけ取り違えるのか？ | [450_kmeans_cluster_shapes](articles/450_kmeans_cluster_shapes) |
| 458 | 件数が少ないとき、割合の「95%の幅」は、正解を何%含むのか？ | [458_proportion_interval_coverage](articles/458_proportion_interval_coverage) |
| 459 | 選ばれた人や店だけで相関を見ると、相関はどれだけ小さく見えるのか？ | [459_range_restriction_correlation](articles/459_range_restriction_correlation) |
| 469 | 同じ店や同じ人の中で似ているデータを、ばらばらの件数として検定すると、効果が0でも何%で「差あり」が出るのか？ | [469_clustered_data_naive_test](articles/469_clustered_data_naive_test) |
| 475 | 解約率は、分母の取り方でどれだけ違って見えるのか？ | [475_churn_rate_denominator](articles/475_churn_rate_denominator) |
| 479 | 地域の平均どうしの相関は、1人ずつの相関とどれだけ違うのか？ | [479_ecological_correlation](articles/479_ecological_correlation) |
| 486 | 損害額の分布を少ない件数で当てはめると、最尤法とモーメント法のどちらが99%点を外しやすいのか？ | [486_loss_fit_mle_vs_moments](articles/486_loss_fit_mle_vs_moments) |
| 487 | 保険料の上乗せを「標準偏差」「分散」「期待効用」で決めると、契約の大きさで上乗せ率はどれだけ食い違うのか？ | [487_risk_loading_principles](articles/487_risk_loading_principles) |
| 489 | 5歳刻みの死亡率から各歳の死亡率を作ると、65歳からの年金の現価はどれだけずれるのか？ | [489_life_table_interpolation_annuity](articles/489_life_table_interpolation_annuity) |
| 496 | 外れ値が1点あると、相関0.5の50件のデータで、ピアソンの相関は何%の回で向きが逆になるのか？ | [496_outlier_correlation_shift](articles/496_outlier_correlation_shift) |
| 498 | 各群20件で2つの割合の差を検定すると、効果が0でも何%で「差あり」と出るのか？ | [498_two_proportion_small_n_tests](articles/498_two_proportion_small_n_tests) |
| 499 | 故障の割合0.5%の500台でロジスティック回帰をすると、係数は何%大きく出て、何%の回で推定できないのか？ | [499_rare_event_logistic_firth](articles/499_rare_event_logistic_firth) |
| 510 | 同じ検証データで2つのモデルを比べると、本当は同じ力でも何%の回で「片方が良い」と出るのか？ | [510_same_validation_model_tie](articles/510_same_validation_model_tie) |
| 519 | 100万件のデータでは、相関0.01のような小さな関係でも何%の回で「有意」と出るのか？ | [519_large_n_tiny_correlation](articles/519_large_n_tiny_correlation) |
| 520 | 0を含むデータを log(x+1) で変換して回帰すると、係数はどれだけずれるのか？ | [520_log1p_regression_bias](articles/520_log1p_regression_bias) |
| 530 | 裾の重いデータで2つの群を比べると、t 検定と順位の検定で、差を見つける力はどれだけ違うのか？ | [530_heavy_tail_t_vs_rank_test](articles/530_heavy_tail_t_vs_rank_test) |
| 538 | 0か1かの結果を線形回帰で当てると、確率が0〜1をはみ出す割合と、効果の推定はどれだけずれるのか？ | [538_linear_probability_vs_logit](articles/538_linear_probability_vs_logit) |
| 540 | 事故の件数をポアソン回帰で当てるとき、契約の期間（露出）を入れ忘れると、要因の効き目はどれだけずれるのか？ | [540_poisson_exposure_offset](articles/540_poisson_exposure_offset) |
| 546 | 2つの系列のずらし幅を0〜12か月で動かして最も強い相関を選ぶと、関係がなくても相関はどれだけ高く出るのか？ | [546_lag_search_spurious_corr](articles/546_lag_search_spurious_corr) |
| 547 | 自動車保険のような等級制度で、等級の分布が落ち着くまでに何年かかり、平均の割引率はどこに落ち着くのか？ | [547_bonus_malus_markov](articles/547_bonus_malus_markov) |
| 549 | 自己相関のある日次データで、ふつうのブートストラップの95%区間は、正解を何%含むのか？ | [549_block_bootstrap_coverage](articles/549_block_bootstrap_coverage) |
| 550 | 回帰に入れる変数を「有意なものだけ残す」で選ぶと、残った係数はどれだけ大きく出るのか？ | [550_selection_coef_inflation](articles/550_selection_coef_inflation) |
| 556 | 同じ分母で割った2つの比率は、もとの数に関係がなくてもどれだけ相関するのか？ | [556_shared_denominator_ratio_corr](articles/556_shared_denominator_ratio_corr) |
| 557 | 効き方が層で違うのに、交互作用を入れずに回帰すると、全体の係数は何を表すのか？ | [557_no_interaction_weighting](articles/557_no_interaction_weighting) |
| 559 | 前後の差で比べるか、前の値を入れた回帰で比べるかで、効果の答えが変わるのはなぜか？ | [559_change_score_vs_ancova](articles/559_change_score_vs_ancova) |
| 569 | 死亡率の実績と予定の比を、件数で見るか保険金額で見るかで、どれだけ違うのか？ | [569_ae_count_vs_amount](articles/569_ae_count_vs_amount) |
| 576 | 時系列のデータをランダムに分けて確かめると、時間の順に分けた場合より成績はどれだけ良く見えるのか？ | [576_random_vs_time_split](articles/576_random_vs_time_split) |
| 577 | 2つの測り方の一致を、相関で見るか、差の平均と幅で見るかで、結論はどう変わるのか？ | [577_correlation_vs_agreement](articles/577_correlation_vs_agreement) |
| 578 | 平均の差を見るとき、群で散らばりが違うと、ふつうのt検定は何%の回で「差あり」と言うのか？ | [578_student_vs_welch](articles/578_student_vs_welch) |
| 586 | 裾の重いデータで平均の差を比べると、t検定と順位の検定で検出力はどれだけ違うのか？ | [586_ttest_vs_rank_heavy_tails](articles/586_ttest_vs_rank_heavy_tails) |
| 588 | 散らばりが水準で変わるデータで、予測の区間を「残差の標準偏差×2」で作ると、何%の回が外れるのか？ | [588_prediction_interval_heteroscedastic](articles/588_prediction_interval_heteroscedastic) |
| 589 | 階級に区切った度数分布表から平均と中央値を出すと、元のデータの値とどれだけずれるのか？ | [589_grouped_table_mean_median](articles/589_grouped_table_mean_median) |
| 600 | 過去10年の損害から分布を推定するとき、推定の誤差を入れないと、99.5%点はどれだけ小さく出るのか？ | [600_parameter_uncertainty_quantile](articles/600_parameter_uncertainty_quantile) |
| 610 | 説明変数に測りまちがいがあると、回帰の係数はどれだけ小さく出るのか？ | [610_measurement_error_attenuation](articles/610_measurement_error_attenuation) |
| 616 | ロジスティック回帰で、ある区分の全員が同じ結果だと、係数と区間はどうなるのか？ | [616_logistic_complete_separation](articles/616_logistic_complete_separation) |
| 619 | 外れ値が混ざったデータで、ふつうの回帰と Huber の回帰では、係数はどれだけ違うのか？ | [619_huber_vs_ols_outliers](articles/619_huber_vs_ols_outliers) |
| 626 | 2つの事業の損害を「独立」と置いて合わせると、合計の99.5%点はどれだけ小さく出るのか？ | [626_aggregation_independence_var](articles/626_aggregation_independence_var) |
| 627 | 相関の強さが同じでも、正規コピュラと t コピュラでは、同時に大きな損害が出る確率はどれだけ違うのか？ | [627_copula_tail_dependence](articles/627_copula_tail_dependence) |
| 629 | 相関の強い2つの列があると、並べ替えの重要度はどれだけ小さく出るのか？ | [629_permutation_importance_correlated](articles/629_permutation_importance_correlated) |
| 636 | 件数が少なく変数が多いとき、リッジ回帰はふつうの回帰より予測の誤差をどれだけ減らすのか？ | [636_ridge_vs_ols_small_n](articles/636_ridge_vs_ols_small_n) |
| 645 | 5段階の評価を平均で比べるか、上位2つの割合で比べるかで、店の順位はどれだけ入れ替わるのか？ | [645_likert_mean_vs_top2box](articles/645_likert_mean_vs_top2box) |
| 647 | 回帰不連続で、境目のまわりの幅を変えると、効果の推定の偏りとばらつきはどう入れ替わるのか？ | [647_rd_bandwidth](articles/647_rd_bandwidth) |
| 648 | 効きの弱い操作変数を使うと、推定はどれだけふつうの回帰の側に引っぱられるのか？ | [648_weak_instrument](articles/648_weak_instrument) |
| 650 | 散らばりが条件で変わるデータで、90%点を回帰で出すと、ふつうの回帰と分位点回帰はどれだけ違うのか？ | [650_quantile_regression_vs_ols](articles/650_quantile_regression_vs_ols) |
| 656 | 同じ店の前と後を比べるとき、対応のない検定にすると、差を見つける力はどれだけ落ちるのか？ | [656_paired_vs_unpaired_test](articles/656_paired_vs_unpaired_test) |
| 658 | ゼロを含むデータを log(y+c) で回帰すると、c の選び方で係数はどれだけ変わるのか？ | [658_log1p_constant_choice](articles/658_log1p_constant_choice) |
| 660 | 回帰の「平均の区間」を新しい1件の予測の区間と取り違えると、何%の回が外れるのか？ | [660_ci_vs_prediction_interval](articles/660_ci_vs_prediction_interval) |
| 668 | 1列ずつ3σで見る方法とマハラノビス距離では、相関を崩す異常をどれだけ見つけられるのか？ | [668_mahalanobis_anomaly](articles/668_mahalanobis_anomaly) |
| 676 | ベイズの A/B テストで、事前分布を強く置くと、効果の推定と「勝つ確率」はどれだけ動くのか？ | [676_bayesian_ab_prior](articles/676_bayesian_ab_prior) |
| 678 | A/B テストで、前の期間の購入額を使って調整すると、必要な人数はどれだけ減るのか？ | [678_cuped_variance_reduction](articles/678_cuped_variance_reduction) |
| 680 | 歪んだ分布の平均の95%区間は、何件あれば本当に95%当たるのか？ | [680_clt_skewed_mean](articles/680_clt_skewed_mean) |
| 688 | 店の固定効果だけ入れて、年ごとの流れを入れないと、施策の効果はどれだけずれるのか？ | [688_panel_time_effects](articles/688_panel_time_effects) |
| 689 | 結果に効く変数をロジスティック回帰に入れないと、施策と関係のない変数でも、施策の係数はどれだけ小さく出るのか？ | [689_logit_noncollapsibility](articles/689_logit_noncollapsibility) |
| 690 | 30件で相関0.3と出たとき、本当の相関はどの範囲にあると言えるのか？ | [690_correlation_ci_small_n](articles/690_correlation_ci_small_n) |
| 695 | 1人あたりの処理件数を、出勤した日数で割るか働いた時間で割るかで、担当者の順位はどれだけ入れ替わるのか？ | [695_productivity_denominator](articles/695_productivity_denominator) |
| 696 | AIC・BIC・交差検証で回帰の変数を選ぶと、本当の変数を何%当てるのか？ | [696_aic_bic_cv_selection](articles/696_aic_bic_cv_selection) |
| 697 | ダミー変数の基準のカテゴリを変えると、係数と有意の見え方はどれだけ変わるのか？ | [697_reference_category](articles/697_reference_category) |
| 698 | 件数が多いと、正規性の検定はどれだけ小さなずれでも「正規でない」と言うのか？ | [698_normality_test_large_n](articles/698_normality_test_large_n) |
| 699 | 構造変化の時点をグラフを見てから決めて検定すると、変化がなくても何%で「変化あり」になるのか？ | [699_structural_break_post_hoc](articles/699_structural_break_post_hoc) |
| 706 | 件数のデータにばらつきの大きさを考えずポアソン回帰を使うと、効果が0でも何%で「有意」になるのか？ | [706_poisson_overdispersion_se](articles/706_poisson_overdispersion_se) |
| 707 | 散らばりが x とともに広がるデータで、ふつうの標準誤差の95%区間は何%当たるのか？ | [707_robust_se_heteroscedastic](articles/707_robust_se_heteroscedastic) |
| 708 | 誤差に自己相関のある時系列で回帰すると、ふつうの標準誤差は何倍小さく出るのか？ | [708_autocorrelated_errors_se](articles/708_autocorrelated_errors_se) |
| 709 | y を対数にした回帰の係数を「そのまま%」と読むと、効果が大きいときどれだけずれるのか？ | [709_log_coef_percent](articles/709_log_coef_percent) |
| 717 | 5段階の評価を1〜5の数として回帰するのと、順序ロジットで見るのとでは、効果の向きや有意はどれだけ違うのか？ | [717_ordinal_vs_linear_likert](articles/717_ordinal_vs_linear_likert) |
| 720 | 2つの系列が同じ原因で動き、片方が遅れて反応するとき、グレンジャー因果の検定は何%で「因果あり」と言うのか？ | [720_granger_common_driver](articles/720_granger_common_driver) |
| 726 | クリック率をクリック単位で数えて検定すると、ユーザー単位で割り付けた A/B テストで、効果が0でも何%で「差あり」になるのか？ | [726_ratio_metric_delta_method](articles/726_ratio_metric_delta_method) |
| 727 | 「有意な差がない」ことを「同じ」と読むと、本当は差のある案を何%で同じとしてしまうのか？ | [727_tost_equivalence](articles/727_tost_equivalence) |
| 736 | 「新しさ」と「手堅さ」のどちらかが高い企画だけ通る審査では、通った企画の中で2つはどれだけ逆の関係に見えるのか？ | [736_berkson_selection_bias](articles/736_berkson_selection_bias) |
| 737 | 施策の効き道になる変数を回帰に入れると、施策の効果はどれだけ小さく出るのか？ | [737_mediator_adjustment](articles/737_mediator_adjustment) |
| 739 | 入れる変数の組み合わせを有意になるまで探すと、効果が0の施策でも何%で「有意」になるのか？ | [739_covariate_search_false_positive](articles/739_covariate_search_false_positive) |
| 740 | 件数が少ないとき、関係のない変数を入れた回帰の R² はどれだけ高く出るのか？ | [740_r2_small_n_inflation](articles/740_r2_small_n_inflation) |
| 746 | 曲がった単調な関係で、ピアソンの相関とスピアマンの相関はどれだけ違うのか？ | [746_spearman_vs_pearson](articles/746_spearman_vs_pearson) |
| 748 | ある日に「利用中」の会員だけに聞くと、平均の利用期間は本当の何倍に見えるのか？ | [748_length_biased_sampling](articles/748_length_biased_sampling) |
| 750 | 交互作用を入れた回帰で、変数を中心化しないと、主効果の係数はどう読めてしまうのか？ | [750_centering_interaction_main_effect](articles/750_centering_interaction_main_effect) |
| 754 | 欠品率を「欠品した SKU の数」で数えるか「売上の重み」で数えるかで、店の比べ方はどれだけ変わるのか？ | [754_stockout_rate_weighting](articles/754_stockout_rate_weighting) |
| 756 | ブートストラップの回数を100回・1,000回・10,000回と変えると、95%区間の端はどれだけ揺れるのか？ | [756_bootstrap_replications](articles/756_bootstrap_replications) |
| 760 | 欠けた値を「-999」で埋めたまま回帰すると、係数はどれだけずれるのか？ | [760_sentinel_value_regression](articles/760_sentinel_value_regression) |
| 767 | カテゴリを1・2・3の数にして線形回帰に入れると、ダミー変数と比べて予測はどれだけ悪くなるのか？ | [767_label_encoding_linear](articles/767_label_encoding_linear) |
| 768 | 強く相関する変数があるとき、部分依存の図はどれだけ本当の効き方とずれるのか？ | [768_pdp_correlated_features](articles/768_pdp_correlated_features) |
| 769 | 交差検証の fold ごとの成績から出した標準誤差は、本当のばらつきをどれだけ小さく見るのか？ | [769_k_fold_se_underestimate](articles/769_k_fold_se_underestimate) |
| 777 | 大きい店では有意・小さい店では有意でない、を「効き方が違う」と読むと、何%で誤るのか？ | [777_difference_in_significance](articles/777_difference_in_significance) |
| 778 | 件数のそろわない2元配置で、平方和の型（I・II・III）を変えると、有意の見え方はどれだけ変わるのか？ | [778_anova_sum_of_squares_type](articles/778_anova_sum_of_squares_type) |
| 779 | 混合正規分布を EM 法で当てはめると、初期値によって何%の回で別の答えになるのか？ | [779_em_initialization](articles/779_em_initialization) |
| 782 | 表の1列だけを並べ替えると、何行の値が別の行とつながってしまうのか？ | [782_partial_sort_misalign](articles/782_partial_sort_misalign) |
| 790 | 学習データを2倍にすると、テストの誤差はどれだけ減り、どこで頭打ちになるのか？ | [790_learning_curve](articles/790_learning_curve) |
| 796 | 有意にならなかった結果から検出力を後で計算すると、何を言っていることになるのか？ | [796_post_hoc_power](articles/796_post_hoc_power) |
| 797 | 2つの95%区間が重なっていたら「差なし」と読むと、本当は差がある場合を何%見逃すのか？ | [797_ci_overlap_rule](articles/797_ci_overlap_rule) |
| 798 | グラフのひげが標準偏差か標準誤差かを取り違えると、差の大きさはどれだけ違って見えるのか？ | [798_sd_vs_se_errorbars](articles/798_sd_vs_se_errorbars) |
| 800 | U字の関係では、相関係数と相互情報量はどれだけ違う答えを出すのか？ | [800_mutual_information_vs_corr](articles/800_mutual_information_vs_corr) |

</details>

<details><summary><b>機械学習・モデル評価</b>（139本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F03 | 地価を決めているのは何か？ | [F03_land_price_ml](articles/F03_land_price_ml) |
| F05 | 医療費の地域差は「県」と「市町村」のどちらで決まるか？ | [F05_medical_cost_hierarchical](articles/F05_medical_cost_hierarchical) |
| F07 | 新卒は何年目に辞めやすいのか？ | [F07_turnover_survival](articles/F07_turnover_survival) |
| F08 | 1,740市区町村を62の指標で分けると何タイプか？ | [F08_municipal_segments](articles/F08_municipal_segments) |
| F09 | 国会で「賃上げ」はいつから語られるようになったのか？ | [F09_diet_text](articles/F09_diet_text) |
| F13 | 失業率を来月まで予測できるか？ | [F13_unemployment_forecast](articles/F13_unemployment_forecast) |
| F16 | 保育所に通う子どもが増えた町で、女性は働きに出たのか？ | [F16_childcare_dml](articles/F16_childcare_dml) |
| F18 | 景気は今どうなのか？ | [F18_nowcast_dfm](articles/F18_nowcast_dfm) |
| F19 | 小さな町の検診受診率は、どこまで信用できるのか？ | [F19_small_area_fh](articles/F19_small_area_fh) |
| F20 | 出生率は隣の町と似るのか？ | [F20_tfr_spatial_regression](articles/F20_tfr_spatial_regression) |
| F22 | 明日の電力需要はどこまで当てられるか？ | [F22_power_demand_forecast](articles/F22_power_demand_forecast) |
| F26 | 政策の効果を見つけるには、何県・何年のデータが要るのか？ | [F26_power_simulation](articles/F26_power_simulation) |
| F33 | 人の移動は距離でどれだけ減るのか？ | [F33_migration_gravity](articles/F33_migration_gravity) |
| F35 | 景気の「山」と「谷」をデータだけで当てられるか？ | [F35_business_cycle_markov](articles/F35_business_cycle_markov) |
| F36 | 全国と47都道府県の宿泊者数の予測を、足し算が合うようにそろえると？ | [F36_hierarchical_forecast](articles/F36_hierarchical_forecast) |
| F48 | ガソリンが10%上がると、買う量は何%減るか？ | [F48_gasoline_elasticity](articles/F48_gasoline_elasticity) |
| F55 | ベイズで出生数を予測すると、予測の幅はどう変わるのか？ | [F55_births_bsts](articles/F55_births_bsts) |
| F57 | インフルエンザの流行は、SIRモデルで再現できるか？ | [F57_flu_sir](articles/F57_flu_sir) |
| F66 | 統計の推計方法が変わると、数字はどれだけ動くのか？ | [F66_series_breaks](articles/F66_series_breaks) |
| F67 | 気温が1℃上がると、電気の使用量は何%増えるか？ | [F67_temp_power_gam](articles/F67_temp_power_gam) |
| F68 | 訪日客の「来る季節」は、国によっていくつの型に分かれるか？ | [F68_inbound_seasonality_clusters](articles/F68_inbound_seasonality_clusters) |
| F73 | 街の人の「景気の声」は、数字より先に動くか？ | [F73_watcher_text_tone](articles/F73_watcher_text_tone) |
| F74 | 観測点のない場所の気温は、どこまで当てられるか？ | [F74_temperature_kriging](articles/F74_temperature_kriging) |
| F86 | 平均寿命はこの先どこまで延びるのか？ | [F86_lee_carter_e0](articles/F86_lee_carter_e0) |
| F88 | 携帯料金の値下げは、物価をどれだけ下げたか？ | [F88_mobile_fee_rdit](articles/F88_mobile_fee_rdit) |
| F90 | 月次の統計で、四半期のGDPをどこまで当てられるか？ | [F90_midas_nowcast](articles/F90_midas_nowcast) |
| F91 | 機械学習の「何が効いているか」は、手法で答えが変わるか？ | [F91_interpretation_methods](articles/F91_interpretation_methods) |
| F92 | 電力需要の「上振れ」はどこまで見込めばよいか？ | [F92_power_quantile_forecast](articles/F92_power_quantile_forecast) |
| F99 | 作るものを変えると、カロリーの自給率はどこまで上がるか？ | [F99_food_self_sufficiency_lp](articles/F99_food_self_sufficiency_lp) |
| F100 | 同じ問いを5つの手法で分析すると、答えはそろうのか？ | [F100_five_methods_one_question](articles/F100_five_methods_one_question) |
| F101 | 物価と賃金は、長い目で見ると一緒に動いているのか？ | [F101_price_wage_cointegration](articles/F101_price_wage_cointegration) |
| F104 | 気温と電力需要の関係を、ガウス過程の時系列で読むと？ | [F104_gp_power_temperature](articles/F104_gp_power_temperature) |
| F106 | 同じ県の会社は、同じように閉鎖しやすいのか？ | [F106_shared_frailty](articles/F106_shared_frailty) |
| F107 | 市区町村のつながり（隣接・通勤）を使うと、予測は良くなるか？ | [F107_gcn_municipal](articles/F107_gcn_municipal) |
| F108 | 予測モデルは、地域によって外れ方が偏っていないか？ | [F108_prediction_fairness](articles/F108_prediction_fairness) |
| F109 | どのデータを集めれば、予測は早く良くなるか？ | [F109_active_learning_land_price](articles/F109_active_learning_land_price) |
| F110 | 予測モデルの設定は、どう選ぶのが効率的か？ | [F110_hyperparam_bayesopt](articles/F110_hyperparam_bayesopt) |
| F111 | 人口が減る町で、店はいつ消えるのか？ | [F111_shop_abm](articles/F111_shop_abm) |
| F112 | 救急隊が全部出払う確率は、隊を1つ増やすとどれだけ下がるか？ | [F112_ambulance_queueing](articles/F112_ambulance_queueing) |
| F116 | 47都道府県の指標を1つの「暮らしやすさ」にまとめると、重みでどれだけ順位が変わるか？ | [F116_composite_index_weights](articles/F116_composite_index_weights) |
| F117 | 調査の回答率が下がると、結果はどれだけずれるか？ | [F117_nonresponse_weighting](articles/F117_nonresponse_weighting) |
| F119 | 予測した記事は、その後どれだけ当たったか？ | [F119_forecast_scorecard](articles/F119_forecast_scorecard) |
| F123 | 「場所で分けて確かめる」と、記事の結論は変わったか？ | [F123_spatial_block_cv_review](articles/F123_spatial_block_cv_review) |
| F126 | 暑い日の何日後まで、熱中症の搬送は増えるのか？ | [F126_heatstroke_dlnm](articles/F126_heatstroke_dlnm) |
| F127 | 空き家は、人口が減った分だけ増えたのか？ | [F127_vacant_houses_decomposition](articles/F127_vacant_houses_decomposition) |
| F131 | 大学に進む人が増えると、地元に残る若者は減るのか？ | [F131_univ_youth_migration](articles/F131_univ_youth_migration) |
| F133 | 輸出先は、距離と経済規模でどこまで決まるのか？ | [F133_export_gravity](articles/F133_export_gravity) |
| F137 | 郵便物は、いつ半分になるのか？ | [F137_postal_decay](articles/F137_postal_decay) |
| F139 | 副業をしている人は、どんな働き方の人か？ | [F139_side_job_loglinear](articles/F139_side_job_loglinear) |
| F143 | 漁獲量の減り方は、魚の種類でどう違うのか？ | [F143_fish_catch_decline](articles/F143_fish_catch_decline) |
| F144 | 水道料金の差は、人口密度と水源でどこまで説明できるか？ | [F144_water_tariff_density](articles/F144_water_tariff_density) |
| F148 | 会社は「休眠」をはさんでどう移り変わるのか？ | [F148_dormancy_multistate](articles/F148_dormancy_multistate) |
| F149 | 生存分析を機械学習でやると、何が良くなるのか？ | [F149_ml_survival](articles/F149_ml_survival) |
| F150 | 季節のパターンそのものは、年々変わっているのか？ | [F150_dynamic_seasonality](articles/F150_dynamic_seasonality) |
| F151 | 47都道府県の求人倍率の「同じ動き」は、いくつに分けられるか？ | [F151_pref_hierarchical_dfm](articles/F151_pref_hierarchical_dfm) |
| F153 | 平均でなく「分布」で比べると、地域の差は何に見えるか？ | [F153_distribution_regional](articles/F153_distribution_regional) |
| F157 | 電力需要の予測を、1年通して運用したらどうなるか？ | [F157_power_forecast_operation](articles/F157_power_forecast_operation) |
| F158 | 地価の予測モデルは、毎年作り直す必要があるのか？ | [F158_land_price_update](articles/F158_land_price_update) |
| F159 | 出生数の予測を、毎月の速報で更新すると当たり方は変わるか？ | [F159_births_nowcast](articles/F159_births_nowcast) |
| F161 | 同じデータで記事を書き直すと、結論はどれだけ変わるか？ | [F161_rewrite_old_articles](articles/F161_rewrite_old_articles) |
| F163 | 125本の看板記事で、いちばん効いた頑健性チェックは何だったか？ | [F163_robustness_checks_review](articles/F163_robustness_checks_review) |
| F167 | 「100年に1度の大雨」は、本当に100年に1度なのか？ | [F167_return_period_heavy_rain](articles/F167_return_period_heavy_rain) |
| F170 | 産業の構成比を比べるとき、割合のまま回帰してよいか？ | [F170_compositional_industry_shares](articles/F170_compositional_industry_shares) |
| F171 | 人口ピラミッドの「形」は、いくつの型に分かれるか？ | [F171_pyramid_shape_fda](articles/F171_pyramid_shape_fda) |
| F174 | 景気の「局面」は、データから自動で見つけられるか？ | [F174_business_cycle_hmm_multiseries](articles/F174_business_cycle_hmm_multiseries) |
| F175 | 予測モデルの精度は、どの特徴量の「おかげ」なのか？ | [F175_r2_shapley_decomposition](articles/F175_r2_shapley_decomposition) |
| F179 | 欠測を埋める方法で、答えはどれだけ変わるか？ | [F179_imputation_by_estimand](articles/F179_imputation_by_estimand) |
| F180 | 2つの統計の数字は、本当に同じものを測っているか？ | [F180_measurement_agreement](articles/F180_measurement_agreement) |
| F190 | 暑い夏と寒い冬に、亡くなる人はどれだけ増えるのか？ | [F190_excess_deaths_temperature](articles/F190_excess_deaths_temperature) |
| F192 | 国債の金利は、何で動いているのか？ | [F192_jgb_yield_curve_pca](articles/F192_jgb_yield_curve_pca) |
| F197 | 地区をまとめて選ぶと、精度はどれだけ落ちるのか？ | [F197_cluster_sampling_deff](articles/F197_cluster_sampling_deff) |
| F200 | 200本の看板記事で使ったデータと手法は、どうつながっているか？ | [F200_method_data_network](articles/F200_method_data_network) |
| F205 | 予測モデルは、作る前に何を決め、外れをいくらと見て、いつ作り直すのか？ | [F205_power_forecast_practice_part1](articles/F205_power_forecast_practice_part1) |
| F206 | 予測は、エリアと合計をどうそろえ、どう見せ、1年回すと何が起きるのか？ | [F206_power_forecast_practice_part2](articles/F206_power_forecast_practice_part2) |
| F207 | 地価はどこで上がり、駅ができると何が起きるのか？ | [F207_landprice_series_part1](articles/F207_landprice_series_part1) |
| F208 | マンションの値段は地価とどう動き、地価の予測はどこで外れ続けるのか？ | [F208_landprice_series_part2](articles/F208_landprice_series_part2) |
| F209 | この5年の値上がりは、どの品目から来て、誰に重く、家計は何を減らしたのか？ | [F209_prices_household_series_part1](articles/F209_prices_household_series_part1) |
| F231 | 売上の予測は、何か月先まで役に立つのか？ | [F231_sales_forecast_horizon](articles/F231_sales_forecast_horizon) |
| F239 | 広告費は、売上にどれだけ効いているのか？ | [F239_marketing_mix_model](articles/F239_marketing_mix_model) |
| F240 | キャンペーンの効果を、比べる相手がないときにどう測るか？ | [F240_campaign_effect_no_control](articles/F240_campaign_effect_no_control) |
| F241 | 顧客はどれくらいで離れていくのか？ | [F241_customer_churn_survival](articles/F241_customer_churn_survival) |
| F245 | 1つの依頼に、1時間でどこまで答えられるか？ | [F245_one_hour_request](articles/F245_one_hour_request) |
| F250 | 売上が落ちた月に、理由を説明する（業務の再現：架空の会社で） シリーズ③の5本目。F247 の mart を使い、架空の | [F250_sales_drop_explanation_fictional_retail](articles/F250_sales_drop_explanation_fictional_retail) |
| F252 | 来期の予算のための需要予測（業務の再現：架空の会社で） シリーズ③の7本目。架空の食品スーパー「サンプルマート（架空）」 | [F252_budget_forecast_fictional_retail](articles/F252_budget_forecast_fictional_retail) |
| F255 | 1年の分析業務を振り返る（業務の再現：架空の会社で） シリーズ③の10本目・最後。架空の食品スーパー「サンプルマート（架 | [F255_year_review_fictional_retail](articles/F255_year_review_fictional_retail) |
| F259 | 需要予測の外れは、在庫と欠品のどちらに効かせるべきか？ | [F259_forecast_error_inventory_cost](articles/F259_forecast_error_inventory_cost) |
| F261 | 潜在成長率は、計算の仕方でどれだけ変わるのか？ | [F261_potential_growth_methods](articles/F261_potential_growth_methods) |
| F271 | 見られるダッシュボードと、見られないダッシュボードの違いは何か？ | [F271_dashboard_answer_cost](articles/F271_dashboard_answer_cost) |
| 019 | 1,740市区町村を「似た街」に分けてみた：k-means で5つのグループ、でも境目はあいまいだった | [019_municipal_clusters](articles/019_municipal_clusters) |
| 022 | 保育所を増やした県で、出生率は上がったか？ | [022_nursery_birthrate_fe](articles/022_nursery_birthrate_fe) |
| 044 | 2050年の人口推計は何で決まっているのか？ | [044_population_rf](articles/044_population_rf) |
| 133 | 私立小学校の学習費は公立の4.8倍。差の大部分は授業料や入学金で、公立中学生は塾代のほうが多かった | [133_school_expenses](articles/133_school_expenses) |
| 164 | 学習塾の受講生は2018年から1割減。それでも売上はトレンド通りに伸び、支えたのは1人当たりの受講料だった | [164_juku_sales](articles/164_juku_sales) |
| 286 | 予測モデルは、線形回帰と勾配ブースティングのどちらから始めるか？ | [286_linear_vs_gbm_first](articles/286_linear_vs_gbm_first) |
| 307 | 問い合わせの記録を、カテゴリに自動で分けられるか？ | [307_inquiry_text_classification](articles/307_inquiry_text_classification) |
| 310 | Kaggle：アンサンブルは、何本混ぜると効かなくなるのか？ | [310_kaggle_ensemble_size](articles/310_kaggle_ensemble_size) |
| 320 | 無事故の年数は、次の年の事故をどこまで当てるのか？ | [320_no_claim_years_predict](articles/320_no_claim_years_predict) |
| 361 | 予測の良し悪しは、物差しを変えるとどれだけ順位が入れ替わるのか？ | [361_forecast_metric_ranking](articles/361_forecast_metric_ranking) |
| 362 | 時系列をばらばらに分けて確かめると、予測の精度をどれだけ甘く見積もるのか？ | [362_shuffled_cv_time_series](articles/362_shuffled_cv_time_series) |
| 449 | 指標の単位をそろえないまま主成分分析をすると、第1主成分はどれだけ変わるのか？ | [449_pca_units_standardization](articles/449_pca_units_standardization) |
| 450 | k-means は、丸くないまとまりや大きさの違うまとまりを、どれだけ取り違えるのか？ | [450_kmeans_cluster_shapes](articles/450_kmeans_cluster_shapes) |
| 460 | 予測に「答えが漏れた列」が混ざると、確かめの成績はどれだけ良く見え、本番でどれだけ落ちるのか？ | [460_target_leakage_validation](articles/460_target_leakage_validation) |
| 470 | めったに起きない出来事の予測は、正解率で測るとどれだけ良く見えるのか？ | [470_rare_event_accuracy_paradox](articles/470_rare_event_accuracy_paradox) |
| 509 | 起きる割合が学習のときから変わると、0.5で切る予測は何件を見逃すのか？ | [509_prior_shift_threshold](articles/509_prior_shift_threshold) |
| 510 | 同じ検証データで2つのモデルを比べると、本当は同じ力でも何%の回で「片方が良い」と出るのか？ | [510_same_validation_model_tie](articles/510_same_validation_model_tie) |
| 536 | 乱数の種を変えるだけで、同じモデルの検証の成績は何ポイント揺れるのか？ | [536_seed_only_score_spread](articles/536_seed_only_score_spread) |
| 558 | 予測確率が「30%」と出た人のうち、本当に起きるのは何%なのか？ | [558_probability_calibration](articles/558_probability_calibration) |
| 576 | 時系列のデータをランダムに分けて確かめると、時間の順に分けた場合より成績はどれだけ良く見えるのか？ | [576_random_vs_time_split](articles/576_random_vs_time_split) |
| 587 | 同じテスト用データでモデルの調整を何度もくり返すと、テストの成績はどれだけ楽観的になるのか？ | [587_test_set_reuse](articles/587_test_set_reuse) |
| 608 | 件数の少ないクラスがあるとき、層化しない交差検証では何%の fold にそのクラスが入らないのか？ | [608_stratified_cv_rare_class](articles/608_stratified_cv_rare_class) |
| 609 | 交差検証の K を2・5・10・n と変えると、成績の見積もりの偏りとばらつきはどう変わるのか？ | [609_cv_fold_count_k](articles/609_cv_fold_count_k) |
| 617 | 時間で効き方の変わる要因に、Cox の比例ハザードモデルを当てると、ハザード比は何を表すのか？ | [617_cox_nonproportional_hazards](articles/617_cox_nonproportional_hazards) |
| 618 | 起きる割合が1%のとき、ROC の AUC と PR の AUC では、予測の良し悪しの見え方はどれだけ違うのか？ | [618_roc_vs_pr_auc_imbalance](articles/618_roc_vs_pr_auc_imbalance) |
| 628 | ランダムフォレストの不純度による重要度は、値の種類の多い列をどれだけ重く見るのか？ | [628_rf_impurity_importance_bias](articles/628_rf_impurity_importance_bias) |
| 629 | 相関の強い2つの列があると、並べ替えの重要度はどれだけ小さく出るのか？ | [629_permutation_importance_correlated](articles/629_permutation_importance_correlated) |
| 630 | Lasso で選ばれる変数は、データを少し変えるとどれだけ入れ替わるのか？ | [630_lasso_selection_stability](articles/630_lasso_selection_stability) |
| 636 | 件数が少なく変数が多いとき、リッジ回帰はふつうの回帰より予測の誤差をどれだけ減らすのか？ | [636_ridge_vs_ols_small_n](articles/636_ridge_vs_ols_small_n) |
| 637 | 決定木の深さを増やすと、学習のデータと新しいデータの成績はどこで分かれるのか？ | [637_tree_depth_overfit](articles/637_tree_depth_overfit) |
| 638 | 主成分の数を「固有値1以上」「累積80%」「並行分析」で選ぶと、本当の数を何%で当てるのか？ | [638_pca_number_of_components](articles/638_pca_number_of_components) |
| 639 | k-means の k をエルボーとシルエットで選ぶと、本当のまとまりの数を何%で当てるのか？ | [639_kmeans_choose_k](articles/639_kmeans_choose_k) |
| 686 | 単位をそろえずに Lasso をかけると、どの変数が選ばれやすくなるのか？ | [686_lasso_without_scaling](articles/686_lasso_without_scaling) |
| 687 | 勾配ブースティングの学習率を大きくすると、木の数を合わせても成績はどれだけ変わるのか？ | [687_boosting_learning_rate](articles/687_boosting_learning_rate) |
| 696 | AIC・BIC・交差検証で回帰の変数を選ぶと、本当の変数を何%当てるのか？ | [696_aic_bic_cv_selection](articles/696_aic_bic_cv_selection) |
| 710 | 効かない変数を足していくと、k近傍法の当たり方はどれだけ落ちるのか？ | [710_knn_dimension_curse](articles/710_knn_dimension_curse) |
| 716 | 交差検証でハイパーパラメータを選び、同じ交差検証の成績を報告すると、本当の成績よりどれだけよく見えるのか？ | [716_nested_cv_optimism](articles/716_nested_cv_optimism) |
| 728 | 決定木を学習データを少し入れ替えて作り直すと、最初の分かれ目の変数は何%で入れ替わるのか？ | [728_tree_instability](articles/728_tree_instability) |
| 729 | t-SNE の2次元の図で、まとまりの大きさや間の距離は、元のデータをどれだけ映しているのか？ | [729_tsne_perplexity_clusters](articles/729_tsne_perplexity_clusters) |
| 730 | 階層クラスタリングのつなぎ方（最短・最長・群平均・ウォード）で、本当のまとまりを何%で当てるのか？ | [730_hierarchical_linkage](articles/730_hierarchical_linkage) |
| 747 | ランダムフォレストの OOB 誤差は、交差検証の誤差やテストの誤差とどれだけ合うのか？ | [747_rf_oob_vs_cv](articles/747_rf_oob_vs_cv) |
| 758 | 件数が少ないとき、モデルの「上位10%のリフト」はどれだけ揺れるのか？ | [758_top_decile_lift_noise](articles/758_top_decile_lift_noise) |
| 759 | 正解のラベルが1割まちがっていると、モデルの正解率はどれだけ低く見えるのか？ | [759_label_noise_evaluation](articles/759_label_noise_evaluation) |
| 766 | カテゴリを「目的変数の平均」で置きかえて学習すると、学習データの成績はどれだけよく見えるのか？ | [766_target_encoding_leak](articles/766_target_encoding_leak) |
| 769 | 交差検証の fold ごとの成績から出した標準誤差は、本当のばらつきをどれだけ小さく見るのか？ | [769_k_fold_se_underestimate](articles/769_k_fold_se_underestimate) |
| 770 | 傾向スコアか結果のモデルのどちらかがまちがっているとき、二重に頑健な推定はどれだけずれるのか？ | [770_doubly_robust](articles/770_doubly_robust) |
| 779 | 混合正規分布を EM 法で当てはめると、初期値によって何%の回で別の答えになるのか？ | [779_em_initialization](articles/779_em_initialization) |
| 780 | DBSCAN の eps を少し変えると、まとまりの数と外れ値の数はどれだけ変わるのか？ | [780_dbscan_eps](articles/780_dbscan_eps) |
| 788 | 変数選びを交差検証の前に全部のデータでやると、関係のないデータでも正解率はどれだけ高く出るのか？ | [788_feature_selection_leak](articles/788_feature_selection_leak) |
| 789 | 学習とテストを1回だけ分けたとき、テストの成績はどれだけ振れるのか？ | [789_single_split_variance](articles/789_single_split_variance) |
| 790 | 学習データを2倍にすると、テストの誤差はどれだけ減り、どこで頭打ちになるのか？ | [790_learning_curve](articles/790_learning_curve) |

</details>

<details><summary><b>顧客分析・生存分析</b>（67本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F07 | 新卒は何年目に辞めやすいのか？ | [F07_turnover_survival](articles/F07_turnover_survival) |
| F28 | 法人は何年続くのか？ | [F28_corporate_survival](articles/F28_corporate_survival) |
| F79 | 会社の終わり方は「閉鎖」か「合併」か？ | [F79_closure_vs_merger](articles/F79_closure_vs_merger) |
| F87 | 結婚が減ったのは「時代」のせいか「世代」のせいか？ | [F87_marriage_apc](articles/F87_marriage_apc) |
| F105 | 閉鎖を数年おきの調査でしか確かめられないと、生存曲線はどこまでずれるか？ | [F105_interval_censoring](articles/F105_interval_censoring) |
| F106 | 同じ県の会社は、同じように閉鎖しやすいのか？ | [F106_shared_frailty](articles/F106_shared_frailty) |
| F142 | 森林は、「切れる木」がどれだけ増えたのか？ | [F142_forest_age_harvest](articles/F142_forest_age_harvest) |
| F148 | 会社は「休眠」をはさんでどう移り変わるのか？ | [F148_dormancy_multistate](articles/F148_dormancy_multistate) |
| F149 | 生存分析を機械学習でやると、何が良くなるのか？ | [F149_ml_survival](articles/F149_ml_survival) |
| F241 | 顧客はどれくらいで離れていくのか？ | [F241_customer_churn_survival](articles/F241_customer_churn_survival) |
| F246 | 分析担当として最初にやること：KPI を決める（業務の再現：架空の会社で） シリーズ③の1本目。架空の食品スーパー「サン | [F246_kpi_definitions_fictional_retail](articles/F246_kpi_definitions_fictional_retail) |
| F251 | 販促の効果を測る（業務の再現：架空の会社で） シリーズ③の6本目。F247 の mart の架空の食品スーパー「サンプル | [F251_promo_effect_fictional_retail](articles/F251_promo_effect_fictional_retail) |
| F264 | 自動車の事故率は、高齢化でどこまで説明できるのか？ | [F264_auto_accident_rate_aging](articles/F264_auto_accident_rate_aging) |
| F279 | RFM で分けた顧客は、その後どう動くのか？ | [F279_rfm_segment_transitions](articles/F279_rfm_segment_transitions) |
| 245 | 顧客の重複を SQL で片づけるとき、どのキーで同じ人とみなすか？ | [245_sql_dedup_customers](articles/245_sql_dedup_customers) |
| 286 | 予測モデルは、線形回帰と勾配ブースティングのどちらから始めるか？ | [286_linear_vs_gbm_first](articles/286_linear_vs_gbm_first) |
| 312 | SQL の NULL は、集計をどれだけ黙ってずらすのか？ | [312_sql_null_aggregation](articles/312_sql_null_aggregation) |
| 326 | 古いシステムから新しいシステムへ移したデータは、何を照合すれば「同じ」と言えるか？ | [326_migration_reconciliation](articles/326_migration_reconciliation) |
| 344 | 「アクティブな顧客」は、定義でどれだけ人数が変わるのか？ | [344_active_customer_definitions](articles/344_active_customer_definitions) |
| 365 | 似た相手を選んで比べる方法は、測っていない違いがあるとどこまで外れるのか？ | [365_matching_unmeasured_confounder](articles/365_matching_unmeasured_confounder) |
| 372 | CSV を Excel で開いて保存すると、何セルが変わってしまうのか？ | [372_csv_excel_roundtrip](articles/372_csv_excel_roundtrip) |
| 386 | 「以上」と「超」、「以下」と「未満」を取り違えると、何件が別の区分に入るのか？ | [386_boundary_inclusive_exclusive](articles/386_boundary_inclusive_exclusive) |
| 387 | チェックデジットは、打ち間違いの何割を止めるのか？ | [387_check_digit_detection](articles/387_check_digit_detection) |
| 388 | 登録月ごとの継続率の表で、まだ観測できていない月を0と数えると、どれだけ低く出るのか？ | [388_cohort_retention_censoring](articles/388_cohort_retention_censoring) |
| 403 | ORDER BY のない SELECT の並びに頼ると、結果はどれだけ再現しないのか？ | [403_select_without_order_by](articles/403_select_without_order_by) |
| 407 | 名前を消しただけの顧客データは、何%の人が1人に絞れてしまうのか？ | [407_k_anonymity_customer_data](articles/407_k_anonymity_customer_data) |
| 413 | 途中で解約した契約に返す保険料は、日割りと短期率でどれだけ違うのか？ | [413_cancellation_refund_methods](articles/413_cancellation_refund_methods) |
| 428 | 文字コードを取り違えて CSV を読むと、何行が壊れ、何行が黙って通るのか？ | [428_csv_encoding_mismatch](articles/428_csv_encoding_mismatch) |
| 432 | 死亡率の将来の下がり方を過去から延ばす方法は、正解の分かるデータでどれだけ当たるのか？ | [432_lee_carter_known_truth](articles/432_lee_carter_known_truth) |
| 453 | 数字が文字として入った列を並べ替えると、何件が違う順番になるのか？ | [453_numbers_stored_as_text](articles/453_numbers_stored_as_text) |
| 460 | 予測に「答えが漏れた列」が混ざると、確かめの成績はどれだけ良く見え、本番でどれだけ落ちるのか？ | [460_target_leakage_validation](articles/460_target_leakage_validation) |
| 475 | 解約率は、分母の取り方でどれだけ違って見えるのか？ | [475_churn_rate_denominator](articles/475_churn_rate_denominator) |
| 482 | ポイントの失効を「付与日から1年」と「月末に一括」にすると、2025〜2026年の失効額と月の数字はどれだけ変わるのか？ | [482_point_expiry_rules](articles/482_point_expiry_rules) |
| 485 | 論理削除のフラグと履歴の期間を見落とすと、注文の件数と売上は何%多く出るのか？ | [485_soft_delete_flags](articles/485_soft_delete_flags) |
| 490 | 解約率の仮定が実際とずれると、保険の将来の利益の見込みはどれだけ動くのか？ | [490_lapse_assumption_profit_sensitivity](articles/490_lapse_assumption_profit_sensitivity) |
| 495 | 会員ランクを「暦年」と「直近12か月」で判定すると、2025年の12月には何%の会員のランクが食い違うのか？ | [495_member_rank_calendar_vs_rolling](articles/495_member_rank_calendar_vs_rolling) |
| 504 | 取消された注文を残したまま初回購入月を決めると、新規顧客の数は何%多く出るのか？ | [504_first_purchase_month_cancellations](articles/504_first_purchase_month_cancellations) |
| 505 | 定期便の次回のお届け日を「30日後」と「毎月同じ日」で決めると、1年の出荷回数と月の出荷数はどれだけ違うのか？ | [505_subscription_next_delivery_rules](articles/505_subscription_next_delivery_rules) |
| 535 | 顧客の年齢を「登録したときの年齢」のまま集計すると、年代別の構成は何年でどれだけずれるのか？ | [535_age_at_registration_drift](articles/535_age_at_registration_drift) |
| 558 | 予測確率が「30%」と出た人のうち、本当に起きるのは何%なのか？ | [558_probability_calibration](articles/558_probability_calibration) |
| 572 | 同じ時刻の行が並ぶとき、ROW_NUMBERで「最新の1行」を選ぶと、実行のたびに何件入れ替わるのか？ | [572_row_number_ties](articles/572_row_number_ties) |
| 573 | 会員の「休眠」を最終購入から90日で切るか180日で切るかで、休眠の人数と「復活」の割合はどれだけ変わるのか？ | [573_dormant_threshold_days](articles/573_dormant_threshold_days) |
| 575 | 顧客が引っ越したとき、売上を「売った時点の住所」で数えるか「今の住所」で数えるかで、地域別の売上はどれだけ動くのか？ | [575_address_at_sale_vs_now](articles/575_address_at_sale_vs_now) |
| 584 | 同じ人が別のIDで登録された顧客表を、電話・メール・氏名＋生年月日で寄せると、顧客数とリピート率はどれだけ変わるのか？ | [584_customer_dedup_keys](articles/584_customer_dedup_keys) |
| 601 | 外部結合（LEFT JOIN）のあと WHERE で右の表の列を絞ると、何件の行が黙って消えるのか？ | [601_left_join_where_filter](articles/601_left_join_where_filter) |
| 608 | 件数の少ないクラスがあるとき、層化しない交差検証では何%の fold にそのクラスが入らないのか？ | [608_stratified_cv_rare_class](articles/608_stratified_cv_rare_class) |
| 615 | 顧客の生涯の売上を「月の購入額÷退会率」で出すと、登録月ごとの実績からどれだけずれるのか？ | [615_ltv_simple_vs_cohort](articles/615_ltv_simple_vs_cohort) |
| 622 | 「新規の顧客」を過去何年さかのぼって判定するかで、新規の割合はどれだけ変わるのか？ | [622_new_customer_lookback](articles/622_new_customer_lookback) |
| 632 | マスタは今日、明細は昨日の時点の表をつなぐと、何件が片方にしかないのか？ | [632_master_detail_snapshot_lag](articles/632_master_detail_snapshot_lag) |
| 634 | CASE WHEN の条件の並べ方で、何件が別の区分に入るのか？ | [634_case_when_order](articles/634_case_when_order) |
| 643 | キャンペーンを使った人と使わなかった人を比べると、効果が0でもどれだけ差が出るのか？ | [643_campaign_users_self_selection](articles/643_campaign_users_self_selection) |
| 651 | ページの滞在時間を「次のページを開いた時刻との差」で測ると、最後に見たページの分はどれだけ抜け落ちるのか？ | [651_last_page_dwell_time](articles/651_last_page_dwell_time) |
| 654 | 大文字と小文字を区別するかしないかで、GROUP BY の件数とつながる行はどれだけ変わるのか？ | [654_collation_case_grouping](articles/654_collation_case_grouping) |
| 655 | 平均の購入間隔を「2回以上買った人」だけで出すと、本当の間隔よりどれだけ短く出るのか？ | [655_purchase_interval_selection](articles/655_purchase_interval_selection) |
| 665 | 会員カードを出した客だけで客単価を見ると、店全体の客単価よりどれだけ高く出るのか？ | [665_member_card_spend_bias](articles/665_member_card_spend_bias) |
| 670 | 退会と転居の2つの理由で会員が抜けるとき、片方を打ち切りにした生存曲線は、退会の割合をどれだけ大きく見るのか？ | [670_competing_risks](articles/670_competing_risks) |
| 691 | 同じ顧客の重複行から「最初」と「最新」のどちらを残すかで、属性の集計はどれだけ変わるのか？ | [691_dedup_keep_first_or_last](articles/691_dedup_keep_first_or_last) |
| 704 | 年齢を「年の差」だけで出すと、誕生日前の会員は何%が1歳多く数えられるのか？ | [704_age_datediff_year](articles/704_age_datediff_year) |
| 705 | リピート率を「30日以内」で数えるか「90日以内」で数えるかで、月ごとの比べ方はどれだけ変わるのか？ | [705_repeat_rate_window](articles/705_repeat_rate_window) |
| 725 | 購入回数で顧客を5等分すると、同じ回数の人が別の段に分かれるのはどれだけか？ | [725_rfm_quintile_ties](articles/725_rfm_quintile_ties) |
| 731 | 「上位10%の顧客で売上の何割」を、買わなかった会員を含めて数えるか除くかで、どれだけ違うのか？ | [731_top_share_zero_customers](articles/731_top_share_zero_customers) |
| 734 | 「1回1万円以上の注文がある顧客」と「合計1万円以上の顧客」を取り違えると、何人がずれるのか？ | [734_where_vs_having](articles/734_where_vs_having) |
| 742 | LEFT JOIN のあと COUNT(*) で注文数を数えると、注文0件の顧客は何件と数えられるのか？ | [742_left_join_count_star](articles/742_left_join_count_star) |
| 743 | 退会した会員の番号を新しい会員に使い回すと、何人の新しい会員に前の人の購入がつくのか？ | [743_id_reuse_history](articles/743_id_reuse_history) |
| 744 | 会員番号の偶数と奇数で2群に分けると、番号の振り方によって群の間にどれだけ差が出るのか？ | [744_id_parity_split](articles/744_id_parity_split) |
| 748 | ある日に「利用中」の会員だけに聞くと、平均の利用期間は本当の何倍に見えるのか？ | [748_length_biased_sampling](articles/748_length_biased_sampling) |
| 763 | 継続月数を0から数えるか1から数えるかで、継続率の表はどれだけずれて読まれるのか？ | [763_month_index_zero_one](articles/763_month_index_zero_one) |

</details>

<details><summary><b>SQL・データ処理</b>（105本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F12 | 公的統計を毎月自動で更新するには？ | [F12_stats_pipeline](articles/F12_stats_pipeline) |
| F85 | 日本経済の「要」の産業はどれか？ | [F85_io_network](articles/F85_io_network) |
| F96 | e-Statの数万の統計表から、欲しい表をすぐ探せるか？ | [F96_estat_semantic_search](articles/F96_estat_semantic_search) |
| F122 | 手法ごとに、どこでつまずいたか？ | [F122_pitfalls_from_logs](articles/F122_pitfalls_from_logs) |
| F124 | 同じデータを何本の記事で使い回したか？ | [F124_data_lineage_network](articles/F124_data_lineage_network) |
| F125 | 100本を超えた看板記事で、「見えなかった」はどれくらいあったか？ | [F125_null_results_review](articles/F125_null_results_review) |
| F162 | 公的データは「API で取れる」のか？ | [F162_data_access_map](articles/F162_data_access_map) |
| F163 | 125本の看板記事で、いちばん効いた頑健性チェックは何だったか？ | [F163_robustness_checks_review](articles/F163_robustness_checks_review) |
| F176 | 白書の文章は、年々読みやすくなったのか？ | [F176_whitepaper_readability](articles/F176_whitepaper_readability) |
| F181 | 家が建つ数は、金利と人口のどちらで決まるのか？ | [F181_housing_starts_rates_population](articles/F181_housing_starts_rates_population) |
| F231 | 売上の予測は、何か月先まで役に立つのか？ | [F231_sales_forecast_horizon](articles/F231_sales_forecast_horizon) |
| F232 | 店の種類ごとの予測と全体の予測を、どうそろえるか？ | [F232_hierarchical_retail_reconciliation](articles/F232_hierarchical_retail_reconciliation) |
| F233 | 祝日・連休・天気は、売上をどれだけ動かすのか？ | [F233_calendar_weather_sales](articles/F233_calendar_weather_sales) |
| F234 | 価格を1%上げると、買われる量は何%減るのか？ | [F234_price_elasticity_practice](articles/F234_price_elasticity_practice) |
| F235 | 在庫はどれだけ持てばよいのか？ | [F235_inventory_newsvendor](articles/F235_inventory_newsvendor) |
| F236 | A/B テストは、何人集めれば「差」が分かるのか？ | [F236_ab_test_sample_size](articles/F236_ab_test_sample_size) |
| F237 | A/B テストを途中で見ると、何がまずいのか？ | [F237_ab_test_peeking_sequential](articles/F237_ab_test_peeking_sequential) |
| F238 | 前の期間のデータを使うと、テストはどれだけ早く終わるか？ | [F238_ab_test_cuped](articles/F238_ab_test_cuped) |
| F239 | 広告費は、売上にどれだけ効いているのか？ | [F239_marketing_mix_model](articles/F239_marketing_mix_model) |
| F240 | キャンペーンの効果を、比べる相手がないときにどう測るか？ | [F240_campaign_effect_no_control](articles/F240_campaign_effect_no_control) |
| F241 | 顧客はどれくらいで離れていくのか？ | [F241_customer_churn_survival](articles/F241_customer_churn_survival) |
| F242 | 毎日の KPI の「いつもと違う」を、どう自動で知らせるか？ | [F242_kpi_anomaly_alerts](articles/F242_kpi_anomaly_alerts) |
| F243 | どの指標を見れば、売上の変化の理由が分かるのか？ | [F243_kpi_tree_decomposition](articles/F243_kpi_tree_decomposition) |
| F244 | 集計の SQL は、どう書けば間違えにくいか？ | [F244_sql_aggregation_pitfalls](articles/F244_sql_aggregation_pitfalls) |
| F245 | 1つの依頼に、1時間でどこまで答えられるか？ | [F245_one_hour_request](articles/F245_one_hour_request) |
| F246 | 分析担当として最初にやること：KPI を決める（業務の再現：架空の会社で） シリーズ③の1本目。架空の食品スーパー「サン | [F246_kpi_definitions_fictional_retail](articles/F246_kpi_definitions_fictional_retail) |
| F247 | データを集めて、使える形に整える（業務の再現：架空の会社で） シリーズ③の2本目。F246 の合成データ「サンプルマート | [F247_data_mart_fictional_retail](articles/F247_data_mart_fictional_retail) |
| F248 | 月次レポートの「型」を作る（業務の再現：架空の会社で） シリーズ③の3本目。F246 の KPI 定義 v1 と F24 | [F248_monthly_report_template_fictional_retail](articles/F248_monthly_report_template_fictional_retail) |
| F249 | ダッシュボードを作る（業務の再現：架空の会社で） シリーズ③の続き。F246 の KPI 定義 v1 と F247 の  | [F249_powerbi_dashboard_fictional_retail](articles/F249_powerbi_dashboard_fictional_retail) |
| F250 | 売上が落ちた月に、理由を説明する（業務の再現：架空の会社で） シリーズ③の5本目。F247 の mart を使い、架空の | [F250_sales_drop_explanation_fictional_retail](articles/F250_sales_drop_explanation_fictional_retail) |
| F251 | 販促の効果を測る（業務の再現：架空の会社で） シリーズ③の6本目。F247 の mart の架空の食品スーパー「サンプル | [F251_promo_effect_fictional_retail](articles/F251_promo_effect_fictional_retail) |
| F252 | 来期の予算のための需要予測（業務の再現：架空の会社で） シリーズ③の7本目。架空の食品スーパー「サンプルマート（架空）」 | [F252_budget_forecast_fictional_retail](articles/F252_budget_forecast_fictional_retail) |
| F253 | データの品質を毎月チェックする（業務の再現：架空の会社で） シリーズ③の8本目。架空の食品スーパー「サンプルマート（架空 | [F253_monthly_data_quality_checks_fictional_retail](articles/F253_monthly_data_quality_checks_fictional_retail) |
| F254 | 分析を引き継げる形にする（業務の再現：架空の会社で） シリーズ③の9本目。F246〜F251（コミット e5e9800） | [F254_handover_package_fictional_retail](articles/F254_handover_package_fictional_retail) |
| F259 | 需要予測の外れは、在庫と欠品のどちらに効かせるべきか？ | [F259_forecast_error_inventory_cost](articles/F259_forecast_error_inventory_cost) |
| F271 | 見られるダッシュボードと、見られないダッシュボードの違いは何か？ | [F271_dashboard_answer_cost](articles/F271_dashboard_answer_cost) |
| F275 | 集計の SQL は、どう書けば直しやすく、直し忘れに気づけるか？ | [F275_sql_change_requests](articles/F275_sql_change_requests) |
| 232 | 前年同月比と12か月移動平均は、SQL のウィンドウ関数だけで出せる。ただし月が1つ抜けると、LAG は12か月分の前年 | [232_sql_window_yoy_moving_avg](articles/232_sql_window_yoy_moving_avg) |
| 233 | 集計の合計が会計の数字と合わないとき、SQL のどこから疑うか？ | [233_sql_reconcile_totals](articles/233_sql_reconcile_totals) |
| 243 | 縦長の統計表をレポートの形にする SQL は、CASE WHEN で書ける。ただし業態が1つ増えると、その行は黙って落ち | [243_sql_pivot_report](articles/243_sql_pivot_report) |
| 245 | 顧客の重複を SQL で片づけるとき、どのキーで同じ人とみなすか？ | [245_sql_dedup_customers](articles/245_sql_dedup_customers) |
| 260 | 取り込む前のチェックは、壊れたファイルをどこまで止めるか？ | [260_schema_validation_injected](articles/260_schema_validation_injected) |
| 261 | データ辞書（列の説明書）は、何を書くと役に立つのか？ | [261_data_dictionary_ssdse](articles/261_data_dictionary_ssdse) |
| 270 | 市町村の合併を、SQL でどう扱うか？ | [270_sql_municipal_code_scd2](articles/270_sql_municipal_code_scd2) |
| 283 | 食料品の輸出は、どの品目で伸びたのか？ | [283_food_exports_by_item](articles/283_food_exports_by_item) |
| 294 | SQL のクエリが遅いとき、まず何を見るか？ | [294_slow_query_first_checks](articles/294_slow_query_first_checks) |
| 295 | 集計をストアドプロシージャにまとめると、何がうれしいのか？ | [295_stored_procedure_params](articles/295_stored_procedure_params) |
| 301 | 公的統計の CSV を、SQL Server に毎月取り込む形はどう作るか？ | [301_sql_monthly_csv_load](articles/301_sql_monthly_csv_load) |
| 311 | 表をつなぐと、合計はなぜ増えたり減ったりするのか？ | [311_sql_join_fanout](articles/311_sql_join_fanout) |
| 312 | SQL の NULL は、集計をどれだけ黙ってずらすのか？ | [312_sql_null_aggregation](articles/312_sql_null_aggregation) |
| 313 | 月の集計で、月末の最終日はどれだけ落ちているのか？ | [313_sql_month_end_boundary](articles/313_sql_month_end_boundary) |
| 314 | 契約の「在籍件数」を、SQL でどう数えるか？ | [314_sql_policy_exposure](articles/314_sql_policy_exposure) |
| 315 | 1年分の保険料を、月ごとの売上にどう分けるか？ | [315_sql_earned_premium](articles/315_sql_earned_premium) |
| 326 | 古いシステムから新しいシステムへ移したデータは、何を照合すれば「同じ」と言えるか？ | [326_migration_reconciliation](articles/326_migration_reconciliation) |
| 327 | C# の Math.Round と SQL Server の ROUND と Excel の ROUND は、同じ答えを返すのか？ | [327_rounding_csharp_sql_excel](articles/327_rounding_csharp_sql_excel) |
| 330 | 同じファイルを2回取り込んでも、数字が二重にならない形はどう作るか？ | [330_idempotent_load](articles/330_idempotent_load) |
| 359 | 累計を出すウィンドウ関数は、同じ日付の行があると何がずれるのか？ | [359_running_total_ties](articles/359_running_total_ties) |
| 360 | 「上位3件」を取る SQL は、同じ点数があると何件返すのか？ | [360_top3_with_ties](articles/360_top3_with_ties) |
| 372 | CSV を Excel で開いて保存すると、何セルが変わってしまうのか？ | [372_csv_excel_roundtrip](articles/372_csv_excel_roundtrip) |
| 373 | pandas で型を指定せずに読むと、何列が意図と違う型になるのか？ | [373_pandas_dtype_inference](articles/373_pandas_dtype_inference) |
| 375 | 全角と半角、前後の空白で、キーはどれだけつながらないのか？ | [375_key_normalization_join](articles/375_key_normalization_join) |
| 381 | どのライブラリを、何本の記事で使ったか？ | [381_libraries_used](articles/381_libraries_used) |
| 401 | 集計用の表は、1枚の大きな表と、事実とマスタに分けた表のどちらが直しやすいか？ | [401_wide_table_vs_star_schema](articles/401_wide_table_vs_star_schema) |
| 403 | ORDER BY のない SELECT の並びに頼ると、結果はどれだけ再現しないのか？ | [403_select_without_order_by](articles/403_select_without_order_by) |
| 404 | SQL を書き直したとき、結果が同じだとどう確かめるか？ | [404_sql_rewrite_equivalence](articles/404_sql_rewrite_equivalence) |
| 406 | SQL の見直しの観点10個を、自分の記事の SQL に当てると何件引っかかるか？ | [406_sql_review_checklist_hits](articles/406_sql_review_checklist_hits) |
| 411 | 「保険年齢」と「満年齢」では、同じ契約者の年齢区分はどれだけ変わるのか？ | [411_insurance_age_vs_attained_age](articles/411_insurance_age_vs_attained_age) |
| 428 | 文字コードを取り違えて CSV を読むと、何行が壊れ、何行が黙って通るのか？ | [428_csv_encoding_mismatch](articles/428_csv_encoding_mismatch) |
| 455 | 1ページずつ順に取り込むと、途中で行が増減したとき、何行が重なり、何行が抜けるのか？ | [455_pagination_drift_during_load](articles/455_pagination_drift_during_load) |
| 463 | 連番のはずの番号の抜けと重複は、どの確かめ方で何件見つかるのか？ | [463_sequence_gaps_duplicates](articles/463_sequence_gaps_duplicates) |
| 464 | 短くしたハッシュをキーにすると、何行から衝突が起き、何行がまちがってつながるのか？ | [464_truncated_hash_key_collisions](articles/464_truncated_hash_key_collisions) |
| 491 | 本文の12%に改行があるCSVを行で分けて読むと、1万件のうち何件が壊れるのか？ | [491_csv_embedded_newlines](articles/491_csv_embedded_newlines) |
| 493 | ファイル名の日付で取り込み対象を選ぶと、1年365ファイルのうち遅れて置かれた何件を落とすのか？ | [493_file_selection_late_arrivals](articles/493_file_selection_late_arrivals) |
| 534 | アンケートの「その他」の自由記述を選択肢に振り直すと、各選択肢の割合は何ポイント動くのか？ | [534_survey_other_recode](articles/534_survey_other_recode) |
| 595 | 「完了」「済」「済み」のように表記の揺れたステータス列をそのまま GROUP BY すると、何%の行が別のグループに分かれるのか？ | [595_status_label_variants](articles/595_status_label_variants) |
| 601 | 外部結合（LEFT JOIN）のあと WHERE で右の表の列を絞ると、何件の行が黙って消えるのか？ | [601_left_join_where_filter](articles/601_left_join_where_filter) |
| 612 | 住所を「LIKE '%桜ヶ丘%'」のような部分一致で探すと、何件を余分に拾い、何件を取りこぼすのか？ | [612_like_partial_match_address](articles/612_like_partial_match_address) |
| 623 | 差分の取り込みを「更新日時が前回より後」で行うと、何件が取りこぼされるのか？ | [623_incremental_load_updated_at](articles/623_incremental_load_updated_at) |
| 633 | 送り直しで二重に届いたイベントを除かずに数えると、申込みの数は何%多くなるのか？ | [633_event_retry_duplicates](articles/633_event_retry_duplicates) |
| 635 | ROLLUP の小計の行と、もともと区分が空の行を取り違えると、合計はどれだけずれるのか？ | [635_rollup_null_grouping](articles/635_rollup_null_grouping) |
| 654 | 大文字と小文字を区別するかしないかで、GROUP BY の件数とつながる行はどれだけ変わるのか？ | [654_collation_case_grouping](articles/654_collation_case_grouping) |
| 662 | UNION と UNION ALL を取り違えると、何件の行が消えたり残ったりするのか？ | [662_union_vs_union_all](articles/662_union_vs_union_all) |
| 663 | ウィンドウ関数の PARTITION BY を書き忘れると、店ごとの累計や順位はどれだけ狂うのか？ | [663_window_partition_missing](articles/663_window_partition_missing) |
| 671 | 重複して登録した人を除かずに抽選すると、その人の当選確率は何倍になるのか？ | [671_lottery_duplicate_entries](articles/671_lottery_duplicate_entries) |
| 675 | DISTINCT で重複を消すと、本当に2回あった同じ内容の取引は何件消えるのか？ | [675_distinct_true_duplicates](articles/675_distinct_true_duplicates) |
| 683 | 品名に「_」や「%」を含む行を LIKE で探すと、何件を取り違えるのか？ | [683_like_escape_wildcards](articles/683_like_escape_wildcards) |
| 684 | 桁区切りのカンマが入った数字を CSV に書き出すと、読み込みで何列がずれるのか？ | [684_csv_thousands_separator](articles/684_csv_thousands_separator) |
| 685 | Excel の COUNTIF で「*」や「?」を含む品名を数えると、何件を多く数えるのか？ | [685_countif_wildcards](articles/685_countif_wildcards) |
| 691 | 同じ顧客の重複行から「最初」と「最新」のどちらを残すかで、属性の集計はどれだけ変わるのか？ | [691_dedup_keep_first_or_last](articles/691_dedup_keep_first_or_last) |
| 703 | 売上のない月が行ごと抜けた表で LAG を使って前月比を出すと、何行が2か月前と比べてしまうのか？ | [703_lag_missing_months](articles/703_lag_missing_months) |
| 715 | 取り込み元に同じキーが2行ある状態で MERGE（UPSERT）すると、何件の値が意図と違う行で上書きされるのか？ | [715_merge_duplicate_source](articles/715_merge_duplicate_source) |
| 721 | 2つの列を区切りなしでつないでキーにすると、別の組み合わせが同じキーになる行は何件あるのか？ | [721_concat_key_collision](articles/721_concat_key_collision) |
| 722 | 整数の列を SQL Server の AVG で平均すると、小数の切り捨てで店ごとの平均はどれだけずれるのか？ | [722_avg_integer_truncation](articles/722_avg_integer_truncation) |
| 733 | 見出し行つきの CSV を何本も縦につなぐと、見出し行が何行まざり、数の列はどうなるのか？ | [733_repeated_header_rows](articles/733_repeated_header_rows) |
| 742 | LEFT JOIN のあと COUNT(*) で注文数を数えると、注文0件の顧客は何件と数えられるのか？ | [742_left_join_count_star](articles/742_left_join_count_star) |
| 751 | PIVOT の列を固定で書いておくと、あとから増えた区分の売上は何%消えるのか？ | [751_pivot_fixed_columns](articles/751_pivot_fixed_columns) |
| 752 | 先頭に BOM のついた CSV を csv モジュールで読むと、最初の列名が一致せず、何行の売上が黙って集計から落ちるのか？ | [752_csv_bom_header](articles/752_csv_bom_header) |
| 755 | 時刻つきの日時のまま GROUP BY すると、日ごとの集計は何行に分かれてしまうのか？ | [755_group_by_datetime_not_date](articles/755_group_by_datetime_not_date) |
| 762 | 申込率を小数の桁の少ない DECIMAL に入れると、率はどれだけ丸まり、店の順位はどれだけ入れ替わるのか？ | [762_decimal_scale_division](articles/762_decimal_scale_division) |
| 764 | pandas の groupby が欠けたキーの行を黙って落とすと、合計はどれだけ減るのか？ | [764_pandas_groupby_dropna](articles/764_pandas_groupby_dropna) |
| 765 | 「NA」という区分名を pandas で読むと、何行が欠けた値になってしまうのか？ | [765_pandas_na_string](articles/765_pandas_na_string) |
| 771 | 104万行を超える CSV を Excel で開くと、どれだけの行と売上が消えるのか？ | [771_excel_row_limit](articles/771_excel_row_limit) |
| 773 | 列の順番が違う2つの表を UNION ALL でつなぐと、何行の値が別の列に入るのか？ | [773_union_column_order](articles/773_union_column_order) |
| 791 | 0で割るのを NULLIF で避けると、その店は平均から黙って消え、全体の率はどれだけ変わるのか？ | [791_nullif_drop_from_avg](articles/791_nullif_drop_from_avg) |
| 793 | 空の文字と NULL を区別せずに数えると、未入力の件数はどれだけずれるのか？ | [793_empty_string_vs_null](articles/793_empty_string_vs_null) |

</details>

<details><summary><b>Excel</b>（13本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F170 | 産業の構成比を比べるとき、割合のまま回帰してよいか？ | [F170_compositional_industry_shares](articles/F170_compositional_industry_shares) |
| 279 | 手作業の月次 Excel レポートを、Python でどう自動にするか？ | [279_excel_report_automation](articles/279_excel_report_automation) |
| 327 | C# の Math.Round と SQL Server の ROUND と Excel の ROUND は、同じ答えを返すのか？ | [327_rounding_csharp_sql_excel](articles/327_rounding_csharp_sql_excel) |
| 372 | CSV を Excel で開いて保存すると、何セルが変わってしまうのか？ | [372_csv_excel_roundtrip](articles/372_csv_excel_roundtrip) |
| 374 | VLOOKUP は、どんなときに黙って間違った値を返すのか？ | [374_vlookup_silent_errors](articles/374_vlookup_silent_errors) |
| 474 | 見出しを結合セルや空欄で省いた Excel の表を読むと、何行が区分を失うのか？ | [474_blank_headings_filldown](articles/474_blank_headings_filldown) |
| 492 | Excelの日付のシリアル値を読み替えるとき、起点の取り違えで何行が何日ずれるのか？ | [492_excel_serial_dates](articles/492_excel_serial_dates) |
| 515 | Excel の SUM でフィルタで隠した行も含めて合計すると、表の合計は何%多くなるのか？ | [515_excel_sum_vs_subtotal_hidden](articles/515_excel_sum_vs_subtotal_hidden) |
| 685 | Excel の COUNTIF で「*」や「?」を含む品名を数えると、何件を多く数えるのか？ | [685_countif_wildcards](articles/685_countif_wildcards) |
| 714 | 空白のセルと0のセルが混ざった列を Excel の AVERAGE で平均すると、値はどれだけ変わるのか？ | [714_excel_average_blank_zero](articles/714_excel_average_blank_zero) |
| 741 | 16桁以上の番号を Excel で開くと、何件の番号が別の値に変わり、何件が同じ番号になるのか？ | [741_excel_15_digit_ids](articles/741_excel_15_digit_ids) |
| 771 | 104万行を超える CSV を Excel で開くと、どれだけの行と売上が消えるのか？ | [771_excel_row_limit](articles/771_excel_row_limit) |
| 781 | 数の列に文字が1つまざると、Excel のピボットの集計はどう変わり、合計はどれだけ消えるのか？ | [781_pivot_count_default](articles/781_pivot_count_default) |

</details>

<details><summary><b>集計の定義・KPI</b>（138本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F06 | 高齢化は地図の上で固まっているか？ | [F06_aging_spatial](articles/F06_aging_spatial) |
| F42 | 季節調整を自分でやると、公表値と同じになるか？ | [F42_seasonal_adjustment](articles/F42_seasonal_adjustment) |
| F60 | 去年いちばん悪かった県は、今年よくなるのか？ | [F60_regression_to_mean](articles/F60_regression_to_mean) |
| F63 | 「前年比」と「前月比」、景気の変わり目を早く見つけられるのはどちらか？ | [F63_yoy_vs_mom](articles/F63_yoy_vs_mom) |
| F84 | 男女の賃金差のうち、「説明できる部分」はどれだけか？ | [F84_oaxaca_gender_wage](articles/F84_oaxaca_gender_wage) |
| F88 | 携帯料金の値下げは、物価をどれだけ下げたか？ | [F88_mobile_fee_rdit](articles/F88_mobile_fee_rdit) |
| F95 | 新幹線の効果は、隣の県にもこぼれたのか？ | [F95_shinkansen_spillover](articles/F95_shinkansen_spillover) |
| F97 | 「前年比+1%」は、本当に増えたと言えるのか？ | [F97_sampling_error_yoy](articles/F97_sampling_error_yoy) |
| F103 | 電力需要や物価の「長い記憶」は、どれくらい続くか？ | [F103_long_memory](articles/F103_long_memory) |
| F106 | 同じ県の会社は、同じように閉鎖しやすいのか？ | [F106_shared_frailty](articles/F106_shared_frailty) |
| F116 | 47都道府県の指標を1つの「暮らしやすさ」にまとめると、重みでどれだけ順位が変わるか？ | [F116_composite_index_weights](articles/F116_composite_index_weights) |
| F122 | 手法ごとに、どこでつまずいたか？ | [F122_pitfalls_from_logs](articles/F122_pitfalls_from_logs) |
| F124 | 同じデータを何本の記事で使い回したか？ | [F124_data_lineage_network](articles/F124_data_lineage_network) |
| F125 | 100本を超えた看板記事で、「見えなかった」はどれくらいあったか？ | [F125_null_results_review](articles/F125_null_results_review) |
| F127 | 空き家は、人口が減った分だけ増えたのか？ | [F127_vacant_houses_decomposition](articles/F127_vacant_houses_decomposition) |
| F131 | 大学に進む人が増えると、地元に残る若者は減るのか？ | [F131_univ_youth_migration](articles/F131_univ_youth_migration) |
| F135 | 雨の日は、小売の売上をどれだけ動かすのか？ | [F135_rain_retail](articles/F135_rain_retail) |
| F136 | 鉄道の利用は、コロナ前にどこまで戻ったのか？ | [F136_rail_covid_recovery](articles/F136_rail_covid_recovery) |
| F137 | 郵便物は、いつ半分になるのか？ | [F137_postal_decay](articles/F137_postal_decay) |
| F145 | ごみの量は、有料化のあとに減ったのか？ | [F145_waste_fee_did](articles/F145_waste_fee_did) |
| F150 | 季節のパターンそのものは、年々変わっているのか？ | [F150_dynamic_seasonality](articles/F150_dynamic_seasonality) |
| F151 | 47都道府県の求人倍率の「同じ動き」は、いくつに分けられるか？ | [F151_pref_hierarchical_dfm](articles/F151_pref_hierarchical_dfm) |
| F152 | 統計の速報は、確報でどれだけ直されるのか？ | [F152_revision_news_noise](articles/F152_revision_news_noise) |
| F155 | 分析の手順を変えると、答えはどこまで変わるか？ | [F155_multiverse](articles/F155_multiverse) |
| F158 | 地価の予測モデルは、毎年作り直す必要があるのか？ | [F158_land_price_update](articles/F158_land_price_update) |
| F161 | 同じデータで記事を書き直すと、結論はどれだけ変わるか？ | [F161_rewrite_old_articles](articles/F161_rewrite_old_articles) |
| F164 | 図をどう作ると、読まれ方が変わったか？ | [F164_figures_and_reads](articles/F164_figures_and_reads) |
| F169 | 円安と株高は、大きく動く日にだけ一緒に動くのか？ | [F169_yen_stock_copula](articles/F169_yen_stock_copula) |
| F170 | 産業の構成比を比べるとき、割合のまま回帰してよいか？ | [F170_compositional_industry_shares](articles/F170_compositional_industry_shares) |
| F176 | 白書の文章は、年々読みやすくなったのか？ | [F176_whitepaper_readability](articles/F176_whitepaper_readability) |
| F180 | 2つの統計の数字は、本当に同じものを測っているか？ | [F180_measurement_agreement](articles/F180_measurement_agreement) |
| F181 | 家が建つ数は、金利と人口のどちらで決まるのか？ | [F181_housing_starts_rates_population](articles/F181_housing_starts_rates_population) |
| F183 | 車を持つ世帯は、どこで減りはじめたのか？ | [F183_car_ownership_change_points](articles/F183_car_ownership_change_points) |
| F185 | 宅配便の個数は、どこまで通販で説明できるのか？ | [F185_parcels_online_shopping](articles/F185_parcels_online_shopping) |
| F186 | 電気料金の値上がりは、家計のどこに効いたのか？ | [F186_electricity_bill_household_burden](articles/F186_electricity_bill_household_burden) |
| F188 | 労働災害は、どの産業で減り、どこで減らなかったのか？ | [F188_occupational_injury_by_industry](articles/F188_occupational_injury_by_industry) |
| F189 | 日本人の1日は、20年でどう変わったのか？ | [F189_time_use_composition](articles/F189_time_use_composition) |
| F191 | お金の量を増やすと、貸出は増えたのか？ | [F191_money_base_lending](articles/F191_money_base_lending) |
| F192 | 国債の金利は、何で動いているのか？ | [F192_jgb_yield_curve_pca](articles/F192_jgb_yield_curve_pca) |
| F193 | インターネットの通信量は、どの時間に、どれだけ増えたのか？ | [F193_internet_traffic_decomposition](articles/F193_internet_traffic_decomposition) |
| F195 | 夜の明かりで、地域の経済活動はどこまで分かるか？ | [F195_night_lights_gdp](articles/F195_night_lights_gdp) |
| F199 | 季節調整のやり方で、「景気の山」の時期は変わるのか？ | [F199_seasonal_adjustment_turning_points](articles/F199_seasonal_adjustment_turning_points) |
| F203 | 出生率が下がったのは、結婚が減ったからか、夫婦の子どもが減ったからか？ | [F203_births_marriage_series_part1](articles/F203_births_marriage_series_part1) |
| F204 | 出生の支援策は、結婚・第1子・第2子のどこに効いたのか？ | [F204_births_marriage_series_part2](articles/F204_births_marriage_series_part2) |
| F205 | 予測モデルは、作る前に何を決め、外れをいくらと見て、いつ作り直すのか？ | [F205_power_forecast_practice_part1](articles/F205_power_forecast_practice_part1) |
| F209 | この5年の値上がりは、どの品目から来て、誰に重く、家計は何を減らしたのか？ | [F209_prices_household_series_part1](articles/F209_prices_household_series_part1) |
| F233 | 祝日・連休・天気は、売上をどれだけ動かすのか？ | [F233_calendar_weather_sales](articles/F233_calendar_weather_sales) |
| F240 | キャンペーンの効果を、比べる相手がないときにどう測るか？ | [F240_campaign_effect_no_control](articles/F240_campaign_effect_no_control) |
| F242 | 毎日の KPI の「いつもと違う」を、どう自動で知らせるか？ | [F242_kpi_anomaly_alerts](articles/F242_kpi_anomaly_alerts) |
| F243 | どの指標を見れば、売上の変化の理由が分かるのか？ | [F243_kpi_tree_decomposition](articles/F243_kpi_tree_decomposition) |
| F245 | 1つの依頼に、1時間でどこまで答えられるか？ | [F245_one_hour_request](articles/F245_one_hour_request) |
| F246 | 分析担当として最初にやること：KPI を決める（業務の再現：架空の会社で） シリーズ③の1本目。架空の食品スーパー「サン | [F246_kpi_definitions_fictional_retail](articles/F246_kpi_definitions_fictional_retail) |
| F247 | データを集めて、使える形に整える（業務の再現：架空の会社で） シリーズ③の2本目。F246 の合成データ「サンプルマート | [F247_data_mart_fictional_retail](articles/F247_data_mart_fictional_retail) |
| F248 | 月次レポートの「型」を作る（業務の再現：架空の会社で） シリーズ③の3本目。F246 の KPI 定義 v1 と F24 | [F248_monthly_report_template_fictional_retail](articles/F248_monthly_report_template_fictional_retail) |
| F249 | ダッシュボードを作る（業務の再現：架空の会社で） シリーズ③の続き。F246 の KPI 定義 v1 と F247 の  | [F249_powerbi_dashboard_fictional_retail](articles/F249_powerbi_dashboard_fictional_retail) |
| F250 | 売上が落ちた月に、理由を説明する（業務の再現：架空の会社で） シリーズ③の5本目。F247 の mart を使い、架空の | [F250_sales_drop_explanation_fictional_retail](articles/F250_sales_drop_explanation_fictional_retail) |
| F251 | 販促の効果を測る（業務の再現：架空の会社で） シリーズ③の6本目。F247 の mart の架空の食品スーパー「サンプル | [F251_promo_effect_fictional_retail](articles/F251_promo_effect_fictional_retail) |
| F252 | 来期の予算のための需要予測（業務の再現：架空の会社で） シリーズ③の7本目。架空の食品スーパー「サンプルマート（架空）」 | [F252_budget_forecast_fictional_retail](articles/F252_budget_forecast_fictional_retail) |
| F253 | データの品質を毎月チェックする（業務の再現：架空の会社で） シリーズ③の8本目。架空の食品スーパー「サンプルマート（架空 | [F253_monthly_data_quality_checks_fictional_retail](articles/F253_monthly_data_quality_checks_fictional_retail) |
| F256 | 自然災害の保険金は、この30年でどれだけ大きくなったのか？ | [F256_natural_disaster_insurance_payouts](articles/F256_natural_disaster_insurance_payouts) |
| F257 | 労働経済白書の「賃上げが広がった」は、どのデータでどこまで言えるのか？ | [F257_wage_spillover_whitepaper](articles/F257_wage_spillover_whitepaper) |
| F258 | 「実質賃金○か月連続マイナス」は、どの物価で割るかで変わるのか？ | [F258_real_wage_deflator_streak](articles/F258_real_wage_deflator_streak) |
| F261 | 潜在成長率は、計算の仕方でどれだけ変わるのか？ | [F261_potential_growth_methods](articles/F261_potential_growth_methods) |
| F262 | 「出生数が過去最少」は、女性の人口の減少でどこまで説明できるか？ | [F262_births_record_low_decomposition](articles/F262_births_record_low_decomposition) |
| F266 | 「米の値段が上がった」は、どの段階で起きたのか？ | [F266_rice_price_stages](articles/F266_rice_price_stages) |
| F267 | 売上の目標を、客数と客単価の目標にどう分けるか？ | [F267_kpi_target_allocation_cvs](articles/F267_kpi_target_allocation_cvs) |
| F273 | 観光白書の「地方への分散」は、宿泊データで見えているか？ | [F273_regional_dispersion_lodging](articles/F273_regional_dispersion_lodging) |
| F274 | 「人手不足倒産が過去最多」は、会社の数と数え方をそろえても増えたのか？ | [F274_labor_shortage_bankruptcy_rate](articles/F274_labor_shortage_bankruptcy_rate) |
| F275 | 集計の SQL は、どう書けば直しやすく、直し忘れに気づけるか？ | [F275_sql_change_requests](articles/F275_sql_change_requests) |
| F280 | 医療費の伸びは、年齢・回数・日数・1日当たりのどれで決まっているのか？ | [F280_medical_cost_three_elements](articles/F280_medical_cost_three_elements) |
| F281 | 食料自給率の目標と実際の差は、どこから来ているのか？ | [F281_food_self_sufficiency_target_gap](articles/F281_food_self_sufficiency_target_gap) |
| F282 | 「円安で輸出が増えた」は、数量と価格に分けるとどうか？ | [F282_yen_exports_quantity_price](articles/F282_yen_exports_quantity_price) |
| F283 | 値上げの前後で、売れ方はどう変わったか？ | [F283_price_hike_front_loading](articles/F283_price_hike_front_loading) |
| F285 | エネルギー基本計画の電力需要の見通しは、過去にどれだけ当たったか？ | [F285_power_demand_outlook_accuracy](articles/F285_power_demand_outlook_accuracy) |
| F287 | 同じ数字を、経営向けと現場向けでどう書き分けるか？ | [F287_report_two_audiences](articles/F287_report_two_audiences) |
| F289 | 情報通信白書のデジタル化の指標は、生産性と結びついているか？ | [F289_ict_capital_productivity](articles/F289_ict_capital_productivity) |
| F293 | 毎月の数字の「おかしい」を、どう自動で見つけるか？ | [F293_monthly_anomaly_public_stats](articles/F293_monthly_anomaly_public_stats) |
| 011 | 「平均所得ランキング」をそのまま信じていいか？ | [011_income_ranking](articles/011_income_ranking) |
| 149 | 川や海に比べて、湖だけ環境基準の達成率が低いのはなぜか？ | [149_lake_water_quality](articles/149_lake_water_quality) |
| 234 | 前月比の増減を、客数と客単価にどう分けるか？ | [234_mom_change_decomposition](articles/234_mom_change_decomposition) |
| 241 | 公的データを使って困ったことは何だったか？ | [241_public_data_troubles](articles/241_public_data_troubles) |
| 272 | 毎月の数字は、前月比・前年同月比・季節調整のどれで読むか？ | [272_seasonal_adjust_monthly](articles/272_seasonal_adjust_monthly) |
| 277 | 製造業の生産の見込みは、94%の月で実績より高かった。平均の外れは−2.8%で、機械の業種ほど大きい。過去の外れの平均だ | [277_production_forecast_accuracy](articles/277_production_forecast_accuracy) |
| 278 | KPI カードの矢印は、何と比べて付けるか？ | [278_kpi_card_comparison](articles/278_kpi_card_comparison) |
| 341 | 月次の数字は、締めてから何日たてば「確定」と言えるのか？ | [341_month_close_completeness](articles/341_month_close_completeness) |
| 342 | 締めたあとに訂正されたデータで、先月のレポートの数字を再現できるか？ | [342_restate_and_reproduce_reports](articles/342_restate_and_reproduce_reports) |
| 344 | 「アクティブな顧客」は、定義でどれだけ人数が変わるのか？ | [344_active_customer_definitions](articles/344_active_customer_definitions) |
| 345 | 店ごとの平均を平均すると、全体の平均からどれだけずれるのか？ | [345_average_of_averages](articles/345_average_of_averages) |
| 356 | 曜日の並びが違うだけで、前年同月比は何ポイント動くのか？ | [356_weekday_mix_yoy](articles/356_weekday_mix_yoy) |
| 358 | 売上が0の日が表にないと、1日あたりの平均はどれだけ高く出るのか？ | [358_missing_zero_days](articles/358_missing_zero_days) |
| 371 | 中央値や90%点は、計算の定義でどれだけ違うのか？ | [371_percentile_definitions](articles/371_percentile_definitions) |
| 390 | 年間の予算を月に割る方法で、月ごとの達成率はどれだけ変わるのか？ | [390_budget_monthly_allocation](articles/390_budget_monthly_allocation) |
| 409 | 複数回答の設問は、分母の取り方で割合が何ポイント変わるのか？ | [409_multiple_response_denominators](articles/409_multiple_response_denominators) |
| 443 | 分類を付け替えたあと、過去の集計は「当時の区分」と「今の区分」でどれだけ違うのか？ | [443_reclassification_asof_vs_current](articles/443_reclassification_asof_vs_current) |
| 449 | 指標の単位をそろえないまま主成分分析をすると、第1主成分はどれだけ変わるのか？ | [449_pca_units_standardization](articles/449_pca_units_standardization) |
| 451 | 「5営業日後」の期日は、祝日の持ち方で何件ずれるのか？ | [451_business_day_due_dates](articles/451_business_day_due_dates) |
| 471 | 年初からの累計で見た前年比は、売上の変化に何か月遅れて気づくのか？ | [471_ytd_yoy_lag](articles/471_ytd_yoy_lag) |
| 472 | 返品を「売れた月」に戻すか「返ってきた月」で引くかで、月の売上はどれだけ変わるのか？ | [472_returns_which_month](articles/472_returns_which_month) |
| 475 | 解約率は、分母の取り方でどれだけ違って見えるのか？ | [475_churn_rate_denominator](articles/475_churn_rate_denominator) |
| 481 | 同じ売上を20日締めと月末締めで集計すると、2023〜2025年の月の数字は平均何%ずれるのか？ | [481_closing_day_20th_vs_monthend](articles/481_closing_day_20th_vs_monthend) |
| 512 | 割合を小数1桁で表示すると、前月からの増減が「0.0」や逆の向きに見える月は何か月あるのか？ | [512_rounded_display_mom_change](articles/512_rounded_display_mom_change) |
| 514 | 入庫と出庫の記録が遅れて届くと、在庫が一時的にマイナスになる日は何日あるのか？ | [514_inventory_record_delay_negative](articles/514_inventory_record_delay_negative) |
| 524 | 深夜まで営業する店で、売上を暦日で切るか「朝5時締めの営業日」で切るかで、曜日別の売上はどれだけ変わるのか？ | [524_business_day_cutoff_5am](articles/524_business_day_cutoff_5am) |
| 534 | アンケートの「その他」の自由記述を選択肢に振り直すと、各選択肢の割合は何ポイント動くのか？ | [534_survey_other_recode](articles/534_survey_other_recode) |
| 556 | 同じ分母で割った2つの比率は、もとの数に関係がなくてもどれだけ相関するのか？ | [556_shared_denominator_ratio_corr](articles/556_shared_denominator_ratio_corr) |
| 562 | 「直近30日」に今日を含めるか、時刻で切るか日付で切るかで、数字はどれだけ変わるのか？ | [562_rolling_30day_definition](articles/562_rolling_30day_definition) |
| 563 | 千円単位と円単位の数字が混ざった表から、桁のずれた行をどう見つけるのか？ | [563_thousand_yen_unit_mix](articles/563_thousand_yen_unit_mix) |
| 574 | 部署の統廃合があったとき、過去の部署別の数字を今の組織に組み替えると、推移はどう変わるのか？ | [574_reorg_restatement](articles/574_reorg_restatement) |
| 579 | 店ごとの比率を平均するか、合計どうしで比を取るかで、全体の比率はどれだけ違うのか？ | [579_mean_of_ratios_vs_ratio_of_totals](articles/579_mean_of_ratios_vs_ratio_of_totals) |
| 581 | 締め日が20日の会社で、月の売上を暦の月で数えるか締めの期間で数えるかで、月ごとの数字はどれだけずれるのか？ | [581_closing_day_vs_calendar_month](articles/581_closing_day_vs_calendar_month) |
| 590 | 比率の分母が小さい項目を並べると、上位と下位にどれだけ小さい項目が集まるのか？ | [590_small_denominator_ranking](articles/590_small_denominator_ranking) |
| 593 | 開店と閉店がある期間で、「1店あたりの売上」を月末の店数で割るか営業日数で割るかで、どれだけ違うのか？ | [593_per_store_denominator](articles/593_per_store_denominator) |
| 602 | 平均単価を「明細の単価の平均」で出すか「金額の合計÷数量」で出すかで、品目の単価はどれだけ違うのか？ | [602_avg_unit_price_definition](articles/602_avg_unit_price_definition) |
| 603 | 日次の前年比を「前年の同じ日」と比べるか「前年の同じ曜日」と比べるかで、どれだけ違って見えるのか？ | [603_yoy_same_date_vs_weekday](articles/603_yoy_same_date_vs_weekday) |
| 604 | 構成比を四捨五入すると、合計が100%にならない表は何%あり、最大剰余法で直すと各項目はどれだけ動くのか？ | [604_share_rounding_sum100](articles/604_share_rounding_sum100) |
| 611 | 営業日の数が違う月を前年同月と比べると、前年比は何ポイント動くのか？ | [611_yoy_business_days_adjust](articles/611_yoy_business_days_adjust) |
| 642 | 年間の目標を12等分するか、前年の月の比率で分けるかで、「達成した月」の数はどれだけ違うのか？ | [642_monthly_target_phasing](articles/642_monthly_target_phasing) |
| 644 | 毎年の伸び率を足して割った平均と、年率（幾何平均）では、5年後の値はどれだけ違うのか？ | [644_growth_rate_arith_vs_geo](articles/644_growth_rate_arith_vs_geo) |
| 661 | 新しく開いた店と閉じた店を含めたまま前年比を出すと、既存店だけの前年比とどれだけ違うのか？ | [661_existing_store_yoy](articles/661_existing_store_yoy) |
| 664 | 平均単価の前年比を、品目の構成の変化と単価の変化に分けると、それぞれどれだけになるのか？ | [664_price_mix_decomposition](articles/664_price_mix_decomposition) |
| 665 | 会員カードを出した客だけで客単価を見ると、店全体の客単価よりどれだけ高く出るのか？ | [665_member_card_spend_bias](articles/665_member_card_spend_bias) |
| 681 | 「有効」フラグの立った商品だけで集計すると、廃番になった商品の過去の売上はどれだけ消えるのか？ | [681_existing_flag_history](articles/681_existing_flag_history) |
| 682 | 店ごとの前年比を並べるのと、全体の伸びへの寄与度で並べるのでは、順位はどれだけ違うのか？ | [682_contribution_to_growth](articles/682_contribution_to_growth) |
| 695 | 1人あたりの処理件数を、出勤した日数で割るか働いた時間で割るかで、担当者の順位はどれだけ入れ替わるのか？ | [695_productivity_denominator](articles/695_productivity_denominator) |
| 702 | 構成比を WHERE で絞り込んだあとに出すと、全体に対する割合とどれだけ違って見えるのか？ | [702_share_after_filter](articles/702_share_after_filter) |
| 703 | 売上のない月が行ごと抜けた表で LAG を使って前月比を出すと、何行が2か月前と比べてしまうのか？ | [703_lag_missing_months](articles/703_lag_missing_months) |
| 711 | 月の売上を「30」で割るか、その月の日数や営業日数で割るかで、日あたりの前月比はどれだけ違うのか？ | [711_daily_avg_days_in_month](articles/711_daily_avg_days_in_month) |
| 712 | 月の伸び率を年率に直すとき、12倍するか複利で直すかで、どれだけ違うのか？ | [712_annualize_monthly_rate](articles/712_annualize_monthly_rate) |
| 713 | 率が5%から6%になったのを「1ポイント増」と「20%増」のどちらで書くかで、店の並びはどれだけ変わるのか？ | [713_points_vs_percent_change](articles/713_points_vs_percent_change) |
| 723 | 前年がマイナスの利益の伸び率を、ふつうの式で出すと、何店で向きが逆に見えるのか？ | [723_growth_negative_base](articles/723_growth_negative_base) |
| 745 | 4月始まりの年度と暦年で前年比を出すと、伸びの年はどれだけずれて見えるのか？ | [745_fiscal_vs_calendar_year](articles/745_fiscal_vs_calendar_year) |
| 752 | 先頭に BOM のついた CSV を csv モジュールで読むと、最初の列名が一致せず、何行の売上が黙って集計から落ちるのか？ | [752_csv_bom_header](articles/752_csv_bom_header) |
| 753 | 1年が53週ある年に「第N週」で前年同週比を出すと、何週の前年比が本当の伸びから外れるのか？ | [753_week53_yoy](articles/753_week53_yoy) |
| 754 | 欠品率を「欠品した SKU の数」で数えるか「売上の重み」で数えるかで、店の比べ方はどれだけ変わるのか？ | [754_stockout_rate_weighting](articles/754_stockout_rate_weighting) |
| 764 | pandas の groupby が欠けたキーの行を黙って落とすと、合計はどれだけ減るのか？ | [764_pandas_groupby_dropna](articles/764_pandas_groupby_dropna) |
| 774 | 達成率を四捨五入してから「100%以上」を数えると、何店が「達成」に入ってしまうのか？ | [774_achievement_rounding](articles/774_achievement_rounding) |
| 784 | 法人のまとめ買いを混ぜたまま客単価を見ると、個人の客単価はどれだけ高く見えるのか？ | [784_bulk_buyer_mixing](articles/784_bulk_buyer_mixing) |
| 795 | 月の数字を週に直すとき4で割るか4.33で割るかで、週あたりの値はどれだけ違うのか？ | [795_weeks_per_month](articles/795_weeks_per_month) |

</details>

<details><summary><b>可視化・報告・BI</b>（48本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F08 | 1,740市区町村を62の指標で分けると何タイプか？ | [F08_municipal_segments](articles/F08_municipal_segments) |
| F44 | 出生率のトレンドはいつ折れたのか？ | [F44_structural_breaks](articles/F44_structural_breaks) |
| F70 | 同じ数字でも、グラフの見せ方で印象はどこまで変わるのか？ | [F70_chart_honesty](articles/F70_chart_honesty) |
| F87 | 結婚が減ったのは「時代」のせいか「世代」のせいか？ | [F87_marriage_apc](articles/F87_marriage_apc) |
| F89 | 最低賃金の効果、これまでの推定をまとめると？ | [F89_minwage_meta](articles/F89_minwage_meta) |
| F107 | 市区町村のつながり（隣接・通勤）を使うと、予測は良くなるか？ | [F107_gcn_municipal](articles/F107_gcn_municipal) |
| F124 | 同じデータを何本の記事で使い回したか？ | [F124_data_lineage_network](articles/F124_data_lineage_network) |
| F130 | 介護の認定率の地域差は、高齢化だけで説明できるか？ | [F130_care_certification_shrinkage](articles/F130_care_certification_shrinkage) |
| F131 | 大学に進む人が増えると、地元に残る若者は減るのか？ | [F131_univ_youth_migration](articles/F131_univ_youth_migration) |
| F141 | 特許の出願は、どの分野で地方に広がったのか？ | [F141_ip_regional_concentration](articles/F141_ip_regional_concentration) |
| F143 | 漁獲量の減り方は、魚の種類でどう違うのか？ | [F143_fish_catch_decline](articles/F143_fish_catch_decline) |
| F147 | 集計表から「それらしい個票」を作ると、元の分析を再現できるか？ | [F147_synthetic_from_tables](articles/F147_synthetic_from_tables) |
| F171 | 人口ピラミッドの「形」は、いくつの型に分かれるか？ | [F171_pyramid_shape_fda](articles/F171_pyramid_shape_fda) |
| F174 | 景気の「局面」は、データから自動で見つけられるか？ | [F174_business_cycle_hmm_multiseries](articles/F174_business_cycle_hmm_multiseries) |
| F188 | 労働災害は、どの産業で減り、どこで減らなかったのか？ | [F188_occupational_injury_by_industry](articles/F188_occupational_injury_by_industry) |
| F206 | 予測は、エリアと合計をどうそろえ、どう見せ、1年回すと何が起きるのか？ | [F206_power_forecast_practice_part2](articles/F206_power_forecast_practice_part2) |
| F231 | 売上の予測は、何か月先まで役に立つのか？ | [F231_sales_forecast_horizon](articles/F231_sales_forecast_horizon) |
| F232 | 店の種類ごとの予測と全体の予測を、どうそろえるか？ | [F232_hierarchical_retail_reconciliation](articles/F232_hierarchical_retail_reconciliation) |
| F233 | 祝日・連休・天気は、売上をどれだけ動かすのか？ | [F233_calendar_weather_sales](articles/F233_calendar_weather_sales) |
| F234 | 価格を1%上げると、買われる量は何%減るのか？ | [F234_price_elasticity_practice](articles/F234_price_elasticity_practice) |
| F235 | 在庫はどれだけ持てばよいのか？ | [F235_inventory_newsvendor](articles/F235_inventory_newsvendor) |
| F237 | A/B テストを途中で見ると、何がまずいのか？ | [F237_ab_test_peeking_sequential](articles/F237_ab_test_peeking_sequential) |
| F240 | キャンペーンの効果を、比べる相手がないときにどう測るか？ | [F240_campaign_effect_no_control](articles/F240_campaign_effect_no_control) |
| F241 | 顧客はどれくらいで離れていくのか？ | [F241_customer_churn_survival](articles/F241_customer_churn_survival) |
| F242 | 毎日の KPI の「いつもと違う」を、どう自動で知らせるか？ | [F242_kpi_anomaly_alerts](articles/F242_kpi_anomaly_alerts) |
| F243 | どの指標を見れば、売上の変化の理由が分かるのか？ | [F243_kpi_tree_decomposition](articles/F243_kpi_tree_decomposition) |
| F248 | 月次レポートの「型」を作る（業務の再現：架空の会社で） シリーズ③の3本目。F246 の KPI 定義 v1 と F24 | [F248_monthly_report_template_fictional_retail](articles/F248_monthly_report_template_fictional_retail) |
| F249 | ダッシュボードを作る（業務の再現：架空の会社で） シリーズ③の続き。F246 の KPI 定義 v1 と F247 の  | [F249_powerbi_dashboard_fictional_retail](articles/F249_powerbi_dashboard_fictional_retail) |
| F250 | 売上が落ちた月に、理由を説明する（業務の再現：架空の会社で） シリーズ③の5本目。F247 の mart を使い、架空の | [F250_sales_drop_explanation_fictional_retail](articles/F250_sales_drop_explanation_fictional_retail) |
| F251 | 販促の効果を測る（業務の再現：架空の会社で） シリーズ③の6本目。F247 の mart の架空の食品スーパー「サンプル | [F251_promo_effect_fictional_retail](articles/F251_promo_effect_fictional_retail) |
| F255 | 1年の分析業務を振り返る（業務の再現：架空の会社で） シリーズ③の10本目・最後。架空の食品スーパー「サンプルマート（架 | [F255_year_review_fictional_retail](articles/F255_year_review_fictional_retail) |
| F271 | 見られるダッシュボードと、見られないダッシュボードの違いは何か？ | [F271_dashboard_answer_cost](articles/F271_dashboard_answer_cost) |
| F275 | 集計の SQL は、どう書けば直しやすく、直し忘れに気づけるか？ | [F275_sql_change_requests](articles/F275_sql_change_requests) |
| F287 | 同じ数字を、経営向けと現場向けでどう書き分けるか？ | [F287_report_two_audiences](articles/F287_report_two_audiences) |
| F288 | 損害額の分布の「裾の重さ」は、データの量でどこまで見分けられるか？ | [F288_tail_heaviness_sample_size](articles/F288_tail_heaviness_sample_size) |
| 240 | グラフの縦軸を0から始めなかったら、どう見えたか？ | [240_axis_zero_baseline_review](articles/240_axis_zero_baseline_review) |
| 243 | 縦長の統計表をレポートの形にする SQL は、CASE WHEN で書ける。ただし業態が1つ増えると、その行は黙って落ち | [243_sql_pivot_report](articles/243_sql_pivot_report) |
| 244 | 毎月のレポートは、結論の1文・要因・次に確かめることの順に、数字から自動で書ける。要因を率で選ぶと、12か月中7か月で金 | [244_monthly_report_order](articles/244_monthly_report_order) |
| 279 | 手作業の月次 Excel レポートを、Python でどう自動にするか？ | [279_excel_report_automation](articles/279_excel_report_automation) |
| 302 | HTML だけで、配れるダッシュボードは作れるか？ | [302_single_html_dashboard](articles/302_single_html_dashboard) |
| 342 | 締めたあとに訂正されたデータで、先月のレポートの数字を再現できるか？ | [342_restate_and_reproduce_reports](articles/342_restate_and_reproduce_reports) |
| 350 | まだ報告されていない事故の件数は、報告の遅れからどこまで当てられるのか？ | [350_ibnr_count_reporting_delay](articles/350_ibnr_count_reporting_delay) |
| 401 | 集計用の表は、1枚の大きな表と、事実とマスタに分けた表のどちらが直しやすいか？ | [401_wide_table_vs_star_schema](articles/401_wide_table_vs_star_schema) |
| 659 | ARIMA の次数を AIC で選ぶと、本当の次数を何%で当て、予測はどれだけ悪くなるのか？ | [659_arima_order_selection](articles/659_arima_order_selection) |
| 696 | AIC・BIC・交差検証で回帰の変数を選ぶと、本当の変数を何%当てるのか？ | [696_aic_bic_cv_selection](articles/696_aic_bic_cv_selection) |
| 699 | 構造変化の時点をグラフを見てから決めて検定すると、変化がなくても何%で「変化あり」になるのか？ | [699_structural_break_post_hoc](articles/699_structural_break_post_hoc) |
| 716 | 交差検証でハイパーパラメータを選び、同じ交差検証の成績を報告すると、本当の成績よりどれだけよく見えるのか？ | [716_nested_cv_optimism](articles/716_nested_cv_optimism) |
| 798 | グラフのひげが標準偏差か標準誤差かを取り違えると、差の大きさはどれだけ違って見えるのか？ | [798_sd_vs_se_errorbars](articles/798_sd_vs_se_errorbars) |

</details>

<details><summary><b>保険数理・リスク</b>（75本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F27 | 市区町村の死亡率の地図は、小さな町ほどぶれる。隣の町の情報を借りる空間ベイズ（BYM2）で描き直すと、地域差の9割以上は | [F27_disease_map_bym2](articles/F27_disease_map_bym2) |
| F49 | 平均寿命の県の差は、何歳の死亡で生まれているのか？ | [F49_life_expectancy_decomposition](articles/F49_life_expectancy_decomposition) |
| F61 | 小さい町の「ランキング1位」は、なぜ毎回入れ替わるのか？ | [F61_funnel_eb_rankings](articles/F61_funnel_eb_rankings) |
| F62 | 死亡率は10年で上がったのか、下がったのか？ | [F62_simpson_standardization](articles/F62_simpson_standardization) |
| F130 | 介護の認定率の地域差は、高齢化だけで説明できるか？ | [F130_care_certification_shrinkage](articles/F130_care_certification_shrinkage) |
| F241 | 顧客はどれくらいで離れていくのか？ | [F241_customer_churn_survival](articles/F241_customer_churn_survival) |
| F256 | 自然災害の保険金は、この30年でどれだけ大きくなったのか？ | [F256_natural_disaster_insurance_payouts](articles/F256_natural_disaster_insurance_payouts) |
| F260 | 「100年に1度の損害」は、どの分布を仮定するかでいくら変わるのか？ | [F260_loss_distribution_return_level](articles/F260_loss_distribution_return_level) |
| F264 | 自動車の事故率は、高齢化でどこまで説明できるのか？ | [F264_auto_accident_rate_aging](articles/F264_auto_accident_rate_aging) |
| F268 | 生命表が5年で変わると、年金の負担はどれだけ動くのか？ | [F268_life_table_annuity_value](articles/F268_life_table_annuity_value) |
| F272 | 火災保険料の地域差は、リスクの差にどこまで見合っているか？ | [F272_fire_insurance_rate_vs_risk](articles/F272_fire_insurance_rate_vs_risk) |
| F276 | 地震保険の付帯率は、地震のあとにどれだけ上がって戻るのか？ | [F276_earthquake_insurance_after_quakes](articles/F276_earthquake_insurance_after_quakes) |
| F280 | 医療費の伸びは、年齢・回数・日数・1日当たりのどれで決まっているのか？ | [F280_medical_cost_three_elements](articles/F280_medical_cost_three_elements) |
| F284 | 豪雨の増え方を、火災保険の料率はどこまで追いかけているのか？ | [F284_heavy_rain_vs_fire_rates](articles/F284_heavy_rain_vs_fire_rates) |
| F288 | 損害額の分布の「裾の重さ」は、データの量でどこまで見分けられるか？ | [F288_tail_heaviness_sample_size](articles/F288_tail_heaviness_sample_size) |
| F291 | 死亡率の改善は、年齢のどこで止まりつつあるのか？ | [F291_mortality_improvement_slowdown](articles/F291_mortality_improvement_slowdown) |
| F294 | 介護の費用は、2040年度にどこまで増えるのか？ | [F294_care_cost_2040_assumptions](articles/F294_care_cost_2040_assumptions) |
| F295 | リスクを分けて計ると、分散効果はどれだけ効くのか？ | [F295_solvency_diversification_copula](articles/F295_solvency_diversification_copula) |
| 314 | 契約の「在籍件数」を、SQL でどう数えるか？ | [314_sql_policy_exposure](articles/314_sql_policy_exposure) |
| 315 | 1年分の保険料を、月ごとの売上にどう分けるか？ | [315_sql_earned_premium](articles/315_sql_earned_premium) |
| 316 | 支払いの進み方から将来の支払いを見積もる方法は、どんなときに外れるのか？ | [316_chain_ladder_when_it_fails](articles/316_chain_ladder_when_it_fails) |
| 317 | 新しい年度の支払いの見積もりは、実績から延ばすのと、見込みの損害率に寄せるのと、どちらが近いか？ | [317_chain_ladder_vs_bf](articles/317_chain_ladder_vs_bf) |
| 318 | 見積もった支払備金の「幅」は、正解を何%含むのか？ | [318_reserve_interval_coverage](articles/318_reserve_interval_coverage) |
| 319 | 小さな集団の事故率は、全体の平均にどれだけ寄せるのがよいか？ | [319_credibility_small_groups](articles/319_credibility_small_groups) |
| 331 | 大きな損害だけを受け持つ「層」の見積もりは、裾の当てはめにどれだけ左右されるのか？ | [331_layer_price_tail_estimate](articles/331_layer_price_tail_estimate) |
| 332 | 免責や支払いの上限で切られたデータから、元の損害の分布は戻せるのか？ | [332_truncated_censored_loss_fit](articles/332_truncated_censored_loss_fit) |
| 333 | 1年の損害の合計の「200年に1度」は、近似でどこまで出せるのか？ | [333_aggregate_loss_tail_quantile](articles/333_aggregate_loss_tail_quantile) |
| 334 | 要因を1つずつ見た事故率の差は、まとめて推定するとどれだけ変わるのか？ | [334_one_way_vs_glm_rating](articles/334_one_way_vs_glm_rating) |
| 335 | 料率の区分を細かくすると、翌年の外れは小さくなるのか、大きくなるのか？ | [335_rating_cells_granularity](articles/335_rating_cells_granularity) |
| 336 | 平均寿命が43〜44歳だった時代に、65歳まで生きた人は、あと何年生きたのか？ | [336_life_expectancy_since_meiji](articles/336_life_expectancy_since_meiji) |
| 343 | 損害率は、事故が起きた年で数えるか、支払った年で数えるかで、どれだけ違うのか？ | [343_loss_ratio_accident_vs_calendar](articles/343_loss_ratio_accident_vs_calendar) |
| 346 | 契約が何件あれば、損害率は安定するのか？ | [346_loss_ratio_stability_by_size](articles/346_loss_ratio_stability_by_size) |
| 348 | 小さな集団の年齢ごとの死亡率は、なめらかにすると真の値にどれだけ近づくのか？ | [348_mortality_graduation_small_group](articles/348_mortality_graduation_small_group) |
| 376 | 全体では上がっているのに、どの区分でも下がっていることは、どれくらい起きるのか？ | [376_simpson_reversal_frequency](articles/376_simpson_reversal_frequency) |
| 411 | 「保険年齢」と「満年齢」では、同じ契約者の年齢区分はどれだけ変わるのか？ | [411_insurance_age_vs_attained_age](articles/411_insurance_age_vs_attained_age) |
| 413 | 途中で解約した契約に返す保険料は、日割りと短期率でどれだけ違うのか？ | [413_cancellation_refund_methods](articles/413_cancellation_refund_methods) |
| 414 | 「期首＋増加−減少＝期末」の照合は、どんな誤りを見つけ、何を見逃すのか？ | [414_roll_forward_reconciliation](articles/414_roll_forward_reconciliation) |
| 416 | 手元の資本と保険料の上乗せで、10年のうちに資本が尽きる確率はどう変わるのか？ | [416_ruin_probability_capital_loading](articles/416_ruin_probability_capital_loading) |
| 417 | 大数の法則が効かないリスクがあると、契約を増やしても損害率の振れはどこで下げ止まるのか？ | [417_undiversifiable_risk_floor](articles/417_undiversifiable_risk_floor) |
| 418 | 同じ再保険料を払うなら、割合で分ける形と大きな損害だけ渡す形で、損害率の振れはどれだけ違うのか？ | [418_quota_share_vs_excess_of_loss](articles/418_quota_share_vs_excess_of_loss) |
| 419 | 契約を代表の契約にまとめて計算すると、結果はどれだけずれるのか？ | [419_model_points_grouping_error](articles/419_model_points_grouping_error) |
| 420 | 1年より短い期間の死亡率は、仮定の置き方でどれだけ違うのか？ | [420_fractional_age_assumptions](articles/420_fractional_age_assumptions) |
| 432 | 死亡率の将来の下がり方を過去から延ばす方法は、正解の分かるデータでどれだけ当たるのか？ | [432_lee_carter_known_truth](articles/432_lee_carter_known_truth) |
| 433 | 「200年に1度」の値をシミュレーションで出すには、何回くり返せばよいのか？ | [433_simulation_runs_variance_reduction](articles/433_simulation_runs_variance_reduction) |
| 436 | いちばん多い死因は、何から何へ入れ替わったのか？ | [436_leading_causes_of_death_since_1899](articles/436_leading_causes_of_death_since_1899) |
| 456 | 料率を改定したあと、過去の保険料を「いまの料率」に直す近似は、契約ごとに計算し直した値からどれだけずれるのか？ | [456_on_level_premium_parallelogram](articles/456_on_level_premium_parallelogram) |
| 457 | 大きな損害に上限を置いてから見込みを出すと、偏りと振れはどう入れ替わるのか？ | [457_large_loss_capping_bias_variance](articles/457_large_loss_capping_bias_variance) |
| 466 | 「200年に1度の値」と「それを超えたときの平均」では、同じデータでどちらの見積もりが大きく振れるのか？ | [466_var_vs_expected_shortfall_noise](articles/466_var_vs_expected_shortfall_noise) |
| 467 | 免責金額を上げた年をまたいで平均の支払額を比べると、損害が同じでも何%上がって見えるのか？ | [467_deductible_change_apparent_severity](articles/467_deductible_change_apparent_severity) |
| 468 | 一律に保険料を上げたとき、事故の少ない契約から先に抜けると、残った契約の損害率はどう動くのか？ | [468_rate_increase_adverse_lapse](articles/468_rate_increase_adverse_lapse) |
| 476 | 損害が一律に5%大きくなると、免責を超えた分の支払いは何%増えるのか？ | [476_loss_inflation_leverage_deductible](articles/476_loss_inflation_leverage_deductible) |
| 477 | 加入のときの審査の効き目を考えずに死亡率を見積もると、どれだけずれるのか？ | [477_select_period_mortality](articles/477_select_period_mortality) |
| 486 | 損害額の分布を少ない件数で当てはめると、最尤法とモーメント法のどちらが99%点を外しやすいのか？ | [486_loss_fit_mle_vs_moments](articles/486_loss_fit_mle_vs_moments) |
| 487 | 保険料の上乗せを「標準偏差」「分散」「期待効用」で決めると、契約の大きさで上乗せ率はどれだけ食い違うのか？ | [487_risk_loading_principles](articles/487_risk_loading_principles) |
| 489 | 5歳刻みの死亡率から各歳の死亡率を作ると、65歳からの年金の現価はどれだけずれるのか？ | [489_life_table_interpolation_annuity](articles/489_life_table_interpolation_annuity) |
| 490 | 解約率の仮定が実際とずれると、保険の将来の利益の見込みはどれだけ動くのか？ | [490_lapse_assumption_profit_sensitivity](articles/490_lapse_assumption_profit_sensitivity) |
| 506 | 事故の件数と1件あたりの額が一緒に動くとき、別々に見積もった年間損害の「200年に1度」はどれだけ小さく出るのか？ | [506_freq_severity_dependence](articles/506_freq_severity_dependence) |
| 507 | 生命表の死亡率を「1年に死亡する確率」と「死亡の速さ」で取り違えると、年金の現価はどれだけずれるのか？ | [507_qx_mx_confusion_annuity](articles/507_qx_mx_confusion_annuity) |
| 508 | 同じ事故の複数の請求を別々の損害として数えると、大きな損害の層の見積もりはどれだけずれるのか？ | [508_claims_per_event_count_unit](articles/508_claims_per_event_count_unit) |
| 516 | 実績の損害率に合わせて毎年保険料を直すと、損害率は落ち着くのか、それとも波打つのか？ | [516_experience_rating_feedback_cycle](articles/516_experience_rating_feedback_cycle) |
| 517 | 保険金額の大きい契約と小さい契約が混ざると、損害率の振れは契約件数ではなく何で決まるのか？ | [517_sum_insured_mix_effective_n](articles/517_sum_insured_mix_effective_n) |
| 518 | 支払いに何年もかかる損害は、利率で割り引くと、払い方の遅さによってどれだけ小さくなるのか？ | [518_discounting_payment_delay](articles/518_discounting_payment_delay) |
| 526 | 1事故ごとの免責と1年の合計の免責では、同じ見込みの支払いでも、支払いの振れはどれだけ違うのか？ | [526_per_claim_vs_aggregate_deductible](articles/526_per_claim_vs_aggregate_deductible) |
| 528 | 5歳刻みで同じ保険料にすると、区分の上の年齢に加入が偏ったとき、損害率は何%上がるのか？ | [528_age_band_skew_loss_ratio](articles/528_age_band_skew_loss_ratio) |
| 547 | 自動車保険のような等級制度で、等級の分布が落ち着くまでに何年かかり、平均の割引率はどこに落ち着くのか？ | [547_bonus_malus_markov](articles/547_bonus_malus_markov) |
| 548 | 過去の損害を今の水準に直すトレンド率が1ポイントずれると、見込みの損害はどれだけずれるのか？ | [548_trend_rate_error](articles/548_trend_rate_error) |
| 566 | 死亡率が下がり続けると、その年の生命表の平均余命は、実際に生きる年数よりどれだけ短く出るのか？ | [566_period_vs_cohort_life_table](articles/566_period_vs_cohort_life_table) |
| 567 | 支払備金の個別見積を途中から厚く積むようにすると、発生ベースのチェインラダーはどれだけ多く見込むのか？ | [567_case_reserve_strengthening](articles/567_case_reserve_strengthening) |
| 568 | 保険金額が実際の価値より小さい契約で、比例てん補を入れると、支払いと必要な保険料はどう変わるのか？ | [568_proportional_vs_first_loss](articles/568_proportional_vs_first_loss) |
| 569 | 死亡率の実績と予定の比を、件数で見るか保険金額で見るかで、どれだけ違うのか？ | [569_ae_count_vs_amount](articles/569_ae_count_vs_amount) |
| 570 | 進展の途中で打ち切ったチェインラダーは、テールファクターを省くと最終損害をどれだけ少なく見るのか？ | [570_chain_ladder_tail_factor](articles/570_chain_ladder_tail_factor) |
| 597 | 年間の総損害を件数×金額で作るとき、件数の年ごとの揺れを無視すると、99.5%点はどれだけ小さく出るのか？ | [597_compound_poisson_vs_nb](articles/597_compound_poisson_vs_nb) |
| 600 | 過去10年の損害から分布を推定するとき、推定の誤差を入れないと、99.5%点はどれだけ小さく出るのか？ | [600_parameter_uncertainty_quantile](articles/600_parameter_uncertainty_quantile) |
| 626 | 2つの事業の損害を「独立」と置いて合わせると、合計の99.5%点はどれだけ小さく出るのか？ | [626_aggregation_independence_var](articles/626_aggregation_independence_var) |
| 627 | 相関の強さが同じでも、正規コピュラと t コピュラでは、同時に大きな損害が出る確率はどれだけ違うのか？ | [627_copula_tail_dependence](articles/627_copula_tail_dependence) |

</details>

<details><summary><b>テキスト・ネットワーク・空間</b>（33本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F03 | 地価を決めているのは何か？ | [F03_land_price_ml](articles/F03_land_price_ml) |
| F06 | 高齢化は地図の上で固まっているか？ | [F06_aging_spatial](articles/F06_aging_spatial) |
| F09 | 国会で「賃上げ」はいつから語られるようになったのか？ | [F09_diet_text](articles/F09_diet_text) |
| F10 | 人の流れで見ると、日本はいくつの「圏」に分かれるか？ | [F10_mobility_network](articles/F10_mobility_network) |
| F18 | 景気は今どうなのか？ | [F18_nowcast_dfm](articles/F18_nowcast_dfm) |
| F20 | 出生率は隣の町と似るのか？ | [F20_tfr_spatial_regression](articles/F20_tfr_spatial_regression) |
| F25 | 経済白書41年分をAIの「文埋め込み」で読むと、政府の関心はどう移ったか？ | [F25_whitepaper_embeddings](articles/F25_whitepaper_embeddings) |
| F27 | 市区町村の死亡率の地図は、小さな町ほどぶれる。隣の町の情報を借りる空間ベイズ（BYM2）で描き直すと、地域差の9割以上は | [F27_disease_map_bym2](articles/F27_disease_map_bym2) |
| F29 | 北陸新幹線の金沢延伸で、石川県の宿泊客はどれだけ増えたか？ | [F29_shinkansen_sdid](articles/F29_shinkansen_sdid) |
| F52 | インフルエンザは、どの県からどの県へ広がるのか？ | [F52_influenza_spread](articles/F52_influenza_spread) |
| F53 | 日銀の声明文は、いつ「強気」から「弱気」に変わったか？ | [F53_boj_statement_tone](articles/F53_boj_statement_tone) |
| F66 | 統計の推計方法が変わると、数字はどれだけ動くのか？ | [F66_series_breaks](articles/F66_series_breaks) |
| F73 | 街の人の「景気の声」は、数字より先に動くか？ | [F73_watcher_text_tone](articles/F73_watcher_text_tone) |
| F74 | 観測点のない場所の気温は、どこまで当てられるか？ | [F74_temperature_kriging](articles/F74_temperature_kriging) |
| F75 | 地価の地図を「なめらかに」描くと、どこまで当たるか？ | [F75_gp_land_price](articles/F75_gp_land_price) |
| F85 | 日本経済の「要」の産業はどれか？ | [F85_io_network](articles/F85_io_network) |
| F95 | 新幹線の効果は、隣の県にもこぼれたのか？ | [F95_shinkansen_spillover](articles/F95_shinkansen_spillover) |
| F96 | e-Statの数万の統計表から、欲しい表をすぐ探せるか？ | [F96_estat_semantic_search](articles/F96_estat_semantic_search) |
| F100 | 同じ問いを5つの手法で分析すると、答えはそろうのか？ | [F100_five_methods_one_question](articles/F100_five_methods_one_question) |
| F107 | 市区町村のつながり（隣接・通勤）を使うと、予測は良くなるか？ | [F107_gcn_municipal](articles/F107_gcn_municipal) |
| F109 | どのデータを集めれば、予測は早く良くなるか？ | [F109_active_learning_land_price](articles/F109_active_learning_land_price) |
| F122 | 手法ごとに、どこでつまずいたか？ | [F122_pitfalls_from_logs](articles/F122_pitfalls_from_logs) |
| F123 | 「場所で分けて確かめる」と、記事の結論は変わったか？ | [F123_spatial_block_cv_review](articles/F123_spatial_block_cv_review) |
| F124 | 同じデータを何本の記事で使い回したか？ | [F124_data_lineage_network](articles/F124_data_lineage_network) |
| F140 | 外国人の住民は、どの地域に、どの速さで増えたのか？ | [F140_foreign_residents_concentration](articles/F140_foreign_residents_concentration) |
| F147 | 集計表から「それらしい個票」を作ると、元の分析を再現できるか？ | [F147_synthetic_from_tables](articles/F147_synthetic_from_tables) |
| F150 | 季節のパターンそのものは、年々変わっているのか？ | [F150_dynamic_seasonality](articles/F150_dynamic_seasonality) |
| F200 | 200本の看板記事で使ったデータと手法は、どうつながっているか？ | [F200_method_data_network](articles/F200_method_data_network) |
| F207 | 地価はどこで上がり、駅ができると何が起きるのか？ | [F207_landprice_series_part1](articles/F207_landprice_series_part1) |
| F208 | マンションの値段は地価とどう動き、地価の予測はどこで外れ続けるのか？ | [F208_landprice_series_part2](articles/F208_landprice_series_part2) |
| F261 | 潜在成長率は、計算の仕方でどれだけ変わるのか？ | [F261_potential_growth_methods](articles/F261_potential_growth_methods) |
| F269 | 「価格転嫁できた企業」は、どんな企業か？ | [F269_sme_price_passthrough](articles/F269_sme_price_passthrough) |
| 031 | 鹿児島は焼酎、東京はワイン：家計調査の「お酒の支出」をコレスポンデンス分析で地図にした | [031_alcohol_ca](articles/031_alcohol_ca) |

</details>

<details><summary><b>再現性・振り返り</b>（100本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F42 | 季節調整を自分でやると、公表値と同じになるか？ | [F42_seasonal_adjustment](articles/F42_seasonal_adjustment) |
| F45 | 将来人口の推計は、自分で再現できるか？ | [F45_population_projection](articles/F45_population_projection) |
| F47 | 都市ごとの「食の好み」を、行列分解で取り出せるか？ | [F47_food_nmf](articles/F47_food_nmf) |
| F57 | インフルエンザの流行は、SIRモデルで再現できるか？ | [F57_flu_sir](articles/F57_flu_sir) |
| F111 | 人口が減る町で、店はいつ消えるのか？ | [F111_shop_abm](articles/F111_shop_abm) |
| F118 | 「保育所と出生率」に、これまでの記事はどう答えたか？ | [F118_childcare_fertility_synthesis](articles/F118_childcare_fertility_synthesis) |
| F119 | 予測した記事は、その後どれだけ当たったか？ | [F119_forecast_scorecard](articles/F119_forecast_scorecard) |
| F120 | 2025年国勢調査で、記事の結論は変わったか？ | [F120_census2025_update](articles/F120_census2025_update) |
| F121 | 「最低賃金と雇用」に、4本の記事はどう答えたか？ | [F121_minwage_methods_review](articles/F121_minwage_methods_review) |
| F122 | 手法ごとに、どこでつまずいたか？ | [F122_pitfalls_from_logs](articles/F122_pitfalls_from_logs) |
| F123 | 「場所で分けて確かめる」と、記事の結論は変わったか？ | [F123_spatial_block_cv_review](articles/F123_spatial_block_cv_review) |
| F124 | 同じデータを何本の記事で使い回したか？ | [F124_data_lineage_network](articles/F124_data_lineage_network) |
| F125 | 100本を超えた看板記事で、「見えなかった」はどれくらいあったか？ | [F125_null_results_review](articles/F125_null_results_review) |
| F146 | 統計の秘匿をノイズで置き換えると、分析の答えはどれだけ変わるか？ | [F146_dp_noise_vs_suppression](articles/F146_dp_noise_vs_suppression) |
| F147 | 集計表から「それらしい個票」を作ると、元の分析を再現できるか？ | [F147_synthetic_from_tables](articles/F147_synthetic_from_tables) |
| F154 | 推定の「不確かさ」は、図の形で何が読み取れるかが変わるのか？ | [F154_uncertainty_viz](articles/F154_uncertainty_viz) |
| F157 | 電力需要の予測を、1年通して運用したらどうなるか？ | [F157_power_forecast_operation](articles/F157_power_forecast_operation) |
| F159 | 出生数の予測を、毎月の速報で更新すると当たり方は変わるか？ | [F159_births_nowcast](articles/F159_births_nowcast) |
| F161 | 同じデータで記事を書き直すと、結論はどれだけ変わるか？ | [F161_rewrite_old_articles](articles/F161_rewrite_old_articles) |
| F162 | 公的データは「API で取れる」のか？ | [F162_data_access_map](articles/F162_data_access_map) |
| F163 | 125本の看板記事で、いちばん効いた頑健性チェックは何だったか？ | [F163_robustness_checks_review](articles/F163_robustness_checks_review) |
| F165 | データ分析の「再現できる形」は、どこまで作れたか？ | [F165_reproducibility_audit](articles/F165_reproducibility_audit) |
| F167 | 「100年に1度の大雨」は、本当に100年に1度なのか？ | [F167_return_period_heavy_rain](articles/F167_return_period_heavy_rain) |
| F168 | 猛暑日の数は、どこまで増えたと言えるか？ | [F168_extreme_heat_trend](articles/F168_extreme_heat_trend) |
| F177 | 「差がある」は、並べ替えで確かめるとどうなるか？ | [F177_permutation_tests](articles/F177_permutation_tests) |
| F192 | 国債の金利は、何で動いているのか？ | [F192_jgb_yield_curve_pca](articles/F192_jgb_yield_curve_pca) |
| F200 | 200本の看板記事で使ったデータと手法は、どうつながっているか？ | [F200_method_data_network](articles/F200_method_data_network) |
| F246 | 分析担当として最初にやること：KPI を決める（業務の再現：架空の会社で） シリーズ③の1本目。架空の食品スーパー「サン | [F246_kpi_definitions_fictional_retail](articles/F246_kpi_definitions_fictional_retail) |
| F247 | データを集めて、使える形に整える（業務の再現：架空の会社で） シリーズ③の2本目。F246 の合成データ「サンプルマート | [F247_data_mart_fictional_retail](articles/F247_data_mart_fictional_retail) |
| F248 | 月次レポートの「型」を作る（業務の再現：架空の会社で） シリーズ③の3本目。F246 の KPI 定義 v1 と F24 | [F248_monthly_report_template_fictional_retail](articles/F248_monthly_report_template_fictional_retail) |
| F249 | ダッシュボードを作る（業務の再現：架空の会社で） シリーズ③の続き。F246 の KPI 定義 v1 と F247 の  | [F249_powerbi_dashboard_fictional_retail](articles/F249_powerbi_dashboard_fictional_retail) |
| F250 | 売上が落ちた月に、理由を説明する（業務の再現：架空の会社で） シリーズ③の5本目。F247 の mart を使い、架空の | [F250_sales_drop_explanation_fictional_retail](articles/F250_sales_drop_explanation_fictional_retail) |
| F251 | 販促の効果を測る（業務の再現：架空の会社で） シリーズ③の6本目。F247 の mart の架空の食品スーパー「サンプル | [F251_promo_effect_fictional_retail](articles/F251_promo_effect_fictional_retail) |
| F252 | 来期の予算のための需要予測（業務の再現：架空の会社で） シリーズ③の7本目。架空の食品スーパー「サンプルマート（架空）」 | [F252_budget_forecast_fictional_retail](articles/F252_budget_forecast_fictional_retail) |
| F253 | データの品質を毎月チェックする（業務の再現：架空の会社で） シリーズ③の8本目。架空の食品スーパー「サンプルマート（架空 | [F253_monthly_data_quality_checks_fictional_retail](articles/F253_monthly_data_quality_checks_fictional_retail) |
| F254 | 分析を引き継げる形にする（業務の再現：架空の会社で） シリーズ③の9本目。F246〜F251（コミット e5e9800） | [F254_handover_package_fictional_retail](articles/F254_handover_package_fictional_retail) |
| F255 | 1年の分析業務を振り返る（業務の再現：架空の会社で） シリーズ③の10本目・最後。架空の食品スーパー「サンプルマート（架 | [F255_year_review_fictional_retail](articles/F255_year_review_fictional_retail) |
| F256 | 自然災害の保険金は、この30年でどれだけ大きくなったのか？ | [F256_natural_disaster_insurance_payouts](articles/F256_natural_disaster_insurance_payouts) |
| F260 | 「100年に1度の損害」は、どの分布を仮定するかでいくら変わるのか？ | [F260_loss_distribution_return_level](articles/F260_loss_distribution_return_level) |
| F261 | 潜在成長率は、計算の仕方でどれだけ変わるのか？ | [F261_potential_growth_methods](articles/F261_potential_growth_methods) |
| F262 | 「出生数が過去最少」は、女性の人口の減少でどこまで説明できるか？ | [F262_births_record_low_decomposition](articles/F262_births_record_low_decomposition) |
| F263 | 比べる相手がないとき、何を対照にするか？ | [F263_control_choice_nationwide_policy](articles/F263_control_choice_nationwide_policy) |
| F265 | 少子化対策の「2025年の数値目標」は、決めた時点のペースで届くと読めたのか？ | [F265_policy_targets_pace](articles/F265_policy_targets_pace) |
| F266 | 「米の値段が上がった」は、どの段階で起きたのか？ | [F266_rice_price_stages](articles/F266_rice_price_stages) |
| F267 | 売上の目標を、客数と客単価の目標にどう分けるか？ | [F267_kpi_target_allocation_cvs](articles/F267_kpi_target_allocation_cvs) |
| F268 | 生命表が5年で変わると、年金の負担はどれだけ動くのか？ | [F268_life_table_annuity_value](articles/F268_life_table_annuity_value) |
| F269 | 「価格転嫁できた企業」は、どんな企業か？ | [F269_sme_price_passthrough](articles/F269_sme_price_passthrough) |
| F270 | 「訪日客が過去最多」は、1人あたりの支出で見ても最多か？ | [F270_inbound_record_per_capita](articles/F270_inbound_record_per_capita) |
| F271 | 見られるダッシュボードと、見られないダッシュボードの違いは何か？ | [F271_dashboard_answer_cost](articles/F271_dashboard_answer_cost) |
| F272 | 火災保険料の地域差は、リスクの差にどこまで見合っているか？ | [F272_fire_insurance_rate_vs_risk](articles/F272_fire_insurance_rate_vs_risk) |
| F273 | 観光白書の「地方への分散」は、宿泊データで見えているか？ | [F273_regional_dispersion_lodging](articles/F273_regional_dispersion_lodging) |
| F274 | 「人手不足倒産が過去最多」は、会社の数と数え方をそろえても増えたのか？ | [F274_labor_shortage_bankruptcy_rate](articles/F274_labor_shortage_bankruptcy_rate) |
| F275 | 集計の SQL は、どう書けば直しやすく、直し忘れに気づけるか？ | [F275_sql_change_requests](articles/F275_sql_change_requests) |
| F276 | 地震保険の付帯率は、地震のあとにどれだけ上がって戻るのか？ | [F276_earthquake_insurance_after_quakes](articles/F276_earthquake_insurance_after_quakes) |
| F277 | 最低賃金の審議会資料にある指標で、上げ幅はどこまで説明できるか？ | [F277_minimum_wage_council_indicators](articles/F277_minimum_wage_council_indicators) |
| F278 | 「空き家が過去最多」は、住宅の数が増えた分を除くとどうか？ | [F278_vacant_record_stock_vs_rate](articles/F278_vacant_record_stock_vs_rate) |
| F279 | RFM で分けた顧客は、その後どう動くのか？ | [F279_rfm_segment_transitions](articles/F279_rfm_segment_transitions) |
| F280 | 医療費の伸びは、年齢・回数・日数・1日当たりのどれで決まっているのか？ | [F280_medical_cost_three_elements](articles/F280_medical_cost_three_elements) |
| F281 | 食料自給率の目標と実際の差は、どこから来ているのか？ | [F281_food_self_sufficiency_target_gap](articles/F281_food_self_sufficiency_target_gap) |
| F282 | 「円安で輸出が増えた」は、数量と価格に分けるとどうか？ | [F282_yen_exports_quantity_price](articles/F282_yen_exports_quantity_price) |
| F283 | 値上げの前後で、売れ方はどう変わったか？ | [F283_price_hike_front_loading](articles/F283_price_hike_front_loading) |
| F284 | 豪雨の増え方を、火災保険の料率はどこまで追いかけているのか？ | [F284_heavy_rain_vs_fire_rates](articles/F284_heavy_rain_vs_fire_rates) |
| F285 | エネルギー基本計画の電力需要の見通しは、過去にどれだけ当たったか？ | [F285_power_demand_outlook_accuracy](articles/F285_power_demand_outlook_accuracy) |
| F286 | 「物価高で節約」は家計調査のどこに表れているか？ | [F286_household_saving_items](articles/F286_household_saving_items) |
| F287 | 同じ数字を、経営向けと現場向けでどう書き分けるか？ | [F287_report_two_audiences](articles/F287_report_two_audiences) |
| F288 | 損害額の分布の「裾の重さ」は、データの量でどこまで見分けられるか？ | [F288_tail_heaviness_sample_size](articles/F288_tail_heaviness_sample_size) |
| F289 | 情報通信白書のデジタル化の指標は、生産性と結びついているか？ | [F289_ict_capital_productivity](articles/F289_ict_capital_productivity) |
| F290 | アンケートの回答の偏りは、重み付けでどこまで直せるか？ | [F290_survey_weighting_limits](articles/F290_survey_weighting_limits) |
| F291 | 死亡率の改善は、年齢のどこで止まりつつあるのか？ | [F291_mortality_improvement_slowdown](articles/F291_mortality_improvement_slowdown) |
| F292 | 南海トラフの被害想定は、人口が変わるとどう動くか？ | [F292_quake_damage_population](articles/F292_quake_damage_population) |
| F293 | 毎月の数字の「おかしい」を、どう自動で見つけるか？ | [F293_monthly_anomaly_public_stats](articles/F293_monthly_anomaly_public_stats) |
| F294 | 介護の費用は、2040年度にどこまで増えるのか？ | [F294_care_cost_2040_assumptions](articles/F294_care_cost_2040_assumptions) |
| F295 | リスクを分けて計ると、分散効果はどれだけ効くのか？ | [F295_solvency_diversification_copula](articles/F295_solvency_diversification_copula) |
| 240 | グラフの縦軸を0から始めなかったら、どう見えたか？ | [240_axis_zero_baseline_review](articles/240_axis_zero_baseline_review) |
| 241 | 公的データを使って困ったことは何だったか？ | [241_public_data_troubles](articles/241_public_data_troubles) |
| 242 | 分析の「言えないこと」は、どう書くと誠実か？ | [242_limits_section_writing](articles/242_limits_section_writing) |
| 252 | 外れ値を消すか残すか、どう決めてきたか？ | [252_outlier_handling](articles/252_outlier_handling) |
| 253 | p値0.05の線を、どう扱ってきたか？ | [253_p_value_line](articles/253_p_value_line) |
| 269 | 「データが取れない」とき、どう代わりを探したか？ | [269_finding_substitute_data](articles/269_finding_substitute_data) |
| 286 | 予測モデルは、線形回帰と勾配ブースティングのどちらから始めるか？ | [286_linear_vs_gbm_first](articles/286_linear_vs_gbm_first) |
| 287 | 頑健性チェックは、いくつやれば十分か？ | [287_how_many_robustness_checks](articles/287_how_many_robustness_checks) |
| 288 | 書き続けてわかった、分析記事の書き方は何か？ | [288_writing_lessons_record](articles/288_writing_lessons_record) |
| 312 | SQL の NULL は、集計をどれだけ黙ってずらすのか？ | [312_sql_null_aggregation](articles/312_sql_null_aggregation) |
| 313 | 月の集計で、月末の最終日はどれだけ落ちているのか？ | [313_sql_month_end_boundary](articles/313_sql_month_end_boundary) |
| 321 | 題名に書いた数字は、結果のファイルと合っているか？ | [321_title_numbers_check](articles/321_title_numbers_check) |
| 325 | 同じ処理を、何回書き直していたか？ | [325_code_reuse_duplicates](articles/325_code_reuse_duplicates) |
| 327 | C# の Math.Round と SQL Server の ROUND と Excel の ROUND は、同じ答えを返すのか？ | [327_rounding_csharp_sql_excel](articles/327_rounding_csharp_sql_excel) |
| 342 | 締めたあとに訂正されたデータで、先月のレポートの数字を再現できるか？ | [342_restate_and_reproduce_reports](articles/342_restate_and_reproduce_reports) |
| 351 | 出典には、統計の名前・表の番号・取得日がそろっているか？ | [351_source_citation_elements](articles/351_source_citation_elements) |
| 355 | README の8つの節は、どれだけそろっているか？ | [355_readme_sections_coverage](articles/355_readme_sections_coverage) |
| 372 | CSV を Excel で開いて保存すると、何セルが変わってしまうのか？ | [372_csv_excel_roundtrip](articles/372_csv_excel_roundtrip) |
| 374 | VLOOKUP は、どんなときに黙って間違った値を返すのか？ | [374_vlookup_silent_errors](articles/374_vlookup_silent_errors) |
| 375 | 全角と半角、前後の空白で、キーはどれだけつながらないのか？ | [375_key_normalization_join](articles/375_key_normalization_join) |
| 382 | 記事どうしは、どうつながっているか？ | [382_article_links_network](articles/382_article_links_network) |
| 385 | 図には、軸の名前・単位・出典がそろっているか？ | [385_figure_elements_check](articles/385_figure_elements_check) |
| 403 | ORDER BY のない SELECT の並びに頼ると、結果はどれだけ再現しないのか？ | [403_select_without_order_by](articles/403_select_without_order_by) |
| 406 | SQL の見直しの観点10個を、自分の記事の SQL に当てると何件引っかかるか？ | [406_sql_review_checklist_hits](articles/406_sql_review_checklist_hits) |
| 412 | 月末に始まった契約の「1か月後」は、いつになるのか？ | [412_monthly_anniversary_dates](articles/412_monthly_anniversary_dates) |
| 427 | 「2025/1/5」「R7.1.5」「20250105」が混ざった日付の列は、機械に読ませると何件が別の日になるのか？ | [427_mixed_date_formats](articles/427_mixed_date_formats) |
| F297 | 自分の分析記事1,066本は、決めた書き方をどこまで守っていたのか？ | [F297_article_practice_audit](articles/F297_article_practice_audit) |

</details>

<details><summary><b>その他（記述・要因分解など）</b>（391本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F21 | 公的統計の「いつもと違う動き」を自動で見つけられるか？ | [F21_anomaly_detection](articles/F21_anomaly_detection) |
| F23 | 救急車をどこに置けば、到着が早くなるか？ | [F23_ambulance_location](articles/F23_ambulance_location) |
| F38 | 観光客が1兆円使うと、日本全体の生産はいくら増えるのか？ | [F38_input_output_tourism](articles/F38_input_output_tourism) |
| F40 | 所得の格差は「県の間」と「県の中」のどちらにあるか？ | [F40_inequality_decomposition](articles/F40_inequality_decomposition) |
| F58 | 合計特殊出生率は、年齢のどこで下がったのか？ | [F58_tfr_age_tempo](articles/F58_tfr_age_tempo) |
| F64 | エンゲル係数の上昇は、本当に生活苦か？ | [F64_engel_decomposition](articles/F64_engel_decomposition) |
| F69 | 統計表の「-」は0なのか、欠測なのか？ | [F69_data_quality](articles/F69_data_quality) |
| F83 | 日本の生産性の伸びは「産業の中」か「産業の入れ替わり」か？ | [F83_productivity_shift_share](articles/F83_productivity_shift_share) |
| F93 | PDF の統計表を機械で読むと、どれくらい間違えるか？ | [F93_pdf_table_extraction](articles/F93_pdf_table_extraction) |
| F94 | 市町村合併をどう扱うかで、20年の推移の分析は変わるか？ | [F94_municipal_merger_panel](articles/F94_municipal_merger_panel) |
| 000 | 女性の労働力率は何で決まる？ | [000_women_labor](articles/000_women_labor) |
| 001 | 納税者1人あたりの所得は、なぜ街によって違うのか？ | [001_income_municipal](articles/001_income_municipal) |
| 008 | 人が集まっている街は、所得が高い街か？ | [008_migration_income](articles/008_migration_income) |
| 009 | 子どもが多く生まれる街は、所得が高い街か？ | [009_births_income](articles/009_births_income) |
| 010 | 外国人住民が多いのは、どんな市区町村か？ | [010_foreign_residents_income](articles/010_foreign_residents_income) |
| 012 | 東京23区の中の所得の差は何倍か？ | [012_tokyo23_income](articles/012_tokyo23_income) |
| 013 | 昼に人が集まる街は、所得が高い街か？ | [013_daynight_income](articles/013_daynight_income) |
| 014 | ふるさと納税で「赤字」になるのは、どんな街か？ | [014_furusato_balance](articles/014_furusato_balance) |
| 015 | 財政力が強い町は、住民の所得が高い町か？ | [015_fiscal_strength](articles/015_fiscal_strength) |
| 016 | 人口あたりの医師が多いのは、どんな市区町村か？ | [016_doctors](articles/016_doctors) |
| 021 | 福島市の桃は全国の6倍、高知市のかつおは4.5倍：家計調査で「その街らしい食卓」と似た街を探した | [021_prefcapital_food](articles/021_prefcapital_food) |
| 023 | スマホでゲームや音楽を楽しむ人が多いのは、どの県か？ | [023_games_music_aging](articles/023_games_music_aging) |
| 024 | ふるさと納税は一部の自治体に集中しているか？ | [024_furusato_concentration](articles/024_furusato_concentration) |
| 025 | 外国人の宿泊はコロナ前に戻ったか？ | [025_inbound_recovery](articles/025_inbound_recovery) |
| 026 | 人が転入してくる年に、その県の地価は上がるか？ | [026_migration_landprice_fe](articles/026_migration_landprice_fe) |
| 027 | YouTube などの動画サイトは誰が見ている？ | [027_video_viewers_age](articles/027_video_viewers_age) |
| 028 | 動画サイトの利用率、都道府県の差は「誤差」なのか？ | [028_video_usage_funnel](articles/028_video_usage_funnel) |
| 030 | 通勤時間が長い県は、何の時間を削っているか？ | [030_commute_sleep](articles/030_commute_sleep) |
| 032 | 人口が2倍の街には、飲食店も2倍あるか？ | [032_scaling_law](articles/032_scaling_law) |
| 033 | 高校卒業後の進学率、県の差は縮まっているか？ | [033_university_convergence](articles/033_university_convergence) |
| 034 | テレワークをしたことがある人は6年で4倍に。でも年収・性別・住む県で大きな差（通信利用動向調査） | [034_telework](articles/034_telework) |
| 035 | 円安は、どれくらい物価を上げるのか？ | [035_yen_prices_var](articles/035_yen_prices_var) |
| 038 | 築年数と駅からの距離で、マンションはいくら安くなる？ | [038_condo_age_station](articles/038_condo_age_station) |
| 039 | 駅の利用者はコロナ前に戻ったか？ | [039_station_recovery](articles/039_station_recovery) |
| 040 | 1年で利用者が半分になった駅は本当か？ | [040_data_breaks](articles/040_data_breaks) |
| 041 | 今の地価は、バブルのピークの何%か？ | [041_landprice_bubble](articles/041_landprice_bubble) |
| 042 | この10年で地価が上がった場所・下がった場所：全国2万地点で見ると、同じ県の中でも「高い所ほど上がる」二極化だった | [042_landprice_polarization](articles/042_landprice_polarization) |
| 043 | 2050年に人口が半分未満になる市町村は341。将来推計を「出生・死亡」と「人の移動」に分けてみた | [043_population_2050](articles/043_population_2050) |
| 045 | 50代前半の月給は20代前半の何倍？ | [045_wage_curve](articles/045_wage_curve) |
| 046 | 都道府県の年収差は「職種の違い」から来ているのか？ | [046_wage_shiftshare](articles/046_wage_shiftshare) |
| 047 | 2022年以降、死亡数は「予想」より毎年9万〜13万人多い。ただし予想の作り方で6年の合計は8万〜47万人まで変わる | [047_excess_deaths](articles/047_excess_deaths) |
| 049 | 大学進学率はどこまで上がる？ | [049_university_scurve](articles/049_university_scurve) |
| 050 | 子どもはほぼ半分、学校は4分の1減。小学校の数と子どもの数を77年分比べたら、減り方は「時期」で決まっていた | [050_school_closures](articles/050_school_closures) |
| 051 | 家計の株は「売り越し」なのに400兆円増えた。資金循環統計で、買った分と値上がり分を分けてみた | [051_household_assets](articles/051_household_assets) |
| 052 | 日本の家計は「値上がりした後に買う」のか？ | [052_household_flows](articles/052_household_flows) |
| 053 | 東京都の外国人は47年で7倍。国籍ごとの「住む場所の偏り」を非類似度指数で測ったら、多くは小さくなっていた | [053_tokyo_foreign_segregation](articles/053_tokyo_foreign_segregation) |
| 054 | 東京都の外国人は10年で75%増。区市ごとの伸びの差は「国籍構成」ではなく、ほぼ「地域独自」だった | [054_tokyo_foreign_growth](articles/054_tokyo_foreign_growth) |
| 055 | 日本の気温の「最高記録」は、最近30年で5回。気温が変わらなければ0.27回のはずだった | [055_temperature_records](articles/055_temperature_records) |
| 056 | 1時間に100mm以上の雨は、40年で2倍に。強い雨ほど速く増えていた | [056_heavy_rain](articles/056_heavy_rain) |
| 057 | 暑さ指数31の日は、25の日の約7倍。熱中症の救急搬送を、6都市10年分の日別データで調べた | [057_wbgt_heatstroke](articles/057_wbgt_heatstroke) |
| 058 | 「夏の初めほど熱中症になりやすい」はデータで見えるか？ | [058_heatstroke_season](articles/058_heatstroke_season) |
| 059 | 交通事故29万件で「死亡事故になりやすい条件」を調べた。単独事故・歩行者・深夜・カーブで高かった | [059_fatal_accidents](articles/059_fatal_accidents) |
| 060 | 人身事故は6年で25%減。それでも「75歳以上」と「自転車」が第1当事者の事故だけは増えていた | [060_accidents_change](articles/060_accidents_change) |
| 061 | 大都市圏の中古マンションは4年で約3割上昇。品質をそろえて比べると、戸建ての伸びはその半分ほどだった | [061_house_price_index](articles/061_house_price_index) |
| 062 | 同じ条件の中古マンションでも、レインズの成約価格は登記ベースの取引価格より約1割低かった | [062_contract_vs_transaction](articles/062_contract_vs_transaction) |
| 063 | 訪問介護の事業所は減っていなかった。ただ2024年の報酬改定のあと、撤退のしやすさは通所介護と比べて1.4倍になっていた | [063_home_care_entry_exit](articles/063_home_care_entry_exit) |
| 064 | 訪問介護の事業所が1つもない市区町村は、5年半で46から83に増えていた | [064_home_care_access](articles/064_home_care_access) |
| 065 | Mが1大きい地震は約9分の1しか起きない。ただし小さな地震まで数えると、この法則は崩れて見える | [065_earthquake_bvalue](articles/065_earthquake_bvalue) |
| 066 | 余震はほぼ「経過時間に反比例」して減る。東北・熊本・能登の3つの地震で、減り方の指数はどれも1.03〜1.08だった | [066_aftershock_omori](articles/066_aftershock_omori) |
| 067 | 食中毒は25年でほぼ半減。腸炎ビブリオやサルモネラは激減し、代わりにアニサキスが増え、ノロウイルスは2025年に戻ってき | [067_food_poisoning_trend](articles/067_food_poisoning_trend) |
| 068 | 食中毒の患者の4分の1は、上位1%の大きな事件から。仕出屋とノロウイルスの事件が大きくなりやすかった | [068_food_poisoning_size](articles/068_food_poisoning_size) |
| 069 | 台風の数は75年でやや少なめに。でも日本に近づく台風の数は、ほとんど変わっていなかった | [069_typhoon_counts](articles/069_typhoon_counts) |
| 070 | 台風が最も発達する場所は北へ移ったか。1980年以降の全台風では10年で0.4度北上、強い台風に限るとはっきりしなかった | [070_typhoon_latitude](articles/070_typhoon_latitude) |
| 071 | 日曜に開いている診療所は8%。平日夜7時以降の診療は全国で4分の1、近畿では5〜7割だった | [071_clinic_hours](articles/071_clinic_hours) |
| 072 | 薬局の半分は、医療機関から50m以内にあった。産婦人科を掲げる医療機関が掲載されていない市区町村は864 | [072_pharmacy_distance](articles/072_pharmacy_distance) |
| 073 | 工場などから出る化学物質の排出は、24年で3分の1になっていた。いちばん効いたのは、続けて届け出ている事業所の削減だった | [073_prtr_decline](articles/073_prtr_decline) |
| 074 | 化学物質の排出の半分は、届け出ている事業所の上位1%から出ていた。この集中は24年間ほとんど変わっていない | [074_prtr_concentration](articles/074_prtr_concentration) |
| 075 | さくらの開花は1960〜80年代より約5日早く、かえでの紅葉は約11日遅くなっていた | [075_sakura_autumn_leaves](articles/075_sakura_autumn_leaves) |
| 076 | とのさまがえるを記録した地点は9割減。ほかの生き物の減少の多くは、観測地点そのものが減った分だった | [076_phenology_animals](articles/076_phenology_animals) |
| 077 | インフルエンザの流行の山は3シーズン続けて年内に。伝染性紅斑は2025年、マイコプラズマ肺炎は2024年に大きな流行があ | [077_infectious_peaks](articles/077_infectious_peaks) |
| 078 | インフルエンザの流行は毎シーズン沖縄が先行。本土での広がり方は年ごとに違い、手足口病は南から北へ進んでいた | [078_infectious_onset](articles/078_infectious_onset) |
| 079 | 都道府県をまたぐ引っ越しは1971年がピークで、今はその半分。それでも東京圏への転入超過は70年間ほぼ毎年続いていた | [079_migration_tokyo](articles/079_migration_tokyo) |
| 080 | 引っ越しが距離に左右される度合いは1970年までに弱まり、その後50年ほぼ同じ。東京圏へ向かう割合は西日本や中部で上がり | [080_migration_gravity](articles/080_migration_gravity) |
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
| 098 | 2019年より売上が多いのはスーパーやドラッグストア。でもコロナ前の伸び方には、コンビニとドラッグストアが届いていなかっ | [098_retail_recovery](articles/098_retail_recovery) |
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
| 124 | 辞める理由の4分の3は「個人的理由」。女性の結婚・出産による離職は14%から3%に減った | [124_turnover_reasons](articles/124_turnover_reasons) |
| 125 | 昼夜間人口比率1位は千代田区の1,355。でも30年でほぼ半分に下がり、住む人が増えた | [125_daytime_population](articles/125_daytime_population) |
| 126 | 副業をする人は年収の低い人と高い人に多いU字型。正規は2.6%、役員・自営業主は9%前後 | [126_side_jobs](articles/126_side_jobs) |
| 127 | 物価が高い県は13年ずっと東京都。ただ家賃を除くと、2023年から北海道が1位になった | [127_regional_prices](articles/127_regional_prices) |
| 128 | ピアノは静岡県が100%、眼鏡枠は福井県が92%。1県に生産が集中する製造品は全体の1割 | [128_product_concentration](articles/128_product_concentration) |
| 129 | 住まいの不満、多いのは断熱・地震・高齢者への配慮。治安への不満は10年で半分に、断熱はほぼ変わらず | [129_housing_satisfaction](articles/129_housing_satisfaction) |
| 130 | 日本人観光客の日帰りは埼玉99%、和歌山51%。人数では9割が日帰りでも、お金では半分ほど | [130_tourism_daytrip](articles/130_tourism_daytrip) |
| 131 | 入院患者の平均年齢は60年で36歳から73歳に。4人に3人が65歳以上、それでも年齢ごとの入院は半分に | [131_inpatient_age](articles/131_inpatient_age) |
| 132 | 高齢者1人あたりの介護給付費は全国31.2万円。大阪府37.6万円、栃木県26.4万円で、差の3分の1は年齢構成で説明で | [132_ltc_benefits](articles/132_ltc_benefits) |
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
| 145 | 訪日客の支出は「買物」から「宿泊」へ。中国は買物の割合が51%→37%、欧米は宿泊に4割以上を使っていた | [145_inbound_spending](articles/145_inbound_spending) |
| 146 | 診療所は15年で6%増。腎臓内科・糖尿病内科・美容外科を掲げる所は2倍以上に、小児科と外科は2割減っていた | [146_clinic_specialties](articles/146_clinic_specialties) |
| 147 | 通所介護は2015年度まで訪問介護の2倍の速さで増えた。コロナ後は逆転し、訪問介護のほうが伸びていた | [147_home_vs_day_care](articles/147_home_vs_day_care) |
| 148 | 小学校の先生の年齢構成は、「ふたコブ」からどう変わったか？ | [148_teacher_age](articles/148_teacher_age) |
| 150 | 黄砂の観測日数は、2000年代から減ったのか？ | [150_yellow_sand](articles/150_yellow_sand) |
| 151 | 農業経営体は5年で22%減、石川県は36%減。経営主のいちばん多い年齢は70〜74歳になった | [151_farm_decline](articles/151_farm_decline) |
| 152 | スマホを9割以上が持つのは50代まで。60代は89%に迫り、70代68%・80歳以上33%で大きな段差があった | [152_smartphone_age](articles/152_smartphone_age) |
| 153 | 平均初婚年齢の上昇は2013〜14年頃に止まった。夫は31.1歳で横ばい、妻は11年で0.3歳だけ上がった | [153_first_marriage_age](articles/153_first_marriage_age) |
| 154 | 最低賃金の地域差は2014年度をピークに縮まった。最高÷最低は1.31倍から1.18倍に、それでも差額は195円ある | [154_minimum_wage_gap](articles/154_minimum_wage_gap) |
| 155 | 病床利用率は1〜2月が高い。ただ一番大きいのは12月末の落ち込みで、月末が土日でも約3ポイント下がる | [155_bed_occupancy_season](articles/155_bed_occupancy_season) |
| 156 | ネット販売の売上比率が高いのは航空運輸業の32%。全体では売上の1.2%で、電子商取引をする企業は4%のままだった | [156_ec_sales_by_industry](articles/156_ec_sales_by_industry) |
| 157 | よく出される飲み薬は1年で101億錠。子どもはアレルギーの薬が4割、40〜74歳の男性は糖尿病の薬がいちばん多かった | [157_drugs_by_sex_age](articles/157_drugs_by_sex_age) |
| 158 | サービス産業の売上は2023年3月にコロナ前を回復。宿泊業は2019年の118%まで伸びたが、飲食店は85%のままだった | [158_service_recovery](articles/158_service_recovery) |
| 159 | 1人あたり医療費は15年で42%増。ただ年齢別では10代が+87%、70代は+5%で、全体の伸びは高齢化によるところが大 | [159_medical_cost_by_age](articles/159_medical_cost_by_age) |
| 160 | 国内旅行は「日帰り化」していなかった。日帰りの割合は2014年の50%から2025年は46%に下がり、出張の日帰りが特に | [160_daytrip_share](articles/160_daytrip_share) |
| 161 | 特定健診の受診率は健保組合83%、市町村国保38%。15年で差は29ポイントから45ポイントに広がっていた | [161_health_checkup_rate](articles/161_health_checkup_rate) |
| 162 | 介護をしながら働く人は5年で18万人増えて365万人に。増えたのは50〜60代で、増加の8割は働く人の年齢構成の変化だっ | [162_working_carers](articles/162_working_carers) |
| 163 | 調剤医療費の伸び、この5年は半分が薬局の技術料、4割が注射薬。内服薬は日数が3割伸びても1日の値段が2割下がった | [163_dispensing_costs](articles/163_dispensing_costs) |
| 165 | 人口あたりの看護師は高知が最多で埼玉の2.1倍。上位10県はすべて中国・四国・九州だった | [165_nurses_by_pref](articles/165_nurses_by_pref) |
| 167 | 医療費の中で割合が最も伸びた病気はがんなどの新生物で13.1%から15.0%に。循環器は20.8%から18.2%に下がっ | [167_medical_cost_by_disease](articles/167_medical_cost_by_disease) |
| 168 | 産業廃棄物は年3.7億t。電気・水道業、農業、建設業がそれぞれ2割強で、種類では汚泥が42%を占めていた | [168_industrial_waste_by_industry](articles/168_industrial_waste_by_industry) |
| 169 | 外国人労働者は10年で2.4倍。製造業は1位のまま割合が31%から25%に下がり、医療・福祉は8.4倍、建設業は5.0倍 | [169_foreign_workers_by_industry](articles/169_foreign_workers_by_industry) |
| 170 | 日本企業の海外現地法人は2021年度にASEANが中国を上回った。中国の現地法人で働く人は9年で4割減った | [170_overseas_affiliates_region](articles/170_overseas_affiliates_region) |
| 172 | 理容所はピークから26%減、美容所は60年で3.1倍。銭湯は84%減、クリーニングは58%減だった | [172_barber_beauty_salons](articles/172_barber_beauty_salons) |
| 173 | 家庭の光熱費の内訳で52都市を分けると3タイプ。灯油型の4都市は光熱費が都市ガス型の1.5倍だった | [173_household_energy_types](articles/173_household_energy_types) |
| 174 | 「3年で3割辞める」大卒は28年中27年で30%以上。高卒は50%から37%に下がり、1年目に辞める割合は減っていた | [174_three_year_turnover](articles/174_three_year_turnover) |
| 175 | ゴルフ場の利用者は2000年比95でコロナ前並み。ボウリング場は34まで減ったが、それでも2019年までの減り方の延長よ | [175_golf_bowling_users](articles/175_golf_bowling_users) |
| 176 | コンテナの港ランキングは15年でほとんど動かなかった。上位10港は2012年から同じ顔ぶれで、2024年の量は2019年 | [176_container_ports](articles/176_container_ports) |
| 177 | 入院する人の割合の県差は、年齢をそろえても2.2倍残る。上位12県のうち10県が九州・四国・山口だった | [177_treatment_rate_age_adjusted](articles/177_treatment_rate_age_adjusted) |
| 178 | 産業廃棄物の再生利用率は2008年度から52〜55%で横ばい。汚泥を除けば9割近く、紙くずやばいじんは13年で10ポイン | [178_industrial_waste_recycling](articles/178_industrial_waste_recycling) |
| 179 | 外国人労働者の半分が技能実習の県もある。宮崎・青森・高知は全国の2.5倍で、東京は0.28倍だった | [179_technical_intern_specialization](articles/179_technical_intern_specialization) |
| 180 | 日本の輸出先、米国の割合は30年で27%から18%台に。中国は5%から17%になり、インドとベトナムが上位10か国に入っ | [180_export_destination_ranking](articles/180_export_destination_ranking) |
| 181 | 鉄道の定期外はコロナ前を超えたのに、定期は2019年度の87%のまま。5年で約19億人分が戻っていなかった | [181_rail_commuter_recovery](articles/181_rail_commuter_recovery) |
| 182 | 人口あたりの病床数、最多の高知は神奈川の3倍。上位15のうち14が中国・四国・九州。差は療養と精神の病床で大きかった | [182_hospital_beds_west_east](articles/182_hospital_beds_west_east) |
| 183 | 日本の温室効果ガスは2013年度から25%減。減った量の37%は産業部門で、鉄鋼だけで16%。業務と家庭も4割近くを占め | [183_ghg_sector_contribution](articles/183_ghg_sector_contribution) |
| 184 | 大卒の3年以内離職率、5人未満の事業所は58%、1,000人以上は24%。規模が10倍になるごとに約12ポイント下がり、 | [184_turnover_by_firm_size](articles/184_turnover_by_firm_size) |
| 185 | 売上100億円以上の企業は全体の0.46%なのに、売上の7割を占める。上位1%では約77%、約8割の企業の売上は合わせて | [185_sales_concentration](articles/185_sales_concentration) |
| 186 | トラックの荷物、運送会社が運ぶ割合は1970年度の24%から67%に。距離をかけると88%で、自家用は平均20km余りの | [186_truck_commercial_share](articles/186_truck_commercial_share) |
| 187 | 病院の外来患者は2025年も2019年の9割。静岡96から秋田84まで県で差があり、47都道府県のすべてがコロナ前に戻っ | [187_outpatient_recovery_pref](articles/187_outpatient_recovery_pref) |
| 188 | 塾代のピークは中3で年34万円。通う割合は中3が79%で最も高いが、通う子1人の金額は高3の45万円が最も多い | [188_juku_cost_by_grade](articles/188_juku_cost_by_grade) |
| 189 | 家庭のCO2は北海道が全国の1.7倍。ただエネルギーが最も少ない沖縄も全国より多く、最少は九州。差を広げるのは電気のつく | [189_household_co2_region](articles/189_household_co2_region) |
| 190 | 黄砂の観測日は福岡が年7.5日で東京の9.5倍。東京で見えた日の7割は福岡でも観測、ただ最も西の那覇は福岡の半分以下だっ | [190_yellow_sand_stations](articles/190_yellow_sand_stations) |
| 191 | 野菜の産地はどれだけ集中しているか。ばれいしょは北海道が8割、41品目のうち20品目は上位3県で半分以上だった | [191_vegetable_concentration](articles/191_vegetable_concentration) |
| 192 | 障害者の実雇用率、大企業と小さな企業の差は12年で縮まらず0.59→0.75ポイントに。法定雇用率が上がる年は大企業ほど | [192_disability_employment_size](articles/192_disability_employment_size) |
| 193 | 市区町村の稼ぎ頭は製造業が5割。全国では医療・福祉が最大でも、1,741市区町村のうち910で製造業が1位だった | [193_municipal_earning_industry](articles/193_municipal_earning_industry) |
| 194 | 大きな都市ほど自動車を使わない。人口10倍で分担率は23ポイント低いが、100万都市でも東京23区12%と仙台市50%の | [194_city_size_car_share](articles/194_city_size_car_share) |
| 195 | 病院は35年で2割減。減った分の8割は100床未満の小さな病院で、150〜199床だけが増えていた | [195_hospital_bed_size](articles/195_hospital_bed_size) |
| 196 | 女性の小学校長は10年で19%から30%に。石川は58%、島根・長崎は12%で、10年前に女性の教頭が多かった県ほど今の | [196_female_principals](articles/196_female_principals) |
| 197 | 騒音の苦情で工場は20年で4割減。代わりに建設業が6割増えて、いまは工事の音が騒音の苦情の4割を占める | [197_noise_complaints](articles/197_noise_complaints) |
| 198 | 日照時間の「晴れの県ランキング」は30年たってもほとんど入れ替わらない。山梨は39年中21年で1位、秋田は34年で下位5 | [198_sunshine_rank](articles/198_sunshine_rank) |
| 199 | 主要147漁港の水揚げは、上位10港で半分近く。下位半分の73港は合わせて5%で、10年で大きな港への集中が進んだ | [199_fishing_ports](articles/199_fishing_ports) |
| 200 | 勤務間インターバル制度の導入は1,000人以上の企業で20%、30〜99人は6%。7年で差は4ポイントから14ポイントに | [200_work_interval](articles/200_work_interval) |
| 201 | サービス業の売上は人数にほぼ比例。人が10倍の事業所は売上11.4倍、ただ葬儀や結婚式場は大きいほど1人あたりが下がる | [201_service_sales_scale](articles/201_service_sales_scale) |
| 202 | 分譲マンションの年収倍率は2024年度調査まで5倍台、2025年度は6.57倍に。購入資金は1年で37.7%増えた | [202_condo_income_ratio](articles/202_condo_income_ratio) |
| 203 | 埼玉県の観光客の3分の1は越谷市。上位5市で6割を占め、この割合は15年ほぼ変わらない | [203_saitama_tourism_concentration](articles/203_saitama_tourism_concentration) |
| 204 | HbA1c 6.5%以上の人は特定健診で7.26%。年齢をそろえても佐賀県8.72%、長野県6.34%と1.38倍の差 | [204_health_checkup_hba1c](articles/204_health_checkup_hba1c) |
| 205 | 図書館で1人が借りる本は年4.78冊。滋賀県は7.30冊、青森県と秋田県は2.74冊で2.7倍の差 | [205_library_loans](articles/205_library_loans) |
| 206 | 食品ロスは12年で182万トン減。事業系94万トン、家庭系88万トンとほぼ半々で、外食は2年続けて増加 | [206_food_loss](articles/206_food_loss) |
| 207 | 紫外線のピークは6月でなく7〜8月。那覇の7月は10.3と札幌の1.7倍 | [207_uv_index](articles/207_uv_index) |
| 208 | 牛乳の生産は1994年から29%減。ヨーグルトなどのはっ酵乳は5.5倍になり、牛乳の3分の1に | [208_milk_products](articles/208_milk_products) |
| 209 | 都道府県ランキングの1位は、10年で半分近く入れ替わる。334指標で1位が同じだったのは56% | [209_pref_rank_turnover](articles/209_pref_rank_turnover) |
| 210 | ストライキは1974年の5,211件から27件に。1976年から年11%ずつ減り、2003年からは年20〜50件台で横ば | [210_strikes](articles/210_strikes) |
| 211 | 家賃を除いても、物価の地域差は2割しか縮まない。東京都は1位から3位に、北海道が1位に | [211_regional_price_ex_rent](articles/211_regional_price_ex_rent) |
| 212 | 労働分配率は景気後退期に上がる。14回中13回で上昇し、平均4.1ポイント | [212_labor_share_cycle](articles/212_labor_share_cycle) |
| 213 | 昭和54年以前のマンションは役員の47%が70歳以上。同じ築年を5年後に見ると、さらに高齢化していた | [213_condo_aging](articles/213_condo_aging) |
| 215 | 医療費は23年で18兆円増えた。高齢化の分は57%、残りの多くは一人当たり医療費の伸び | [215_medical_cost_aging](articles/215_medical_cost_aging) |
| 216 | 要介護認定者は2007年度から1.6倍に。増えたのは軽い区分で、要介護5は1.16倍にとどまった | [216_care_levels](articles/216_care_levels) |
| 217 | 給食の自校方式は神奈川で87%、島根で1%。15年で39都道府県が自校方式の割合を減らした | [217_school_lunch_kitchens](articles/217_school_lunch_kitchens) |
| 218 | 食品ロスの2030年度目標、家庭系は今のペースなら届く。事業系はここ3年横ばいで、届くかは読み切れない | [218_food_loss_2030](articles/218_food_loss_2030) |
| 219 | 2025年の梅雨明けは8地方で1951年以降最も早かった。それでも76年で見ると、梅雨明けは早まっていない | [219_baiu_end_trend](articles/219_baiu_end_trend) |
| 220 | 養豚は1戸2.4頭から2,811頭に。2,000頭以上の経営が頭数の8割を持つが、ジニ係数はむしろ下がった | [220_livestock_scale](articles/220_livestock_scale) |
| 221 | 理想の子ども数と実際の差は、広がっていなかった。縮んだのは、理想が2.67人から2.25人に下がったから | [221_ideal_vs_actual_children](articles/221_ideal_vs_actual_children) |
| 222 | 労災でいちばん多いのは転倒で、16年で1.6倍に。60歳以上では死傷の4割が転倒だった | [222_falls_elderly_workers](articles/222_falls_elderly_workers) |
| 223 | ネットで買う品目の順位は、10年でほとんど入れ替わらなかった。大きく上がったのは出前で、21位から13位に | [223_online_shopping_rank](articles/223_online_shopping_rank) |
| 225 | 建設工事の受注は、3月にふつうの月の2倍入る。年度末の山をつくっているのは公共工事より民間の非製造業だった | [225_construction_orders_fiscal_yearend](articles/225_construction_orders_fiscal_yearend) |
| 226 | 円安が大きかった国の訪日客ほど、円で見た支出が増えた。国と年の違いを除くと、円安1%で支出は0.89%増えていた | [226_fx_inbound_spending](articles/226_fx_inbound_spending) |
| 227 | コーヒーにかけるお金は10年で1.7倍。家で淹れる量は2019年とほぼ同じで、増えたのは豆の値段と喫茶店だった | [227_coffee_home_vs_cafe](articles/227_coffee_home_vs_cafe) |
| 228 | 外食は2019年より15%多いが、物価を除くと5%少ない。戻っていないのは70歳以上と50代の世帯で、喫茶代はどの年齢で | [228_eating_out_recovery_by_age](articles/228_eating_out_recovery_by_age) |
| 229 | お菓子の支出は10年で33%増えたが、物価を除くと7%減った。値段が1.75倍のチョコレートは実質4割減で、ビスケットと | [229_sweets_nominal_vs_real](articles/229_sweets_nominal_vs_real) |
| 230 | お酒の支出で増えたのはビールとチューハイ。発泡酒・ビール風は量で3割減り、ビールは3割増えたが、ビール系を合わせた量は7 | [230_alcohol_mix_shift](articles/230_alcohol_mix_shift) |
| 231 | 2025年、米の支出が2015年以降で初めてパンを上回った。米を買った量は2019年とほぼ同じで、逆転は1kgあたりの値 | [231_bread_vs_rice](articles/231_bread_vs_rice) |
| 235 | 大学院の入学者の17%は社会人。博士課程では4割になったが、人数の多い修士課程では25年前の1割から9%に下がり、学部に | [235_adult_learners_grad_school](articles/235_adult_learners_grad_school) |
| 236 | 理学・工学の女子学生は25年で1.4倍、割合は12%から20%に。伸び始めたのは2010年ごろからで、機械・電気は1割前 | [236_women_in_stem_faculties](articles/236_women_in_stem_faculties) |
| 237 | 短期大学の学生は1993年の53万人から7.1万人へ7分の1に。人文と家政は2000年の1〜2割まで減り、いまは学生の3 | [237_junior_college_decline](articles/237_junior_college_decline) |
| 238 | 修士の入学者は25年で14%増。増えたのは分野をまたぐ研究科と工学で、社会科学は3割、教育は6割減った。博士では人文と社 | [238_grad_entrants_by_field](articles/238_grad_entrants_by_field) |
| 239 | 専門学校の生徒は1992年の86万人から62万人に。20年で増えたのは商業・動物・情報の学科、減ったのは看護・受験補習・ | [239_vocational_school_fields](articles/239_vocational_school_fields) |
| 246 | 宿泊客が2019年を超えたのは、従業者30人未満の施設が先だった。100人以上の大きな施設が超えたのは2025年で、延べ | [246_lodging_recovery_by_size](articles/246_lodging_recovery_by_size) |
| 247 | 休日が1日多い月、観光の宿に泊まる日本人は2019年までは1.2%多かった。2023〜25年はほぼ0%だが、差ははっきり | [247_lodging_holidays_weekday](articles/247_lodging_holidays_weekday) |
| 249 | 宿泊施設は2019年から1.4万増えて7.3万に。1施設あたりの宿泊者は1割減ったが、それは従業者0〜9人の小さい施設が | [249_lodging_guests_per_facility](articles/249_lodging_guests_per_facility) |
| 250 | 1回の宿泊の平均泊数は1.34泊から1.42泊に伸びた。伸びの4分の3は外国人（1.60泊→1.81泊と、客に占める割合 | [250_lodging_nights_per_stay](articles/250_lodging_nights_per_stay) |
| 251 | 結論が逆になったとき、何を見落としていたか？ | [251_conclusion_reversals](articles/251_conclusion_reversals) |
| 254 | 米の作況指数の揺れは、2000年以降にそれまでの4割ほどに小さくなった。夏の気温の揺れは同じくらいで、1℃涼しい夏の落ち | [254_rice_yield_volatility](articles/254_rice_yield_volatility) |
| 255 | 野菜の作付面積は1973年から半分に。27品目中25品目で減り、減った面積の半分強はばれいしょ・だいこん・すいか・はくさ | [255_vegetable_area_by_item](articles/255_vegetable_area_by_item) |
| 256 | 1人あたりの肉の量が魚を上回ったのは2011年度。熱量ではもっと早く、1979年度に上回っていた。魚は2001年度の40 | [256_fish_vs_meat_crossover](articles/256_fish_vs_meat_crossover) |
| 257 | 1人あたりの油の量は1985年度ごろに伸びが止まり、2021年度まで13〜15kgで横ばいだった。2022年度からは下が | [257_oil_consumption_plateau](articles/257_oil_consumption_plateau) |
| 258 | 小麦の10a当たり収量は60年で1.9倍。伸びの45%は北海道の収量の伸びで、北海道の面積が3%から57%に増えた分も1 | [258_wheat_yield_growth](articles/258_wheat_yield_growth) |
| 259 | 統計表を毎年取り直すとき、何で「変わった」を見つけるか？ | [259_stat_file_version_check](articles/259_stat_file_version_check) |
| 263 | 初めて雪が積もる日は、1931〜60年と1995〜2024年の平均を比べると4日ほど遅くなった。9地点のうち8地点で遅く | [263_first_snow_cover_trend](articles/263_first_snow_cover_trend) |
| 264 | 1日の気温差は、95年で0.5℃縮んだ。夜の最低気温が昼の最高気温より速く上がったからだが、1990年代からは最高気温の | [264_diurnal_temperature_range](articles/264_diurnal_temperature_range) |
| 265 | 雨の降る日は、1931〜60年と1996〜2025年の平均を比べると4%減り、降った日の雨量は4%増えた。13地点すべて | [265_wet_days_rain_intensity](articles/265_wet_days_rain_intensity) |
| 266 | 最低気温が0℃を下回る最初の日は、1931〜60年と1995〜2024年の平均を比べると9日遅くなった。春の最後の日は1 | [266_first_frost_day_trend](articles/266_first_frost_day_trend) |
| 273 | 電子部品の生産は、2015年までは鉱工業全体とほぼ同じ時期に山と谷を迎え、下がり幅は2〜5倍だった。2016年以降は一緒 | [273_electronic_parts_cycle](articles/273_electronic_parts_cycle) |
| 275 | 製造業の稼働率は、2025年の平均で1978年以降の月の下から5%の低さだった。2018年からの減りは、能力の削減（−5 | [275_capacity_utilization_by_industry](articles/275_capacity_utilization_by_industry) |
| 276 | 鉱工業の出荷のうち輸出向けは、1998年の13%から2025年は22%に。輸出向けは1.5倍、国内向けは2割減ったが、輸 | [276_export_vs_domestic_shipments](articles/276_export_vs_domestic_shipments) |
| 280 | 週次の数字を毎週メールで自動配信するとき、いつ送るか？ | [280_weekly_kpi_email](articles/280_weekly_kpi_email) |
| 281 | 輸入は、どの品目で円安の影響を受けたのか？ | [281_import_price_quantity_yen](articles/281_import_price_quantity_yen) |
| 282 | 輸入元が少数の国に偏っている品目はどれか？ | [282_import_source_concentration](articles/282_import_source_concentration) |
| 284 | 港ごとの輸出は、何に偏っているのか？ | [284_customs_export_mix](articles/284_customs_export_mix) |
| 285 | 輸入の半分は、何品目で占められているのか？ | [285_import_pareto_items](articles/285_import_pareto_items) |
| 289 | 婚姻届が多い月は、春と秋の山から3月と11月に移った。1970年代に年平均の4割ほどだった8月はふつうの月になり、201 | [289_marriage_registration_month](articles/289_marriage_registration_month) |
| 290 | 第1子を産む母の年齢は、1975年から2014年まで上にも下にも広がり、10%点から90%点の幅は8.8歳から15.2歳 | [290_first_birth_mother_age_spread](articles/290_first_birth_mother_age_spread) |
| 291 | 第1子が生まれたときの父の平均年齢は、50年で28.3歳から32.8歳に。母は25.7歳から31.0歳で、上がり方は母の | [291_father_mother_age_gap](articles/291_father_mother_age_gap) |
| 292 | 生まれたときの体重が2,500g未満の割合は、1975年の5.1%から2005年の9.5%まで上がり、その後は9〜10% | [292_birth_weight_trend](articles/292_birth_weight_trend) |
| 293 | 双子以上の分娩は、2025年に分娩1,000件あたり12.9件で、1995年以降で最も高い割合になった。2015年からの | [293_multiple_births_trend](articles/293_multiple_births_trend) |
| 297 | 持ち家の割合は、年齢でどう違うのか？ | [297_owner_rate_by_age](articles/297_owner_rate_by_age) |
| 298 | 1人あたりの住まいの広さは、広くなったのか？ | [298_floor_space_per_person](articles/298_floor_space_per_person) |
| 299 | 築年数の古い家は、どれだけ増えたのか？ | [299_old_owned_houses](articles/299_old_owned_houses) |
| 300 | 家賃は、広さあたりでどれだけ違うのか？ | [300_rent_per_tatami](articles/300_rent_per_tatami) |
| 303 | E2E テストの考え方を、データの処理にも使えるか？ | [303_e2e_tests_for_data_pipeline](articles/303_e2e_tests_for_data_pipeline) |
| 304 | 省エネの窓は、どれだけ広まったのか？ | [304_double_glazing_spread](articles/304_double_glazing_spread) |
| 305 | DAX の CALCULATE は、何をしているのか？ | [305_dax_calculate_filter_context](articles/305_dax_calculate_filter_context) |
| 306 | スプレッドシートの申込集計を、GAS でどう自動にするか？ | [306_gas_sheet_aggregation](articles/306_gas_sheet_aggregation) |
| 308 | Kaggle：最終提出の2本を、どう選んだか？ | [308_kaggle_final_two_selection](articles/308_kaggle_final_two_selection) |
| 309 | Kaggle Playground：特徴量を足し続けて、どこで伸びが止まったか？ | [309_kaggle_feature_saturation](articles/309_kaggle_feature_saturation) |
| 322 | 書いた記事は、何か月で「古い数字」になるのか？ | [322_months_until_stale](articles/322_months_until_stale) |
| 323 | 公開したあとの手直しは、どれくらいあったか？ | [323_commits_after_publish](articles/323_commits_after_publish) |
| 324 | 自分の文章は、読みやすくなったのか？ | [324_sentence_length_trend](articles/324_sentence_length_trend) |
| 328 | 行ごとに丸めてから足すのと、足してから丸めるのでは、どれだけ違うのか？ | [328_round_then_sum_order](articles/328_round_then_sum_order) |
| 329 | 金額を小数（FLOAT）で持つと、合計はどれだけずれるのか？ | [329_float_money_sum](articles/329_float_money_sum) |
| 337 | 1966年の丙午に、出生はどれだけ減ったのか？ | [337_hinoeuma_1966_births](articles/337_hinoeuma_1966_births) |
| 338 | 1918〜20年の流行で、死亡はふだんよりどれだけ多かったのか？ | [338_excess_deaths_1918_1920](articles/338_excess_deaths_1918_1920) |
| 339 | 働く人の半分が農業を離れたのは、いつだったのか？ | [339_leaving_agriculture](articles/339_leaving_agriculture) |
| 340 | 高校に進む人が9割を超えるまで、何年かかったのか？ | [340_high_school_enrollment](articles/340_high_school_enrollment) |
| 349 | 実際の死亡数と見込みの比は、何人分のデータで安定するのか？ | [349_ae_ratio_stability](articles/349_ae_ratio_stability) |
| 353 | 結論の言い切り方は、どう変わったか？ | [353_conclusion_sentence_endings](articles/353_conclusion_sentence_endings) |
| 354 | 地域を比べた記事で、順位の表はどれだけ載せていたか？ | [354_regional_ranking_tables](articles/354_regional_ranking_tables) |
| 357 | 「週」の決め方で、週次の売上はどれだけ変わるのか？ | [357_week_definitions](articles/357_week_definitions) |
| 366 | 祝日と3連休は、70年でどれだけ増えたのか？ | [366_holidays_long_weekends](articles/366_holidays_long_weekends) |
| 367 | 1つの世帯の人数は、100年でどう減ったのか？ | [367_household_size_100_years](articles/367_household_size_100_years) |
| 368 | 日本の輸出の主役は、何から何へ入れ替わったのか？ | [368_export_leaders_since_1962](articles/368_export_leaders_since_1962) |
| 369 | エネルギーの主役は、石炭から石油へ、いつ入れ替わったのか？ | [369_coal_to_oil_energy_shift](articles/369_coal_to_oil_energy_shift) |
| 370 | 雇われて働く人が8割を超えたのは、いつだったのか？ | [370_employee_share_80_percent](articles/370_employee_share_80_percent) |
| 378 | 重なりのある2つの名簿から、全体の人数はどこまで当てられるのか？ | [378_capture_recapture_two_lists](articles/378_capture_recapture_two_lists) |
| 379 | 何件調べて誤りが0件なら、「誤りは1%未満」と言えるのか？ | [379_zero_errors_in_sample](articles/379_zero_errors_in_sample) |
| 383 | 先に決めた確かめ方のうち、実際にはできなかったものは何だったか？ | [383_plan_deviations](articles/383_plan_deviations) |
| 384 | 置いたデータは、どれくらいの大きさだったか？ | [384_data_folder_sizes](articles/384_data_folder_sizes) |
| 389 | 申込みまでの通過率は、数え方でどれだけ変わるのか？ | [389_funnel_counting_definitions](articles/389_funnel_counting_definitions) |
| 395 | 関係のない2つの右肩上がりの系列は、どれくらい「関係あり」と出てしまうのか？ | [395_spurious_regression_trending_series](articles/395_spurious_regression_trending_series) |
| 396 | 自然災害で亡くなる人は、いつから大きく減ったのか？ | [396_disaster_deaths_since_1945](articles/396_disaster_deaths_since_1945) |
| 397 | 住まいは、いつから「共同住宅」が増えたのか？ | [397_apartments_and_high_rise](articles/397_apartments_and_high_rise) |
| 398 | 家から職場までの時間は、住まいの種類でどれだけ違うのか？ | [398_commute_time_by_tenure](articles/398_commute_time_by_tenure) |
| 399 | 世帯の貯蓄は、年齢でどう積み上がっているのか？ | [399_savings_by_age](articles/399_savings_by_age) |
| 400 | 漁業で働く人は、何歳の人が残っているのか？ | [400_fishery_workers_by_age](articles/400_fishery_workers_by_age) |
| 402 | 速くするために作った集計済みの表は、元の表とどれくらいずれていくのか？ | [402_summary_table_drift](articles/402_summary_table_drift) |
| 405 | 「合計は変わらない」「件数は減らない」という決まりだけで、処理の誤りはどこまで見つかるか？ | [405_invariant_property_tests](articles/405_invariant_property_tests) |
| 408 | 件数の小さいセルを隠した集計表は、引き算で何セル分かってしまうのか？ | [408_cell_suppression_subtraction](articles/408_cell_suppression_subtraction) |
| 421 | 生まれて1年以内に亡くなる子は、いつ、どれだけ速く減ったのか？ | [421_infant_mortality_since_1899](articles/421_infant_mortality_since_1899) |
| 422 | 中学校を出てすぐ働く人は、いつ、ほとんどいなくなったのか？ | [422_junior_high_leavers_to_work](articles/422_junior_high_leavers_to_work) |
| 423 | 「市」に住む人が半分を超えたのは、いつだったのか？ | [423_city_population_share](articles/423_city_population_share) |
| 424 | 日本の人口の「真ん中の年齢」は、100年でどう上がったのか？ | [424_median_age_100_years](articles/424_median_age_100_years) |
| 425 | 赤ちゃんが生まれる場所は、自宅から病院へ、いつ入れ替わったのか？ | [425_birthplace_home_to_hospital](articles/425_birthplace_home_to_hospital) |
| 426 | 外貨の売上を円に直すとき、どの日のレートを使うかで、月の売上はどれだけ変わるのか？ | [426_fx_rate_date_choice](articles/426_fx_rate_date_choice) |
| 429 | 共通の費用を部門に配る基準を変えると、何部門の損益の符号が変わるのか？ | [429_overhead_allocation_bases](articles/429_overhead_allocation_bases) |
| 431 | 金利が動いたとき、将来の支払いの現在価値の変化は、近似でどこまで出せるのか？ | [431_duration_convexity_approximation](articles/431_duration_convexity_approximation) |
| 434 | 残った店だけで平均を取ると、成績はどれだけ良く見えるのか？ | [434_survivorship_bias_stores](articles/434_survivorship_bias_stores) |
| 437 | 人を運ぶ主役は、鉄道から自動車へ、いつ入れ替わったのか？ | [437_rail_to_car_passenger_km](articles/437_rail_to_car_passenger_km) |
| 438 | 1年に働く時間は、いつ2,000時間を切ったのか？ | [438_annual_working_hours](articles/438_annual_working_hours) |
| 439 | 3人目より後に生まれる子は、いつから少数になったのか？ | [439_birth_order_shares](articles/439_birth_order_shares) |
| 440 | 女性の進学先は、短大から4年制大学へ、いつ入れ替わったのか？ | [440_women_junior_college_to_university](articles/440_women_junior_college_to_university) |
| 441 | 基準の年が変わった指数をつなぐとき、つなぎ方で長期の伸びはどれだけ変わるのか？ | [441_index_rebasing_link_methods](articles/441_index_rebasing_link_methods) |
| 444 | 税込みと税抜きの金額が混ざった表を足すと、売上はどれだけずれるのか？ | [444_tax_included_excluded_mix](articles/444_tax_included_excluded_mix) |
| 445 | 順番に動かすはずの集計を、順番を違えて流すと、何枚の表が古い数字のままになるのか？ | [445_pipeline_run_order_stale_tables](articles/445_pipeline_run_order_stale_tables) |
| 447 | 5歳刻みや千円単位に丸めたデータから出した平均とばらつきは、元のデータとどれだけ違うのか？ | [447_rounded_data_mean_sd](articles/447_rounded_data_mean_sd) |
| 452 | 小計や合計の行が混ざった表をそのまま足すと、合計は何倍になるのか？ | [452_subtotal_rows_double_count](articles/452_subtotal_rows_double_count) |
| 454 | 2つの処理が同時に同じ行を書き換えると、何件の更新が消えるのか？ | [454_lost_updates_concurrent_writes](articles/454_lost_updates_concurrent_writes) |
| 461 | 区分ごとのユニーク人数を足すと、全体の人数より何%多くなるのか？ | [461_distinct_counts_not_additive](articles/461_distinct_counts_not_additive) |
| 462 | 2つの期間が重なるかどうかの条件を書き間違えると、何件が漏れ、何件が余分に入るのか？ | [462_interval_overlap_conditions](articles/462_interval_overlap_conditions) |
| 465 | サーバーごとに時計がずれていると、ログの出来事の順番は何件逆になるのか？ | [465_clock_skew_event_order](articles/465_clock_skew_event_order) |
| 473 | 値引きやクーポンを明細に割り振る方法で、商品ごとの粗利はどれだけ変わるのか？ | [473_discount_allocation_margin](articles/473_discount_allocation_margin) |
| 478 | オッズ比を「何倍なりやすい」と読むと、どれだけ大げさになるのか？ | [478_odds_ratio_vs_risk_ratio](articles/478_odds_ratio_vs_risk_ratio) |
| 480 | ヒストグラムは、幅と始点の取り方で、山の数がどれだけ変わるのか？ | [480_histogram_bins_modes](articles/480_histogram_bins_modes) |
| 483 | 在庫を「入った順」と「期限の近い順」で引き当てると、廃棄と欠品はどれだけ変わるのか？ | [483_fifo_vs_fefo_allocation](articles/483_fifo_vs_fefo_allocation) |
| 484 | 明細の「単価×数量」と「金額」を確かめる8つの方法は、誤り1,200件のうち何件を見つけ、何件空振りするのか？ | [484_line_amount_checks](articles/484_line_amount_checks) |
| 488 | 事故0件の契約が多いデータをポアソンで見ると、2件以上の事故を起こす割合はどれだけ小さく出るのか？ | [488_zero_inflated_claim_counts](articles/488_zero_inflated_claim_counts) |
| 494 | 入れ子の注文JSONを平らにすると、行は何倍になり、合計は何%ずれるのか？ | [494_nested_json_flatten](articles/494_nested_json_flatten) |
| 500 | 抜けた日を「前の値」で埋めると、最後の60日が抜けたとき、1年の傾きの誤差は何%になるのか？ | [500_locf_fill_mean_slope](articles/500_locf_fill_mean_slope) |
| 501 | 入金の消込を金額だけで合わせると、何件が別の請求に消し込まれるのか？ | [501_payment_matching_amount_only](articles/501_payment_matching_amount_only) |
| 502 | 売上を受注日・出荷日・検収日のどれで数えるかで、月の売上と前年同月比はどれだけ動くのか？ | [502_revenue_date_basis](articles/502_revenue_date_basis) |
| 503 | ログのセッションを何分空いたら切るかで、セッション数と1回あたりの滞在はどれだけ変わるのか？ | [503_session_timeout_definitions](articles/503_session_timeout_definitions) |
| 511 | ログの利用者IDが Cookie だと、ユニーク利用者は本当の人数の何倍に数えられるのか？ | [511_cookie_vs_login_unique_users](articles/511_cookie_vs_login_unique_users) |
| 513 | ログを10件に1件だけ残して10倍すると、小さな区分の件数はどれだけ振れるのか？ | [513_log_sampling_small_segments](articles/513_log_sampling_small_segments) |
| 521 | 問い合わせの対応時間を「営業時間」で数えるか「暦の時間」で数えるかで、期限内に返せた割合は何ポイント変わるのか？ | [521_sla_business_vs_calendar_hours](articles/521_sla_business_vs_calendar_hours) |
| 522 | 在庫回転日数を「期首と期末の平均在庫」で出すと、毎日の在庫から出した値と何日ずれるのか？ | [522_inventory_days_average_method](articles/522_inventory_days_average_method) |
| 523 | 未完了の案件を除いてリードタイムの中央値を出すと、本当より何日短く出るのか？ | [523_lead_time_open_cases_median](articles/523_lead_time_open_cases_median) |
| 525 | メールの開封率は、画像の自動読み込みによる「見かけの開封」を除くと何ポイント下がるのか？ | [525_email_open_rate_auto_load](articles/525_email_open_rate_auto_load) |
| 527 | 予定利率と実際の利回りが0.5ポイントずれると、30年の積立金はどれだけ足りなくなるのか？ | [527_guaranteed_rate_gap_accumulation](articles/527_guaranteed_rate_gap_accumulation) |
| 531 | 納期の遵守率は、「当初の約束日」と「変更後の日」のどちらで数えるかで何ポイント違うのか？ | [531_delivery_promise_date_basis](articles/531_delivery_promise_date_basis) |
| 532 | NPS は、回答が50件や200件のとき、本当は同じ店どうしでも何ポイント差が出てしまうのか？ | [532_nps_small_sample_gap](articles/532_nps_small_sample_gap) |
| 533 | 残業時間を15分単位で切り捨てて集計すると、1か月の時間は何%少なく出るのか？ | [533_overtime_truncation_monthly](articles/533_overtime_truncation_monthly) |
| 537 | 回答の選択肢が「1,000万円以上」で打ち切られていると、平均はどれだけ小さく出るのか？ | [537_topcoded_income_mean](articles/537_topcoded_income_mean) |
| 541 | 郵便番号から都道府県・市区町村を引くと、古い番号や事業所の個別番号のせいで何件が引けないのか？ | [541_postal_code_lookup_gaps](articles/541_postal_code_lookup_gaps) |
| 542 | 問い合わせの分類を2人が別々に付けると、何%が食い違い、偶然の一致を除いた一致の度合い（カッパ係数）はいくつになるのか？ | [542_label_agreement_kappa](articles/542_label_agreement_kappa) |
| 543 | 予約枠の稼働率は、無断キャンセルと直前キャンセルをどう数えるかで何ポイント違うのか？ | [543_booking_utilization_definitions](articles/543_booking_utilization_definitions) |
| 544 | 棚卸の差異を月末にまとめて計上すると、月の粗利はどれだけ振れるのか？ | [544_inventory_count_margin_swing](articles/544_inventory_count_margin_swing) |
| 545 | 割引を2つ重ねるとき、「足し算」「掛け算」「適用の順番」の違いで、請求額は何件・何円違うのか？ | [545_stacked_discount_order](articles/545_stacked_discount_order) |
| 551 | 月の途中で単価が変わったとき、適用開始日を見ずに今の単価で集計すると、金額はどれだけずれるのか？ | [551_price_master_effective_date](articles/551_price_master_effective_date) |
| 552 | 訂正を「取消（赤）＋再登録（黒）」で入れる伝票では、件数と金額をどう数えればよいのか？ | [552_red_black_correction_count](articles/552_red_black_correction_count) |
| 553 | 売掛金の滞留を、請求日から数えるか支払期日から数えるかで、区分ごとの金額はどれだけ動くのか？ | [553_ar_aging_basis](articles/553_ar_aging_basis) |
| 554 | セット商品の売上を構成品に分けるとき、金額の割り振り方で商品別の売上はどれだけ変わるのか？ | [554_bundle_revenue_allocation](articles/554_bundle_revenue_allocation) |
| 555 | 社内のテスト用アカウントの行を外す条件を変えると、利用者数と売上はどれだけ動くのか？ | [555_test_account_exclusion](articles/555_test_account_exclusion) |
| 560 | 効果を「差」で見るか「比」で見るかで、効果の大きい層が入れ替わるのはなぜか？ | [560_effect_scale_ranking](articles/560_effect_scale_ranking) |
| 561 | 同じ人が続けて送った問い合わせを、何分以内なら1件とみなすかで、件数はどれだけ変わるのか？ | [561_inquiry_dedup_window](articles/561_inquiry_dedup_window) |
| 564 | 注文を何回かに分けて出荷すると、「出荷済みの注文」の数え方でどれだけ違うのか？ | [564_partial_shipment_definition](articles/564_partial_shipment_definition) |
| 565 | 状態が何度も変わる申込みで、過去のある日の状態を履歴からどう戻すのか？ | [565_status_history_asof](articles/565_status_history_asof) |
| 571 | UTCで保存した時刻を日本時間に直さずに日付で集計すると、何件が前日に入るのか？ | [571_utc_date_aggregation](articles/571_utc_date_aggregation) |
| 582 | 複数の担当者で受けた案件の成果を、主担当に全部付けるか人数で割るかで、担当者別の実績の順位はどれだけ入れ替わるのか？ | [582_shared_deal_credit](articles/582_shared_deal_credit) |
| 583 | 在庫を帳簿上の数で見るか、引当を除いた使える数で見るかで、欠品の判定は何品目変わるのか？ | [583_available_vs_on_hand](articles/583_available_vs_on_hand) |
| 585 | 個・箱・ケースの単位が混ざった出荷明細を換算せずに足すと、品目別の数量はどれだけずれるのか？ | [585_unit_conversion](articles/585_unit_conversion) |
| 591 | 欠品していた日の売上を0と見るか欠測と見るかで、平均の需要はどれだけ少なく見えるのか？ | [591_stockout_censored_demand](articles/591_stockout_censored_demand) |
| 592 | 同じ商品の色・サイズ違いを1品目と数えるか別々に数えるかで、売れ筋の順位はどれだけ変わるのか？ | [592_parent_vs_sku_ranking](articles/592_parent_vs_sku_ranking) |
| 594 | 日をまたぐ夜のシフトを、開始日で数えるか日ごとに分けるかで、日ごとの労働時間はどれだけ違うのか？ | [594_overnight_shift_split](articles/594_overnight_shift_split) |
| 598 | 年の途中で売る1年契約では、事故を事故年で数えるか契約年度で数えるかで、事故率の推移はどれだけ違って見えるのか？ | [598_calendar_vs_policy_year](articles/598_calendar_vs_policy_year) |
| 599 | 事故のあった人ほど契約を更新しないと、翌年の保有の事故率はどれだけ下がって見えるのか？ | [599_renewal_selection](articles/599_renewal_selection) |
| 605 | 先頭の0が落ちた商品コードや取引先コードで表をつなぐと、何件がつながらず、何件が別のコードにつながるのか？ | [605_leading_zero_codes](articles/605_leading_zero_codes) |
| 606 | 指標を10個見るとき、Bonferroni・Holm・BH の補正で、本当の効果を見つける力はどれだけ違うのか？ | [606_multiple_testing_corrections_power](articles/606_multiple_testing_corrections_power) |
| 613 | 安全在庫を需要のばらつきだけで決めると、届くまでの日数がばらつくとき欠品は何%になるのか？ | [613_safety_stock_leadtime_var](articles/613_safety_stock_leadtime_var) |
| 614 | 平均の問い合わせ件数から窓口の人数を決めると、待ち時間はどれだけ長くなるのか？ | [614_staffing_erlang_c](articles/614_staffing_erlang_c) |
| 624 | 週の途中の数字を先週の合計と比べると、どれだけ低く見えるのか？ | [624_partial_week_comparison](articles/624_partial_week_comparison) |
| 625 | データの先頭1,000行だけで中身を確かめると、後ろにある異常は何%見つかるのか？ | [625_head_rows_quality_check](articles/625_head_rows_quality_check) |
| 631 | 発注をケース単位に切り上げると、在庫は平均で何日分多く持つことになるのか？ | [631_case_pack_rounding_inventory](articles/631_case_pack_rounding_inventory) |
| 641 | 整数どうしの割り算で割合を出すと、何%の行が0になるのか？ | [641_integer_division_ratio](articles/641_integer_division_ratio) |
| 652 | 採番の連番の最大値で件数を見ると、欠番のせいで何%多く数えるのか？ | [652_max_id_vs_count](articles/652_max_id_vs_count) |
| 653 | 層ごとに抽出率の違うサンプルを、重みを付けずに平均すると、全体の値はどれだけずれるのか？ | [653_stratified_sample_weights](articles/653_stratified_sample_weights) |
| 657 | 交互作用を見つけるには、主効果を見つけるときの何倍の件数が要るのか？ | [657_interaction_power](articles/657_interaction_power) |
| 666 | 見逃しと空振りのコストが違うとき、確率0.5で切るのと費用で決めた閾値では、損失はどれだけ違うのか？ | [666_cost_based_threshold](articles/666_cost_based_threshold) |
| 667 | 反応しそうな人に配るのと、配ったら反応が増える人に配るのでは、増える件数はどれだけ違うのか？ | [667_uplift_vs_response](articles/667_uplift_vs_response) |
| 669 | 部品の故障の起き方を「毎年同じ割合」と置くと、使った年数ごとの故障の見込みはどれだけずれるのか？ | [669_weibull_failure_rate](articles/669_weibull_failure_rate) |
| 672 | 回答者の年代の偏りを重み付けで直すと、アンケートの結果はどれだけ動き、ばらつきはどれだけ増えるのか？ | [672_survey_weighting](articles/672_survey_weighting) |
| 673 | 1つの注文を、使ったクーポンそれぞれに全額付けると、クーポン別の売上の合計は実際の何倍になるのか？ | [673_coupon_double_attribution](articles/673_coupon_double_attribution) |
| 674 | 広告の成果を「最後の接点」に付けるか均等に分けるかで、広告ごとの成果はどれだけ違うのか？ | [674_ad_attribution_models](articles/674_ad_attribution_models) |
| 692 | 文字数の上限を len() で確かめると、絵文字や結合文字を含む文は何件が見た目と違う数になるのか？ | [692_char_length_emoji](articles/692_char_length_emoji) |
| 693 | 月数を「月の境目をまたいだ回数」で数えると、契約の経過月数は何件ずれるのか？ | [693_datediff_month_boundary](articles/693_datediff_month_boundary) |
| 700 | 選択肢を1つ足したとき、多項ロジットは他の選択肢のシェアをどう奪うと見て、本当の動きとどれだけずれるのか？ | [700_multinomial_logit_iia](articles/700_multinomial_logit_iia) |
| 701 | 「2024/1/5」のように0を埋めない日付を文字列のまま並べ替えると、何行が順番を間違えるのか？ | [701_string_date_sort](articles/701_string_date_sort) |
| 718 | 件数の少ない店が多いとき、店ごとの平均を「そのまま」出すのと、ランダム効果で縮めるのとでは、どれだけ当たり方が違うのか？ | [718_random_vs_fixed_small_groups](articles/718_random_vs_fixed_small_groups) |
| 732 | うるう年の2月29日を含む月の前年同月比は、日数をそろえないとどれだけ高く見えるのか？ | [732_leap_day_yoy](articles/732_leap_day_yoy) |
| 735 | ユニークな人数を近似の関数で数えると、件数の少ない区分でどれだけずれるのか？ | [735_approx_count_distinct_error](articles/735_approx_count_distinct_error) |
| 738 | 件数の少ないデータでジニ係数を出すと、本当の値よりどれだけ小さく出るのか？ | [738_gini_small_sample_bias](articles/738_gini_small_sample_bias) |
| 757 | LOESS の span を小さくするか大きくするかで、曲がり具合の見え方と誤差はどう入れ替わるのか？ | [757_loess_span](articles/757_loess_span) |
| 761 | 長さの足りない列に名前を入れると、後ろが切れて別の商品が同じ名前になるのは何件か？ | [761_varchar_truncation_collision](articles/761_varchar_truncation_collision) |
| 772 | 「12:30 AM」のような午前午後の表記を読み違えると、時間帯別の件数はどれだけずれるのか？ | [772_ampm_parsing](articles/772_ampm_parsing) |
| 775 | 前回の順位と比べるとき、前回いなかった店を外すかどうかで、「順位が上がった店」の数はどれだけ変わるのか？ | [775_rank_change_new_entries](articles/775_rank_change_new_entries) |
| 783 | 合計の範囲を固定したまま行を足していくと、月の合計はどれだけ少なく出るのか？ | [783_sum_range_not_extended](articles/783_sum_range_not_extended) |
| 785 | 「1時間30分」を「1.30」と書いて合計すると、月の作業時間はどれだけ少なく出るのか？ | [785_hhmm_decimal_confusion](articles/785_hhmm_decimal_confusion) |
| 786 | 曲がった関係に直線を当てはめると、「効果」はどの範囲で大きく、どの範囲で小さく読まれるのか？ | [786_linear_fit_curved_relation](articles/786_linear_fit_curved_relation) |
| 787 | 標準化した係数の大きさで変数の大事さを並べると、データのばらつき方でどれだけ順位が変わるのか？ | [787_standardized_coef_importance](articles/787_standardized_coef_importance) |
| 792 | 率の列に「0.05」と「5」が混ざっていると、平均はどれだけずれるのか？ | [792_percent_scale_mix](articles/792_percent_scale_mix) |
| 794 | 1つの商品が2つのカテゴリに入る表でカテゴリ別に売上を足すと、全体の何倍になるのか？ | [794_multi_category_double_count](articles/794_multi_category_double_count) |

</details>


## 業務の場面別

| 場面 | 本数 |
|---|---|
| 小売・店舗 | 182 |
| EC・会員・Web | 96 |
| マーケティング・広告 | 23 |
| 需要予測・在庫 | 37 |
| 業務の集計・報告 | 143 |
| 作業時間・処理件数 | 4 |
| 保険 | 74 |
| 公的統計・地域・人口 | 300 |

<details><summary><b>小売・店舗</b>（182本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F34 | 同じお金で、どの市町村が多くのサービスを出しているか？ | [F34_municipal_efficiency](articles/F34_municipal_efficiency) |
| F47 | 都市ごとの「食の好み」を、行列分解で取り出せるか？ | [F47_food_nmf](articles/F47_food_nmf) |
| F48 | ガソリンが10%上がると、買う量は何%減るか？ | [F48_gasoline_elasticity](articles/F48_gasoline_elasticity) |
| F103 | 電力需要や物価の「長い記憶」は、どれくらい続くか？ | [F103_long_memory](articles/F103_long_memory) |
| F111 | 人口が減る町で、店はいつ消えるのか？ | [F111_shop_abm](articles/F111_shop_abm) |
| F113 | 物価指数の作り方で、インフレ率はどれだけ変わるか？ | [F113_price_index_formulas](articles/F113_price_index_formulas) |
| F133 | 輸出先は、距離と経済規模でどこまで決まるのか？ | [F133_export_gravity](articles/F133_export_gravity) |
| F135 | 雨の日は、小売の売上をどれだけ動かすのか？ | [F135_rain_retail](articles/F135_rain_retail) |
| F209 | この5年の値上がりは、どの品目から来て、誰に重く、家計は何を減らしたのか？ | [F209_prices_household_series_part1](articles/F209_prices_household_series_part1) |
| F210 | 円安は品目の値段にどれだけ時間をかけて届き、物価の見通しは家計と企業でどれだけ違うのか？ | [F210_prices_household_series_part2](articles/F210_prices_household_series_part2) |
| F231 | 売上の予測は、何か月先まで役に立つのか？ | [F231_sales_forecast_horizon](articles/F231_sales_forecast_horizon) |
| F232 | 店の種類ごとの予測と全体の予測を、どうそろえるか？ | [F232_hierarchical_retail_reconciliation](articles/F232_hierarchical_retail_reconciliation) |
| F233 | 祝日・連休・天気は、売上をどれだけ動かすのか？ | [F233_calendar_weather_sales](articles/F233_calendar_weather_sales) |
| F234 | 価格を1%上げると、買われる量は何%減るのか？ | [F234_price_elasticity_practice](articles/F234_price_elasticity_practice) |
| F235 | 在庫はどれだけ持てばよいのか？ | [F235_inventory_newsvendor](articles/F235_inventory_newsvendor) |
| F239 | 広告費は、売上にどれだけ効いているのか？ | [F239_marketing_mix_model](articles/F239_marketing_mix_model) |
| F243 | どの指標を見れば、売上の変化の理由が分かるのか？ | [F243_kpi_tree_decomposition](articles/F243_kpi_tree_decomposition) |
| F244 | 集計の SQL は、どう書けば間違えにくいか？ | [F244_sql_aggregation_pitfalls](articles/F244_sql_aggregation_pitfalls) |
| F245 | 1つの依頼に、1時間でどこまで答えられるか？ | [F245_one_hour_request](articles/F245_one_hour_request) |
| F246 | 分析担当として最初にやること：KPI を決める（業務の再現：架空の会社で） シリーズ③の1本目。架空の食品スーパー「サン | [F246_kpi_definitions_fictional_retail](articles/F246_kpi_definitions_fictional_retail) |
| F247 | データを集めて、使える形に整える（業務の再現：架空の会社で） シリーズ③の2本目。F246 の合成データ「サンプルマート | [F247_data_mart_fictional_retail](articles/F247_data_mart_fictional_retail) |
| F248 | 月次レポートの「型」を作る（業務の再現：架空の会社で） シリーズ③の3本目。F246 の KPI 定義 v1 と F24 | [F248_monthly_report_template_fictional_retail](articles/F248_monthly_report_template_fictional_retail) |
| F249 | ダッシュボードを作る（業務の再現：架空の会社で） シリーズ③の続き。F246 の KPI 定義 v1 と F247 の  | [F249_powerbi_dashboard_fictional_retail](articles/F249_powerbi_dashboard_fictional_retail) |
| F250 | 売上が落ちた月に、理由を説明する（業務の再現：架空の会社で） シリーズ③の5本目。F247 の mart を使い、架空の | [F250_sales_drop_explanation_fictional_retail](articles/F250_sales_drop_explanation_fictional_retail) |
| F251 | 販促の効果を測る（業務の再現：架空の会社で） シリーズ③の6本目。F247 の mart の架空の食品スーパー「サンプル | [F251_promo_effect_fictional_retail](articles/F251_promo_effect_fictional_retail) |
| F252 | 来期の予算のための需要予測（業務の再現：架空の会社で） シリーズ③の7本目。架空の食品スーパー「サンプルマート（架空）」 | [F252_budget_forecast_fictional_retail](articles/F252_budget_forecast_fictional_retail) |
| F253 | データの品質を毎月チェックする（業務の再現：架空の会社で） シリーズ③の8本目。架空の食品スーパー「サンプルマート（架空 | [F253_monthly_data_quality_checks_fictional_retail](articles/F253_monthly_data_quality_checks_fictional_retail) |
| F254 | 分析を引き継げる形にする（業務の再現：架空の会社で） シリーズ③の9本目。F246〜F251（コミット e5e9800） | [F254_handover_package_fictional_retail](articles/F254_handover_package_fictional_retail) |
| F255 | 1年の分析業務を振り返る（業務の再現：架空の会社で） シリーズ③の10本目・最後。架空の食品スーパー「サンプルマート（架 | [F255_year_review_fictional_retail](articles/F255_year_review_fictional_retail) |
| F259 | 需要予測の外れは、在庫と欠品のどちらに効かせるべきか？ | [F259_forecast_error_inventory_cost](articles/F259_forecast_error_inventory_cost) |
| F263 | 比べる相手がないとき、何を対照にするか？ | [F263_control_choice_nationwide_policy](articles/F263_control_choice_nationwide_policy) |
| F266 | 「米の値段が上がった」は、どの段階で起きたのか？ | [F266_rice_price_stages](articles/F266_rice_price_stages) |
| F267 | 売上の目標を、客数と客単価の目標にどう分けるか？ | [F267_kpi_target_allocation_cvs](articles/F267_kpi_target_allocation_cvs) |
| F275 | 集計の SQL は、どう書けば直しやすく、直し忘れに気づけるか？ | [F275_sql_change_requests](articles/F275_sql_change_requests) |
| F281 | 食料自給率の目標と実際の差は、どこから来ているのか？ | [F281_food_self_sufficiency_target_gap](articles/F281_food_self_sufficiency_target_gap) |
| F282 | 「円安で輸出が増えた」は、数量と価格に分けるとどうか？ | [F282_yen_exports_quantity_price](articles/F282_yen_exports_quantity_price) |
| F283 | 値上げの前後で、売れ方はどう変わったか？ | [F283_price_hike_front_loading](articles/F283_price_hike_front_loading) |
| F286 | 「物価高で節約」は家計調査のどこに表れているか？ | [F286_household_saving_items](articles/F286_household_saving_items) |
| F287 | 同じ数字を、経営向けと現場向けでどう書き分けるか？ | [F287_report_two_audiences](articles/F287_report_two_audiences) |
| F293 | 毎月の数字の「おかしい」を、どう自動で見つけるか？ | [F293_monthly_anomaly_public_stats](articles/F293_monthly_anomaly_public_stats) |
| 032 | 人口が2倍の街には、飲食店も2倍あるか？ | [032_scaling_law](articles/032_scaling_law) |
| 085 | 食品の値上げで、米は2倍でも量は減らず、魚や果物は大きく減った。家計調査の127品目で見る | [085_food_price_quantity](articles/085_food_price_quantity) |
| 097 | ドラッグストアの売上は11年で約1.9倍。伸びの中心は食品で、売上の3分の1を超えた | [097_drugstore](articles/097_drugstore) |
| 098 | 2019年より売上が多いのはスーパーやドラッグストア。でもコロナ前の伸び方には、コンビニとドラッグストアが届いていなかっ | [098_retail_recovery](articles/098_retail_recovery) |
| 105 | 牛乳1Lは那覇364円・長岡214円。同じ品目の値段の都市差は、16年でははっきり縮まっていなかった | [105_price_city_gap](articles/105_price_city_gap) |
| 142 | エアコンは27年、薄型テレビは7年で広がった。家電と車の普及率のS字と、ピーク後に下がった品目 | [142_durable_goods](articles/142_durable_goods) |
| 156 | ネット販売の売上比率が高いのは航空運輸業の32%。全体では売上の1.2%で、電子商取引をする企業は4%のままだった | [156_ec_sales_by_industry](articles/156_ec_sales_by_industry) |
| 158 | サービス産業の売上は2023年3月にコロナ前を回復。宿泊業は2019年の118%まで伸びたが、飲食店は85%のままだった | [158_service_recovery](articles/158_service_recovery) |
| 164 | 学習塾の受講生は2018年から1割減。それでも売上はトレンド通りに伸び、支えたのは1人当たりの受講料だった | [164_juku_sales](articles/164_juku_sales) |
| 185 | 売上100億円以上の企業は全体の0.46%なのに、売上の7割を占める。上位1%では約77%、約8割の企業の売上は合わせて | [185_sales_concentration](articles/185_sales_concentration) |
| 191 | 野菜の産地はどれだけ集中しているか。ばれいしょは北海道が8割、41品目のうち20品目は上位3県で半分以上だった | [191_vegetable_concentration](articles/191_vegetable_concentration) |
| 201 | サービス業の売上は人数にほぼ比例。人が10倍の事業所は売上11.4倍、ただ葬儀や結婚式場は大きいほど1人あたりが下がる | [201_service_sales_scale](articles/201_service_sales_scale) |
| 223 | ネットで買う品目の順位は、10年でほとんど入れ替わらなかった。大きく上がったのは出前で、21位から13位に | [223_online_shopping_rank](articles/223_online_shopping_rank) |
| 227 | コーヒーにかけるお金は10年で1.7倍。家で淹れる量は2019年とほぼ同じで、増えたのは豆の値段と喫茶店だった | [227_coffee_home_vs_cafe](articles/227_coffee_home_vs_cafe) |
| 234 | 前月比の増減を、客数と客単価にどう分けるか？ | [234_mom_change_decomposition](articles/234_mom_change_decomposition) |
| 244 | 毎月のレポートは、結論の1文・要因・次に確かめることの順に、数字から自動で書ける。要因を率で選ぶと、12か月中7か月で金 | [244_monthly_report_order](articles/244_monthly_report_order) |
| 255 | 野菜の作付面積は1973年から半分に。27品目中25品目で減り、減った面積の半分強はばれいしょ・だいこん・すいか・はくさ | [255_vegetable_area_by_item](articles/255_vegetable_area_by_item) |
| 279 | 手作業の月次 Excel レポートを、Python でどう自動にするか？ | [279_excel_report_automation](articles/279_excel_report_automation) |
| 281 | 輸入は、どの品目で円安の影響を受けたのか？ | [281_import_price_quantity_yen](articles/281_import_price_quantity_yen) |
| 282 | 輸入元が少数の国に偏っている品目はどれか？ | [282_import_source_concentration](articles/282_import_source_concentration) |
| 283 | 食料品の輸出は、どの品目で伸びたのか？ | [283_food_exports_by_item](articles/283_food_exports_by_item) |
| 285 | 輸入の半分は、何品目で占められているのか？ | [285_import_pareto_items](articles/285_import_pareto_items) |
| 305 | DAX の CALCULATE は、何をしているのか？ | [305_dax_calculate_filter_context](articles/305_dax_calculate_filter_context) |
| 315 | 1年分の保険料を、月ごとの売上にどう分けるか？ | [315_sql_earned_premium](articles/315_sql_earned_premium) |
| 330 | 同じファイルを2回取り込んでも、数字が二重にならない形はどう作るか？ | [330_idempotent_load](articles/330_idempotent_load) |
| 345 | 店ごとの平均を平均すると、全体の平均からどれだけずれるのか？ | [345_average_of_averages](articles/345_average_of_averages) |
| 356 | 曜日の並びが違うだけで、前年同月比は何ポイント動くのか？ | [356_weekday_mix_yoy](articles/356_weekday_mix_yoy) |
| 357 | 「週」の決め方で、週次の売上はどれだけ変わるのか？ | [357_week_definitions](articles/357_week_definitions) |
| 358 | 売上が0の日が表にないと、1日あたりの平均はどれだけ高く出るのか？ | [358_missing_zero_days](articles/358_missing_zero_days) |
| 360 | 「上位3件」を取る SQL は、同じ点数があると何件返すのか？ | [360_top3_with_ties](articles/360_top3_with_ties) |
| 361 | 予測の良し悪しは、物差しを変えるとどれだけ順位が入れ替わるのか？ | [361_forecast_metric_ranking](articles/361_forecast_metric_ranking) |
| 363 | たまにしか売れない商品の需要は、どの方法で予測するのがよいか？ | [363_intermittent_demand_methods](articles/363_intermittent_demand_methods) |
| 364 | 成績の悪かった店だけに手を打つと、何もしなくてもどれだけ「良くなって」見えるのか？ | [364_regression_to_mean_store_action](articles/364_regression_to_mean_store_action) |
| 368 | 日本の輸出の主役は、何から何へ入れ替わったのか？ | [368_export_leaders_since_1962](articles/368_export_leaders_since_1962) |
| 372 | CSV を Excel で開いて保存すると、何セルが変わってしまうのか？ | [372_csv_excel_roundtrip](articles/372_csv_excel_roundtrip) |
| 374 | VLOOKUP は、どんなときに黙って間違った値を返すのか？ | [374_vlookup_silent_errors](articles/374_vlookup_silent_errors) |
| 401 | 集計用の表は、1枚の大きな表と、事実とマスタに分けた表のどちらが直しやすいか？ | [401_wide_table_vs_star_schema](articles/401_wide_table_vs_star_schema) |
| 402 | 速くするために作った集計済みの表は、元の表とどれくらいずれていくのか？ | [402_summary_table_drift](articles/402_summary_table_drift) |
| 410 | 売れ筋を A・B・C に分ける分析は、期間と区切りでどれだけ入れ替わるのか？ | [410_abc_analysis_period_cutoffs](articles/410_abc_analysis_period_cutoffs) |
| 415 | 月の途中の実績から、月末の着地をどう見込むか？ | [415_month_end_landing_forecast](articles/415_month_end_landing_forecast) |
| 426 | 外貨の売上を円に直すとき、どの日のレートを使うかで、月の売上はどれだけ変わるのか？ | [426_fx_rate_date_choice](articles/426_fx_rate_date_choice) |
| 429 | 共通の費用を部門に配る基準を変えると、何部門の損益の符号が変わるのか？ | [429_overhead_allocation_bases](articles/429_overhead_allocation_bases) |
| 430 | 同じ仕入れと販売でも、在庫の評価の方法で、月の粗利はどれだけ違うのか？ | [430_inventory_valuation_methods](articles/430_inventory_valuation_methods) |
| 434 | 残った店だけで平均を取ると、成績はどれだけ良く見えるのか？ | [434_survivorship_bias_stores](articles/434_survivorship_bias_stores) |
| 443 | 分類を付け替えたあと、過去の集計は「当時の区分」と「今の区分」でどれだけ違うのか？ | [443_reclassification_asof_vs_current](articles/443_reclassification_asof_vs_current) |
| 444 | 税込みと税抜きの金額が混ざった表を足すと、売上はどれだけずれるのか？ | [444_tax_included_excluded_mix](articles/444_tax_included_excluded_mix) |
| 449 | 指標の単位をそろえないまま主成分分析をすると、第1主成分はどれだけ変わるのか？ | [449_pca_units_standardization](articles/449_pca_units_standardization) |
| 454 | 2つの処理が同時に同じ行を書き換えると、何件の更新が消えるのか？ | [454_lost_updates_concurrent_writes](articles/454_lost_updates_concurrent_writes) |
| 459 | 選ばれた人や店だけで相関を見ると、相関はどれだけ小さく見えるのか？ | [459_range_restriction_correlation](articles/459_range_restriction_correlation) |
| 461 | 区分ごとのユニーク人数を足すと、全体の人数より何%多くなるのか？ | [461_distinct_counts_not_additive](articles/461_distinct_counts_not_additive) |
| 469 | 同じ店や同じ人の中で似ているデータを、ばらばらの件数として検定すると、効果が0でも何%で「差あり」が出るのか？ | [469_clustered_data_naive_test](articles/469_clustered_data_naive_test) |
| 471 | 年初からの累計で見た前年比は、売上の変化に何か月遅れて気づくのか？ | [471_ytd_yoy_lag](articles/471_ytd_yoy_lag) |
| 472 | 返品を「売れた月」に戻すか「返ってきた月」で引くかで、月の売上はどれだけ変わるのか？ | [472_returns_which_month](articles/472_returns_which_month) |
| 473 | 値引きやクーポンを明細に割り振る方法で、商品ごとの粗利はどれだけ変わるのか？ | [473_discount_allocation_margin](articles/473_discount_allocation_margin) |
| 481 | 同じ売上を20日締めと月末締めで集計すると、2023〜2025年の月の数字は平均何%ずれるのか？ | [481_closing_day_20th_vs_monthend](articles/481_closing_day_20th_vs_monthend) |
| 483 | 在庫を「入った順」と「期限の近い順」で引き当てると、廃棄と欠品はどれだけ変わるのか？ | [483_fifo_vs_fefo_allocation](articles/483_fifo_vs_fefo_allocation) |
| 485 | 論理削除のフラグと履歴の期間を見落とすと、注文の件数と売上は何%多く出るのか？ | [485_soft_delete_flags](articles/485_soft_delete_flags) |
| 502 | 売上を受注日・出荷日・検収日のどれで数えるかで、月の売上と前年同月比はどれだけ動くのか？ | [502_revenue_date_basis](articles/502_revenue_date_basis) |
| 514 | 入庫と出庫の記録が遅れて届くと、在庫が一時的にマイナスになる日は何日あるのか？ | [514_inventory_record_delay_negative](articles/514_inventory_record_delay_negative) |
| 522 | 在庫回転日数を「期首と期末の平均在庫」で出すと、毎日の在庫から出した値と何日ずれるのか？ | [522_inventory_days_average_method](articles/522_inventory_days_average_method) |
| 524 | 深夜まで営業する店で、売上を暦日で切るか「朝5時締めの営業日」で切るかで、曜日別の売上はどれだけ変わるのか？ | [524_business_day_cutoff_5am](articles/524_business_day_cutoff_5am) |
| 532 | NPS は、回答が50件や200件のとき、本当は同じ店どうしでも何ポイント差が出てしまうのか？ | [532_nps_small_sample_gap](articles/532_nps_small_sample_gap) |
| 543 | 予約枠の稼働率は、無断キャンセルと直前キャンセルをどう数えるかで何ポイント違うのか？ | [543_booking_utilization_definitions](articles/543_booking_utilization_definitions) |
| 544 | 棚卸の差異を月末にまとめて計上すると、月の粗利はどれだけ振れるのか？ | [544_inventory_count_margin_swing](articles/544_inventory_count_margin_swing) |
| 554 | セット商品の売上を構成品に分けるとき、金額の割り振り方で商品別の売上はどれだけ変わるのか？ | [554_bundle_revenue_allocation](articles/554_bundle_revenue_allocation) |
| 555 | 社内のテスト用アカウントの行を外す条件を変えると、利用者数と売上はどれだけ動くのか？ | [555_test_account_exclusion](articles/555_test_account_exclusion) |
| 556 | 同じ分母で割った2つの比率は、もとの数に関係がなくてもどれだけ相関するのか？ | [556_shared_denominator_ratio_corr](articles/556_shared_denominator_ratio_corr) |
| 557 | 効き方が層で違うのに、交互作用を入れずに回帰すると、全体の係数は何を表すのか？ | [557_no_interaction_weighting](articles/557_no_interaction_weighting) |
| 559 | 前後の差で比べるか、前の値を入れた回帰で比べるかで、効果の答えが変わるのはなぜか？ | [559_change_score_vs_ancova](articles/559_change_score_vs_ancova) |
| 562 | 「直近30日」に今日を含めるか、時刻で切るか日付で切るかで、数字はどれだけ変わるのか？ | [562_rolling_30day_definition](articles/562_rolling_30day_definition) |
| 571 | UTCで保存した時刻を日本時間に直さずに日付で集計すると、何件が前日に入るのか？ | [571_utc_date_aggregation](articles/571_utc_date_aggregation) |
| 575 | 顧客が引っ越したとき、売上を「売った時点の住所」で数えるか「今の住所」で数えるかで、地域別の売上はどれだけ動くのか？ | [575_address_at_sale_vs_now](articles/575_address_at_sale_vs_now) |
| 579 | 店ごとの比率を平均するか、合計どうしで比を取るかで、全体の比率はどれだけ違うのか？ | [579_mean_of_ratios_vs_ratio_of_totals](articles/579_mean_of_ratios_vs_ratio_of_totals) |
| 581 | 締め日が20日の会社で、月の売上を暦の月で数えるか締めの期間で数えるかで、月ごとの数字はどれだけずれるのか？ | [581_closing_day_vs_calendar_month](articles/581_closing_day_vs_calendar_month) |
| 583 | 在庫を帳簿上の数で見るか、引当を除いた使える数で見るかで、欠品の判定は何品目変わるのか？ | [583_available_vs_on_hand](articles/583_available_vs_on_hand) |
| 585 | 個・箱・ケースの単位が混ざった出荷明細を換算せずに足すと、品目別の数量はどれだけずれるのか？ | [585_unit_conversion](articles/585_unit_conversion) |
| 588 | 散らばりが水準で変わるデータで、予測の区間を「残差の標準偏差×2」で作ると、何%の回が外れるのか？ | [588_prediction_interval_heteroscedastic](articles/588_prediction_interval_heteroscedastic) |
| 590 | 比率の分母が小さい項目を並べると、上位と下位にどれだけ小さい項目が集まるのか？ | [590_small_denominator_ranking](articles/590_small_denominator_ranking) |
| 591 | 欠品していた日の売上を0と見るか欠測と見るかで、平均の需要はどれだけ少なく見えるのか？ | [591_stockout_censored_demand](articles/591_stockout_censored_demand) |
| 592 | 同じ商品の色・サイズ違いを1品目と数えるか別々に数えるかで、売れ筋の順位はどれだけ変わるのか？ | [592_parent_vs_sku_ranking](articles/592_parent_vs_sku_ranking) |
| 593 | 開店と閉店がある期間で、「1店あたりの売上」を月末の店数で割るか営業日数で割るかで、どれだけ違うのか？ | [593_per_store_denominator](articles/593_per_store_denominator) |
| 602 | 平均単価を「明細の単価の平均」で出すか「金額の合計÷数量」で出すかで、品目の単価はどれだけ違うのか？ | [602_avg_unit_price_definition](articles/602_avg_unit_price_definition) |
| 603 | 日次の前年比を「前年の同じ日」と比べるか「前年の同じ曜日」と比べるかで、どれだけ違って見えるのか？ | [603_yoy_same_date_vs_weekday](articles/603_yoy_same_date_vs_weekday) |
| 605 | 先頭の0が落ちた商品コードや取引先コードで表をつなぐと、何件がつながらず、何件が別のコードにつながるのか？ | [605_leading_zero_codes](articles/605_leading_zero_codes) |
| 613 | 安全在庫を需要のばらつきだけで決めると、届くまでの日数がばらつくとき欠品は何%になるのか？ | [613_safety_stock_leadtime_var](articles/613_safety_stock_leadtime_var) |
| 615 | 顧客の生涯の売上を「月の購入額÷退会率」で出すと、登録月ごとの実績からどれだけずれるのか？ | [615_ltv_simple_vs_cohort](articles/615_ltv_simple_vs_cohort) |
| 624 | 週の途中の数字を先週の合計と比べると、どれだけ低く見えるのか？ | [624_partial_week_comparison](articles/624_partial_week_comparison) |
| 631 | 発注をケース単位に切り上げると、在庫は平均で何日分多く持つことになるのか？ | [631_case_pack_rounding_inventory](articles/631_case_pack_rounding_inventory) |
| 641 | 整数どうしの割り算で割合を出すと、何%の行が0になるのか？ | [641_integer_division_ratio](articles/641_integer_division_ratio) |
| 642 | 年間の目標を12等分するか、前年の月の比率で分けるかで、「達成した月」の数はどれだけ違うのか？ | [642_monthly_target_phasing](articles/642_monthly_target_phasing) |
| 644 | 毎年の伸び率を足して割った平均と、年率（幾何平均）では、5年後の値はどれだけ違うのか？ | [644_growth_rate_arith_vs_geo](articles/644_growth_rate_arith_vs_geo) |
| 645 | 5段階の評価を平均で比べるか、上位2つの割合で比べるかで、店の順位はどれだけ入れ替わるのか？ | [645_likert_mean_vs_top2box](articles/645_likert_mean_vs_top2box) |
| 653 | 層ごとに抽出率の違うサンプルを、重みを付けずに平均すると、全体の値はどれだけずれるのか？ | [653_stratified_sample_weights](articles/653_stratified_sample_weights) |
| 656 | 同じ店の前と後を比べるとき、対応のない検定にすると、差を見つける力はどれだけ落ちるのか？ | [656_paired_vs_unpaired_test](articles/656_paired_vs_unpaired_test) |
| 658 | ゼロを含むデータを log(y+c) で回帰すると、c の選び方で係数はどれだけ変わるのか？ | [658_log1p_constant_choice](articles/658_log1p_constant_choice) |
| 660 | 回帰の「平均の区間」を新しい1件の予測の区間と取り違えると、何%の回が外れるのか？ | [660_ci_vs_prediction_interval](articles/660_ci_vs_prediction_interval) |
| 661 | 新しく開いた店と閉じた店を含めたまま前年比を出すと、既存店だけの前年比とどれだけ違うのか？ | [661_existing_store_yoy](articles/661_existing_store_yoy) |
| 662 | UNION と UNION ALL を取り違えると、何件の行が消えたり残ったりするのか？ | [662_union_vs_union_all](articles/662_union_vs_union_all) |
| 663 | ウィンドウ関数の PARTITION BY を書き忘れると、店ごとの累計や順位はどれだけ狂うのか？ | [663_window_partition_missing](articles/663_window_partition_missing) |
| 664 | 平均単価の前年比を、品目の構成の変化と単価の変化に分けると、それぞれどれだけになるのか？ | [664_price_mix_decomposition](articles/664_price_mix_decomposition) |
| 665 | 会員カードを出した客だけで客単価を見ると、店全体の客単価よりどれだけ高く出るのか？ | [665_member_card_spend_bias](articles/665_member_card_spend_bias) |
| 673 | 1つの注文を、使ったクーポンそれぞれに全額付けると、クーポン別の売上の合計は実際の何倍になるのか？ | [673_coupon_double_attribution](articles/673_coupon_double_attribution) |
| 675 | DISTINCT で重複を消すと、本当に2回あった同じ内容の取引は何件消えるのか？ | [675_distinct_true_duplicates](articles/675_distinct_true_duplicates) |
| 679 | 層別に割り付けると、単純な無作為の割り付けよりも効果の推定のばらつきはどれだけ小さくなるのか？ | [679_stratified_randomization](articles/679_stratified_randomization) |
| 681 | 「有効」フラグの立った商品だけで集計すると、廃番になった商品の過去の売上はどれだけ消えるのか？ | [681_existing_flag_history](articles/681_existing_flag_history) |
| 682 | 店ごとの前年比を並べるのと、全体の伸びへの寄与度で並べるのでは、順位はどれだけ違うのか？ | [682_contribution_to_growth](articles/682_contribution_to_growth) |
| 688 | 店の固定効果だけ入れて、年ごとの流れを入れないと、施策の効果はどれだけずれるのか？ | [688_panel_time_effects](articles/688_panel_time_effects) |
| 697 | ダミー変数の基準のカテゴリを変えると、係数と有意の見え方はどれだけ変わるのか？ | [697_reference_category](articles/697_reference_category) |
| 700 | 選択肢を1つ足したとき、多項ロジットは他の選択肢のシェアをどう奪うと見て、本当の動きとどれだけずれるのか？ | [700_multinomial_logit_iia](articles/700_multinomial_logit_iia) |
| 702 | 構成比を WHERE で絞り込んだあとに出すと、全体に対する割合とどれだけ違って見えるのか？ | [702_share_after_filter](articles/702_share_after_filter) |
| 703 | 売上のない月が行ごと抜けた表で LAG を使って前月比を出すと、何行が2か月前と比べてしまうのか？ | [703_lag_missing_months](articles/703_lag_missing_months) |
| 711 | 月の売上を「30」で割るか、その月の日数や営業日数で割るかで、日あたりの前月比はどれだけ違うのか？ | [711_daily_avg_days_in_month](articles/711_daily_avg_days_in_month) |
| 713 | 率が5%から6%になったのを「1ポイント増」と「20%増」のどちらで書くかで、店の並びはどれだけ変わるのか？ | [713_points_vs_percent_change](articles/713_points_vs_percent_change) |
| 714 | 空白のセルと0のセルが混ざった列を Excel の AVERAGE で平均すると、値はどれだけ変わるのか？ | [714_excel_average_blank_zero](articles/714_excel_average_blank_zero) |
| 718 | 件数の少ない店が多いとき、店ごとの平均を「そのまま」出すのと、ランダム効果で縮めるのとでは、どれだけ当たり方が違うのか？ | [718_random_vs_fixed_small_groups](articles/718_random_vs_fixed_small_groups) |
| 719 | 施策の開始時期が店ごとにずれ、効果が時間とともに大きくなるとき、ふつうの二方向固定効果の推定はどれだけずれるのか？ | [719_staggered_did_twfe](articles/719_staggered_did_twfe) |
| 722 | 整数の列を SQL Server の AVG で平均すると、小数の切り捨てで店ごとの平均はどれだけずれるのか？ | [722_avg_integer_truncation](articles/722_avg_integer_truncation) |
| 723 | 前年がマイナスの利益の伸び率を、ふつうの式で出すと、何店で向きが逆に見えるのか？ | [723_growth_negative_base](articles/723_growth_negative_base) |
| 724 | 日次の売上に7日以外の幅の移動平均をかけると、曜日の波はどれだけ残るのか？ | [724_moving_avg_window_weekday](articles/724_moving_avg_window_weekday) |
| 730 | 階層クラスタリングのつなぎ方（最短・最長・群平均・ウォード）で、本当のまとまりを何%で当てるのか？ | [730_hierarchical_linkage](articles/730_hierarchical_linkage) |
| 731 | 「上位10%の顧客で売上の何割」を、買わなかった会員を含めて数えるか除くかで、どれだけ違うのか？ | [731_top_share_zero_customers](articles/731_top_share_zero_customers) |
| 732 | うるう年の2月29日を含む月の前年同月比は、日数をそろえないとどれだけ高く見えるのか？ | [732_leap_day_yoy](articles/732_leap_day_yoy) |
| 733 | 見出し行つきの CSV を何本も縦につなぐと、見出し行が何行まざり、数の列はどうなるのか？ | [733_repeated_header_rows](articles/733_repeated_header_rows) |
| 734 | 「1回1万円以上の注文がある顧客」と「合計1万円以上の顧客」を取り違えると、何人がずれるのか？ | [734_where_vs_having](articles/734_where_vs_having) |
| 737 | 施策の効き道になる変数を回帰に入れると、施策の効果はどれだけ小さく出るのか？ | [737_mediator_adjustment](articles/737_mediator_adjustment) |
| 750 | 交互作用を入れた回帰で、変数を中心化しないと、主効果の係数はどう読めてしまうのか？ | [750_centering_interaction_main_effect](articles/750_centering_interaction_main_effect) |
| 751 | PIVOT の列を固定で書いておくと、あとから増えた区分の売上は何%消えるのか？ | [751_pivot_fixed_columns](articles/751_pivot_fixed_columns) |
| 752 | 先頭に BOM のついた CSV を csv モジュールで読むと、最初の列名が一致せず、何行の売上が黙って集計から落ちるのか？ | [752_csv_bom_header](articles/752_csv_bom_header) |
| 754 | 欠品率を「欠品した SKU の数」で数えるか「売上の重み」で数えるかで、店の比べ方はどれだけ変わるのか？ | [754_stockout_rate_weighting](articles/754_stockout_rate_weighting) |
| 761 | 長さの足りない列に名前を入れると、後ろが切れて別の商品が同じ名前になるのは何件か？ | [761_varchar_truncation_collision](articles/761_varchar_truncation_collision) |
| 762 | 申込率を小数の桁の少ない DECIMAL に入れると、率はどれだけ丸まり、店の順位はどれだけ入れ替わるのか？ | [762_decimal_scale_division](articles/762_decimal_scale_division) |
| 765 | 「NA」という区分名を pandas で読むと、何行が欠けた値になってしまうのか？ | [765_pandas_na_string](articles/765_pandas_na_string) |
| 771 | 104万行を超える CSV を Excel で開くと、どれだけの行と売上が消えるのか？ | [771_excel_row_limit](articles/771_excel_row_limit) |
| 773 | 列の順番が違う2つの表を UNION ALL でつなぐと、何行の値が別の列に入るのか？ | [773_union_column_order](articles/773_union_column_order) |
| 774 | 達成率を四捨五入してから「100%以上」を数えると、何店が「達成」に入ってしまうのか？ | [774_achievement_rounding](articles/774_achievement_rounding) |
| 775 | 前回の順位と比べるとき、前回いなかった店を外すかどうかで、「順位が上がった店」の数はどれだけ変わるのか？ | [775_rank_change_new_entries](articles/775_rank_change_new_entries) |
| 776 | 差の差で対照を1店だけ選ぶと、施策の効果の推定はどれだけ振れるのか？ | [776_single_control_did](articles/776_single_control_did) |
| 777 | 大きい店では有意・小さい店では有意でない、を「効き方が違う」と読むと、何%で誤るのか？ | [777_difference_in_significance](articles/777_difference_in_significance) |
| 781 | 数の列に文字が1つまざると、Excel のピボットの集計はどう変わり、合計はどれだけ消えるのか？ | [781_pivot_count_default](articles/781_pivot_count_default) |
| 784 | 法人のまとめ買いを混ぜたまま客単価を見ると、個人の客単価はどれだけ高く見えるのか？ | [784_bulk_buyer_mixing](articles/784_bulk_buyer_mixing) |
| 791 | 0で割るのを NULLIF で避けると、その店は平均から黙って消え、全体の率はどれだけ変わるのか？ | [791_nullif_drop_from_avg](articles/791_nullif_drop_from_avg) |
| 794 | 1つの商品が2つのカテゴリに入る表でカテゴリ別に売上を足すと、全体の何倍になるのか？ | [794_multi_category_double_count](articles/794_multi_category_double_count) |

</details>

<details><summary><b>EC・会員・Web</b>（96本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F101 | 物価と賃金は、長い目で見ると一緒に動いているのか？ | [F101_price_wage_cointegration](articles/F101_price_wage_cointegration) |
| F122 | 手法ごとに、どこでつまずいたか？ | [F122_pitfalls_from_logs](articles/F122_pitfalls_from_logs) |
| F139 | 副業をしている人は、どんな働き方の人か？ | [F139_side_job_loglinear](articles/F139_side_job_loglinear) |
| F141 | 特許の出願は、どの分野で地方に広がったのか？ | [F141_ip_regional_concentration](articles/F141_ip_regional_concentration) |
| F162 | 公的データは「API で取れる」のか？ | [F162_data_access_map](articles/F162_data_access_map) |
| F164 | 図をどう作ると、読まれ方が変わったか？ | [F164_figures_and_reads](articles/F164_figures_and_reads) |
| F176 | 白書の文章は、年々読みやすくなったのか？ | [F176_whitepaper_readability](articles/F176_whitepaper_readability) |
| F183 | 車を持つ世帯は、どこで減りはじめたのか？ | [F183_car_ownership_change_points](articles/F183_car_ownership_change_points) |
| F185 | 宅配便の個数は、どこまで通販で説明できるのか？ | [F185_parcels_online_shopping](articles/F185_parcels_online_shopping) |
| F236 | A/B テストは、何人集めれば「差」が分かるのか？ | [F236_ab_test_sample_size](articles/F236_ab_test_sample_size) |
| F237 | A/B テストを途中で見ると、何がまずいのか？ | [F237_ab_test_peeking_sequential](articles/F237_ab_test_peeking_sequential) |
| F238 | 前の期間のデータを使うと、テストはどれだけ早く終わるか？ | [F238_ab_test_cuped](articles/F238_ab_test_cuped) |
| F241 | 顧客はどれくらいで離れていくのか？ | [F241_customer_churn_survival](articles/F241_customer_churn_survival) |
| F242 | 毎日の KPI の「いつもと違う」を、どう自動で知らせるか？ | [F242_kpi_anomaly_alerts](articles/F242_kpi_anomaly_alerts) |
| F244 | 集計の SQL は、どう書けば間違えにくいか？ | [F244_sql_aggregation_pitfalls](articles/F244_sql_aggregation_pitfalls) |
| F246 | 分析担当として最初にやること：KPI を決める（業務の再現：架空の会社で） シリーズ③の1本目。架空の食品スーパー「サン | [F246_kpi_definitions_fictional_retail](articles/F246_kpi_definitions_fictional_retail) |
| F247 | データを集めて、使える形に整える（業務の再現：架空の会社で） シリーズ③の2本目。F246 の合成データ「サンプルマート | [F247_data_mart_fictional_retail](articles/F247_data_mart_fictional_retail) |
| F249 | ダッシュボードを作る（業務の再現：架空の会社で） シリーズ③の続き。F246 の KPI 定義 v1 と F247 の  | [F249_powerbi_dashboard_fictional_retail](articles/F249_powerbi_dashboard_fictional_retail) |
| F251 | 販促の効果を測る（業務の再現：架空の会社で） シリーズ③の6本目。F247 の mart の架空の食品スーパー「サンプル | [F251_promo_effect_fictional_retail](articles/F251_promo_effect_fictional_retail) |
| F270 | 「訪日客が過去最多」は、1人あたりの支出で見ても最多か？ | [F270_inbound_record_per_capita](articles/F270_inbound_record_per_capita) |
| F271 | 見られるダッシュボードと、見られないダッシュボードの違いは何か？ | [F271_dashboard_answer_cost](articles/F271_dashboard_answer_cost) |
| F279 | RFM で分けた顧客は、その後どう動くのか？ | [F279_rfm_segment_transitions](articles/F279_rfm_segment_transitions) |
| 233 | 集計の合計が会計の数字と合わないとき、SQL のどこから疑うか？ | [233_sql_reconcile_totals](articles/233_sql_reconcile_totals) |
| 245 | 顧客の重複を SQL で片づけるとき、どのキーで同じ人とみなすか？ | [245_sql_dedup_customers](articles/245_sql_dedup_customers) |
| 294 | SQL のクエリが遅いとき、まず何を見るか？ | [294_slow_query_first_checks](articles/294_slow_query_first_checks) |
| 311 | 表をつなぐと、合計はなぜ増えたり減ったりするのか？ | [311_sql_join_fanout](articles/311_sql_join_fanout) |
| 312 | SQL の NULL は、集計をどれだけ黙ってずらすのか？ | [312_sql_null_aggregation](articles/312_sql_null_aggregation) |
| 326 | 古いシステムから新しいシステムへ移したデータは、何を照合すれば「同じ」と言えるか？ | [326_migration_reconciliation](articles/326_migration_reconciliation) |
| 342 | 締めたあとに訂正されたデータで、先月のレポートの数字を再現できるか？ | [342_restate_and_reproduce_reports](articles/342_restate_and_reproduce_reports) |
| 344 | 「アクティブな顧客」は、定義でどれだけ人数が変わるのか？ | [344_active_customer_definitions](articles/344_active_customer_definitions) |
| 365 | 似た相手を選んで比べる方法は、測っていない違いがあるとどこまで外れるのか？ | [365_matching_unmeasured_confounder](articles/365_matching_unmeasured_confounder) |
| 372 | CSV を Excel で開いて保存すると、何セルが変わってしまうのか？ | [372_csv_excel_roundtrip](articles/372_csv_excel_roundtrip) |
| 386 | 「以上」と「超」、「以下」と「未満」を取り違えると、何件が別の区分に入るのか？ | [386_boundary_inclusive_exclusive](articles/386_boundary_inclusive_exclusive) |
| 387 | チェックデジットは、打ち間違いの何割を止めるのか？ | [387_check_digit_detection](articles/387_check_digit_detection) |
| 388 | 登録月ごとの継続率の表で、まだ観測できていない月を0と数えると、どれだけ低く出るのか？ | [388_cohort_retention_censoring](articles/388_cohort_retention_censoring) |
| 389 | 申込みまでの通過率は、数え方でどれだけ変わるのか？ | [389_funnel_counting_definitions](articles/389_funnel_counting_definitions) |
| 403 | ORDER BY のない SELECT の並びに頼ると、結果はどれだけ再現しないのか？ | [403_select_without_order_by](articles/403_select_without_order_by) |
| 407 | 名前を消しただけの顧客データは、何%の人が1人に絞れてしまうのか？ | [407_k_anonymity_customer_data](articles/407_k_anonymity_customer_data) |
| 413 | 途中で解約した契約に返す保険料は、日割りと短期率でどれだけ違うのか？ | [413_cancellation_refund_methods](articles/413_cancellation_refund_methods) |
| 428 | 文字コードを取り違えて CSV を読むと、何行が壊れ、何行が黙って通るのか？ | [428_csv_encoding_mismatch](articles/428_csv_encoding_mismatch) |
| 453 | 数字が文字として入った列を並べ替えると、何件が違う順番になるのか？ | [453_numbers_stored_as_text](articles/453_numbers_stored_as_text) |
| 455 | 1ページずつ順に取り込むと、途中で行が増減したとき、何行が重なり、何行が抜けるのか？ | [455_pagination_drift_during_load](articles/455_pagination_drift_during_load) |
| 460 | 予測に「答えが漏れた列」が混ざると、確かめの成績はどれだけ良く見え、本番でどれだけ落ちるのか？ | [460_target_leakage_validation](articles/460_target_leakage_validation) |
| 461 | 区分ごとのユニーク人数を足すと、全体の人数より何%多くなるのか？ | [461_distinct_counts_not_additive](articles/461_distinct_counts_not_additive) |
| 465 | サーバーごとに時計がずれていると、ログの出来事の順番は何件逆になるのか？ | [465_clock_skew_event_order](articles/465_clock_skew_event_order) |
| 472 | 返品を「売れた月」に戻すか「返ってきた月」で引くかで、月の売上はどれだけ変わるのか？ | [472_returns_which_month](articles/472_returns_which_month) |
| 473 | 値引きやクーポンを明細に割り振る方法で、商品ごとの粗利はどれだけ変わるのか？ | [473_discount_allocation_margin](articles/473_discount_allocation_margin) |
| 475 | 解約率は、分母の取り方でどれだけ違って見えるのか？ | [475_churn_rate_denominator](articles/475_churn_rate_denominator) |
| 482 | ポイントの失効を「付与日から1年」と「月末に一括」にすると、2025〜2026年の失効額と月の数字はどれだけ変わるのか？ | [482_point_expiry_rules](articles/482_point_expiry_rules) |
| 485 | 論理削除のフラグと履歴の期間を見落とすと、注文の件数と売上は何%多く出るのか？ | [485_soft_delete_flags](articles/485_soft_delete_flags) |
| 490 | 解約率の仮定が実際とずれると、保険の将来の利益の見込みはどれだけ動くのか？ | [490_lapse_assumption_profit_sensitivity](articles/490_lapse_assumption_profit_sensitivity) |
| 494 | 入れ子の注文JSONを平らにすると、行は何倍になり、合計は何%ずれるのか？ | [494_nested_json_flatten](articles/494_nested_json_flatten) |
| 495 | 会員ランクを「暦年」と「直近12か月」で判定すると、2025年の12月には何%の会員のランクが食い違うのか？ | [495_member_rank_calendar_vs_rolling](articles/495_member_rank_calendar_vs_rolling) |
| 503 | ログのセッションを何分空いたら切るかで、セッション数と1回あたりの滞在はどれだけ変わるのか？ | [503_session_timeout_definitions](articles/503_session_timeout_definitions) |
| 504 | 取消された注文を残したまま初回購入月を決めると、新規顧客の数は何%多く出るのか？ | [504_first_purchase_month_cancellations](articles/504_first_purchase_month_cancellations) |
| 505 | 定期便の次回のお届け日を「30日後」と「毎月同じ日」で決めると、1年の出荷回数と月の出荷数はどれだけ違うのか？ | [505_subscription_next_delivery_rules](articles/505_subscription_next_delivery_rules) |
| 511 | ログの利用者IDが Cookie だと、ユニーク利用者は本当の人数の何倍に数えられるのか？ | [511_cookie_vs_login_unique_users](articles/511_cookie_vs_login_unique_users) |
| 513 | ログを10件に1件だけ残して10倍すると、小さな区分の件数はどれだけ振れるのか？ | [513_log_sampling_small_segments](articles/513_log_sampling_small_segments) |
| 535 | 顧客の年齢を「登録したときの年齢」のまま集計すると、年代別の構成は何年でどれだけずれるのか？ | [535_age_at_registration_drift](articles/535_age_at_registration_drift) |
| 541 | 郵便番号から都道府県・市区町村を引くと、古い番号や事業所の個別番号のせいで何件が引けないのか？ | [541_postal_code_lookup_gaps](articles/541_postal_code_lookup_gaps) |
| 545 | 割引を2つ重ねるとき、「足し算」「掛け算」「適用の順番」の違いで、請求額は何件・何円違うのか？ | [545_stacked_discount_order](articles/545_stacked_discount_order) |
| 552 | 訂正を「取消（赤）＋再登録（黒）」で入れる伝票では、件数と金額をどう数えればよいのか？ | [552_red_black_correction_count](articles/552_red_black_correction_count) |
| 558 | 予測確率が「30%」と出た人のうち、本当に起きるのは何%なのか？ | [558_probability_calibration](articles/558_probability_calibration) |
| 564 | 注文を何回かに分けて出荷すると、「出荷済みの注文」の数え方でどれだけ違うのか？ | [564_partial_shipment_definition](articles/564_partial_shipment_definition) |
| 571 | UTCで保存した時刻を日本時間に直さずに日付で集計すると、何件が前日に入るのか？ | [571_utc_date_aggregation](articles/571_utc_date_aggregation) |
| 572 | 同じ時刻の行が並ぶとき、ROW_NUMBERで「最新の1行」を選ぶと、実行のたびに何件入れ替わるのか？ | [572_row_number_ties](articles/572_row_number_ties) |
| 573 | 会員の「休眠」を最終購入から90日で切るか180日で切るかで、休眠の人数と「復活」の割合はどれだけ変わるのか？ | [573_dormant_threshold_days](articles/573_dormant_threshold_days) |
| 575 | 顧客が引っ越したとき、売上を「売った時点の住所」で数えるか「今の住所」で数えるかで、地域別の売上はどれだけ動くのか？ | [575_address_at_sale_vs_now](articles/575_address_at_sale_vs_now) |
| 584 | 同じ人が別のIDで登録された顧客表を、電話・メール・氏名＋生年月日で寄せると、顧客数とリピート率はどれだけ変わるのか？ | [584_customer_dedup_keys](articles/584_customer_dedup_keys) |
| 601 | 外部結合（LEFT JOIN）のあと WHERE で右の表の列を絞ると、何件の行が黙って消えるのか？ | [601_left_join_where_filter](articles/601_left_join_where_filter) |
| 608 | 件数の少ないクラスがあるとき、層化しない交差検証では何%の fold にそのクラスが入らないのか？ | [608_stratified_cv_rare_class](articles/608_stratified_cv_rare_class) |
| 615 | 顧客の生涯の売上を「月の購入額÷退会率」で出すと、登録月ごとの実績からどれだけずれるのか？ | [615_ltv_simple_vs_cohort](articles/615_ltv_simple_vs_cohort) |
| 622 | 「新規の顧客」を過去何年さかのぼって判定するかで、新規の割合はどれだけ変わるのか？ | [622_new_customer_lookback](articles/622_new_customer_lookback) |
| 632 | マスタは今日、明細は昨日の時点の表をつなぐと、何件が片方にしかないのか？ | [632_master_detail_snapshot_lag](articles/632_master_detail_snapshot_lag) |
| 634 | CASE WHEN の条件の並べ方で、何件が別の区分に入るのか？ | [634_case_when_order](articles/634_case_when_order) |
| 643 | キャンペーンを使った人と使わなかった人を比べると、効果が0でもどれだけ差が出るのか？ | [643_campaign_users_self_selection](articles/643_campaign_users_self_selection) |
| 651 | ページの滞在時間を「次のページを開いた時刻との差」で測ると、最後に見たページの分はどれだけ抜け落ちるのか？ | [651_last_page_dwell_time](articles/651_last_page_dwell_time) |
| 654 | 大文字と小文字を区別するかしないかで、GROUP BY の件数とつながる行はどれだけ変わるのか？ | [654_collation_case_grouping](articles/654_collation_case_grouping) |
| 655 | 平均の購入間隔を「2回以上買った人」だけで出すと、本当の間隔よりどれだけ短く出るのか？ | [655_purchase_interval_selection](articles/655_purchase_interval_selection) |
| 665 | 会員カードを出した客だけで客単価を見ると、店全体の客単価よりどれだけ高く出るのか？ | [665_member_card_spend_bias](articles/665_member_card_spend_bias) |
| 670 | 退会と転居の2つの理由で会員が抜けるとき、片方を打ち切りにした生存曲線は、退会の割合をどれだけ大きく見るのか？ | [670_competing_risks](articles/670_competing_risks) |
| 671 | 重複して登録した人を除かずに抽選すると、その人の当選確率は何倍になるのか？ | [671_lottery_duplicate_entries](articles/671_lottery_duplicate_entries) |
| 673 | 1つの注文を、使ったクーポンそれぞれに全額付けると、クーポン別の売上の合計は実際の何倍になるのか？ | [673_coupon_double_attribution](articles/673_coupon_double_attribution) |
| 691 | 同じ顧客の重複行から「最初」と「最新」のどちらを残すかで、属性の集計はどれだけ変わるのか？ | [691_dedup_keep_first_or_last](articles/691_dedup_keep_first_or_last) |
| 704 | 年齢を「年の差」だけで出すと、誕生日前の会員は何%が1歳多く数えられるのか？ | [704_age_datediff_year](articles/704_age_datediff_year) |
| 705 | リピート率を「30日以内」で数えるか「90日以内」で数えるかで、月ごとの比べ方はどれだけ変わるのか？ | [705_repeat_rate_window](articles/705_repeat_rate_window) |
| 725 | 購入回数で顧客を5等分すると、同じ回数の人が別の段に分かれるのはどれだけか？ | [725_rfm_quintile_ties](articles/725_rfm_quintile_ties) |
| 726 | クリック率をクリック単位で数えて検定すると、ユーザー単位で割り付けた A/B テストで、効果が0でも何%で「差あり」になるのか？ | [726_ratio_metric_delta_method](articles/726_ratio_metric_delta_method) |
| 731 | 「上位10%の顧客で売上の何割」を、買わなかった会員を含めて数えるか除くかで、どれだけ違うのか？ | [731_top_share_zero_customers](articles/731_top_share_zero_customers) |
| 734 | 「1回1万円以上の注文がある顧客」と「合計1万円以上の顧客」を取り違えると、何人がずれるのか？ | [734_where_vs_having](articles/734_where_vs_having) |
| 742 | LEFT JOIN のあと COUNT(*) で注文数を数えると、注文0件の顧客は何件と数えられるのか？ | [742_left_join_count_star](articles/742_left_join_count_star) |
| 743 | 退会した会員の番号を新しい会員に使い回すと、何人の新しい会員に前の人の購入がつくのか？ | [743_id_reuse_history](articles/743_id_reuse_history) |
| 744 | 会員番号の偶数と奇数で2群に分けると、番号の振り方によって群の間にどれだけ差が出るのか？ | [744_id_parity_split](articles/744_id_parity_split) |
| 748 | ある日に「利用中」の会員だけに聞くと、平均の利用期間は本当の何倍に見えるのか？ | [748_length_biased_sampling](articles/748_length_biased_sampling) |
| 755 | 時刻つきの日時のまま GROUP BY すると、日ごとの集計は何行に分かれてしまうのか？ | [755_group_by_datetime_not_date](articles/755_group_by_datetime_not_date) |
| 762 | 申込率を小数の桁の少ない DECIMAL に入れると、率はどれだけ丸まり、店の順位はどれだけ入れ替わるのか？ | [762_decimal_scale_division](articles/762_decimal_scale_division) |

</details>

<details><summary><b>マーケティング・広告</b>（23本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F86 | 平均寿命はこの先どこまで延びるのか？ | [F86_lee_carter_e0](articles/F86_lee_carter_e0) |
| F239 | 広告費は、売上にどれだけ効いているのか？ | [F239_marketing_mix_model](articles/F239_marketing_mix_model) |
| F240 | キャンペーンの効果を、比べる相手がないときにどう測るか？ | [F240_campaign_effect_no_control](articles/F240_campaign_effect_no_control) |
| F242 | 毎日の KPI の「いつもと違う」を、どう自動で知らせるか？ | [F242_kpi_anomaly_alerts](articles/F242_kpi_anomaly_alerts) |
| F244 | 集計の SQL は、どう書けば間違えにくいか？ | [F244_sql_aggregation_pitfalls](articles/F244_sql_aggregation_pitfalls) |
| F249 | ダッシュボードを作る（業務の再現：架空の会社で） シリーズ③の続き。F246 の KPI 定義 v1 と F247 の  | [F249_powerbi_dashboard_fictional_retail](articles/F249_powerbi_dashboard_fictional_retail) |
| F251 | 販促の効果を測る（業務の再現：架空の会社で） シリーズ③の6本目。F247 の mart の架空の食品スーパー「サンプル | [F251_promo_effect_fictional_retail](articles/F251_promo_effect_fictional_retail) |
| F255 | 1年の分析業務を振り返る（業務の再現：架空の会社で） シリーズ③の10本目・最後。架空の食品スーパー「サンプルマート（架 | [F255_year_review_fictional_retail](articles/F255_year_review_fictional_retail) |
| 245 | 顧客の重複を SQL で片づけるとき、どのキーで同じ人とみなすか？ | [245_sql_dedup_customers](articles/245_sql_dedup_customers) |
| 280 | 週次の数字を毎週メールで自動配信するとき、いつ送るか？ | [280_weekly_kpi_email](articles/280_weekly_kpi_email) |
| 306 | スプレッドシートの申込集計を、GAS でどう自動にするか？ | [306_gas_sheet_aggregation](articles/306_gas_sheet_aggregation) |
| 429 | 共通の費用を部門に配る基準を変えると、何部門の損益の符号が変わるのか？ | [429_overhead_allocation_bases](articles/429_overhead_allocation_bases) |
| 462 | 2つの期間が重なるかどうかの条件を書き間違えると、何件が漏れ、何件が余分に入るのか？ | [462_interval_overlap_conditions](articles/462_interval_overlap_conditions) |
| 473 | 値引きやクーポンを明細に割り振る方法で、商品ごとの粗利はどれだけ変わるのか？ | [473_discount_allocation_margin](articles/473_discount_allocation_margin) |
| 494 | 入れ子の注文JSONを平らにすると、行は何倍になり、合計は何%ずれるのか？ | [494_nested_json_flatten](articles/494_nested_json_flatten) |
| 525 | メールの開封率は、画像の自動読み込みによる「見かけの開封」を除くと何ポイント下がるのか？ | [525_email_open_rate_auto_load](articles/525_email_open_rate_auto_load) |
| 584 | 同じ人が別のIDで登録された顧客表を、電話・メール・氏名＋生年月日で寄せると、顧客数とリピート率はどれだけ変わるのか？ | [584_customer_dedup_keys](articles/584_customer_dedup_keys) |
| 643 | キャンペーンを使った人と使わなかった人を比べると、効果が0でもどれだけ差が出るのか？ | [643_campaign_users_self_selection](articles/643_campaign_users_self_selection) |
| 667 | 反応しそうな人に配るのと、配ったら反応が増える人に配るのでは、増える件数はどれだけ違うのか？ | [667_uplift_vs_response](articles/667_uplift_vs_response) |
| 671 | 重複して登録した人を除かずに抽選すると、その人の当選確率は何倍になるのか？ | [671_lottery_duplicate_entries](articles/671_lottery_duplicate_entries) |
| 673 | 1つの注文を、使ったクーポンそれぞれに全額付けると、クーポン別の売上の合計は実際の何倍になるのか？ | [673_coupon_double_attribution](articles/673_coupon_double_attribution) |
| 674 | 広告の成果を「最後の接点」に付けるか均等に分けるかで、広告ごとの成果はどれだけ違うのか？ | [674_ad_attribution_models](articles/674_ad_attribution_models) |
| 758 | 件数が少ないとき、モデルの「上位10%のリフト」はどれだけ揺れるのか？ | [758_top_decile_lift_noise](articles/758_top_decile_lift_noise) |

</details>

<details><summary><b>需要予測・在庫</b>（37本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F22 | 明日の電力需要はどこまで当てられるか？ | [F22_power_demand_forecast](articles/F22_power_demand_forecast) |
| F48 | ガソリンが10%上がると、買う量は何%減るか？ | [F48_gasoline_elasticity](articles/F48_gasoline_elasticity) |
| F85 | 日本経済の「要」の産業はどれか？ | [F85_io_network](articles/F85_io_network) |
| F91 | 機械学習の「何が効いているか」は、手法で答えが変わるか？ | [F91_interpretation_methods](articles/F91_interpretation_methods) |
| F92 | 電力需要の「上振れ」はどこまで見込めばよいか？ | [F92_power_quantile_forecast](articles/F92_power_quantile_forecast) |
| F103 | 電力需要や物価の「長い記憶」は、どれくらい続くか？ | [F103_long_memory](articles/F103_long_memory) |
| F104 | 気温と電力需要の関係を、ガウス過程の時系列で読むと？ | [F104_gp_power_temperature](articles/F104_gp_power_temperature) |
| F108 | 予測モデルは、地域によって外れ方が偏っていないか？ | [F108_prediction_fairness](articles/F108_prediction_fairness) |
| F110 | 予測モデルの設定は、どう選ぶのが効率的か？ | [F110_hyperparam_bayesopt](articles/F110_hyperparam_bayesopt) |
| F150 | 季節のパターンそのものは、年々変わっているのか？ | [F150_dynamic_seasonality](articles/F150_dynamic_seasonality) |
| F152 | 統計の速報は、確報でどれだけ直されるのか？ | [F152_revision_news_noise](articles/F152_revision_news_noise) |
| F154 | 推定の「不確かさ」は、図の形で何が読み取れるかが変わるのか？ | [F154_uncertainty_viz](articles/F154_uncertainty_viz) |
| F157 | 電力需要の予測を、1年通して運用したらどうなるか？ | [F157_power_forecast_operation](articles/F157_power_forecast_operation) |
| F175 | 予測モデルの精度は、どの特徴量の「おかげ」なのか？ | [F175_r2_shapley_decomposition](articles/F175_r2_shapley_decomposition) |
| F205 | 予測モデルは、作る前に何を決め、外れをいくらと見て、いつ作り直すのか？ | [F205_power_forecast_practice_part1](articles/F205_power_forecast_practice_part1) |
| F235 | 在庫はどれだけ持てばよいのか？ | [F235_inventory_newsvendor](articles/F235_inventory_newsvendor) |
| F239 | 広告費は、売上にどれだけ効いているのか？ | [F239_marketing_mix_model](articles/F239_marketing_mix_model) |
| F242 | 毎日の KPI の「いつもと違う」を、どう自動で知らせるか？ | [F242_kpi_anomaly_alerts](articles/F242_kpi_anomaly_alerts) |
| F252 | 来期の予算のための需要予測（業務の再現：架空の会社で） シリーズ③の7本目。架空の食品スーパー「サンプルマート（架空）」 | [F252_budget_forecast_fictional_retail](articles/F252_budget_forecast_fictional_retail) |
| F259 | 需要予測の外れは、在庫と欠品のどちらに効かせるべきか？ | [F259_forecast_error_inventory_cost](articles/F259_forecast_error_inventory_cost) |
| F269 | 「価格転嫁できた企業」は、どんな企業か？ | [F269_sme_price_passthrough](articles/F269_sme_price_passthrough) |
| F281 | 食料自給率の目標と実際の差は、どこから来ているのか？ | [F281_food_self_sufficiency_target_gap](articles/F281_food_self_sufficiency_target_gap) |
| F285 | エネルギー基本計画の電力需要の見通しは、過去にどれだけ当たったか？ | [F285_power_demand_outlook_accuracy](articles/F285_power_demand_outlook_accuracy) |
| 286 | 予測モデルは、線形回帰と勾配ブースティングのどちらから始めるか？ | [286_linear_vs_gbm_first](articles/286_linear_vs_gbm_first) |
| 296 | 需要予測の当たり外れを、毎週どう見張るか？ | [296_forecast_error_control_chart](articles/296_forecast_error_control_chart) |
| 362 | 時系列をばらばらに分けて確かめると、予測の精度をどれだけ甘く見積もるのか？ | [362_shuffled_cv_time_series](articles/362_shuffled_cv_time_series) |
| 363 | たまにしか売れない商品の需要は、どの方法で予測するのがよいか？ | [363_intermittent_demand_methods](articles/363_intermittent_demand_methods) |
| 430 | 同じ仕入れと販売でも、在庫の評価の方法で、月の粗利はどれだけ違うのか？ | [430_inventory_valuation_methods](articles/430_inventory_valuation_methods) |
| 454 | 2つの処理が同時に同じ行を書き換えると、何件の更新が消えるのか？ | [454_lost_updates_concurrent_writes](articles/454_lost_updates_concurrent_writes) |
| 483 | 在庫を「入った順」と「期限の近い順」で引き当てると、廃棄と欠品はどれだけ変わるのか？ | [483_fifo_vs_fefo_allocation](articles/483_fifo_vs_fefo_allocation) |
| 514 | 入庫と出庫の記録が遅れて届くと、在庫が一時的にマイナスになる日は何日あるのか？ | [514_inventory_record_delay_negative](articles/514_inventory_record_delay_negative) |
| 522 | 在庫回転日数を「期首と期末の平均在庫」で出すと、毎日の在庫から出した値と何日ずれるのか？ | [522_inventory_days_average_method](articles/522_inventory_days_average_method) |
| 583 | 在庫を帳簿上の数で見るか、引当を除いた使える数で見るかで、欠品の判定は何品目変わるのか？ | [583_available_vs_on_hand](articles/583_available_vs_on_hand) |
| 591 | 欠品していた日の売上を0と見るか欠測と見るかで、平均の需要はどれだけ少なく見えるのか？ | [591_stockout_censored_demand](articles/591_stockout_censored_demand) |
| 613 | 安全在庫を需要のばらつきだけで決めると、届くまでの日数がばらつくとき欠品は何%になるのか？ | [613_safety_stock_leadtime_var](articles/613_safety_stock_leadtime_var) |
| 631 | 発注をケース単位に切り上げると、在庫は平均で何日分多く持つことになるのか？ | [631_case_pack_rounding_inventory](articles/631_case_pack_rounding_inventory) |
| 754 | 欠品率を「欠品した SKU の数」で数えるか「売上の重み」で数えるかで、店の比べ方はどれだけ変わるのか？ | [754_stockout_rate_weighting](articles/754_stockout_rate_weighting) |

</details>

<details><summary><b>業務の集計・報告</b>（143本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F07 | 新卒は何年目に辞めやすいのか？ | [F07_turnover_survival](articles/F07_turnover_survival) |
| F18 | 景気は今どうなのか？ | [F18_nowcast_dfm](articles/F18_nowcast_dfm) |
| F48 | ガソリンが10%上がると、買う量は何%減るか？ | [F48_gasoline_elasticity](articles/F48_gasoline_elasticity) |
| F54 | 働く女性の賃金は、働いている人だけを見ると高く見えるのか？ | [F54_heckman_women_wage](articles/F54_heckman_women_wage) |
| F55 | ベイズで出生数を予測すると、予測の幅はどう変わるのか？ | [F55_births_bsts](articles/F55_births_bsts) |
| F63 | 「前年比」と「前月比」、景気の変わり目を早く見つけられるのはどちらか？ | [F63_yoy_vs_mom](articles/F63_yoy_vs_mom) |
| F84 | 男女の賃金差のうち、「説明できる部分」はどれだけか？ | [F84_oaxaca_gender_wage](articles/F84_oaxaca_gender_wage) |
| F88 | 携帯料金の値下げは、物価をどれだけ下げたか？ | [F88_mobile_fee_rdit](articles/F88_mobile_fee_rdit) |
| F89 | 最低賃金の効果、これまでの推定をまとめると？ | [F89_minwage_meta](articles/F89_minwage_meta) |
| F90 | 月次の統計で、四半期のGDPをどこまで当てられるか？ | [F90_midas_nowcast](articles/F90_midas_nowcast) |
| F94 | 市町村合併をどう扱うかで、20年の推移の分析は変わるか？ | [F94_municipal_merger_panel](articles/F94_municipal_merger_panel) |
| F97 | 「前年比+1%」は、本当に増えたと言えるのか？ | [F97_sampling_error_yoy](articles/F97_sampling_error_yoy) |
| F102 | 円安が物価に効くのは、円安が大きいときだけか？ | [F102_fx_threshold_passthrough](articles/F102_fx_threshold_passthrough) |
| F117 | 調査の回答率が下がると、結果はどれだけずれるか？ | [F117_nonresponse_weighting](articles/F117_nonresponse_weighting) |
| F120 | 2025年国勢調査で、記事の結論は変わったか？ | [F120_census2025_update](articles/F120_census2025_update) |
| F122 | 手法ごとに、どこでつまずいたか？ | [F122_pitfalls_from_logs](articles/F122_pitfalls_from_logs) |
| F130 | 介護の認定率の地域差は、高齢化だけで説明できるか？ | [F130_care_certification_shrinkage](articles/F130_care_certification_shrinkage) |
| F131 | 大学に進む人が増えると、地元に残る若者は減るのか？ | [F131_univ_youth_migration](articles/F131_univ_youth_migration) |
| F132 | 農家は「やめる」のか「大きくなる」のか？ | [F132_farm_size_transitions](articles/F132_farm_size_transitions) |
| F135 | 雨の日は、小売の売上をどれだけ動かすのか？ | [F135_rain_retail](articles/F135_rain_retail) |
| F136 | 鉄道の利用は、コロナ前にどこまで戻ったのか？ | [F136_rail_covid_recovery](articles/F136_rail_covid_recovery) |
| F138 | テレワークは、どの産業・地域に残ったのか？ | [F138_telework_decomposition](articles/F138_telework_decomposition) |
| F139 | 副業をしている人は、どんな働き方の人か？ | [F139_side_job_loglinear](articles/F139_side_job_loglinear) |
| F141 | 特許の出願は、どの分野で地方に広がったのか？ | [F141_ip_regional_concentration](articles/F141_ip_regional_concentration) |
| F145 | ごみの量は、有料化のあとに減ったのか？ | [F145_waste_fee_did](articles/F145_waste_fee_did) |
| F146 | 統計の秘匿をノイズで置き換えると、分析の答えはどれだけ変わるか？ | [F146_dp_noise_vs_suppression](articles/F146_dp_noise_vs_suppression) |
| F147 | 集計表から「それらしい個票」を作ると、元の分析を再現できるか？ | [F147_synthetic_from_tables](articles/F147_synthetic_from_tables) |
| F149 | 生存分析を機械学習でやると、何が良くなるのか？ | [F149_ml_survival](articles/F149_ml_survival) |
| F150 | 季節のパターンそのものは、年々変わっているのか？ | [F150_dynamic_seasonality](articles/F150_dynamic_seasonality) |
| F152 | 統計の速報は、確報でどれだけ直されるのか？ | [F152_revision_news_noise](articles/F152_revision_news_noise) |
| F162 | 公的データは「API で取れる」のか？ | [F162_data_access_map](articles/F162_data_access_map) |
| F181 | 家が建つ数は、金利と人口のどちらで決まるのか？ | [F181_housing_starts_rates_population](articles/F181_housing_starts_rates_population) |
| F184 | 空の便は、新幹線の開業でどれだけ減ったのか？ | [F184_air_shinkansen_did](articles/F184_air_shinkansen_did) |
| F186 | 電気料金の値上がりは、家計のどこに効いたのか？ | [F186_electricity_bill_household_burden](articles/F186_electricity_bill_household_burden) |
| F188 | 労働災害は、どの産業で減り、どこで減らなかったのか？ | [F188_occupational_injury_by_industry](articles/F188_occupational_injury_by_industry) |
| F191 | お金の量を増やすと、貸出は増えたのか？ | [F191_money_base_lending](articles/F191_money_base_lending) |
| F192 | 国債の金利は、何で動いているのか？ | [F192_jgb_yield_curve_pca](articles/F192_jgb_yield_curve_pca) |
| F193 | インターネットの通信量は、どの時間に、どれだけ増えたのか？ | [F193_internet_traffic_decomposition](articles/F193_internet_traffic_decomposition) |
| F195 | 夜の明かりで、地域の経済活動はどこまで分かるか？ | [F195_night_lights_gdp](articles/F195_night_lights_gdp) |
| F198 | 調査は、何人に聞けば足りるのか？ | [F198_sample_size_planning](articles/F198_sample_size_planning) |
| F199 | 季節調整のやり方で、「景気の山」の時期は変わるのか？ | [F199_seasonal_adjustment_turning_points](articles/F199_seasonal_adjustment_turning_points) |
| F205 | 予測モデルは、作る前に何を決め、外れをいくらと見て、いつ作り直すのか？ | [F205_power_forecast_practice_part1](articles/F205_power_forecast_practice_part1) |
| F206 | 予測は、エリアと合計をどうそろえ、どう見せ、1年回すと何が起きるのか？ | [F206_power_forecast_practice_part2](articles/F206_power_forecast_practice_part2) |
| F207 | 地価はどこで上がり、駅ができると何が起きるのか？ | [F207_landprice_series_part1](articles/F207_landprice_series_part1) |
| F231 | 売上の予測は、何か月先まで役に立つのか？ | [F231_sales_forecast_horizon](articles/F231_sales_forecast_horizon) |
| F232 | 店の種類ごとの予測と全体の予測を、どうそろえるか？ | [F232_hierarchical_retail_reconciliation](articles/F232_hierarchical_retail_reconciliation) |
| F233 | 祝日・連休・天気は、売上をどれだけ動かすのか？ | [F233_calendar_weather_sales](articles/F233_calendar_weather_sales) |
| F234 | 価格を1%上げると、買われる量は何%減るのか？ | [F234_price_elasticity_practice](articles/F234_price_elasticity_practice) |
| F235 | 在庫はどれだけ持てばよいのか？ | [F235_inventory_newsvendor](articles/F235_inventory_newsvendor) |
| F237 | A/B テストを途中で見ると、何がまずいのか？ | [F237_ab_test_peeking_sequential](articles/F237_ab_test_peeking_sequential) |
| F239 | 広告費は、売上にどれだけ効いているのか？ | [F239_marketing_mix_model](articles/F239_marketing_mix_model) |
| F240 | キャンペーンの効果を、比べる相手がないときにどう測るか？ | [F240_campaign_effect_no_control](articles/F240_campaign_effect_no_control) |
| F241 | 顧客はどれくらいで離れていくのか？ | [F241_customer_churn_survival](articles/F241_customer_churn_survival) |
| F242 | 毎日の KPI の「いつもと違う」を、どう自動で知らせるか？ | [F242_kpi_anomaly_alerts](articles/F242_kpi_anomaly_alerts) |
| F243 | どの指標を見れば、売上の変化の理由が分かるのか？ | [F243_kpi_tree_decomposition](articles/F243_kpi_tree_decomposition) |
| F244 | 集計の SQL は、どう書けば間違えにくいか？ | [F244_sql_aggregation_pitfalls](articles/F244_sql_aggregation_pitfalls) |
| F245 | 1つの依頼に、1時間でどこまで答えられるか？ | [F245_one_hour_request](articles/F245_one_hour_request) |
| F246 | 分析担当として最初にやること：KPI を決める（業務の再現：架空の会社で） シリーズ③の1本目。架空の食品スーパー「サン | [F246_kpi_definitions_fictional_retail](articles/F246_kpi_definitions_fictional_retail) |
| F247 | データを集めて、使える形に整える（業務の再現：架空の会社で） シリーズ③の2本目。F246 の合成データ「サンプルマート | [F247_data_mart_fictional_retail](articles/F247_data_mart_fictional_retail) |
| F248 | 月次レポートの「型」を作る（業務の再現：架空の会社で） シリーズ③の3本目。F246 の KPI 定義 v1 と F24 | [F248_monthly_report_template_fictional_retail](articles/F248_monthly_report_template_fictional_retail) |
| F249 | ダッシュボードを作る（業務の再現：架空の会社で） シリーズ③の続き。F246 の KPI 定義 v1 と F247 の  | [F249_powerbi_dashboard_fictional_retail](articles/F249_powerbi_dashboard_fictional_retail) |
| F250 | 売上が落ちた月に、理由を説明する（業務の再現：架空の会社で） シリーズ③の5本目。F247 の mart を使い、架空の | [F250_sales_drop_explanation_fictional_retail](articles/F250_sales_drop_explanation_fictional_retail) |
| F251 | 販促の効果を測る（業務の再現：架空の会社で） シリーズ③の6本目。F247 の mart の架空の食品スーパー「サンプル | [F251_promo_effect_fictional_retail](articles/F251_promo_effect_fictional_retail) |
| F252 | 来期の予算のための需要予測（業務の再現：架空の会社で） シリーズ③の7本目。架空の食品スーパー「サンプルマート（架空）」 | [F252_budget_forecast_fictional_retail](articles/F252_budget_forecast_fictional_retail) |
| F253 | データの品質を毎月チェックする（業務の再現：架空の会社で） シリーズ③の8本目。架空の食品スーパー「サンプルマート（架空 | [F253_monthly_data_quality_checks_fictional_retail](articles/F253_monthly_data_quality_checks_fictional_retail) |
| F255 | 1年の分析業務を振り返る（業務の再現：架空の会社で） シリーズ③の10本目・最後。架空の食品スーパー「サンプルマート（架 | [F255_year_review_fictional_retail](articles/F255_year_review_fictional_retail) |
| F257 | 労働経済白書の「賃上げが広がった」は、どのデータでどこまで言えるのか？ | [F257_wage_spillover_whitepaper](articles/F257_wage_spillover_whitepaper) |
| F259 | 需要予測の外れは、在庫と欠品のどちらに効かせるべきか？ | [F259_forecast_error_inventory_cost](articles/F259_forecast_error_inventory_cost) |
| F265 | 少子化対策の「2025年の数値目標」は、決めた時点のペースで届くと読めたのか？ | [F265_policy_targets_pace](articles/F265_policy_targets_pace) |
| F266 | 「米の値段が上がった」は、どの段階で起きたのか？ | [F266_rice_price_stages](articles/F266_rice_price_stages) |
| F267 | 売上の目標を、客数と客単価の目標にどう分けるか？ | [F267_kpi_target_allocation_cvs](articles/F267_kpi_target_allocation_cvs) |
| F269 | 「価格転嫁できた企業」は、どんな企業か？ | [F269_sme_price_passthrough](articles/F269_sme_price_passthrough) |
| F270 | 「訪日客が過去最多」は、1人あたりの支出で見ても最多か？ | [F270_inbound_record_per_capita](articles/F270_inbound_record_per_capita) |
| F271 | 見られるダッシュボードと、見られないダッシュボードの違いは何か？ | [F271_dashboard_answer_cost](articles/F271_dashboard_answer_cost) |
| F273 | 観光白書の「地方への分散」は、宿泊データで見えているか？ | [F273_regional_dispersion_lodging](articles/F273_regional_dispersion_lodging) |
| F275 | 集計の SQL は、どう書けば直しやすく、直し忘れに気づけるか？ | [F275_sql_change_requests](articles/F275_sql_change_requests) |
| F281 | 食料自給率の目標と実際の差は、どこから来ているのか？ | [F281_food_self_sufficiency_target_gap](articles/F281_food_self_sufficiency_target_gap) |
| F282 | 「円安で輸出が増えた」は、数量と価格に分けるとどうか？ | [F282_yen_exports_quantity_price](articles/F282_yen_exports_quantity_price) |
| F283 | 値上げの前後で、売れ方はどう変わったか？ | [F283_price_hike_front_loading](articles/F283_price_hike_front_loading) |
| F285 | エネルギー基本計画の電力需要の見通しは、過去にどれだけ当たったか？ | [F285_power_demand_outlook_accuracy](articles/F285_power_demand_outlook_accuracy) |
| F287 | 同じ数字を、経営向けと現場向けでどう書き分けるか？ | [F287_report_two_audiences](articles/F287_report_two_audiences) |
| F292 | 南海トラフの被害想定は、人口が変わるとどう動くか？ | [F292_quake_damage_population](articles/F292_quake_damage_population) |
| F293 | 毎月の数字の「おかしい」を、どう自動で見つけるか？ | [F293_monthly_anomaly_public_stats](articles/F293_monthly_anomaly_public_stats) |
| 218 | 食品ロスの2030年度目標、家庭系は今のペースなら届く。事業系はここ3年横ばいで、届くかは読み切れない | [218_food_loss_2030](articles/218_food_loss_2030) |
| 233 | 集計の合計が会計の数字と合わないとき、SQL のどこから疑うか？ | [233_sql_reconcile_totals](articles/233_sql_reconcile_totals) |
| 243 | 縦長の統計表をレポートの形にする SQL は、CASE WHEN で書ける。ただし業態が1つ増えると、その行は黙って落ち | [243_sql_pivot_report](articles/243_sql_pivot_report) |
| 244 | 毎月のレポートは、結論の1文・要因・次に確かめることの順に、数字から自動で書ける。要因を率で選ぶと、12か月中7か月で金 | [244_monthly_report_order](articles/244_monthly_report_order) |
| 278 | KPI カードの矢印は、何と比べて付けるか？ | [278_kpi_card_comparison](articles/278_kpi_card_comparison) |
| 279 | 手作業の月次 Excel レポートを、Python でどう自動にするか？ | [279_excel_report_automation](articles/279_excel_report_automation) |
| 280 | 週次の数字を毎週メールで自動配信するとき、いつ送るか？ | [280_weekly_kpi_email](articles/280_weekly_kpi_email) |
| 295 | 集計をストアドプロシージャにまとめると、何がうれしいのか？ | [295_stored_procedure_params](articles/295_stored_procedure_params) |
| 302 | HTML だけで、配れるダッシュボードは作れるか？ | [302_single_html_dashboard](articles/302_single_html_dashboard) |
| 303 | E2E テストの考え方を、データの処理にも使えるか？ | [303_e2e_tests_for_data_pipeline](articles/303_e2e_tests_for_data_pipeline) |
| 306 | スプレッドシートの申込集計を、GAS でどう自動にするか？ | [306_gas_sheet_aggregation](articles/306_gas_sheet_aggregation) |
| 312 | SQL の NULL は、集計をどれだけ黙ってずらすのか？ | [312_sql_null_aggregation](articles/312_sql_null_aggregation) |
| 313 | 月の集計で、月末の最終日はどれだけ落ちているのか？ | [313_sql_month_end_boundary](articles/313_sql_month_end_boundary) |
| 341 | 月次の数字は、締めてから何日たてば「確定」と言えるのか？ | [341_month_close_completeness](articles/341_month_close_completeness) |
| 342 | 締めたあとに訂正されたデータで、先月のレポートの数字を再現できるか？ | [342_restate_and_reproduce_reports](articles/342_restate_and_reproduce_reports) |
| 350 | まだ報告されていない事故の件数は、報告の遅れからどこまで当てられるのか？ | [350_ibnr_count_reporting_delay](articles/350_ibnr_count_reporting_delay) |
| 390 | 年間の予算を月に割る方法で、月ごとの達成率はどれだけ変わるのか？ | [390_budget_monthly_allocation](articles/390_budget_monthly_allocation) |
| 401 | 集計用の表は、1枚の大きな表と、事実とマスタに分けた表のどちらが直しやすいか？ | [401_wide_table_vs_star_schema](articles/401_wide_table_vs_star_schema) |
| 402 | 速くするために作った集計済みの表は、元の表とどれくらいずれていくのか？ | [402_summary_table_drift](articles/402_summary_table_drift) |
| 408 | 件数の小さいセルを隠した集計表は、引き算で何セル分かってしまうのか？ | [408_cell_suppression_subtraction](articles/408_cell_suppression_subtraction) |
| 443 | 分類を付け替えたあと、過去の集計は「当時の区分」と「今の区分」でどれだけ違うのか？ | [443_reclassification_asof_vs_current](articles/443_reclassification_asof_vs_current) |
| 445 | 順番に動かすはずの集計を、順番を違えて流すと、何枚の表が古い数字のままになるのか？ | [445_pipeline_run_order_stale_tables](articles/445_pipeline_run_order_stale_tables) |
| 460 | 予測に「答えが漏れた列」が混ざると、確かめの成績はどれだけ良く見え、本番でどれだけ落ちるのか？ | [460_target_leakage_validation](articles/460_target_leakage_validation) |
| 468 | 一律に保険料を上げたとき、事故の少ない契約から先に抜けると、残った契約の損害率はどう動くのか？ | [468_rate_increase_adverse_lapse](articles/468_rate_increase_adverse_lapse) |
| 471 | 年初からの累計で見た前年比は、売上の変化に何か月遅れて気づくのか？ | [471_ytd_yoy_lag](articles/471_ytd_yoy_lag) |
| 472 | 返品を「売れた月」に戻すか「返ってきた月」で引くかで、月の売上はどれだけ変わるのか？ | [472_returns_which_month](articles/472_returns_which_month) |
| 475 | 解約率は、分母の取り方でどれだけ違って見えるのか？ | [475_churn_rate_denominator](articles/475_churn_rate_denominator) |
| 481 | 同じ売上を20日締めと月末締めで集計すると、2023〜2025年の月の数字は平均何%ずれるのか？ | [481_closing_day_20th_vs_monthend](articles/481_closing_day_20th_vs_monthend) |
| 512 | 割合を小数1桁で表示すると、前月からの増減が「0.0」や逆の向きに見える月は何か月あるのか？ | [512_rounded_display_mom_change](articles/512_rounded_display_mom_change) |
| 514 | 入庫と出庫の記録が遅れて届くと、在庫が一時的にマイナスになる日は何日あるのか？ | [514_inventory_record_delay_negative](articles/514_inventory_record_delay_negative) |
| 524 | 深夜まで営業する店で、売上を暦日で切るか「朝5時締めの営業日」で切るかで、曜日別の売上はどれだけ変わるのか？ | [524_business_day_cutoff_5am](articles/524_business_day_cutoff_5am) |
| 533 | 残業時間を15分単位で切り捨てて集計すると、1か月の時間は何%少なく出るのか？ | [533_overtime_truncation_monthly](articles/533_overtime_truncation_monthly) |
| 535 | 顧客の年齢を「登録したときの年齢」のまま集計すると、年代別の構成は何年でどれだけずれるのか？ | [535_age_at_registration_drift](articles/535_age_at_registration_drift) |
| 546 | 2つの系列のずらし幅を0〜12か月で動かして最も強い相関を選ぶと、関係がなくても相関はどれだけ高く出るのか？ | [546_lag_search_spurious_corr](articles/546_lag_search_spurious_corr) |
| 551 | 月の途中で単価が変わったとき、適用開始日を見ずに今の単価で集計すると、金額はどれだけずれるのか？ | [551_price_master_effective_date](articles/551_price_master_effective_date) |
| 571 | UTCで保存した時刻を日本時間に直さずに日付で集計すると、何件が前日に入るのか？ | [571_utc_date_aggregation](articles/571_utc_date_aggregation) |
| 574 | 部署の統廃合があったとき、過去の部署別の数字を今の組織に組み替えると、推移はどう変わるのか？ | [574_reorg_restatement](articles/574_reorg_restatement) |
| 579 | 店ごとの比率を平均するか、合計どうしで比を取るかで、全体の比率はどれだけ違うのか？ | [579_mean_of_ratios_vs_ratio_of_totals](articles/579_mean_of_ratios_vs_ratio_of_totals) |
| 581 | 締め日が20日の会社で、月の売上を暦の月で数えるか締めの期間で数えるかで、月ごとの数字はどれだけずれるのか？ | [581_closing_day_vs_calendar_month](articles/581_closing_day_vs_calendar_month) |
| 603 | 日次の前年比を「前年の同じ日」と比べるか「前年の同じ曜日」と比べるかで、どれだけ違って見えるのか？ | [603_yoy_same_date_vs_weekday](articles/603_yoy_same_date_vs_weekday) |
| 611 | 営業日の数が違う月を前年同月と比べると、前年比は何ポイント動くのか？ | [611_yoy_business_days_adjust](articles/611_yoy_business_days_adjust) |
| 613 | 安全在庫を需要のばらつきだけで決めると、届くまでの日数がばらつくとき欠品は何%になるのか？ | [613_safety_stock_leadtime_var](articles/613_safety_stock_leadtime_var) |
| 642 | 年間の目標を12等分するか、前年の月の比率で分けるかで、「達成した月」の数はどれだけ違うのか？ | [642_monthly_target_phasing](articles/642_monthly_target_phasing) |
| 661 | 新しく開いた店と閉じた店を含めたまま前年比を出すと、既存店だけの前年比とどれだけ違うのか？ | [661_existing_store_yoy](articles/661_existing_store_yoy) |
| 664 | 平均単価の前年比を、品目の構成の変化と単価の変化に分けると、それぞれどれだけになるのか？ | [664_price_mix_decomposition](articles/664_price_mix_decomposition) |
| 681 | 「有効」フラグの立った商品だけで集計すると、廃番になった商品の過去の売上はどれだけ消えるのか？ | [681_existing_flag_history](articles/681_existing_flag_history) |
| 682 | 店ごとの前年比を並べるのと、全体の伸びへの寄与度で並べるのでは、順位はどれだけ違うのか？ | [682_contribution_to_growth](articles/682_contribution_to_growth) |
| 691 | 同じ顧客の重複行から「最初」と「最新」のどちらを残すかで、属性の集計はどれだけ変わるのか？ | [691_dedup_keep_first_or_last](articles/691_dedup_keep_first_or_last) |
| 716 | 交差検証でハイパーパラメータを選び、同じ交差検証の成績を報告すると、本当の成績よりどれだけよく見えるのか？ | [716_nested_cv_optimism](articles/716_nested_cv_optimism) |
| 721 | 2つの列を区切りなしでつないでキーにすると、別の組み合わせが同じキーになる行は何件あるのか？ | [721_concat_key_collision](articles/721_concat_key_collision) |
| 731 | 「上位10%の顧客で売上の何割」を、買わなかった会員を含めて数えるか除くかで、どれだけ違うのか？ | [731_top_share_zero_customers](articles/731_top_share_zero_customers) |
| 745 | 4月始まりの年度と暦年で前年比を出すと、伸びの年はどれだけずれて見えるのか？ | [745_fiscal_vs_calendar_year](articles/745_fiscal_vs_calendar_year) |
| 751 | PIVOT の列を固定で書いておくと、あとから増えた区分の売上は何%消えるのか？ | [751_pivot_fixed_columns](articles/751_pivot_fixed_columns) |
| 752 | 先頭に BOM のついた CSV を csv モジュールで読むと、最初の列名が一致せず、何行の売上が黙って集計から落ちるのか？ | [752_csv_bom_header](articles/752_csv_bom_header) |
| 753 | 1年が53週ある年に「第N週」で前年同週比を出すと、何週の前年比が本当の伸びから外れるのか？ | [753_week53_yoy](articles/753_week53_yoy) |
| 755 | 時刻つきの日時のまま GROUP BY すると、日ごとの集計は何行に分かれてしまうのか？ | [755_group_by_datetime_not_date](articles/755_group_by_datetime_not_date) |
| 763 | 継続月数を0から数えるか1から数えるかで、継続率の表はどれだけずれて読まれるのか？ | [763_month_index_zero_one](articles/763_month_index_zero_one) |
| 764 | pandas の groupby が欠けたキーの行を黙って落とすと、合計はどれだけ減るのか？ | [764_pandas_groupby_dropna](articles/764_pandas_groupby_dropna) |
| 774 | 達成率を四捨五入してから「100%以上」を数えると、何店が「達成」に入ってしまうのか？ | [774_achievement_rounding](articles/774_achievement_rounding) |
| 781 | 数の列に文字が1つまざると、Excel のピボットの集計はどう変わり、合計はどれだけ消えるのか？ | [781_pivot_count_default](articles/781_pivot_count_default) |

</details>

<details><summary><b>作業時間・処理件数</b>（4本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F247 | データを集めて、使える形に整える（業務の再現：架空の会社で） シリーズ③の2本目。F246 の合成データ「サンプルマート | [F247_data_mart_fictional_retail](articles/F247_data_mart_fictional_retail) |
| 533 | 残業時間を15分単位で切り捨てて集計すると、1か月の時間は何%少なく出るのか？ | [533_overtime_truncation_monthly](articles/533_overtime_truncation_monthly) |
| 695 | 1人あたりの処理件数を、出勤した日数で割るか働いた時間で割るかで、担当者の順位はどれだけ入れ替わるのか？ | [695_productivity_denominator](articles/695_productivity_denominator) |
| 785 | 「1時間30分」を「1.30」と書いて合計すると、月の作業時間はどれだけ少なく出るのか？ | [785_hhmm_decimal_confusion](articles/785_hhmm_decimal_confusion) |

</details>

<details><summary><b>保険</b>（74本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F27 | 市区町村の死亡率の地図は、小さな町ほどぶれる。隣の町の情報を借りる空間ベイズ（BYM2）で描き直すと、地域差の9割以上は | [F27_disease_map_bym2](articles/F27_disease_map_bym2) |
| F49 | 平均寿命の県の差は、何歳の死亡で生まれているのか？ | [F49_life_expectancy_decomposition](articles/F49_life_expectancy_decomposition) |
| F61 | 小さい町の「ランキング1位」は、なぜ毎回入れ替わるのか？ | [F61_funnel_eb_rankings](articles/F61_funnel_eb_rankings) |
| F62 | 死亡率は10年で上がったのか、下がったのか？ | [F62_simpson_standardization](articles/F62_simpson_standardization) |
| F130 | 介護の認定率の地域差は、高齢化だけで説明できるか？ | [F130_care_certification_shrinkage](articles/F130_care_certification_shrinkage) |
| F241 | 顧客はどれくらいで離れていくのか？ | [F241_customer_churn_survival](articles/F241_customer_churn_survival) |
| F256 | 自然災害の保険金は、この30年でどれだけ大きくなったのか？ | [F256_natural_disaster_insurance_payouts](articles/F256_natural_disaster_insurance_payouts) |
| F260 | 「100年に1度の損害」は、どの分布を仮定するかでいくら変わるのか？ | [F260_loss_distribution_return_level](articles/F260_loss_distribution_return_level) |
| F264 | 自動車の事故率は、高齢化でどこまで説明できるのか？ | [F264_auto_accident_rate_aging](articles/F264_auto_accident_rate_aging) |
| F268 | 生命表が5年で変わると、年金の負担はどれだけ動くのか？ | [F268_life_table_annuity_value](articles/F268_life_table_annuity_value) |
| F272 | 火災保険料の地域差は、リスクの差にどこまで見合っているか？ | [F272_fire_insurance_rate_vs_risk](articles/F272_fire_insurance_rate_vs_risk) |
| F276 | 地震保険の付帯率は、地震のあとにどれだけ上がって戻るのか？ | [F276_earthquake_insurance_after_quakes](articles/F276_earthquake_insurance_after_quakes) |
| F280 | 医療費の伸びは、年齢・回数・日数・1日当たりのどれで決まっているのか？ | [F280_medical_cost_three_elements](articles/F280_medical_cost_three_elements) |
| F284 | 豪雨の増え方を、火災保険の料率はどこまで追いかけているのか？ | [F284_heavy_rain_vs_fire_rates](articles/F284_heavy_rain_vs_fire_rates) |
| F288 | 損害額の分布の「裾の重さ」は、データの量でどこまで見分けられるか？ | [F288_tail_heaviness_sample_size](articles/F288_tail_heaviness_sample_size) |
| F291 | 死亡率の改善は、年齢のどこで止まりつつあるのか？ | [F291_mortality_improvement_slowdown](articles/F291_mortality_improvement_slowdown) |
| F294 | 介護の費用は、2040年度にどこまで増えるのか？ | [F294_care_cost_2040_assumptions](articles/F294_care_cost_2040_assumptions) |
| F295 | リスクを分けて計ると、分散効果はどれだけ効くのか？ | [F295_solvency_diversification_copula](articles/F295_solvency_diversification_copula) |
| 314 | 契約の「在籍件数」を、SQL でどう数えるか？ | [314_sql_policy_exposure](articles/314_sql_policy_exposure) |
| 315 | 1年分の保険料を、月ごとの売上にどう分けるか？ | [315_sql_earned_premium](articles/315_sql_earned_premium) |
| 316 | 支払いの進み方から将来の支払いを見積もる方法は、どんなときに外れるのか？ | [316_chain_ladder_when_it_fails](articles/316_chain_ladder_when_it_fails) |
| 317 | 新しい年度の支払いの見積もりは、実績から延ばすのと、見込みの損害率に寄せるのと、どちらが近いか？ | [317_chain_ladder_vs_bf](articles/317_chain_ladder_vs_bf) |
| 318 | 見積もった支払備金の「幅」は、正解を何%含むのか？ | [318_reserve_interval_coverage](articles/318_reserve_interval_coverage) |
| 331 | 大きな損害だけを受け持つ「層」の見積もりは、裾の当てはめにどれだけ左右されるのか？ | [331_layer_price_tail_estimate](articles/331_layer_price_tail_estimate) |
| 332 | 免責や支払いの上限で切られたデータから、元の損害の分布は戻せるのか？ | [332_truncated_censored_loss_fit](articles/332_truncated_censored_loss_fit) |
| 333 | 1年の損害の合計の「200年に1度」は、近似でどこまで出せるのか？ | [333_aggregate_loss_tail_quantile](articles/333_aggregate_loss_tail_quantile) |
| 334 | 要因を1つずつ見た事故率の差は、まとめて推定するとどれだけ変わるのか？ | [334_one_way_vs_glm_rating](articles/334_one_way_vs_glm_rating) |
| 335 | 料率の区分を細かくすると、翌年の外れは小さくなるのか、大きくなるのか？ | [335_rating_cells_granularity](articles/335_rating_cells_granularity) |
| 336 | 平均寿命が43〜44歳だった時代に、65歳まで生きた人は、あと何年生きたのか？ | [336_life_expectancy_since_meiji](articles/336_life_expectancy_since_meiji) |
| 343 | 損害率は、事故が起きた年で数えるか、支払った年で数えるかで、どれだけ違うのか？ | [343_loss_ratio_accident_vs_calendar](articles/343_loss_ratio_accident_vs_calendar) |
| 346 | 契約が何件あれば、損害率は安定するのか？ | [346_loss_ratio_stability_by_size](articles/346_loss_ratio_stability_by_size) |
| 348 | 小さな集団の年齢ごとの死亡率は、なめらかにすると真の値にどれだけ近づくのか？ | [348_mortality_graduation_small_group](articles/348_mortality_graduation_small_group) |
| 376 | 全体では上がっているのに、どの区分でも下がっていることは、どれくらい起きるのか？ | [376_simpson_reversal_frequency](articles/376_simpson_reversal_frequency) |
| 411 | 「保険年齢」と「満年齢」では、同じ契約者の年齢区分はどれだけ変わるのか？ | [411_insurance_age_vs_attained_age](articles/411_insurance_age_vs_attained_age) |
| 413 | 途中で解約した契約に返す保険料は、日割りと短期率でどれだけ違うのか？ | [413_cancellation_refund_methods](articles/413_cancellation_refund_methods) |
| 414 | 「期首＋増加−減少＝期末」の照合は、どんな誤りを見つけ、何を見逃すのか？ | [414_roll_forward_reconciliation](articles/414_roll_forward_reconciliation) |
| 416 | 手元の資本と保険料の上乗せで、10年のうちに資本が尽きる確率はどう変わるのか？ | [416_ruin_probability_capital_loading](articles/416_ruin_probability_capital_loading) |
| 417 | 大数の法則が効かないリスクがあると、契約を増やしても損害率の振れはどこで下げ止まるのか？ | [417_undiversifiable_risk_floor](articles/417_undiversifiable_risk_floor) |
| 418 | 同じ再保険料を払うなら、割合で分ける形と大きな損害だけ渡す形で、損害率の振れはどれだけ違うのか？ | [418_quota_share_vs_excess_of_loss](articles/418_quota_share_vs_excess_of_loss) |
| 419 | 契約を代表の契約にまとめて計算すると、結果はどれだけずれるのか？ | [419_model_points_grouping_error](articles/419_model_points_grouping_error) |
| 420 | 1年より短い期間の死亡率は、仮定の置き方でどれだけ違うのか？ | [420_fractional_age_assumptions](articles/420_fractional_age_assumptions) |
| 432 | 死亡率の将来の下がり方を過去から延ばす方法は、正解の分かるデータでどれだけ当たるのか？ | [432_lee_carter_known_truth](articles/432_lee_carter_known_truth) |
| 433 | 「200年に1度」の値をシミュレーションで出すには、何回くり返せばよいのか？ | [433_simulation_runs_variance_reduction](articles/433_simulation_runs_variance_reduction) |
| 436 | いちばん多い死因は、何から何へ入れ替わったのか？ | [436_leading_causes_of_death_since_1899](articles/436_leading_causes_of_death_since_1899) |
| 456 | 料率を改定したあと、過去の保険料を「いまの料率」に直す近似は、契約ごとに計算し直した値からどれだけずれるのか？ | [456_on_level_premium_parallelogram](articles/456_on_level_premium_parallelogram) |
| 457 | 大きな損害に上限を置いてから見込みを出すと、偏りと振れはどう入れ替わるのか？ | [457_large_loss_capping_bias_variance](articles/457_large_loss_capping_bias_variance) |
| 466 | 「200年に1度の値」と「それを超えたときの平均」では、同じデータでどちらの見積もりが大きく振れるのか？ | [466_var_vs_expected_shortfall_noise](articles/466_var_vs_expected_shortfall_noise) |
| 467 | 免責金額を上げた年をまたいで平均の支払額を比べると、損害が同じでも何%上がって見えるのか？ | [467_deductible_change_apparent_severity](articles/467_deductible_change_apparent_severity) |
| 468 | 一律に保険料を上げたとき、事故の少ない契約から先に抜けると、残った契約の損害率はどう動くのか？ | [468_rate_increase_adverse_lapse](articles/468_rate_increase_adverse_lapse) |
| 476 | 損害が一律に5%大きくなると、免責を超えた分の支払いは何%増えるのか？ | [476_loss_inflation_leverage_deductible](articles/476_loss_inflation_leverage_deductible) |
| 477 | 加入のときの審査の効き目を考えずに死亡率を見積もると、どれだけずれるのか？ | [477_select_period_mortality](articles/477_select_period_mortality) |
| 486 | 損害額の分布を少ない件数で当てはめると、最尤法とモーメント法のどちらが99%点を外しやすいのか？ | [486_loss_fit_mle_vs_moments](articles/486_loss_fit_mle_vs_moments) |
| 487 | 保険料の上乗せを「標準偏差」「分散」「期待効用」で決めると、契約の大きさで上乗せ率はどれだけ食い違うのか？ | [487_risk_loading_principles](articles/487_risk_loading_principles) |
| 489 | 5歳刻みの死亡率から各歳の死亡率を作ると、65歳からの年金の現価はどれだけずれるのか？ | [489_life_table_interpolation_annuity](articles/489_life_table_interpolation_annuity) |
| 490 | 解約率の仮定が実際とずれると、保険の将来の利益の見込みはどれだけ動くのか？ | [490_lapse_assumption_profit_sensitivity](articles/490_lapse_assumption_profit_sensitivity) |
| 506 | 事故の件数と1件あたりの額が一緒に動くとき、別々に見積もった年間損害の「200年に1度」はどれだけ小さく出るのか？ | [506_freq_severity_dependence](articles/506_freq_severity_dependence) |
| 507 | 生命表の死亡率を「1年に死亡する確率」と「死亡の速さ」で取り違えると、年金の現価はどれだけずれるのか？ | [507_qx_mx_confusion_annuity](articles/507_qx_mx_confusion_annuity) |
| 508 | 同じ事故の複数の請求を別々の損害として数えると、大きな損害の層の見積もりはどれだけずれるのか？ | [508_claims_per_event_count_unit](articles/508_claims_per_event_count_unit) |
| 516 | 実績の損害率に合わせて毎年保険料を直すと、損害率は落ち着くのか、それとも波打つのか？ | [516_experience_rating_feedback_cycle](articles/516_experience_rating_feedback_cycle) |
| 517 | 保険金額の大きい契約と小さい契約が混ざると、損害率の振れは契約件数ではなく何で決まるのか？ | [517_sum_insured_mix_effective_n](articles/517_sum_insured_mix_effective_n) |
| 518 | 支払いに何年もかかる損害は、利率で割り引くと、払い方の遅さによってどれだけ小さくなるのか？ | [518_discounting_payment_delay](articles/518_discounting_payment_delay) |
| 526 | 1事故ごとの免責と1年の合計の免責では、同じ見込みの支払いでも、支払いの振れはどれだけ違うのか？ | [526_per_claim_vs_aggregate_deductible](articles/526_per_claim_vs_aggregate_deductible) |
| 528 | 5歳刻みで同じ保険料にすると、区分の上の年齢に加入が偏ったとき、損害率は何%上がるのか？ | [528_age_band_skew_loss_ratio](articles/528_age_band_skew_loss_ratio) |
| 547 | 自動車保険のような等級制度で、等級の分布が落ち着くまでに何年かかり、平均の割引率はどこに落ち着くのか？ | [547_bonus_malus_markov](articles/547_bonus_malus_markov) |
| 548 | 過去の損害を今の水準に直すトレンド率が1ポイントずれると、見込みの損害はどれだけずれるのか？ | [548_trend_rate_error](articles/548_trend_rate_error) |
| 566 | 死亡率が下がり続けると、その年の生命表の平均余命は、実際に生きる年数よりどれだけ短く出るのか？ | [566_period_vs_cohort_life_table](articles/566_period_vs_cohort_life_table) |
| 567 | 支払備金の個別見積を途中から厚く積むようにすると、発生ベースのチェインラダーはどれだけ多く見込むのか？ | [567_case_reserve_strengthening](articles/567_case_reserve_strengthening) |
| 568 | 保険金額が実際の価値より小さい契約で、比例てん補を入れると、支払いと必要な保険料はどう変わるのか？ | [568_proportional_vs_first_loss](articles/568_proportional_vs_first_loss) |
| 569 | 死亡率の実績と予定の比を、件数で見るか保険金額で見るかで、どれだけ違うのか？ | [569_ae_count_vs_amount](articles/569_ae_count_vs_amount) |
| 570 | 進展の途中で打ち切ったチェインラダーは、テールファクターを省くと最終損害をどれだけ少なく見るのか？ | [570_chain_ladder_tail_factor](articles/570_chain_ladder_tail_factor) |
| 597 | 年間の総損害を件数×金額で作るとき、件数の年ごとの揺れを無視すると、99.5%点はどれだけ小さく出るのか？ | [597_compound_poisson_vs_nb](articles/597_compound_poisson_vs_nb) |
| 600 | 過去10年の損害から分布を推定するとき、推定の誤差を入れないと、99.5%点はどれだけ小さく出るのか？ | [600_parameter_uncertainty_quantile](articles/600_parameter_uncertainty_quantile) |
| 626 | 2つの事業の損害を「独立」と置いて合わせると、合計の99.5%点はどれだけ小さく出るのか？ | [626_aggregation_independence_var](articles/626_aggregation_independence_var) |
| 627 | 相関の強さが同じでも、正規コピュラと t コピュラでは、同時に大きな損害が出る確率はどれだけ違うのか？ | [627_copula_tail_dependence](articles/627_copula_tail_dependence) |

</details>

<details><summary><b>公的統計・地域・人口</b>（300本）</summary>

| # | 問い | フォルダ |
|---|---|---|
| F01 | 最低賃金の引き上げは、雇用を減らしたのか？ | [F01_minimum_wage_did](articles/F01_minimum_wage_did) |
| F03 | 地価を決めているのは何か？ | [F03_land_price_ml](articles/F03_land_price_ml) |
| F05 | 医療費の地域差は「県」と「市町村」のどちらで決まるか？ | [F05_medical_cost_hierarchical](articles/F05_medical_cost_hierarchical) |
| F06 | 高齢化は地図の上で固まっているか？ | [F06_aging_spatial](articles/F06_aging_spatial) |
| F09 | 国会で「賃上げ」はいつから語られるようになったのか？ | [F09_diet_text](articles/F09_diet_text) |
| F10 | 人の流れで見ると、日本はいくつの「圏」に分かれるか？ | [F10_mobility_network](articles/F10_mobility_network) |
| F12 | 公的統計を毎月自動で更新するには？ | [F12_stats_pipeline](articles/F12_stats_pipeline) |
| F14 | コンパクトシティの計画を作った市町村で、中心部の人口密度は保てたのか？ | [F14_compact_city_psm_did](articles/F14_compact_city_psm_did) |
| F15 | 県境をまたぐと最低賃金が違う。隣どうしの町で雇用は違ったか？ | [F15_border_minwage](articles/F15_border_minwage) |
| F17 | 最低賃金の影響が大きかったのはどんな県か？ | [F17_minwage_causal_forest](articles/F17_minwage_causal_forest) |
| F18 | 景気は今どうなのか？ | [F18_nowcast_dfm](articles/F18_nowcast_dfm) |
| F20 | 出生率は隣の町と似るのか？ | [F20_tfr_spatial_regression](articles/F20_tfr_spatial_regression) |
| F21 | 公的統計の「いつもと違う動き」を自動で見つけられるか？ | [F21_anomaly_detection](articles/F21_anomaly_detection) |
| F22 | 明日の電力需要はどこまで当てられるか？ | [F22_power_demand_forecast](articles/F22_power_demand_forecast) |
| F23 | 救急車をどこに置けば、到着が早くなるか？ | [F23_ambulance_location](articles/F23_ambulance_location) |
| F25 | 経済白書41年分をAIの「文埋め込み」で読むと、政府の関心はどう移ったか？ | [F25_whitepaper_embeddings](articles/F25_whitepaper_embeddings) |
| F26 | 政策の効果を見つけるには、何県・何年のデータが要るのか？ | [F26_power_simulation](articles/F26_power_simulation) |
| F29 | 北陸新幹線の金沢延伸で、石川県の宿泊客はどれだけ増えたか？ | [F29_shinkansen_sdid](articles/F29_shinkansen_sdid) |
| F31 | 60歳・65歳で、働く人はどれだけ減るのか？ | [F31_retirement_rdd](articles/F31_retirement_rdd) |
| F32 | 所得の高い町と低い町で、効いている要因は同じか？ | [F32_income_quantile](articles/F32_income_quantile) |
| F33 | 人の移動は距離でどれだけ減るのか？ | [F33_migration_gravity](articles/F33_migration_gravity) |
| F34 | 同じお金で、どの市町村が多くのサービスを出しているか？ | [F34_municipal_efficiency](articles/F34_municipal_efficiency) |
| F36 | 全国と47都道府県の宿泊者数の予測を、足し算が合うようにそろえると？ | [F36_hierarchical_forecast](articles/F36_hierarchical_forecast) |
| F37 | 地価の予測に「この範囲に9割入る」を付けられるか？ | [F37_conformal_land_price](articles/F37_conformal_land_price) |
| F38 | 観光客が1兆円使うと、日本全体の生産はいくら増えるのか？ | [F38_input_output_tourism](articles/F38_input_output_tourism) |
| F39 | 物価・賃金・金利は、どれがどれを動かしているのか？ | [F39_causal_discovery_macro](articles/F39_causal_discovery_macro) |
| F40 | 所得の格差は「県の間」と「県の中」のどちらにあるか？ | [F40_inequality_decomposition](articles/F40_inequality_decomposition) |
| F43 | 金利が上がると、何か月後に何が動くのか？ | [F43_local_projections](articles/F43_local_projections) |
| F44 | 出生率のトレンドはいつ折れたのか？ | [F44_structural_breaks](articles/F44_structural_breaks) |
| F45 | 将来人口の推計は、自分で再現できるか？ | [F45_population_projection](articles/F45_population_projection) |
| F46 | 雇用が増えた町に、人は集まったのか？ | [F46_bartik_iv](articles/F46_bartik_iv) |
| F49 | 平均寿命の県の差は、何歳の死亡で生まれているのか？ | [F49_life_expectancy_decomposition](articles/F49_life_expectancy_decomposition) |
| F51 | 保育所の整備は、出生率に「女性の就業」を通じて効いたのか？ | [F51_childcare_mediation](articles/F51_childcare_mediation) |
| F52 | インフルエンザは、どの県からどの県へ広がるのか？ | [F52_influenza_spread](articles/F52_influenza_spread) |
| F54 | 働く女性の賃金は、働いている人だけを見ると高く見えるのか？ | [F54_heckman_women_wage](articles/F54_heckman_women_wage) |
| F55 | ベイズで出生数を予測すると、予測の幅はどう変わるのか？ | [F55_births_bsts](articles/F55_births_bsts) |
| F57 | インフルエンザの流行は、SIRモデルで再現できるか？ | [F57_flu_sir](articles/F57_flu_sir) |
| F58 | 合計特殊出生率は、年齢のどこで下がったのか？ | [F58_tfr_age_tempo](articles/F58_tfr_age_tempo) |
| F59 | 学力調査の県の順位は、毎年どれくらい入れ替わるのか？ | [F59_test_rank_stability](articles/F59_test_rank_stability) |
| F60 | 去年いちばん悪かった県は、今年よくなるのか？ | [F60_regression_to_mean](articles/F60_regression_to_mean) |
| F62 | 死亡率は10年で上がったのか、下がったのか？ | [F62_simpson_standardization](articles/F62_simpson_standardization) |
| F63 | 「前年比」と「前月比」、景気の変わり目を早く見つけられるのはどちらか？ | [F63_yoy_vs_mom](articles/F63_yoy_vs_mom) |
| F65 | 医師が多い県ほど、平均寿命は長いのか？ | [F65_doctors_life_dag](articles/F65_doctors_life_dag) |
| F66 | 統計の推計方法が変わると、数字はどれだけ動くのか？ | [F66_series_breaks](articles/F66_series_breaks) |
| F67 | 気温が1℃上がると、電気の使用量は何%増えるか？ | [F67_temp_power_gam](articles/F67_temp_power_gam) |
| F69 | 統計表の「-」は0なのか、欠測なのか？ | [F69_data_quality](articles/F69_data_quality) |
| F71 | 都道府県の所得の差は、縮まっているのか？ | [F71_income_convergence](articles/F71_income_convergence) |
| F72 | 家計は、物価が何%上がると思っているのか？ | [F72_inflation_expectations_cp](articles/F72_inflation_expectations_cp) |
| F74 | 観測点のない場所の気温は、どこまで当てられるか？ | [F74_temperature_kriging](articles/F74_temperature_kriging) |
| F75 | 地価の地図を「なめらかに」描くと、どこまで当たるか？ | [F75_gp_land_price](articles/F75_gp_land_price) |
| F76 | 所得が高い県は、ずっと高いままか？ | [F76_income_mobility_markov](articles/F76_income_mobility_markov) |
| F77 | 今の人の流れが続くと、都道府県の人口の分布は最後にどうなるか？ | [F77_migration_markov](articles/F77_migration_markov) |
| F78 | 産業がばらけている町は、不景気に強いのか？ | [F78_industry_portfolio](articles/F78_industry_portfolio) |
| F80 | 47都道府県×100指標を比べると、「有意な差」はいくつ偶然か？ | [F80_multiple_comparisons](articles/F80_multiple_comparisons) |
| F81 | 通勤で町の外へ出る人が多いほど、子どもは少ないのか？ | [F81_commute_gps](articles/F81_commute_gps) |
| F84 | 男女の賃金差のうち、「説明できる部分」はどれだけか？ | [F84_oaxaca_gender_wage](articles/F84_oaxaca_gender_wage) |
| F87 | 結婚が減ったのは「時代」のせいか「世代」のせいか？ | [F87_marriage_apc](articles/F87_marriage_apc) |
| F88 | 携帯料金の値下げは、物価をどれだけ下げたか？ | [F88_mobile_fee_rdit](articles/F88_mobile_fee_rdit) |
| F89 | 最低賃金の効果、これまでの推定をまとめると？ | [F89_minwage_meta](articles/F89_minwage_meta) |
| F90 | 月次の統計で、四半期のGDPをどこまで当てられるか？ | [F90_midas_nowcast](articles/F90_midas_nowcast) |
| F91 | 機械学習の「何が効いているか」は、手法で答えが変わるか？ | [F91_interpretation_methods](articles/F91_interpretation_methods) |
| F92 | 電力需要の「上振れ」はどこまで見込めばよいか？ | [F92_power_quantile_forecast](articles/F92_power_quantile_forecast) |
| F93 | PDF の統計表を機械で読むと、どれくらい間違えるか？ | [F93_pdf_table_extraction](articles/F93_pdf_table_extraction) |
| F94 | 市町村合併をどう扱うかで、20年の推移の分析は変わるか？ | [F94_municipal_merger_panel](articles/F94_municipal_merger_panel) |
| F95 | 新幹線の効果は、隣の県にもこぼれたのか？ | [F95_shinkansen_spillover](articles/F95_shinkansen_spillover) |
| F96 | e-Statの数万の統計表から、欲しい表をすぐ探せるか？ | [F96_estat_semantic_search](articles/F96_estat_semantic_search) |
| F98 | 大きな災害のあと、宿泊客はどれくらいで戻るのか？ | [F98_disaster_lodging_recovery](articles/F98_disaster_lodging_recovery) |
| F100 | 同じ問いを5つの手法で分析すると、答えはそろうのか？ | [F100_five_methods_one_question](articles/F100_five_methods_one_question) |
| F101 | 物価と賃金は、長い目で見ると一緒に動いているのか？ | [F101_price_wage_cointegration](articles/F101_price_wage_cointegration) |
| F102 | 円安が物価に効くのは、円安が大きいときだけか？ | [F102_fx_threshold_passthrough](articles/F102_fx_threshold_passthrough) |
| F103 | 電力需要や物価の「長い記憶」は、どれくらい続くか？ | [F103_long_memory](articles/F103_long_memory) |
| F104 | 気温と電力需要の関係を、ガウス過程の時系列で読むと？ | [F104_gp_power_temperature](articles/F104_gp_power_temperature) |
| F106 | 同じ県の会社は、同じように閉鎖しやすいのか？ | [F106_shared_frailty](articles/F106_shared_frailty) |
| F107 | 市区町村のつながり（隣接・通勤）を使うと、予測は良くなるか？ | [F107_gcn_municipal](articles/F107_gcn_municipal) |
| F108 | 予測モデルは、地域によって外れ方が偏っていないか？ | [F108_prediction_fairness](articles/F108_prediction_fairness) |
| F109 | どのデータを集めれば、予測は早く良くなるか？ | [F109_active_learning_land_price](articles/F109_active_learning_land_price) |
| F110 | 予測モデルの設定は、どう選ぶのが効率的か？ | [F110_hyperparam_bayesopt](articles/F110_hyperparam_bayesopt) |
| F111 | 人口が減る町で、店はいつ消えるのか？ | [F111_shop_abm](articles/F111_shop_abm) |
| F112 | 救急隊が全部出払う確率は、隊を1つ増やすとどれだけ下がるか？ | [F112_ambulance_queueing](articles/F112_ambulance_queueing) |
| F113 | 物価指数の作り方で、インフレ率はどれだけ変わるか？ | [F113_price_index_formulas](articles/F113_price_index_formulas) |
| F114 | 東京の1万円と地方の1万円は、同じ価値か？ | [F114_regional_purchasing_power](articles/F114_regional_purchasing_power) |
| F115 | 統計の公表値から、元のばらつきをどこまで復元できるか？ | [F115_grouped_income_distribution](articles/F115_grouped_income_distribution) |
| F116 | 47都道府県の指標を1つの「暮らしやすさ」にまとめると、重みでどれだけ順位が変わるか？ | [F116_composite_index_weights](articles/F116_composite_index_weights) |
| F117 | 調査の回答率が下がると、結果はどれだけずれるか？ | [F117_nonresponse_weighting](articles/F117_nonresponse_weighting) |
| F118 | 「保育所と出生率」に、これまでの記事はどう答えたか？ | [F118_childcare_fertility_synthesis](articles/F118_childcare_fertility_synthesis) |
| F119 | 予測した記事は、その後どれだけ当たったか？ | [F119_forecast_scorecard](articles/F119_forecast_scorecard) |
| F120 | 2025年国勢調査で、記事の結論は変わったか？ | [F120_census2025_update](articles/F120_census2025_update) |
| F121 | 「最低賃金と雇用」に、4本の記事はどう答えたか？ | [F121_minwage_methods_review](articles/F121_minwage_methods_review) |
| F123 | 「場所で分けて確かめる」と、記事の結論は変わったか？ | [F123_spatial_block_cv_review](articles/F123_spatial_block_cv_review) |
| F124 | 同じデータを何本の記事で使い回したか？ | [F124_data_lineage_network](articles/F124_data_lineage_network) |
| F126 | 暑い日の何日後まで、熱中症の搬送は増えるのか？ | [F126_heatstroke_dlnm](articles/F126_heatstroke_dlnm) |
| F127 | 空き家は、人口が減った分だけ増えたのか？ | [F127_vacant_houses_decomposition](articles/F127_vacant_houses_decomposition) |
| F128 | 家賃は、都心からの距離でどれだけ下がるのか？ | [F128_rent_distance](articles/F128_rent_distance) |
| F129 | 薬の処方量の地域差は、年齢構成でどこまで説明できるか？ | [F129_prescription_age_adjust](articles/F129_prescription_age_adjust) |
| F130 | 介護の認定率の地域差は、高齢化だけで説明できるか？ | [F130_care_certification_shrinkage](articles/F130_care_certification_shrinkage) |
| F131 | 大学に進む人が増えると、地元に残る若者は減るのか？ | [F131_univ_youth_migration](articles/F131_univ_youth_migration) |
| F132 | 農家は「やめる」のか「大きくなる」のか？ | [F132_farm_size_transitions](articles/F132_farm_size_transitions) |
| F133 | 輸出先は、距離と経済規模でどこまで決まるのか？ | [F133_export_gravity](articles/F133_export_gravity) |
| F134 | 再生可能エネルギーの導入は、どこで速く進んだのか？ | [F134_renewable_diffusion](articles/F134_renewable_diffusion) |
| F135 | 雨の日は、小売の売上をどれだけ動かすのか？ | [F135_rain_retail](articles/F135_rain_retail) |
| F136 | 鉄道の利用は、コロナ前にどこまで戻ったのか？ | [F136_rail_covid_recovery](articles/F136_rail_covid_recovery) |
| F138 | テレワークは、どの産業・地域に残ったのか？ | [F138_telework_decomposition](articles/F138_telework_decomposition) |
| F139 | 副業をしている人は、どんな働き方の人か？ | [F139_side_job_loglinear](articles/F139_side_job_loglinear) |
| F140 | 外国人の住民は、どの地域に、どの速さで増えたのか？ | [F140_foreign_residents_concentration](articles/F140_foreign_residents_concentration) |
| F141 | 特許の出願は、どの分野で地方に広がったのか？ | [F141_ip_regional_concentration](articles/F141_ip_regional_concentration) |
| F142 | 森林は、「切れる木」がどれだけ増えたのか？ | [F142_forest_age_harvest](articles/F142_forest_age_harvest) |
| F143 | 漁獲量の減り方は、魚の種類でどう違うのか？ | [F143_fish_catch_decline](articles/F143_fish_catch_decline) |
| F144 | 水道料金の差は、人口密度と水源でどこまで説明できるか？ | [F144_water_tariff_density](articles/F144_water_tariff_density) |
| F145 | ごみの量は、有料化のあとに減ったのか？ | [F145_waste_fee_did](articles/F145_waste_fee_did) |
| F146 | 統計の秘匿をノイズで置き換えると、分析の答えはどれだけ変わるか？ | [F146_dp_noise_vs_suppression](articles/F146_dp_noise_vs_suppression) |
| F147 | 集計表から「それらしい個票」を作ると、元の分析を再現できるか？ | [F147_synthetic_from_tables](articles/F147_synthetic_from_tables) |
| F149 | 生存分析を機械学習でやると、何が良くなるのか？ | [F149_ml_survival](articles/F149_ml_survival) |
| F150 | 季節のパターンそのものは、年々変わっているのか？ | [F150_dynamic_seasonality](articles/F150_dynamic_seasonality) |
| F151 | 47都道府県の求人倍率の「同じ動き」は、いくつに分けられるか？ | [F151_pref_hierarchical_dfm](articles/F151_pref_hierarchical_dfm) |
| F152 | 統計の速報は、確報でどれだけ直されるのか？ | [F152_revision_news_noise](articles/F152_revision_news_noise) |
| F153 | 平均でなく「分布」で比べると、地域の差は何に見えるか？ | [F153_distribution_regional](articles/F153_distribution_regional) |
| F154 | 推定の「不確かさ」は、図の形で何が読み取れるかが変わるのか？ | [F154_uncertainty_viz](articles/F154_uncertainty_viz) |
| F155 | 分析の手順を変えると、答えはどこまで変わるか？ | [F155_multiverse](articles/F155_multiverse) |
| F156 | 最低賃金の効果は、地域の「賃金の低さ」で違うのか？ | [F156_minwage_bite_heterogeneity](articles/F156_minwage_bite_heterogeneity) |
| F157 | 電力需要の予測を、1年通して運用したらどうなるか？ | [F157_power_forecast_operation](articles/F157_power_forecast_operation) |
| F158 | 地価の予測モデルは、毎年作り直す必要があるのか？ | [F158_land_price_update](articles/F158_land_price_update) |
| F159 | 出生数の予測を、毎月の速報で更新すると当たり方は変わるか？ | [F159_births_nowcast](articles/F159_births_nowcast) |
| F160 | 人口の将来推計を、自分で作るとどこまで合うか？ | [F160_cohort_projection_backtest](articles/F160_cohort_projection_backtest) |
| F161 | 同じデータで記事を書き直すと、結論はどれだけ変わるか？ | [F161_rewrite_old_articles](articles/F161_rewrite_old_articles) |
| F162 | 公的データは「API で取れる」のか？ | [F162_data_access_map](articles/F162_data_access_map) |
| F166 | 公的統計の数字は、ベンフォードの法則に従っているか？ | [F166_benford_public_stats](articles/F166_benford_public_stats) |
| F167 | 「100年に1度の大雨」は、本当に100年に1度なのか？ | [F167_return_period_heavy_rain](articles/F167_return_period_heavy_rain) |
| F168 | 猛暑日の数は、どこまで増えたと言えるか？ | [F168_extreme_heat_trend](articles/F168_extreme_heat_trend) |
| F170 | 産業の構成比を比べるとき、割合のまま回帰してよいか？ | [F170_compositional_industry_shares](articles/F170_compositional_industry_shares) |
| F171 | 人口ピラミッドの「形」は、いくつの型に分かれるか？ | [F171_pyramid_shape_fda](articles/F171_pyramid_shape_fda) |
| F172 | 生まれる日・亡くなる日は、曜日と季節でどう偏るか？ | [F172_birth_death_calendar](articles/F172_birth_death_calendar) |
| F173 | 2つの年の所得分布は、どれだけ「動いた」のか？ | [F173_income_distribution_wasserstein](articles/F173_income_distribution_wasserstein) |
| F175 | 予測モデルの精度は、どの特徴量の「おかげ」なのか？ | [F175_r2_shapley_decomposition](articles/F175_r2_shapley_decomposition) |
| F176 | 白書の文章は、年々読みやすくなったのか？ | [F176_whitepaper_readability](articles/F176_whitepaper_readability) |
| F177 | 「差がある」は、並べ替えで確かめるとどうなるか？ | [F177_permutation_tests](articles/F177_permutation_tests) |
| F178 | 回帰の外れ値は、どの点がどれだけ結論を動かしているか？ | [F178_regression_influence](articles/F178_regression_influence) |
| F179 | 欠測を埋める方法で、答えはどれだけ変わるか？ | [F179_imputation_by_estimand](articles/F179_imputation_by_estimand) |
| F180 | 2つの統計の数字は、本当に同じものを測っているか？ | [F180_measurement_agreement](articles/F180_measurement_agreement) |
| F181 | 家が建つ数は、金利と人口のどちらで決まるのか？ | [F181_housing_starts_rates_population](articles/F181_housing_starts_rates_population) |
| F182 | 中古住宅は、新築の何年分の価格差で売られているか？ | [F182_condo_depreciation_curve](articles/F182_condo_depreciation_curve) |
| F183 | 車を持つ世帯は、どこで減りはじめたのか？ | [F183_car_ownership_change_points](articles/F183_car_ownership_change_points) |
| F184 | 空の便は、新幹線の開業でどれだけ減ったのか？ | [F184_air_shinkansen_did](articles/F184_air_shinkansen_did) |
| F185 | 宅配便の個数は、どこまで通販で説明できるのか？ | [F185_parcels_online_shopping](articles/F185_parcels_online_shopping) |
| F186 | 電気料金の値上がりは、家計のどこに効いたのか？ | [F186_electricity_bill_household_burden](articles/F186_electricity_bill_household_burden) |
| F187 | 子どもの身長の伸びは、いつ止まったのか？ | [F187_height_plateau_changepoint](articles/F187_height_plateau_changepoint) |
| F188 | 労働災害は、どの産業で減り、どこで減らなかったのか？ | [F188_occupational_injury_by_industry](articles/F188_occupational_injury_by_industry) |
| F189 | 日本人の1日は、20年でどう変わったのか？ | [F189_time_use_composition](articles/F189_time_use_composition) |
| F190 | 暑い夏と寒い冬に、亡くなる人はどれだけ増えるのか？ | [F190_excess_deaths_temperature](articles/F190_excess_deaths_temperature) |
| F191 | お金の量を増やすと、貸出は増えたのか？ | [F191_money_base_lending](articles/F191_money_base_lending) |
| F194 | 博物館・美術館の入館者は、コロナ前に戻ったのか？ | [F194_museum_covid_recovery](articles/F194_museum_covid_recovery) |
| F195 | 夜の明かりで、地域の経済活動はどこまで分かるか？ | [F195_night_lights_gdp](articles/F195_night_lights_gdp) |
| F196 | 標本調査で、層に分けるとどれだけ精度が上がるのか？ | [F196_stratified_sampling_allocation](articles/F196_stratified_sampling_allocation) |
| F197 | 地区をまとめて選ぶと、精度はどれだけ落ちるのか？ | [F197_cluster_sampling_deff](articles/F197_cluster_sampling_deff) |
| F198 | 調査は、何人に聞けば足りるのか？ | [F198_sample_size_planning](articles/F198_sample_size_planning) |
| F200 | 200本の看板記事で使ったデータと手法は、どうつながっているか？ | [F200_method_data_network](articles/F200_method_data_network) |
| F201 | 最低賃金は誰に届き、雇用をどれだけ動かしたのか？ | [F201_minimum_wage_series_part1](articles/F201_minimum_wage_series_part1) |
| F202 | 最低賃金は「年収の壁」とどう重なり、全国一律にしたら何が起きるのか？ | [F202_minimum_wage_series_part2](articles/F202_minimum_wage_series_part2) |
| F203 | 出生率が下がったのは、結婚が減ったからか、夫婦の子どもが減ったからか？ | [F203_births_marriage_series_part1](articles/F203_births_marriage_series_part1) |
| F204 | 出生の支援策は、結婚・第1子・第2子のどこに効いたのか？ | [F204_births_marriage_series_part2](articles/F204_births_marriage_series_part2) |
| F206 | 予測は、エリアと合計をどうそろえ、どう見せ、1年回すと何が起きるのか？ | [F206_power_forecast_practice_part2](articles/F206_power_forecast_practice_part2) |
| F207 | 地価はどこで上がり、駅ができると何が起きるのか？ | [F207_landprice_series_part1](articles/F207_landprice_series_part1) |
| F208 | マンションの値段は地価とどう動き、地価の予測はどこで外れ続けるのか？ | [F208_landprice_series_part2](articles/F208_landprice_series_part2) |
| F209 | この5年の値上がりは、どの品目から来て、誰に重く、家計は何を減らしたのか？ | [F209_prices_household_series_part1](articles/F209_prices_household_series_part1) |
| F210 | 円安は品目の値段にどれだけ時間をかけて届き、物価の見通しは家計と企業でどれだけ違うのか？ | [F210_prices_household_series_part2](articles/F210_prices_household_series_part2) |
| F231 | 売上の予測は、何か月先まで役に立つのか？ | [F231_sales_forecast_horizon](articles/F231_sales_forecast_horizon) |
| F232 | 店の種類ごとの予測と全体の予測を、どうそろえるか？ | [F232_hierarchical_retail_reconciliation](articles/F232_hierarchical_retail_reconciliation) |
| F233 | 祝日・連休・天気は、売上をどれだけ動かすのか？ | [F233_calendar_weather_sales](articles/F233_calendar_weather_sales) |
| F234 | 価格を1%上げると、買われる量は何%減るのか？ | [F234_price_elasticity_practice](articles/F234_price_elasticity_practice) |
| F235 | 在庫はどれだけ持てばよいのか？ | [F235_inventory_newsvendor](articles/F235_inventory_newsvendor) |
| F238 | 前の期間のデータを使うと、テストはどれだけ早く終わるか？ | [F238_ab_test_cuped](articles/F238_ab_test_cuped) |
| F239 | 広告費は、売上にどれだけ効いているのか？ | [F239_marketing_mix_model](articles/F239_marketing_mix_model) |
| F240 | キャンペーンの効果を、比べる相手がないときにどう測るか？ | [F240_campaign_effect_no_control](articles/F240_campaign_effect_no_control) |
| F242 | 毎日の KPI の「いつもと違う」を、どう自動で知らせるか？ | [F242_kpi_anomaly_alerts](articles/F242_kpi_anomaly_alerts) |
| F243 | どの指標を見れば、売上の変化の理由が分かるのか？ | [F243_kpi_tree_decomposition](articles/F243_kpi_tree_decomposition) |
| F244 | 集計の SQL は、どう書けば間違えにくいか？ | [F244_sql_aggregation_pitfalls](articles/F244_sql_aggregation_pitfalls) |
| F245 | 1つの依頼に、1時間でどこまで答えられるか？ | [F245_one_hour_request](articles/F245_one_hour_request) |
| F246 | 分析担当として最初にやること：KPI を決める（業務の再現：架空の会社で） シリーズ③の1本目。架空の食品スーパー「サン | [F246_kpi_definitions_fictional_retail](articles/F246_kpi_definitions_fictional_retail) |
| F248 | 月次レポートの「型」を作る（業務の再現：架空の会社で） シリーズ③の3本目。F246 の KPI 定義 v1 と F24 | [F248_monthly_report_template_fictional_retail](articles/F248_monthly_report_template_fictional_retail) |
| F252 | 来期の予算のための需要予測（業務の再現：架空の会社で） シリーズ③の7本目。架空の食品スーパー「サンプルマート（架空）」 | [F252_budget_forecast_fictional_retail](articles/F252_budget_forecast_fictional_retail) |
| F256 | 自然災害の保険金は、この30年でどれだけ大きくなったのか？ | [F256_natural_disaster_insurance_payouts](articles/F256_natural_disaster_insurance_payouts) |
| F257 | 労働経済白書の「賃上げが広がった」は、どのデータでどこまで言えるのか？ | [F257_wage_spillover_whitepaper](articles/F257_wage_spillover_whitepaper) |
| F258 | 「実質賃金○か月連続マイナス」は、どの物価で割るかで変わるのか？ | [F258_real_wage_deflator_streak](articles/F258_real_wage_deflator_streak) |
| F259 | 需要予測の外れは、在庫と欠品のどちらに効かせるべきか？ | [F259_forecast_error_inventory_cost](articles/F259_forecast_error_inventory_cost) |
| F261 | 潜在成長率は、計算の仕方でどれだけ変わるのか？ | [F261_potential_growth_methods](articles/F261_potential_growth_methods) |
| F262 | 「出生数が過去最少」は、女性の人口の減少でどこまで説明できるか？ | [F262_births_record_low_decomposition](articles/F262_births_record_low_decomposition) |
| F265 | 少子化対策の「2025年の数値目標」は、決めた時点のペースで届くと読めたのか？ | [F265_policy_targets_pace](articles/F265_policy_targets_pace) |
| F266 | 「米の値段が上がった」は、どの段階で起きたのか？ | [F266_rice_price_stages](articles/F266_rice_price_stages) |
| F267 | 売上の目標を、客数と客単価の目標にどう分けるか？ | [F267_kpi_target_allocation_cvs](articles/F267_kpi_target_allocation_cvs) |
| F268 | 生命表が5年で変わると、年金の負担はどれだけ動くのか？ | [F268_life_table_annuity_value](articles/F268_life_table_annuity_value) |
| F269 | 「価格転嫁できた企業」は、どんな企業か？ | [F269_sme_price_passthrough](articles/F269_sme_price_passthrough) |
| F270 | 「訪日客が過去最多」は、1人あたりの支出で見ても最多か？ | [F270_inbound_record_per_capita](articles/F270_inbound_record_per_capita) |
| F271 | 見られるダッシュボードと、見られないダッシュボードの違いは何か？ | [F271_dashboard_answer_cost](articles/F271_dashboard_answer_cost) |
| F272 | 火災保険料の地域差は、リスクの差にどこまで見合っているか？ | [F272_fire_insurance_rate_vs_risk](articles/F272_fire_insurance_rate_vs_risk) |
| F273 | 観光白書の「地方への分散」は、宿泊データで見えているか？ | [F273_regional_dispersion_lodging](articles/F273_regional_dispersion_lodging) |
| F276 | 地震保険の付帯率は、地震のあとにどれだけ上がって戻るのか？ | [F276_earthquake_insurance_after_quakes](articles/F276_earthquake_insurance_after_quakes) |
| F277 | 最低賃金の審議会資料にある指標で、上げ幅はどこまで説明できるか？ | [F277_minimum_wage_council_indicators](articles/F277_minimum_wage_council_indicators) |
| F278 | 「空き家が過去最多」は、住宅の数が増えた分を除くとどうか？ | [F278_vacant_record_stock_vs_rate](articles/F278_vacant_record_stock_vs_rate) |
| F280 | 医療費の伸びは、年齢・回数・日数・1日当たりのどれで決まっているのか？ | [F280_medical_cost_three_elements](articles/F280_medical_cost_three_elements) |
| F281 | 食料自給率の目標と実際の差は、どこから来ているのか？ | [F281_food_self_sufficiency_target_gap](articles/F281_food_self_sufficiency_target_gap) |
| F282 | 「円安で輸出が増えた」は、数量と価格に分けるとどうか？ | [F282_yen_exports_quantity_price](articles/F282_yen_exports_quantity_price) |
| F283 | 値上げの前後で、売れ方はどう変わったか？ | [F283_price_hike_front_loading](articles/F283_price_hike_front_loading) |
| F284 | 豪雨の増え方を、火災保険の料率はどこまで追いかけているのか？ | [F284_heavy_rain_vs_fire_rates](articles/F284_heavy_rain_vs_fire_rates) |
| F285 | エネルギー基本計画の電力需要の見通しは、過去にどれだけ当たったか？ | [F285_power_demand_outlook_accuracy](articles/F285_power_demand_outlook_accuracy) |
| F286 | 「物価高で節約」は家計調査のどこに表れているか？ | [F286_household_saving_items](articles/F286_household_saving_items) |
| F289 | 情報通信白書のデジタル化の指標は、生産性と結びついているか？ | [F289_ict_capital_productivity](articles/F289_ict_capital_productivity) |
| F290 | アンケートの回答の偏りは、重み付けでどこまで直せるか？ | [F290_survey_weighting_limits](articles/F290_survey_weighting_limits) |
| F291 | 死亡率の改善は、年齢のどこで止まりつつあるのか？ | [F291_mortality_improvement_slowdown](articles/F291_mortality_improvement_slowdown) |
| F292 | 南海トラフの被害想定は、人口が変わるとどう動くか？ | [F292_quake_damage_population](articles/F292_quake_damage_population) |
| F293 | 毎月の数字の「おかしい」を、どう自動で見つけるか？ | [F293_monthly_anomaly_public_stats](articles/F293_monthly_anomaly_public_stats) |
| F294 | 介護の費用は、2040年度にどこまで増えるのか？ | [F294_care_cost_2040_assumptions](articles/F294_care_cost_2040_assumptions) |
| 016 | 人口あたりの医師が多いのは、どんな市区町村か？ | [016_doctors](articles/016_doctors) |
| 022 | 保育所を増やした県で、出生率は上がったか？ | [022_nursery_birthrate_fe](articles/022_nursery_birthrate_fe) |
| 023 | スマホでゲームや音楽を楽しむ人が多いのは、どの県か？ | [023_games_music_aging](articles/023_games_music_aging) |
| 025 | 外国人の宿泊はコロナ前に戻ったか？ | [025_inbound_recovery](articles/025_inbound_recovery) |
| 026 | 人が転入してくる年に、その県の地価は上がるか？ | [026_migration_landprice_fe](articles/026_migration_landprice_fe) |
| 028 | 動画サイトの利用率、都道府県の差は「誤差」なのか？ | [028_video_usage_funnel](articles/028_video_usage_funnel) |
| 030 | 通勤時間が長い県は、何の時間を削っているか？ | [030_commute_sleep](articles/030_commute_sleep) |
| 032 | 人口が2倍の街には、飲食店も2倍あるか？ | [032_scaling_law](articles/032_scaling_law) |
| 033 | 高校卒業後の進学率、県の差は縮まっているか？ | [033_university_convergence](articles/033_university_convergence) |
| 034 | テレワークをしたことがある人は6年で4倍に。でも年収・性別・住む県で大きな差（通信利用動向調査） | [034_telework](articles/034_telework) |
| 035 | 円安は、どれくらい物価を上げるのか？ | [035_yen_prices_var](articles/035_yen_prices_var) |
| 041 | 今の地価は、バブルのピークの何%か？ | [041_landprice_bubble](articles/041_landprice_bubble) |
| 042 | この10年で地価が上がった場所・下がった場所：全国2万地点で見ると、同じ県の中でも「高い所ほど上がる」二極化だった | [042_landprice_polarization](articles/042_landprice_polarization) |
| 043 | 2050年に人口が半分未満になる市町村は341。将来推計を「出生・死亡」と「人の移動」に分けてみた | [043_population_2050](articles/043_population_2050) |
| 044 | 2050年の人口推計は何で決まっているのか？ | [044_population_rf](articles/044_population_rf) |
| 045 | 50代前半の月給は20代前半の何倍？ | [045_wage_curve](articles/045_wage_curve) |
| 046 | 都道府県の年収差は「職種の違い」から来ているのか？ | [046_wage_shiftshare](articles/046_wage_shiftshare) |
| 051 | 家計の株は「売り越し」なのに400兆円増えた。資金循環統計で、買った分と値上がり分を分けてみた | [051_household_assets](articles/051_household_assets) |
| 055 | 日本の気温の「最高記録」は、最近30年で5回。気温が変わらなければ0.27回のはずだった | [055_temperature_records](articles/055_temperature_records) |
| 056 | 1時間に100mm以上の雨は、40年で2倍に。強い雨ほど速く増えていた | [056_heavy_rain](articles/056_heavy_rain) |
| 079 | 都道府県をまたぐ引っ越しは1971年がピークで、今はその半分。それでも東京圏への転入超過は70年間ほぼ毎年続いていた | [079_migration_tokyo](articles/079_migration_tokyo) |
| 082 | 在留外国人が人口の1割以上の市区町村は31。技能実習・特定技能は地方に、留学は東京に多く住んでいた | [082_foreign_residents_where](articles/082_foreign_residents_where) |
| 087 | 実質賃金は1997年から18%下がった。でも1時間当たりでは3%減。物価と同じくらい「働く時間」が効いていた | [087_real_wage](articles/087_real_wage) |
| 090 | 都道府県の求人倍率の差は50年で縮んだが、2019年から止まった。東京都は働く場所で数えると42位 | [090_job_openings_pref](articles/090_job_openings_pref) |
| 095 | 就業者は13年で550万人増えた。増えたのは女性と65歳以上で、人口が減る分を「働く人の割合」が912万人押し上げた | [095_employment_growth](articles/095_employment_growth) |
| 108 | 宿泊者数の回復、日本人は29都道府県でまだ2019年以下。外国人は1.6倍でも、京都・東北は日本人が戻らない | [108_accommodation_recovery](articles/108_accommodation_recovery) |
| 118 | 生活保護の申請は2020年2月を底に増加。2020年4月は前年より25%多く、都道府県の差は少しずつ縮まった | [118_public_assistance_applications](articles/118_public_assistance_applications) |
| 125 | 昼夜間人口比率1位は千代田区の1,355。でも30年でほぼ半分に下がり、住む人が増えた | [125_daytime_population](articles/125_daytime_population) |
| 127 | 物価が高い県は13年ずっと東京都。ただ家賃を除くと、2023年から北海道が1位になった | [127_regional_prices](articles/127_regional_prices) |
| 128 | ピアノは静岡県が100%、眼鏡枠は福井県が92%。1県に生産が集中する製造品は全体の1割 | [128_product_concentration](articles/128_product_concentration) |
| 132 | 高齢者1人あたりの介護給付費は全国31.2万円。大阪府37.6万円、栃木県26.4万円で、差の3分の1は年齢構成で説明で | [132_ltc_benefits](articles/132_ltc_benefits) |
| 140 | 人口ピラミッドの裾がいちばん広かったのは1953年まで。1981年から0〜4歳は40〜44歳より少なくなった | [140_population_pyramid](articles/140_population_pyramid) |
| 151 | 農業経営体は5年で22%減、石川県は36%減。経営主のいちばん多い年齢は70〜74歳になった | [151_farm_decline](articles/151_farm_decline) |
| 154 | 最低賃金の地域差は2014年度をピークに縮まった。最高÷最低は1.31倍から1.18倍に、それでも差額は195円ある | [154_minimum_wage_gap](articles/154_minimum_wage_gap) |
| 161 | 特定健診の受診率は健保組合83%、市町村国保38%。15年で差は29ポイントから45ポイントに広がっていた | [161_health_checkup_rate](articles/161_health_checkup_rate) |
| 165 | 人口あたりの看護師は高知が最多で埼玉の2.1倍。上位10県はすべて中国・四国・九州だった | [165_nurses_by_pref](articles/165_nurses_by_pref) |
| 177 | 入院する人の割合の県差は、年齢をそろえても2.2倍残る。上位12県のうち10県が九州・四国・山口だった | [177_treatment_rate_age_adjusted](articles/177_treatment_rate_age_adjusted) |
| 179 | 外国人労働者の半分が技能実習の県もある。宮崎・青森・高知は全国の2.5倍で、東京は0.28倍だった | [179_technical_intern_specialization](articles/179_technical_intern_specialization) |
| 182 | 人口あたりの病床数、最多の高知は神奈川の3倍。上位15のうち14が中国・四国・九州。差は療養と精神の病床で大きかった | [182_hospital_beds_west_east](articles/182_hospital_beds_west_east) |
| 187 | 病院の外来患者は2025年も2019年の9割。静岡96から秋田84まで県で差があり、47都道府県のすべてがコロナ前に戻っ | [187_outpatient_recovery_pref](articles/187_outpatient_recovery_pref) |
| 191 | 野菜の産地はどれだけ集中しているか。ばれいしょは北海道が8割、41品目のうち20品目は上位3県で半分以上だった | [191_vegetable_concentration](articles/191_vegetable_concentration) |
| 192 | 障害者の実雇用率、大企業と小さな企業の差は12年で縮まらず0.59→0.75ポイントに。法定雇用率が上がる年は大企業ほど | [192_disability_employment_size](articles/192_disability_employment_size) |
| 194 | 大きな都市ほど自動車を使わない。人口10倍で分担率は23ポイント低いが、100万都市でも東京23区12%と仙台市50%の | [194_city_size_car_share](articles/194_city_size_car_share) |
| 196 | 女性の小学校長は10年で19%から30%に。石川は58%、島根・長崎は12%で、10年前に女性の教頭が多かった県ほど今の | [196_female_principals](articles/196_female_principals) |
| 198 | 日照時間の「晴れの県ランキング」は30年たってもほとんど入れ替わらない。山梨は39年中21年で1位、秋田は34年で下位5 | [198_sunshine_rank](articles/198_sunshine_rank) |
| 203 | 埼玉県の観光客の3分の1は越谷市。上位5市で6割を占め、この割合は15年ほぼ変わらない | [203_saitama_tourism_concentration](articles/203_saitama_tourism_concentration) |
| 204 | HbA1c 6.5%以上の人は特定健診で7.26%。年齢をそろえても佐賀県8.72%、長野県6.34%と1.38倍の差 | [204_health_checkup_hba1c](articles/204_health_checkup_hba1c) |
| 205 | 図書館で1人が借りる本は年4.78冊。滋賀県は7.30冊、青森県と秋田県は2.74冊で2.7倍の差 | [205_library_loans](articles/205_library_loans) |
| 209 | 都道府県ランキングの1位は、10年で半分近く入れ替わる。334指標で1位が同じだったのは56% | [209_pref_rank_turnover](articles/209_pref_rank_turnover) |
| 211 | 家賃を除いても、物価の地域差は2割しか縮まない。東京都は1位から3位に、北海道が1位に | [211_regional_price_ex_rent](articles/211_regional_price_ex_rent) |
| 214 | 宿泊の季節の形で47都道府県を5つに分けると、山梨は8月に年平均の1.85倍、東京は1年中ほぼ平ら | [214_lodging_seasonality](articles/214_lodging_seasonality) |
| 217 | 給食の自校方式は神奈川で87%、島根で1%。15年で39都道府県が自校方式の割合を減らした | [217_school_lunch_kitchens](articles/217_school_lunch_kitchens) |
| 219 | 2025年の梅雨明けは8地方で1951年以降最も早かった。それでも76年で見ると、梅雨明けは早まっていない | [219_baiu_end_trend](articles/219_baiu_end_trend) |
| 228 | 外食は2019年より15%多いが、物価を除くと5%少ない。戻っていないのは70歳以上と50代の世帯で、喫茶代はどの年齢で | [228_eating_out_recovery_by_age](articles/228_eating_out_recovery_by_age) |
| 229 | お菓子の支出は10年で33%増えたが、物価を除くと7%減った。値段が1.75倍のチョコレートは実質4割減で、ビスケットと | [229_sweets_nominal_vs_real](articles/229_sweets_nominal_vs_real) |
| 243 | 縦長の統計表をレポートの形にする SQL は、CASE WHEN で書ける。ただし業態が1つ増えると、その行は黙って落ち | [243_sql_pivot_report](articles/243_sql_pivot_report) |
| 254 | 米の作況指数の揺れは、2000年以降にそれまでの4割ほどに小さくなった。夏の気温の揺れは同じくらいで、1℃涼しい夏の落ち | [254_rice_yield_volatility](articles/254_rice_yield_volatility) |
| 259 | 統計表を毎年取り直すとき、何で「変わった」を見つけるか？ | [259_stat_file_version_check](articles/259_stat_file_version_check) |
| 260 | 取り込む前のチェックは、壊れたファイルをどこまで止めるか？ | [260_schema_validation_injected](articles/260_schema_validation_injected) |
| 261 | データ辞書（列の説明書）は、何を書くと役に立つのか？ | [261_data_dictionary_ssdse](articles/261_data_dictionary_ssdse) |
| 264 | 1日の気温差は、95年で0.5℃縮んだ。夜の最低気温が昼の最高気温より速く上がったからだが、1990年代からは最高気温の | [264_diurnal_temperature_range](articles/264_diurnal_temperature_range) |
| 265 | 雨の降る日は、1931〜60年と1996〜2025年の平均を比べると4%減り、降った日の雨量は4%増えた。13地点すべて | [265_wet_days_rain_intensity](articles/265_wet_days_rain_intensity) |
| 266 | 最低気温が0℃を下回る最初の日は、1931〜60年と1995〜2024年の平均を比べると9日遅くなった。春の最後の日は1 | [266_first_frost_day_trend](articles/266_first_frost_day_trend) |
| 269 | 「データが取れない」とき、どう代わりを探したか？ | [269_finding_substitute_data](articles/269_finding_substitute_data) |
| 270 | 市町村の合併を、SQL でどう扱うか？ | [270_sql_municipal_code_scd2](articles/270_sql_municipal_code_scd2) |
| 272 | 毎月の数字は、前月比・前年同月比・季節調整のどれで読むか？ | [272_seasonal_adjust_monthly](articles/272_seasonal_adjust_monthly) |
| 285 | 輸入の半分は、何品目で占められているのか？ | [285_import_pareto_items](articles/285_import_pareto_items) |
| 286 | 予測モデルは、線形回帰と勾配ブースティングのどちらから始めるか？ | [286_linear_vs_gbm_first](articles/286_linear_vs_gbm_first) |
| 301 | 公的統計の CSV を、SQL Server に毎月取り込む形はどう作るか？ | [301_sql_monthly_csv_load](articles/301_sql_monthly_csv_load) |
| 322 | 書いた記事は、何か月で「古い数字」になるのか？ | [322_months_until_stale](articles/322_months_until_stale) |
| 337 | 1966年の丙午に、出生はどれだけ減ったのか？ | [337_hinoeuma_1966_births](articles/337_hinoeuma_1966_births) |
| 338 | 1918〜20年の流行で、死亡はふだんよりどれだけ多かったのか？ | [338_excess_deaths_1918_1920](articles/338_excess_deaths_1918_1920) |
| 351 | 出典には、統計の名前・表の番号・取得日がそろっているか？ | [351_source_citation_elements](articles/351_source_citation_elements) |
| 370 | 雇われて働く人が8割を超えたのは、いつだったのか？ | [370_employee_share_80_percent](articles/370_employee_share_80_percent) |
| 373 | pandas で型を指定せずに読むと、何列が意図と違う型になるのか？ | [373_pandas_dtype_inference](articles/373_pandas_dtype_inference) |
| 376 | 全体では上がっているのに、どの区分でも下がっていることは、どれくらい起きるのか？ | [376_simpson_reversal_frequency](articles/376_simpson_reversal_frequency) |
| 377 | 季節のあるデータで「施策の前後」を比べると、効果0でもどれだけ差が出るのか？ | [377_before_after_seasonal_false_effect](articles/377_before_after_seasonal_false_effect) |
| 390 | 年間の予算を月に割る方法で、月ごとの達成率はどれだけ変わるのか？ | [390_budget_monthly_allocation](articles/390_budget_monthly_allocation) |
| 395 | 関係のない2つの右肩上がりの系列は、どれくらい「関係あり」と出てしまうのか？ | [395_spurious_regression_trending_series](articles/395_spurious_regression_trending_series) |
| 421 | 生まれて1年以内に亡くなる子は、いつ、どれだけ速く減ったのか？ | [421_infant_mortality_since_1899](articles/421_infant_mortality_since_1899) |
| 423 | 「市」に住む人が半分を超えたのは、いつだったのか？ | [423_city_population_share](articles/423_city_population_share) |
| 424 | 日本の人口の「真ん中の年齢」は、100年でどう上がったのか？ | [424_median_age_100_years](articles/424_median_age_100_years) |
| 425 | 赤ちゃんが生まれる場所は、自宅から病院へ、いつ入れ替わったのか？ | [425_birthplace_home_to_hospital](articles/425_birthplace_home_to_hospital) |
| 435 | 対数に直して回帰した予測を元に戻すと、合計はどれだけ小さく出るのか？ | [435_log_retransformation_bias](articles/435_log_retransformation_bias) |
| 439 | 3人目より後に生まれる子は、いつから少数になったのか？ | [439_birth_order_shares](articles/439_birth_order_shares) |
| 441 | 基準の年が変わった指数をつなぐとき、つなぎ方で長期の伸びはどれだけ変わるのか？ | [441_index_rebasing_link_methods](articles/441_index_rebasing_link_methods) |
| 452 | 小計や合計の行が混ざった表をそのまま足すと、合計は何倍になるのか？ | [452_subtotal_rows_double_count](articles/452_subtotal_rows_double_count) |
| 474 | 見出しを結合セルや空欄で省いた Excel の表を読むと、何行が区分を失うのか？ | [474_blank_headings_filldown](articles/474_blank_headings_filldown) |
| 541 | 郵便番号から都道府県・市区町村を引くと、古い番号や事業所の個別番号のせいで何件が引けないのか？ | [541_postal_code_lookup_gaps](articles/541_postal_code_lookup_gaps) |
| F296 | 最低賃金の差の差は、前提をどこまで確かめられるのか？ | [F296_minimum_wage_did_assumptions](articles/F296_minimum_wage_did_assumptions) |

</details>

