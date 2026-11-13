-- T-SQL：未検証（SQL Server では動かしていない）
-- 差分の取り込み。dbo.src_log(event_id, row_key, updated_at datetime2(0), seq bigint)
-- @wm：前回取り込んだ行の updated_at の最大値、@wm_seq：前回の seq の最大値
SELECT * FROM dbo.src_log WHERE updated_at >  @wm;                         -- E1
SELECT * FROM dbo.src_log WHERE updated_at >= @wm;                         -- E2
SELECT * FROM dbo.src_log WHERE updated_at >= DATEADD(second, -60, @wm);   -- E3（キーで上書きして重なりを消す）
SELECT * FROM dbo.src_log WHERE seq > @wm_seq;                             -- E4（コミット順の連番）
