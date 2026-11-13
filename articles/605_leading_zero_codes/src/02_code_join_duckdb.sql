-- 明細のコード（先頭の0が落ちたものを含む）を、マスタのコード（文字）につなぐ（DuckDB 版）
-- K1 文字のまま結合：先頭の0が落ちた行はつながらない
SELECT COUNT(*) AS n, COUNT(m.code) AS matched
FROM lines d LEFT JOIN master m ON m.code = d.code_raw;
-- K2 両方を整数にして結合：つながるが、'0123' と '00123' のように数として同じコードがあると1行が2行に増える
SELECT COUNT(*) AS n, COUNT(m.code) AS matched
FROM lines d LEFT JOIN master m ON CAST(m.code AS INTEGER) = CAST(d.code_raw AS INTEGER);
-- K3 両方を6桁に0で埋めて結合（LPAD）：K2 と同じく、数として同じコードを取り違える
SELECT COUNT(*) AS n, COUNT(m.code) AS matched
FROM lines d LEFT JOIN master m ON LPAD(m.code, 6, '0') = LPAD(d.code_raw, 6, '0');
