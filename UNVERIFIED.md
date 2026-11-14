# 確かめていないこと（未検証の一覧）

## 1. T-SQL 版を SQL Server で試していない記事（231本）
SQL の記事は、DuckDB で流して Python と同じ答えになることを確かめています。SQL Server 向けの書き方（T-SQL 版、ファイル名に `tsql`）は、SQL Server では動かしていません。日付関数・整数の割り算・照合順序・DECIMAL の桁など、DuckDB と SQL Server で動きが違うところがあります。

| # | 問い | フォルダ |
|---|---|---|
| 243 | 縦長の統計表をレポートの形にする SQL は、CASE WHEN で書ける。ただし業態が1つ増えると、その行は黙って落ち | [243_sql_pivot_report](articles/243_sql_pivot_report) |
| 270 | 市町村の合併を、SQL でどう扱うか？ | [270_sql_municipal_code_scd2](articles/270_sql_municipal_code_scd2) |
| 294 | SQL のクエリが遅いとき、まず何を見るか？ | [294_slow_query_first_checks](articles/294_slow_query_first_checks) |
| 296 | 需要予測の当たり外れを、毎週どう見張るか？ | [296_forecast_error_control_chart](articles/296_forecast_error_control_chart) |
| 301 | 公的統計の CSV を、SQL Server に毎月取り込む形はどう作るか？ | [301_sql_monthly_csv_load](articles/301_sql_monthly_csv_load) |
| 326 | 古いシステムから新しいシステムへ移したデータは、何を照合すれば「同じ」と言えるか？ | [326_migration_reconciliation](articles/326_migration_reconciliation) |
| 327 | C# の Math.Round と SQL Server の ROUND と Excel の ROUND は、同じ答えを返すのか？ | [327_rounding_csharp_sql_excel](articles/327_rounding_csharp_sql_excel) |
| 328 | 行ごとに丸めてから足すのと、足してから丸めるのでは、どれだけ違うのか？ | [328_round_then_sum_order](articles/328_round_then_sum_order) |
| 329 | 金額を小数（FLOAT）で持つと、合計はどれだけずれるのか？ | [329_float_money_sum](articles/329_float_money_sum) |
| 330 | 同じファイルを2回取り込んでも、数字が二重にならない形はどう作るか？ | [330_idempotent_load](articles/330_idempotent_load) |
| 341 | 月次の数字は、締めてから何日たてば「確定」と言えるのか？ | [341_month_close_completeness](articles/341_month_close_completeness) |
| 342 | 締めたあとに訂正されたデータで、先月のレポートの数字を再現できるか？ | [342_restate_and_reproduce_reports](articles/342_restate_and_reproduce_reports) |
| 343 | 損害率は、事故が起きた年で数えるか、支払った年で数えるかで、どれだけ違うのか？ | [343_loss_ratio_accident_vs_calendar](articles/343_loss_ratio_accident_vs_calendar) |
| 344 | 「アクティブな顧客」は、定義でどれだけ人数が変わるのか？ | [344_active_customer_definitions](articles/344_active_customer_definitions) |
| 356 | 曜日の並びが違うだけで、前年同月比は何ポイント動くのか？ | [356_weekday_mix_yoy](articles/356_weekday_mix_yoy) |
| 357 | 「週」の決め方で、週次の売上はどれだけ変わるのか？ | [357_week_definitions](articles/357_week_definitions) |
| 358 | 売上が0の日が表にないと、1日あたりの平均はどれだけ高く出るのか？ | [358_missing_zero_days](articles/358_missing_zero_days) |
| 359 | 累計を出すウィンドウ関数は、同じ日付の行があると何がずれるのか？ | [359_running_total_ties](articles/359_running_total_ties) |
| 360 | 「上位3件」を取る SQL は、同じ点数があると何件返すのか？ | [360_top3_with_ties](articles/360_top3_with_ties) |
| 371 | 中央値や90%点は、計算の定義でどれだけ違うのか？ | [371_percentile_definitions](articles/371_percentile_definitions) |
| 375 | 全角と半角、前後の空白で、キーはどれだけつながらないのか？ | [375_key_normalization_join](articles/375_key_normalization_join) |
| 386 | 「以上」と「超」、「以下」と「未満」を取り違えると、何件が別の区分に入るのか？ | [386_boundary_inclusive_exclusive](articles/386_boundary_inclusive_exclusive) |
| 387 | チェックデジットは、打ち間違いの何割を止めるのか？ | [387_check_digit_detection](articles/387_check_digit_detection) |
| 388 | 登録月ごとの継続率の表で、まだ観測できていない月を0と数えると、どれだけ低く出るのか？ | [388_cohort_retention_censoring](articles/388_cohort_retention_censoring) |
| 389 | 申込みまでの通過率は、数え方でどれだけ変わるのか？ | [389_funnel_counting_definitions](articles/389_funnel_counting_definitions) |
| 407 | 名前を消しただけの顧客データは、何%の人が1人に絞れてしまうのか？ | [407_k_anonymity_customer_data](articles/407_k_anonymity_customer_data) |
| 408 | 件数の小さいセルを隠した集計表は、引き算で何セル分かってしまうのか？ | [408_cell_suppression_subtraction](articles/408_cell_suppression_subtraction) |
| 409 | 複数回答の設問は、分母の取り方で割合が何ポイント変わるのか？ | [409_multiple_response_denominators](articles/409_multiple_response_denominators) |
| 410 | 売れ筋を A・B・C に分ける分析は、期間と区切りでどれだけ入れ替わるのか？ | [410_abc_analysis_period_cutoffs](articles/410_abc_analysis_period_cutoffs) |
| 411 | 「保険年齢」と「満年齢」では、同じ契約者の年齢区分はどれだけ変わるのか？ | [411_insurance_age_vs_attained_age](articles/411_insurance_age_vs_attained_age) |
| 412 | 月末に始まった契約の「1か月後」は、いつになるのか？ | [412_monthly_anniversary_dates](articles/412_monthly_anniversary_dates) |
| 413 | 途中で解約した契約に返す保険料は、日割りと短期率でどれだけ違うのか？ | [413_cancellation_refund_methods](articles/413_cancellation_refund_methods) |
| 414 | 「期首＋増加−減少＝期末」の照合は、どんな誤りを見つけ、何を見逃すのか？ | [414_roll_forward_reconciliation](articles/414_roll_forward_reconciliation) |
| 415 | 月の途中の実績から、月末の着地をどう見込むか？ | [415_month_end_landing_forecast](articles/415_month_end_landing_forecast) |
| 426 | 外貨の売上を円に直すとき、どの日のレートを使うかで、月の売上はどれだけ変わるのか？ | [426_fx_rate_date_choice](articles/426_fx_rate_date_choice) |
| 427 | 「2025/1/5」「R7.1.5」「20250105」が混ざった日付の列は、機械に読ませると何件が別の日になるのか？ | [427_mixed_date_formats](articles/427_mixed_date_formats) |
| 429 | 共通の費用を部門に配る基準を変えると、何部門の損益の符号が変わるのか？ | [429_overhead_allocation_bases](articles/429_overhead_allocation_bases) |
| 430 | 同じ仕入れと販売でも、在庫の評価の方法で、月の粗利はどれだけ違うのか？ | [430_inventory_valuation_methods](articles/430_inventory_valuation_methods) |
| 441 | 基準の年が変わった指数をつなぐとき、つなぎ方で長期の伸びはどれだけ変わるのか？ | [441_index_rebasing_link_methods](articles/441_index_rebasing_link_methods) |
| 442 | 移動平均でならすと、向きが変わったことに気づくのは何日遅れるのか？ | [442_moving_average_turn_delay](articles/442_moving_average_turn_delay) |
| 443 | 分類を付け替えたあと、過去の集計は「当時の区分」と「今の区分」でどれだけ違うのか？ | [443_reclassification_asof_vs_current](articles/443_reclassification_asof_vs_current) |
| 444 | 税込みと税抜きの金額が混ざった表を足すと、売上はどれだけずれるのか？ | [444_tax_included_excluded_mix](articles/444_tax_included_excluded_mix) |
| 445 | 順番に動かすはずの集計を、順番を違えて流すと、何枚の表が古い数字のままになるのか？ | [445_pipeline_run_order_stale_tables](articles/445_pipeline_run_order_stale_tables) |
| 451 | 「5営業日後」の期日は、祝日の持ち方で何件ずれるのか？ | [451_business_day_due_dates](articles/451_business_day_due_dates) |
| 452 | 小計や合計の行が混ざった表をそのまま足すと、合計は何倍になるのか？ | [452_subtotal_rows_double_count](articles/452_subtotal_rows_double_count) |
| 453 | 数字が文字として入った列を並べ替えると、何件が違う順番になるのか？ | [453_numbers_stored_as_text](articles/453_numbers_stored_as_text) |
| 454 | 2つの処理が同時に同じ行を書き換えると、何件の更新が消えるのか？ | [454_lost_updates_concurrent_writes](articles/454_lost_updates_concurrent_writes) |
| 455 | 1ページずつ順に取り込むと、途中で行が増減したとき、何行が重なり、何行が抜けるのか？ | [455_pagination_drift_during_load](articles/455_pagination_drift_during_load) |
| 461 | 区分ごとのユニーク人数を足すと、全体の人数より何%多くなるのか？ | [461_distinct_counts_not_additive](articles/461_distinct_counts_not_additive) |
| 462 | 2つの期間が重なるかどうかの条件を書き間違えると、何件が漏れ、何件が余分に入るのか？ | [462_interval_overlap_conditions](articles/462_interval_overlap_conditions) |
| 463 | 連番のはずの番号の抜けと重複は、どの確かめ方で何件見つかるのか？ | [463_sequence_gaps_duplicates](articles/463_sequence_gaps_duplicates) |
| 464 | 短くしたハッシュをキーにすると、何行から衝突が起き、何行がまちがってつながるのか？ | [464_truncated_hash_key_collisions](articles/464_truncated_hash_key_collisions) |
| 465 | サーバーごとに時計がずれていると、ログの出来事の順番は何件逆になるのか？ | [465_clock_skew_event_order](articles/465_clock_skew_event_order) |
| 471 | 年初からの累計で見た前年比は、売上の変化に何か月遅れて気づくのか？ | [471_ytd_yoy_lag](articles/471_ytd_yoy_lag) |
| 472 | 返品を「売れた月」に戻すか「返ってきた月」で引くかで、月の売上はどれだけ変わるのか？ | [472_returns_which_month](articles/472_returns_which_month) |
| 473 | 値引きやクーポンを明細に割り振る方法で、商品ごとの粗利はどれだけ変わるのか？ | [473_discount_allocation_margin](articles/473_discount_allocation_margin) |
| 474 | 見出しを結合セルや空欄で省いた Excel の表を読むと、何行が区分を失うのか？ | [474_blank_headings_filldown](articles/474_blank_headings_filldown) |
| 475 | 解約率は、分母の取り方でどれだけ違って見えるのか？ | [475_churn_rate_denominator](articles/475_churn_rate_denominator) |
| 481 | 同じ売上を20日締めと月末締めで集計すると、2023〜2025年の月の数字は平均何%ずれるのか？ | [481_closing_day_20th_vs_monthend](articles/481_closing_day_20th_vs_monthend) |
| 482 | ポイントの失効を「付与日から1年」と「月末に一括」にすると、2025〜2026年の失効額と月の数字はどれだけ変わるのか？ | [482_point_expiry_rules](articles/482_point_expiry_rules) |
| 484 | 明細の「単価×数量」と「金額」を確かめる8つの方法は、誤り1,200件のうち何件を見つけ、何件空振りするのか？ | [484_line_amount_checks](articles/484_line_amount_checks) |
| 485 | 論理削除のフラグと履歴の期間を見落とすと、注文の件数と売上は何%多く出るのか？ | [485_soft_delete_flags](articles/485_soft_delete_flags) |
| 491 | 本文の12%に改行があるCSVを行で分けて読むと、1万件のうち何件が壊れるのか？ | [491_csv_embedded_newlines](articles/491_csv_embedded_newlines) |
| 492 | Excelの日付のシリアル値を読み替えるとき、起点の取り違えで何行が何日ずれるのか？ | [492_excel_serial_dates](articles/492_excel_serial_dates) |
| 493 | ファイル名の日付で取り込み対象を選ぶと、1年365ファイルのうち遅れて置かれた何件を落とすのか？ | [493_file_selection_late_arrivals](articles/493_file_selection_late_arrivals) |
| 494 | 入れ子の注文JSONを平らにすると、行は何倍になり、合計は何%ずれるのか？ | [494_nested_json_flatten](articles/494_nested_json_flatten) |
| 495 | 会員ランクを「暦年」と「直近12か月」で判定すると、2025年の12月には何%の会員のランクが食い違うのか？ | [495_member_rank_calendar_vs_rolling](articles/495_member_rank_calendar_vs_rolling) |
| 501 | 入金の消込を金額だけで合わせると、何件が別の請求に消し込まれるのか？ | [501_payment_matching_amount_only](articles/501_payment_matching_amount_only) |
| 502 | 売上を受注日・出荷日・検収日のどれで数えるかで、月の売上と前年同月比はどれだけ動くのか？ | [502_revenue_date_basis](articles/502_revenue_date_basis) |
| 503 | ログのセッションを何分空いたら切るかで、セッション数と1回あたりの滞在はどれだけ変わるのか？ | [503_session_timeout_definitions](articles/503_session_timeout_definitions) |
| 504 | 取消された注文を残したまま初回購入月を決めると、新規顧客の数は何%多く出るのか？ | [504_first_purchase_month_cancellations](articles/504_first_purchase_month_cancellations) |
| 505 | 定期便の次回のお届け日を「30日後」と「毎月同じ日」で決めると、1年の出荷回数と月の出荷数はどれだけ違うのか？ | [505_subscription_next_delivery_rules](articles/505_subscription_next_delivery_rules) |
| 511 | ログの利用者IDが Cookie だと、ユニーク利用者は本当の人数の何倍に数えられるのか？ | [511_cookie_vs_login_unique_users](articles/511_cookie_vs_login_unique_users) |
| 512 | 割合を小数1桁で表示すると、前月からの増減が「0.0」や逆の向きに見える月は何か月あるのか？ | [512_rounded_display_mom_change](articles/512_rounded_display_mom_change) |
| 513 | ログを10件に1件だけ残して10倍すると、小さな区分の件数はどれだけ振れるのか？ | [513_log_sampling_small_segments](articles/513_log_sampling_small_segments) |
| 514 | 入庫と出庫の記録が遅れて届くと、在庫が一時的にマイナスになる日は何日あるのか？ | [514_inventory_record_delay_negative](articles/514_inventory_record_delay_negative) |
| 515 | Excel の SUM でフィルタで隠した行も含めて合計すると、表の合計は何%多くなるのか？ | [515_excel_sum_vs_subtotal_hidden](articles/515_excel_sum_vs_subtotal_hidden) |
| 521 | 問い合わせの対応時間を「営業時間」で数えるか「暦の時間」で数えるかで、期限内に返せた割合は何ポイント変わるのか？ | [521_sla_business_vs_calendar_hours](articles/521_sla_business_vs_calendar_hours) |
| 522 | 在庫回転日数を「期首と期末の平均在庫」で出すと、毎日の在庫から出した値と何日ずれるのか？ | [522_inventory_days_average_method](articles/522_inventory_days_average_method) |
| 523 | 未完了の案件を除いてリードタイムの中央値を出すと、本当より何日短く出るのか？ | [523_lead_time_open_cases_median](articles/523_lead_time_open_cases_median) |
| 524 | 深夜まで営業する店で、売上を暦日で切るか「朝5時締めの営業日」で切るかで、曜日別の売上はどれだけ変わるのか？ | [524_business_day_cutoff_5am](articles/524_business_day_cutoff_5am) |
| 525 | メールの開封率は、画像の自動読み込みによる「見かけの開封」を除くと何ポイント下がるのか？ | [525_email_open_rate_auto_load](articles/525_email_open_rate_auto_load) |
| 531 | 納期の遵守率は、「当初の約束日」と「変更後の日」のどちらで数えるかで何ポイント違うのか？ | [531_delivery_promise_date_basis](articles/531_delivery_promise_date_basis) |
| 532 | NPS は、回答が50件や200件のとき、本当は同じ店どうしでも何ポイント差が出てしまうのか？ | [532_nps_small_sample_gap](articles/532_nps_small_sample_gap) |
| 533 | 残業時間を15分単位で切り捨てて集計すると、1か月の時間は何%少なく出るのか？ | [533_overtime_truncation_monthly](articles/533_overtime_truncation_monthly) |
| 534 | アンケートの「その他」の自由記述を選択肢に振り直すと、各選択肢の割合は何ポイント動くのか？ | [534_survey_other_recode](articles/534_survey_other_recode) |
| 535 | 顧客の年齢を「登録したときの年齢」のまま集計すると、年代別の構成は何年でどれだけずれるのか？ | [535_age_at_registration_drift](articles/535_age_at_registration_drift) |
| 543 | 予約枠の稼働率は、無断キャンセルと直前キャンセルをどう数えるかで何ポイント違うのか？ | [543_booking_utilization_definitions](articles/543_booking_utilization_definitions) |
| 551 | 月の途中で単価が変わったとき、適用開始日を見ずに今の単価で集計すると、金額はどれだけずれるのか？ | [551_price_master_effective_date](articles/551_price_master_effective_date) |
| 552 | 訂正を「取消（赤）＋再登録（黒）」で入れる伝票では、件数と金額をどう数えればよいのか？ | [552_red_black_correction_count](articles/552_red_black_correction_count) |
| 553 | 売掛金の滞留を、請求日から数えるか支払期日から数えるかで、区分ごとの金額はどれだけ動くのか？ | [553_ar_aging_basis](articles/553_ar_aging_basis) |
| 554 | セット商品の売上を構成品に分けるとき、金額の割り振り方で商品別の売上はどれだけ変わるのか？ | [554_bundle_revenue_allocation](articles/554_bundle_revenue_allocation) |
| 555 | 社内のテスト用アカウントの行を外す条件を変えると、利用者数と売上はどれだけ動くのか？ | [555_test_account_exclusion](articles/555_test_account_exclusion) |
| 556 | 同じ分母で割った2つの比率は、もとの数に関係がなくてもどれだけ相関するのか？ | [556_shared_denominator_ratio_corr](articles/556_shared_denominator_ratio_corr) |
| 557 | 効き方が層で違うのに、交互作用を入れずに回帰すると、全体の係数は何を表すのか？ | [557_no_interaction_weighting](articles/557_no_interaction_weighting) |
| 558 | 予測確率が「30%」と出た人のうち、本当に起きるのは何%なのか？ | [558_probability_calibration](articles/558_probability_calibration) |
| 559 | 前後の差で比べるか、前の値を入れた回帰で比べるかで、効果の答えが変わるのはなぜか？ | [559_change_score_vs_ancova](articles/559_change_score_vs_ancova) |
| 560 | 効果を「差」で見るか「比」で見るかで、効果の大きい層が入れ替わるのはなぜか？ | [560_effect_scale_ranking](articles/560_effect_scale_ranking) |
| 561 | 同じ人が続けて送った問い合わせを、何分以内なら1件とみなすかで、件数はどれだけ変わるのか？ | [561_inquiry_dedup_window](articles/561_inquiry_dedup_window) |
| 562 | 「直近30日」に今日を含めるか、時刻で切るか日付で切るかで、数字はどれだけ変わるのか？ | [562_rolling_30day_definition](articles/562_rolling_30day_definition) |
| 563 | 千円単位と円単位の数字が混ざった表から、桁のずれた行をどう見つけるのか？ | [563_thousand_yen_unit_mix](articles/563_thousand_yen_unit_mix) |
| 564 | 注文を何回かに分けて出荷すると、「出荷済みの注文」の数え方でどれだけ違うのか？ | [564_partial_shipment_definition](articles/564_partial_shipment_definition) |
| 565 | 状態が何度も変わる申込みで、過去のある日の状態を履歴からどう戻すのか？ | [565_status_history_asof](articles/565_status_history_asof) |
| 566 | 死亡率が下がり続けると、その年の生命表の平均余命は、実際に生きる年数よりどれだけ短く出るのか？ | [566_period_vs_cohort_life_table](articles/566_period_vs_cohort_life_table) |
| 567 | 支払備金の個別見積を途中から厚く積むようにすると、発生ベースのチェインラダーはどれだけ多く見込むのか？ | [567_case_reserve_strengthening](articles/567_case_reserve_strengthening) |
| 568 | 保険金額が実際の価値より小さい契約で、比例てん補を入れると、支払いと必要な保険料はどう変わるのか？ | [568_proportional_vs_first_loss](articles/568_proportional_vs_first_loss) |
| 569 | 死亡率の実績と予定の比を、件数で見るか保険金額で見るかで、どれだけ違うのか？ | [569_ae_count_vs_amount](articles/569_ae_count_vs_amount) |
| 570 | 進展の途中で打ち切ったチェインラダーは、テールファクターを省くと最終損害をどれだけ少なく見るのか？ | [570_chain_ladder_tail_factor](articles/570_chain_ladder_tail_factor) |
| 571 | UTCで保存した時刻を日本時間に直さずに日付で集計すると、何件が前日に入るのか？ | [571_utc_date_aggregation](articles/571_utc_date_aggregation) |
| 572 | 同じ時刻の行が並ぶとき、ROW_NUMBERで「最新の1行」を選ぶと、実行のたびに何件入れ替わるのか？ | [572_row_number_ties](articles/572_row_number_ties) |
| 573 | 会員の「休眠」を最終購入から90日で切るか180日で切るかで、休眠の人数と「復活」の割合はどれだけ変わるのか？ | [573_dormant_threshold_days](articles/573_dormant_threshold_days) |
| 574 | 部署の統廃合があったとき、過去の部署別の数字を今の組織に組み替えると、推移はどう変わるのか？ | [574_reorg_restatement](articles/574_reorg_restatement) |
| 575 | 顧客が引っ越したとき、売上を「売った時点の住所」で数えるか「今の住所」で数えるかで、地域別の売上はどれだけ動くのか？ | [575_address_at_sale_vs_now](articles/575_address_at_sale_vs_now) |
| 576 | 時系列のデータをランダムに分けて確かめると、時間の順に分けた場合より成績はどれだけ良く見えるのか？ | [576_random_vs_time_split](articles/576_random_vs_time_split) |
| 577 | 2つの測り方の一致を、相関で見るか、差の平均と幅で見るかで、結論はどう変わるのか？ | [577_correlation_vs_agreement](articles/577_correlation_vs_agreement) |
| 578 | 平均の差を見るとき、群で散らばりが違うと、ふつうのt検定は何%の回で「差あり」と言うのか？ | [578_student_vs_welch](articles/578_student_vs_welch) |
| 579 | 店ごとの比率を平均するか、合計どうしで比を取るかで、全体の比率はどれだけ違うのか？ | [579_mean_of_ratios_vs_ratio_of_totals](articles/579_mean_of_ratios_vs_ratio_of_totals) |
| 580 | 傾向スコアで重みを付けるとき、極端な重みを切り詰めると、推定の偏りとばらつきはどう変わるのか？ | [580_ipw_weight_trimming](articles/580_ipw_weight_trimming) |
| 581 | 締め日が20日の会社で、月の売上を暦の月で数えるか締めの期間で数えるかで、月ごとの数字はどれだけずれるのか？ | [581_closing_day_vs_calendar_month](articles/581_closing_day_vs_calendar_month) |
| 582 | 複数の担当者で受けた案件の成果を、主担当に全部付けるか人数で割るかで、担当者別の実績の順位はどれだけ入れ替わるのか？ | [582_shared_deal_credit](articles/582_shared_deal_credit) |
| 583 | 在庫を帳簿上の数で見るか、引当を除いた使える数で見るかで、欠品の判定は何品目変わるのか？ | [583_available_vs_on_hand](articles/583_available_vs_on_hand) |
| 584 | 同じ人が別のIDで登録された顧客表を、電話・メール・氏名＋生年月日で寄せると、顧客数とリピート率はどれだけ変わるのか？ | [584_customer_dedup_keys](articles/584_customer_dedup_keys) |
| 585 | 個・箱・ケースの単位が混ざった出荷明細を換算せずに足すと、品目別の数量はどれだけずれるのか？ | [585_unit_conversion](articles/585_unit_conversion) |
| 586 | 裾の重いデータで平均の差を比べると、t検定と順位の検定で検出力はどれだけ違うのか？ | [586_ttest_vs_rank_heavy_tails](articles/586_ttest_vs_rank_heavy_tails) |
| 587 | 同じテスト用データでモデルの調整を何度もくり返すと、テストの成績はどれだけ楽観的になるのか？ | [587_test_set_reuse](articles/587_test_set_reuse) |
| 588 | 散らばりが水準で変わるデータで、予測の区間を「残差の標準偏差×2」で作ると、何%の回が外れるのか？ | [588_prediction_interval_heteroscedastic](articles/588_prediction_interval_heteroscedastic) |
| 589 | 階級に区切った度数分布表から平均と中央値を出すと、元のデータの値とどれだけずれるのか？ | [589_grouped_table_mean_median](articles/589_grouped_table_mean_median) |
| 590 | 比率の分母が小さい項目を並べると、上位と下位にどれだけ小さい項目が集まるのか？ | [590_small_denominator_ranking](articles/590_small_denominator_ranking) |
| 591 | 欠品していた日の売上を0と見るか欠測と見るかで、平均の需要はどれだけ少なく見えるのか？ | [591_stockout_censored_demand](articles/591_stockout_censored_demand) |
| 592 | 同じ商品の色・サイズ違いを1品目と数えるか別々に数えるかで、売れ筋の順位はどれだけ変わるのか？ | [592_parent_vs_sku_ranking](articles/592_parent_vs_sku_ranking) |
| 593 | 開店と閉店がある期間で、「1店あたりの売上」を月末の店数で割るか営業日数で割るかで、どれだけ違うのか？ | [593_per_store_denominator](articles/593_per_store_denominator) |
| 594 | 日をまたぐ夜のシフトを、開始日で数えるか日ごとに分けるかで、日ごとの労働時間はどれだけ違うのか？ | [594_overnight_shift_split](articles/594_overnight_shift_split) |
| 595 | 「完了」「済」「済み」のように表記の揺れたステータス列をそのまま GROUP BY すると、何%の行が別のグループに分かれるのか？ | [595_status_label_variants](articles/595_status_label_variants) |
| 596 | 小さい契約群の実績を全体の平均とどう混ぜるか？ | [596_buhlmann_credibility](articles/596_buhlmann_credibility) |
| 597 | 年間の総損害を件数×金額で作るとき、件数の年ごとの揺れを無視すると、99.5%点はどれだけ小さく出るのか？ | [597_compound_poisson_vs_nb](articles/597_compound_poisson_vs_nb) |
| 598 | 年の途中で売る1年契約では、事故を事故年で数えるか契約年度で数えるかで、事故率の推移はどれだけ違って見えるのか？ | [598_calendar_vs_policy_year](articles/598_calendar_vs_policy_year) |
| 599 | 事故のあった人ほど契約を更新しないと、翌年の保有の事故率はどれだけ下がって見えるのか？ | [599_renewal_selection](articles/599_renewal_selection) |
| 600 | 過去10年の損害から分布を推定するとき、推定の誤差を入れないと、99.5%点はどれだけ小さく出るのか？ | [600_parameter_uncertainty_quantile](articles/600_parameter_uncertainty_quantile) |
| 601 | 外部結合（LEFT JOIN）のあと WHERE で右の表の列を絞ると、何件の行が黙って消えるのか？ | [601_left_join_where_filter](articles/601_left_join_where_filter) |
| 602 | 平均単価を「明細の単価の平均」で出すか「金額の合計÷数量」で出すかで、品目の単価はどれだけ違うのか？ | [602_avg_unit_price_definition](articles/602_avg_unit_price_definition) |
| 604 | 構成比を四捨五入すると、合計が100%にならない表は何%あり、最大剰余法で直すと各項目はどれだけ動くのか？ | [604_share_rounding_sum100](articles/604_share_rounding_sum100) |
| 605 | 先頭の0が落ちた商品コードや取引先コードで表をつなぐと、何件がつながらず、何件が別のコードにつながるのか？ | [605_leading_zero_codes](articles/605_leading_zero_codes) |
| 612 | 住所を「LIKE '%桜ヶ丘%'」のような部分一致で探すと、何件を余分に拾い、何件を取りこぼすのか？ | [612_like_partial_match_address](articles/612_like_partial_match_address) |
| 621 | A/B テストの割り付けが 50:50 からずれていることに、何人集まれば気づけるのか？ | [621_ab_sample_ratio_mismatch](articles/621_ab_sample_ratio_mismatch) |
| 622 | 「新規の顧客」を過去何年さかのぼって判定するかで、新規の割合はどれだけ変わるのか？ | [622_new_customer_lookback](articles/622_new_customer_lookback) |
| 623 | 差分の取り込みを「更新日時が前回より後」で行うと、何件が取りこぼされるのか？ | [623_incremental_load_updated_at](articles/623_incremental_load_updated_at) |
| 624 | 週の途中の数字を先週の合計と比べると、どれだけ低く見えるのか？ | [624_partial_week_comparison](articles/624_partial_week_comparison) |
| 625 | データの先頭1,000行だけで中身を確かめると、後ろにある異常は何%見つかるのか？ | [625_head_rows_quality_check](articles/625_head_rows_quality_check) |
| 631 | 発注をケース単位に切り上げると、在庫は平均で何日分多く持つことになるのか？ | [631_case_pack_rounding_inventory](articles/631_case_pack_rounding_inventory) |
| 632 | マスタは今日、明細は昨日の時点の表をつなぐと、何件が片方にしかないのか？ | [632_master_detail_snapshot_lag](articles/632_master_detail_snapshot_lag) |
| 633 | 送り直しで二重に届いたイベントを除かずに数えると、申込みの数は何%多くなるのか？ | [633_event_retry_duplicates](articles/633_event_retry_duplicates) |
| 634 | CASE WHEN の条件の並べ方で、何件が別の区分に入るのか？ | [634_case_when_order](articles/634_case_when_order) |
| 635 | ROLLUP の小計の行と、もともと区分が空の行を取り違えると、合計はどれだけずれるのか？ | [635_rollup_null_grouping](articles/635_rollup_null_grouping) |
| 641 | 整数どうしの割り算で割合を出すと、何%の行が0になるのか？ | [641_integer_division_ratio](articles/641_integer_division_ratio) |
| 642 | 年間の目標を12等分するか、前年の月の比率で分けるかで、「達成した月」の数はどれだけ違うのか？ | [642_monthly_target_phasing](articles/642_monthly_target_phasing) |
| 643 | キャンペーンを使った人と使わなかった人を比べると、効果が0でもどれだけ差が出るのか？ | [643_campaign_users_self_selection](articles/643_campaign_users_self_selection) |
| 644 | 毎年の伸び率を足して割った平均と、年率（幾何平均）では、5年後の値はどれだけ違うのか？ | [644_growth_rate_arith_vs_geo](articles/644_growth_rate_arith_vs_geo) |
| 645 | 5段階の評価を平均で比べるか、上位2つの割合で比べるかで、店の順位はどれだけ入れ替わるのか？ | [645_likert_mean_vs_top2box](articles/645_likert_mean_vs_top2box) |
| 651 | ページの滞在時間を「次のページを開いた時刻との差」で測ると、最後に見たページの分はどれだけ抜け落ちるのか？ | [651_last_page_dwell_time](articles/651_last_page_dwell_time) |
| 652 | 採番の連番の最大値で件数を見ると、欠番のせいで何%多く数えるのか？ | [652_max_id_vs_count](articles/652_max_id_vs_count) |
| 653 | 層ごとに抽出率の違うサンプルを、重みを付けずに平均すると、全体の値はどれだけずれるのか？ | [653_stratified_sample_weights](articles/653_stratified_sample_weights) |
| 654 | 大文字と小文字を区別するかしないかで、GROUP BY の件数とつながる行はどれだけ変わるのか？ | [654_collation_case_grouping](articles/654_collation_case_grouping) |
| 655 | 平均の購入間隔を「2回以上買った人」だけで出すと、本当の間隔よりどれだけ短く出るのか？ | [655_purchase_interval_selection](articles/655_purchase_interval_selection) |
| 661 | 新しく開いた店と閉じた店を含めたまま前年比を出すと、既存店だけの前年比とどれだけ違うのか？ | [661_existing_store_yoy](articles/661_existing_store_yoy) |
| 662 | UNION と UNION ALL を取り違えると、何件の行が消えたり残ったりするのか？ | [662_union_vs_union_all](articles/662_union_vs_union_all) |
| 663 | ウィンドウ関数の PARTITION BY を書き忘れると、店ごとの累計や順位はどれだけ狂うのか？ | [663_window_partition_missing](articles/663_window_partition_missing) |
| 664 | 平均単価の前年比を、品目の構成の変化と単価の変化に分けると、それぞれどれだけになるのか？ | [664_price_mix_decomposition](articles/664_price_mix_decomposition) |
| 665 | 会員カードを出した客だけで客単価を見ると、店全体の客単価よりどれだけ高く出るのか？ | [665_member_card_spend_bias](articles/665_member_card_spend_bias) |
| 671 | 重複して登録した人を除かずに抽選すると、その人の当選確率は何倍になるのか？ | [671_lottery_duplicate_entries](articles/671_lottery_duplicate_entries) |
| 672 | 回答者の年代の偏りを重み付けで直すと、アンケートの結果はどれだけ動き、ばらつきはどれだけ増えるのか？ | [672_survey_weighting](articles/672_survey_weighting) |
| 673 | 1つの注文を、使ったクーポンそれぞれに全額付けると、クーポン別の売上の合計は実際の何倍になるのか？ | [673_coupon_double_attribution](articles/673_coupon_double_attribution) |
| 674 | 広告の成果を「最後の接点」に付けるか均等に分けるかで、広告ごとの成果はどれだけ違うのか？ | [674_ad_attribution_models](articles/674_ad_attribution_models) |
| 675 | DISTINCT で重複を消すと、本当に2回あった同じ内容の取引は何件消えるのか？ | [675_distinct_true_duplicates](articles/675_distinct_true_duplicates) |
| 681 | 「有効」フラグの立った商品だけで集計すると、廃番になった商品の過去の売上はどれだけ消えるのか？ | [681_existing_flag_history](articles/681_existing_flag_history) |
| 682 | 店ごとの前年比を並べるのと、全体の伸びへの寄与度で並べるのでは、順位はどれだけ違うのか？ | [682_contribution_to_growth](articles/682_contribution_to_growth) |
| 683 | 品名に「_」や「%」を含む行を LIKE で探すと、何件を取り違えるのか？ | [683_like_escape_wildcards](articles/683_like_escape_wildcards) |
| 684 | 桁区切りのカンマが入った数字を CSV に書き出すと、読み込みで何列がずれるのか？ | [684_csv_thousands_separator](articles/684_csv_thousands_separator) |
| 691 | 同じ顧客の重複行から「最初」と「最新」のどちらを残すかで、属性の集計はどれだけ変わるのか？ | [691_dedup_keep_first_or_last](articles/691_dedup_keep_first_or_last) |
| 693 | 月数を「月の境目をまたいだ回数」で数えると、契約の経過月数は何件ずれるのか？ | [693_datediff_month_boundary](articles/693_datediff_month_boundary) |
| 695 | 1人あたりの処理件数を、出勤した日数で割るか働いた時間で割るかで、担当者の順位はどれだけ入れ替わるのか？ | [695_productivity_denominator](articles/695_productivity_denominator) |
| 701 | 「2024/1/5」のように0を埋めない日付を文字列のまま並べ替えると、何行が順番を間違えるのか？ | [701_string_date_sort](articles/701_string_date_sort) |
| 702 | 構成比を WHERE で絞り込んだあとに出すと、全体に対する割合とどれだけ違って見えるのか？ | [702_share_after_filter](articles/702_share_after_filter) |
| 703 | 売上のない月が行ごと抜けた表で LAG を使って前月比を出すと、何行が2か月前と比べてしまうのか？ | [703_lag_missing_months](articles/703_lag_missing_months) |
| 704 | 年齢を「年の差」だけで出すと、誕生日前の会員は何%が1歳多く数えられるのか？ | [704_age_datediff_year](articles/704_age_datediff_year) |
| 705 | リピート率を「30日以内」で数えるか「90日以内」で数えるかで、月ごとの比べ方はどれだけ変わるのか？ | [705_repeat_rate_window](articles/705_repeat_rate_window) |
| 711 | 月の売上を「30」で割るか、その月の日数や営業日数で割るかで、日あたりの前月比はどれだけ違うのか？ | [711_daily_avg_days_in_month](articles/711_daily_avg_days_in_month) |
| 713 | 率が5%から6%になったのを「1ポイント増」と「20%増」のどちらで書くかで、店の並びはどれだけ変わるのか？ | [713_points_vs_percent_change](articles/713_points_vs_percent_change) |
| 715 | 取り込み元に同じキーが2行ある状態で MERGE（UPSERT）すると、何件の値が意図と違う行で上書きされるのか？ | [715_merge_duplicate_source](articles/715_merge_duplicate_source) |
| 721 | 2つの列を区切りなしでつないでキーにすると、別の組み合わせが同じキーになる行は何件あるのか？ | [721_concat_key_collision](articles/721_concat_key_collision) |
| 722 | 整数の列を SQL Server の AVG で平均すると、小数の切り捨てで店ごとの平均はどれだけずれるのか？ | [722_avg_integer_truncation](articles/722_avg_integer_truncation) |
| 723 | 前年がマイナスの利益の伸び率を、ふつうの式で出すと、何店で向きが逆に見えるのか？ | [723_growth_negative_base](articles/723_growth_negative_base) |
| 724 | 日次の売上に7日以外の幅の移動平均をかけると、曜日の波はどれだけ残るのか？ | [724_moving_avg_window_weekday](articles/724_moving_avg_window_weekday) |
| 725 | 購入回数で顧客を5等分すると、同じ回数の人が別の段に分かれるのはどれだけか？ | [725_rfm_quintile_ties](articles/725_rfm_quintile_ties) |
| 731 | 「上位10%の顧客で売上の何割」を、買わなかった会員を含めて数えるか除くかで、どれだけ違うのか？ | [731_top_share_zero_customers](articles/731_top_share_zero_customers) |
| 732 | うるう年の2月29日を含む月の前年同月比は、日数をそろえないとどれだけ高く見えるのか？ | [732_leap_day_yoy](articles/732_leap_day_yoy) |
| 733 | 見出し行つきの CSV を何本も縦につなぐと、見出し行が何行まざり、数の列はどうなるのか？ | [733_repeated_header_rows](articles/733_repeated_header_rows) |
| 734 | 「1回1万円以上の注文がある顧客」と「合計1万円以上の顧客」を取り違えると、何人がずれるのか？ | [734_where_vs_having](articles/734_where_vs_having) |
| 735 | ユニークな人数を近似の関数で数えると、件数の少ない区分でどれだけずれるのか？ | [735_approx_count_distinct_error](articles/735_approx_count_distinct_error) |
| 741 | 16桁以上の番号を Excel で開くと、何件の番号が別の値に変わり、何件が同じ番号になるのか？ | [741_excel_15_digit_ids](articles/741_excel_15_digit_ids) |
| 742 | LEFT JOIN のあと COUNT(*) で注文数を数えると、注文0件の顧客は何件と数えられるのか？ | [742_left_join_count_star](articles/742_left_join_count_star) |
| 743 | 退会した会員の番号を新しい会員に使い回すと、何人の新しい会員に前の人の購入がつくのか？ | [743_id_reuse_history](articles/743_id_reuse_history) |
| 744 | 会員番号の偶数と奇数で2群に分けると、番号の振り方によって群の間にどれだけ差が出るのか？ | [744_id_parity_split](articles/744_id_parity_split) |
| 745 | 4月始まりの年度と暦年で前年比を出すと、伸びの年はどれだけずれて見えるのか？ | [745_fiscal_vs_calendar_year](articles/745_fiscal_vs_calendar_year) |
| 751 | PIVOT の列を固定で書いておくと、あとから増えた区分の売上は何%消えるのか？ | [751_pivot_fixed_columns](articles/751_pivot_fixed_columns) |
| 752 | 先頭に BOM のついた CSV を csv モジュールで読むと、最初の列名が一致せず、何行の売上が黙って集計から落ちるのか？ | [752_csv_bom_header](articles/752_csv_bom_header) |
| 753 | 1年が53週ある年に「第N週」で前年同週比を出すと、何週の前年比が本当の伸びから外れるのか？ | [753_week53_yoy](articles/753_week53_yoy) |
| 754 | 欠品率を「欠品した SKU の数」で数えるか「売上の重み」で数えるかで、店の比べ方はどれだけ変わるのか？ | [754_stockout_rate_weighting](articles/754_stockout_rate_weighting) |
| 755 | 時刻つきの日時のまま GROUP BY すると、日ごとの集計は何行に分かれてしまうのか？ | [755_group_by_datetime_not_date](articles/755_group_by_datetime_not_date) |
| 761 | 長さの足りない列に名前を入れると、後ろが切れて別の商品が同じ名前になるのは何件か？ | [761_varchar_truncation_collision](articles/761_varchar_truncation_collision) |
| 762 | 申込率を小数の桁の少ない DECIMAL に入れると、率はどれだけ丸まり、店の順位はどれだけ入れ替わるのか？ | [762_decimal_scale_division](articles/762_decimal_scale_division) |
| 763 | 継続月数を0から数えるか1から数えるかで、継続率の表はどれだけずれて読まれるのか？ | [763_month_index_zero_one](articles/763_month_index_zero_one) |
| 764 | pandas の groupby が欠けたキーの行を黙って落とすと、合計はどれだけ減るのか？ | [764_pandas_groupby_dropna](articles/764_pandas_groupby_dropna) |
| 765 | 「NA」という区分名を pandas で読むと、何行が欠けた値になってしまうのか？ | [765_pandas_na_string](articles/765_pandas_na_string) |
| 771 | 104万行を超える CSV を Excel で開くと、どれだけの行と売上が消えるのか？ | [771_excel_row_limit](articles/771_excel_row_limit) |
| 772 | 「12:30 AM」のような午前午後の表記を読み違えると、時間帯別の件数はどれだけずれるのか？ | [772_ampm_parsing](articles/772_ampm_parsing) |
| 773 | 列の順番が違う2つの表を UNION ALL でつなぐと、何行の値が別の列に入るのか？ | [773_union_column_order](articles/773_union_column_order) |
| 774 | 達成率を四捨五入してから「100%以上」を数えると、何店が「達成」に入ってしまうのか？ | [774_achievement_rounding](articles/774_achievement_rounding) |
| 775 | 前回の順位と比べるとき、前回いなかった店を外すかどうかで、「順位が上がった店」の数はどれだけ変わるのか？ | [775_rank_change_new_entries](articles/775_rank_change_new_entries) |
| 781 | 数の列に文字が1つまざると、Excel のピボットの集計はどう変わり、合計はどれだけ消えるのか？ | [781_pivot_count_default](articles/781_pivot_count_default) |
| 782 | 表の1列だけを並べ替えると、何行の値が別の行とつながってしまうのか？ | [782_partial_sort_misalign](articles/782_partial_sort_misalign) |
| 783 | 合計の範囲を固定したまま行を足していくと、月の合計はどれだけ少なく出るのか？ | [783_sum_range_not_extended](articles/783_sum_range_not_extended) |
| 784 | 法人のまとめ買いを混ぜたまま客単価を見ると、個人の客単価はどれだけ高く見えるのか？ | [784_bulk_buyer_mixing](articles/784_bulk_buyer_mixing) |
| 785 | 「1時間30分」を「1.30」と書いて合計すると、月の作業時間はどれだけ少なく出るのか？ | [785_hhmm_decimal_confusion](articles/785_hhmm_decimal_confusion) |
| 791 | 0で割るのを NULLIF で避けると、その店は平均から黙って消え、全体の率はどれだけ変わるのか？ | [791_nullif_drop_from_avg](articles/791_nullif_drop_from_avg) |
| 792 | 率の列に「0.05」と「5」が混ざっていると、平均はどれだけずれるのか？ | [792_percent_scale_mix](articles/792_percent_scale_mix) |
| 793 | 空の文字と NULL を区別せずに数えると、未入力の件数はどれだけずれるのか？ | [793_empty_string_vs_null](articles/793_empty_string_vs_null) |
| 794 | 1つの商品が2つのカテゴリに入る表でカテゴリ別に売上を足すと、全体の何倍になるのか？ | [794_multi_category_double_count](articles/794_multi_category_double_count) |
| 795 | 月の数字を週に直すとき4で割るか4.33で割るかで、週あたりの値はどれだけ違うのか？ | [795_weeks_per_month](articles/795_weeks_per_month) |
| F234 | 価格を1%上げると、買われる量は何%減るのか？ | [F234_price_elasticity_practice](articles/F234_price_elasticity_practice) |
| F237 | A/B テストを途中で見ると、何がまずいのか？ | [F237_ab_test_peeking_sequential](articles/F237_ab_test_peeking_sequential) |
| F243 | どの指標を見れば、売上の変化の理由が分かるのか？ | [F243_kpi_tree_decomposition](articles/F243_kpi_tree_decomposition) |

## 2. Excel の動きを Python で再現した記事（13本）
Excel の関数やピボットの動きは Python で再現したもので、Excel では試していません。

| # | 問い | フォルダ |
|---|---|---|
| 327 | C# の Math.Round と SQL Server の ROUND と Excel の ROUND は、同じ答えを返すのか？ | [327_rounding_csharp_sql_excel](articles/327_rounding_csharp_sql_excel) |
| 371 | 中央値や90%点は、計算の定義でどれだけ違うのか？ | [371_percentile_definitions](articles/371_percentile_definitions) |
| 372 | CSV を Excel で開いて保存すると、何セルが変わってしまうのか？ | [372_csv_excel_roundtrip](articles/372_csv_excel_roundtrip) |
| 374 | VLOOKUP は、どんなときに黙って間違った値を返すのか？ | [374_vlookup_silent_errors](articles/374_vlookup_silent_errors) |
| 492 | Excelの日付のシリアル値を読み替えるとき、起点の取り違えで何行が何日ずれるのか？ | [492_excel_serial_dates](articles/492_excel_serial_dates) |
| 515 | Excel の SUM でフィルタで隠した行も含めて合計すると、表の合計は何%多くなるのか？ | [515_excel_sum_vs_subtotal_hidden](articles/515_excel_sum_vs_subtotal_hidden) |
| 685 | Excel の COUNTIF で「*」や「?」を含む品名を数えると、何件を多く数えるのか？ | [685_countif_wildcards](articles/685_countif_wildcards) |
| 714 | 空白のセルと0のセルが混ざった列を Excel の AVERAGE で平均すると、値はどれだけ変わるのか？ | [714_excel_average_blank_zero](articles/714_excel_average_blank_zero) |
| 741 | 16桁以上の番号を Excel で開くと、何件の番号が別の値に変わり、何件が同じ番号になるのか？ | [741_excel_15_digit_ids](articles/741_excel_15_digit_ids) |
| 771 | 104万行を超える CSV を Excel で開くと、どれだけの行と売上が消えるのか？ | [771_excel_row_limit](articles/771_excel_row_limit) |
| 781 | 数の列に文字が1つまざると、Excel のピボットの集計はどう変わり、合計はどれだけ消えるのか？ | [781_pivot_count_default](articles/781_pivot_count_default) |
| 782 | 表の1列だけを並べ替えると、何行の値が別の行とつながってしまうのか？ | [782_partial_sort_misalign](articles/782_partial_sort_misalign) |
| 783 | 合計の範囲を固定したまま行を足していくと、月の合計はどれだけ少なく出るのか？ | [783_sum_range_not_extended](articles/783_sum_range_not_extended) |

## 確かめられたら
SQL Server・Excel で試して結果が分かったものは、この一覧から外し、各記事の README に結果を書きます。
