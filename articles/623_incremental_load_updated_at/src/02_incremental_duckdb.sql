-- 差分の取り込み（DuckDB 版）。src_log(event_id, row_key, updated_at, commit_at, seq)
-- 取り込みの時点 :run_at に見えている（コミット済みの）行のうち、前回の印より後のものを取る
-- E1：updated_at > 前回の最大値
SELECT COUNT(*) FROM src_log WHERE commit_at <= $run_at AND updated_at > $wm;
-- E2：updated_at >= 前回の最大値
SELECT COUNT(*) FROM src_log WHERE commit_at <= $run_at AND updated_at >= $wm;
-- E3：updated_at >= 前回の最大値 − 60秒（重ねて取り、キーで上書きする）
SELECT COUNT(*) FROM src_log WHERE commit_at <= $run_at AND updated_at >= $wm - INTERVAL 60 SECOND;
-- E4：コミット順の連番 seq > 前回の最大値
SELECT COUNT(*) FROM src_log WHERE commit_at <= $run_at AND seq > $wm_seq;
