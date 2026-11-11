-- F244 集計 SQL の誤り版と正しい版（sqlite）

-- A1 [bad] 粒度・二重計上：2025年の業態別販売額（品目の合計行・中分類まで足す）
SELECT gyotai, SUM(sales) FROM retail WHERE ym LIKE '2025-%' GROUP BY gyotai;

-- A1 [good] 粒度・二重計上：2025年の業態別販売額（品目の合計行・中分類まで足す）
SELECT r.gyotai, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_leaf=1 AND r.ym LIKE '2025-%' GROUP BY r.gyotai;

-- A2 [bad] 粒度・二重計上：家電大型専門店の月次販売額（2021年からの細かい分類も足す）
SELECT ym, SUM(sales) FROM retail WHERE gyotai='家電大型専門店' AND item<>'商品販売額' GROUP BY ym;

-- A2 [good] 粒度・二重計上：家電大型専門店の月次販売額（2021年からの細かい分類も足す）
SELECT r.ym, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_leaf=1 AND r.gyotai='家電大型専門店' GROUP BY r.ym;

-- A3 [bad] JOIN の行の増え方：月次のスーパー販売額に祝日の数を付ける（祝日の表をそのまま JOIN）
SELECT r.ym, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item LEFT JOIN holidays h ON substr(h.date,1,7)=r.ym WHERE d.is_total=1 AND r.gyotai='スーパー' GROUP BY r.ym;

-- A3 [good] JOIN の行の増え方：月次のスーパー販売額に祝日の数を付ける（祝日の表をそのまま JOIN）
SELECT r.ym, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item LEFT JOIN (SELECT substr(date,1,7) AS ym, COUNT(*) AS n_hol FROM holidays GROUP BY substr(date,1,7)) h ON h.ym=r.ym WHERE d.is_total=1 AND r.gyotai='スーパー' GROUP BY r.ym;

-- A4 [bad] 整数の割り算：スーパーの前年同月比（%）
SELECT ym, (s - s12) * 100 / s12 FROM (SELECT r.ym, r.sales AS s, LAG(r.sales,12) OVER (ORDER BY r.ym) AS s12 FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND r.gyotai='スーパー') t WHERE s12 IS NOT NULL;

-- A4 [good] 整数の割り算：スーパーの前年同月比（%）
SELECT ym, CAST(s - s12 AS REAL) * 100 / s12 FROM (SELECT r.ym, r.sales AS s, LAG(r.sales,12) OVER (ORDER BY r.ym) AS s12 FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND r.gyotai='スーパー') t WHERE s12 IS NOT NULL;

-- A5 [bad] 期間の境目：2024年度（2024年4月〜2025年3月）の業態別販売額
SELECT r.gyotai, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND substr(r.ym,1,4)='2024' GROUP BY r.gyotai;

-- A5 [good] 期間の境目：2024年度（2024年4月〜2025年3月）の業態別販売額
SELECT r.gyotai, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND r.ym >= '2024-04' AND r.ym <= '2025-03' GROUP BY r.gyotai;

-- A6 [bad] ウィンドウ関数：コンビニの直近12か月の合計（12か月そろわない月も出す）
SELECT ym, SUM(s) OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) FROM (SELECT r.ym, r.sales AS s FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND r.gyotai='コンビニ') t;

-- A6 [good] ウィンドウ関数：コンビニの直近12か月の合計（12か月そろわない月も出す）
SELECT ym, s12 FROM (SELECT ym, SUM(s) OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS s12, COUNT(*) OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS n FROM (SELECT r.ym, r.sales AS s FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND r.gyotai='コンビニ') t) u WHERE n = 12;

-- B1 [bad] JOIN の行の増え方：月次の売上（支払いの表を JOIN してから明細を足す）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id JOIN payments p ON p.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B1 [good] JOIN の行の増え方：月次の売上（支払いの表を JOIN してから明細を足す）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id  WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B2 [bad] JOIN の行の増え方：月次の売上（支払いと発送の両方を JOIN）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id JOIN payments p ON p.order_id=o.order_id JOIN shipments s ON s.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B2 [good] JOIN の行の増え方：月次の売上（支払いと発送の両方を JOIN）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id  WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B3 [bad] NULL：月次の値引き後の売上（クーポンなしの値引きは NULL）
SELECT m, SUM(g - discount_yen) FROM (SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7) AS m, o.order_id, MAX(o.discount_yen) AS discount_yen, SUM(i.qty*i.unit_price) AS g FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7), o.order_id) t GROUP BY m;

-- B3 [good] NULL：月次の値引き後の売上（クーポンなしの値引きは NULL）
SELECT m, SUM(g - COALESCE(discount_yen,0)) FROM (SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7) AS m, o.order_id, MAX(o.discount_yen) AS discount_yen, SUM(i.qty*i.unit_price) AS g FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7), o.order_id) t GROUP BY m;

-- B4 [bad] NULL：月次の1注文あたり平均値引き額（全注文で割る）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), AVG(discount_yen) FROM orders o WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B4 [good] NULL：月次の1注文あたり平均値引き額（全注文で割る）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), AVG(CAST(COALESCE(discount_yen,0) AS REAL)) FROM orders o WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B5 [bad] NULL：だれも紹介していない顧客の数（NOT IN と NULL）
SELECT 'all', COUNT(*) FROM customers c WHERE c.customer_id NOT IN (SELECT referrer_id FROM customers);

-- B5 [good] NULL：だれも紹介していない顧客の数（NOT IN と NULL）
SELECT 'all', COUNT(*) FROM customers c WHERE NOT EXISTS (SELECT 1 FROM customers x WHERE x.referrer_id = c.customer_id);

-- B6 [bad] 数え方（DISTINCT）：月次の購入した顧客の数（日ごとの人数を足す）
SELECT m, SUM(n) FROM (SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7) AS m, substr(datetime(o.ts_utc, '+9 hours'),1,10) AS d, COUNT(DISTINCT o.customer_id) AS n FROM orders o WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7), substr(datetime(o.ts_utc, '+9 hours'),1,10)) t GROUP BY m;

-- B6 [good] 数え方（DISTINCT）：月次の購入した顧客の数（日ごとの人数を足す）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), COUNT(DISTINCT o.customer_id) FROM orders o WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B7 [bad] 数え方（DISTINCT）：月次の購入した顧客の数（明細を JOIN して COUNT(*)）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), COUNT(*) FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B7 [good] 数え方（DISTINCT）：月次の購入した顧客の数（明細を JOIN して COUNT(*)）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), COUNT(DISTINCT o.customer_id) FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B8 [bad] 日付・時間帯：月次の売上（UTC のまま月に分ける）
SELECT substr(o.ts_utc,1,7), SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(o.ts_utc,1,7);

-- B8 [good] 日付・時間帯：月次の売上（UTC のまま月に分ける）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id  WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B9 [bad] 日付・時間帯：12月の売上（BETWEEN '12-01' AND '12-31' で時刻つきの列を絞る）
SELECT 'dec', SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' AND datetime(o.ts_utc, '+9 hours') BETWEEN '2025-12-01' AND '2025-12-31';

-- B9 [good] 日付・時間帯：12月の売上（BETWEEN '12-01' AND '12-31' で時刻つきの列を絞る）
SELECT 'dec', SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' AND datetime(o.ts_utc, '+9 hours') >= '2025-12-01' AND datetime(o.ts_utc, '+9 hours') < '2026-01-01';

-- B10 [bad] ウィンドウ関数：顧客ごとの最後の注文日（LAST_VALUE の既定の範囲）
SELECT customer_id, CAST(julianday(lastd) - julianday('2025-01-01') AS INTEGER) FROM (SELECT DISTINCT o.customer_id, substr(LAST_VALUE(datetime(o.ts_utc, '+9 hours')) OVER (PARTITION BY o.customer_id ORDER BY o.ts_utc),1,10) AS lastd FROM orders o WHERE o.status='paid') t;

-- B10 [good] ウィンドウ関数：顧客ごとの最後の注文日（LAST_VALUE の既定の範囲）
SELECT customer_id, CAST(julianday(lastd) - julianday('2025-01-01') AS INTEGER) FROM (SELECT DISTINCT o.customer_id, substr(LAST_VALUE(datetime(o.ts_utc, '+9 hours')) OVER (PARTITION BY o.customer_id ORDER BY o.ts_utc ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING),1,10) AS lastd FROM orders o WHERE o.status='paid') t;

-- B11 [bad] ウィンドウ関数：日次売上の7日移動平均（注文のない日は行がない）
SELECT d, AVG(g) OVER (ORDER BY d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) FROM (SELECT substr(datetime(o.ts_utc, '+9 hours'),1,10) AS d, SUM(i.qty*i.unit_price) AS g FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,10)) t;

-- B11 [good] ウィンドウ関数：日次売上の7日移動平均（注文のない日は行がない）
SELECT d, ma FROM (SELECT c.d, AVG(CAST(COALESCE(t.g,0) AS REAL)) OVER (ORDER BY c.d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma, COUNT(*) OVER (ORDER BY c.d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS n FROM dates c LEFT JOIN (SELECT substr(datetime(o.ts_utc, '+9 hours'),1,10) AS d, SUM(i.qty*i.unit_price) AS g FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,10)) t ON t.d=c.d) u WHERE n = 7;

-- B12 [bad] 整数の割り算：日次の購入率（注文数 ÷ 訪問数）
SELECT s.d, COALESCE(n,0) / s.sessions FROM sessions s LEFT JOIN (SELECT substr(datetime(o.ts_utc, '+9 hours'),1,10) AS d, COUNT(*) AS n FROM orders o WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,10)) t ON t.d=s.d;

-- B12 [good] 整数の割り算：日次の購入率（注文数 ÷ 訪問数）
SELECT s.d, CAST(COALESCE(n,0) AS REAL) / s.sessions FROM sessions s LEFT JOIN (SELECT substr(datetime(o.ts_utc, '+9 hours'),1,10) AS d, COUNT(*) AS n FROM orders o WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,10)) t ON t.d=s.d;

-- B13 [bad] 定義のずれ：月次の購入率（日ごとの率の平均）
SELECT substr(s.d,1,7), AVG(CAST(COALESCE(n,0) AS REAL) / s.sessions) FROM sessions s LEFT JOIN (SELECT substr(datetime(o.ts_utc, '+9 hours'),1,10) AS d, COUNT(*) AS n FROM orders o WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,10)) t ON t.d=s.d GROUP BY substr(s.d,1,7);

-- B13 [good] 定義のずれ：月次の購入率（日ごとの率の平均）
SELECT substr(s.d,1,7), SUM(CAST(COALESCE(n,0) AS REAL)) / SUM(s.sessions) FROM sessions s LEFT JOIN (SELECT substr(datetime(o.ts_utc, '+9 hours'),1,10) AS d, COUNT(*) AS n FROM orders o WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,10)) t ON t.d=s.d GROUP BY substr(s.d,1,7);

-- B14 [bad] JOIN の行の増え方：月次の返品額（返品を注文番号だけで JOIN）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), SUM(r.ret_qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id JOIN returns r ON r.order_id=i.order_id WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B14 [good] JOIN の行の増え方：月次の返品額（返品を注文番号だけで JOIN）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), SUM(r.ret_qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id JOIN returns r ON r.order_id=i.order_id AND r.line_no=i.line_no WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B15 [bad] 絞り込みの漏れ：月次の売上（キャンセルを除き忘れ）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);

-- B15 [good] 絞り込みの漏れ：月次の売上（キャンセルを除き忘れ）
SELECT substr(datetime(o.ts_utc, '+9 hours'),1,7), SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id  WHERE o.status='paid' GROUP BY substr(datetime(o.ts_utc, '+9 hours'),1,7);
