-- F232 SQL（SQL Server 互換の書き方）：予測と誤差を入れる表
CREATE TABLE forecast_long (
    method   NVARCHAR(40)  NOT NULL,  -- そろえ方（ベース・MinT など）
    node     NVARCHAR(80)  NOT NULL,  -- 例：'百貨店/飲食料品'
    parent   NVARCHAR(80)  NULL,      -- 1つ上のノード（全体は NULL か空）
    level    INT           NOT NULL,  -- 0=全体 1=業態 2=中分類 3=商品
    ym       CHAR(7)       NOT NULL,  -- 'YYYY-MM'
    forecast FLOAT         NOT NULL   -- 販売額（百万円）
);
CREATE TABLE ape_long (
    cond      NVARCHAR(60) NOT NULL,  -- 条件（主・コロナ前 など）
    origin    CHAR(7)      NOT NULL,  -- 予測の起点
    method    NVARCHAR(40) NOT NULL,
    node      NVARCHAR(80) NOT NULL,
    level     INT          NOT NULL,
    horizon   INT          NOT NULL,  -- 何か月先（1〜12）
    ape       FLOAT        NOT NULL,  -- 絶対パーセント誤差
    actual    FLOAT        NOT NULL
);
