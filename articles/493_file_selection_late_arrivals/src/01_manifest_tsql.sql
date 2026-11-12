-- 493：取り込み済みのファイルを「名前と中身（版）」で記録し、置き直しは入れ直す（T-SQL、未検証）
CREATE TABLE load_manifest (
    file_name   NVARCHAR(260) NOT NULL,
    file_hash   CHAR(64)      NOT NULL,     -- 中身のハッシュ（SHA-256 など）。版の見分けに使う
    loaded_at   DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
    row_count   INT           NOT NULL,
    CONSTRAINT pk_manifest PRIMARY KEY (file_name, file_hash)
);
-- 取り込む前に、置き場のファイル一覧（#files：file_name, file_hash）と突き合わせる
SELECT f.file_name, f.file_hash
FROM #files f
LEFT JOIN load_manifest m ON m.file_name = f.file_name AND m.file_hash = f.file_hash
WHERE m.file_name IS NULL;               -- まだ入れていない（新しい名前か、直した版）

-- 直した版のときは、同じ名前で入れた行を消してから入れ直す（1つのトランザクションで）
BEGIN TRAN;
  DELETE FROM sales WHERE source_file = @file_name;
  -- INSERT INTO sales (...) SELECT ... FROM stg_sales WHERE source_file = @file_name;
  INSERT INTO load_manifest (file_name, file_hash, row_count) VALUES (@file_name, @file_hash, @rows);
COMMIT;
