-- 送り直しで二重に届いたイベントの数え方（DuckDB 版）
-- events(event_id, user_id, event_type, client_ts, received_at, attempt)
-- D0 そのまま
SELECT COUNT(*) FROM events WHERE event_type = 'apply';
-- D1 全部の列が同じ行だけを除く
SELECT COUNT(*) FROM (SELECT DISTINCT * FROM events WHERE event_type = 'apply');
-- D2 受け取り時刻と試行回数を除いた列で同じ行を除く
SELECT COUNT(*) FROM (SELECT DISTINCT event_id, user_id, event_type, client_ts FROM events WHERE event_type = 'apply');
-- D3 イベントIDで1行にする
SELECT COUNT(DISTINCT event_id) FROM events WHERE event_type = 'apply';
