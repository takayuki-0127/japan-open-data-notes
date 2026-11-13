-- T-SQL：未検証（SQL Server では動かしていない）
SELECT COUNT(*) FROM dbo.events WHERE event_type = 'apply';                                                        -- D0
SELECT COUNT(*) FROM (SELECT DISTINCT * FROM dbo.events WHERE event_type = 'apply') AS t;                           -- D1
SELECT COUNT(*) FROM (SELECT DISTINCT event_id, user_id, event_type, client_ts FROM dbo.events WHERE event_type = 'apply') AS t;  -- D2
SELECT COUNT(DISTINCT event_id) FROM dbo.events WHERE event_type = 'apply';                                         -- D3
