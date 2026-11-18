# SOURCES（元データの取得元）

取得日：2026-11-18（01_fetch.py と同じ URL から取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| jasso_nippon_2009.pdf | 2009年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2020/08/date2009n.pdf | a604671cd06e |
| jasso_nippon_2010.pdf | 2010年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2020/08/date2010n.pdf | 15a55d3c8264 |
| jasso_nippon_2011.pdf | 2011年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2020/08/date2011n.pdf | 62475c6f5a2f |
| jasso_nippon_2012.pdf | 2012年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2020/08/date2012n.pdf | e9f5993770cb |
| jasso_nippon_2013.pdf | 2013年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2020/08/date2013n.pdf | 0b519821f6c6 |
| jasso_nippon_2014.pdf | 2014年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2020/08/date2014n.pdf | e3924b320171 |
| jasso_nippon_2015.pdf | 2015年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2020/08/date2015n.pdf | 7b3838a67c1a |
| jasso_nippon_2016.pdf | 2016年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2020/08/date2016n.pdf | 9be835e7632d |
| jasso_nippon_2017.pdf | 2017年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2020/08/date2017n.pdf | e5feecdeb3e8 |
| jasso_nippon_2018.pdf | 2018年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2020/08/date2018n.pdf | 55cf51b45d4d |
| jasso_nippon_2019.pdf | 2019年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2021/03/date2019n.pdf | e6c1a23b0296 |
| jasso_nippon_2020.pdf | 2020年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2022/11/date2020n.pdf | fc152188a041 |
| jasso_nippon_2021.pdf | 2021年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2023/02/date2021n.pdf | da096e9b42b5 |
| jasso_nippon_2022.pdf | 2022年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2024/04/data2022n.pdf | bbd5ca1d4ac3 |
| jasso_nippon_2023.pdf | 2023年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2025/04/data2023n.pdf | ee9a98ea44a4 |
| jasso_nippon_2024.pdf | 2024年度 日本人学生留学状況調査結果（JASSO） | https://www.studyinjapan.go.jp/ja/_mt/2026/05/data2024n.pdf | 4086f6caa9cf |
| mext_2024-05-24_release.pdf | 文部科学省「外国人留学生在籍状況調査」及び「日本人の海外留学者数」等について（2024年5月24日） | https://www.mext.go.jp/content/20260529-mxt_kotokoku02-000027891_3.pdf | 2fa22f397eb4 |
| mext_2025-04-30_release.pdf | 文部科学省「日本人学生の海外留学状況」及び「外国人留学生の在籍状況」を公表します（2025年4月30日） | https://www.mext.go.jp/content/20250430-mxt_kotokoku02-000027891_2.pdf | aa2628db3d6e |
| mext_2026-05-29_release.pdf | 文部科学省「日本人学生の海外留学状況」及び「外国人留学生の在籍状況」を公表します（2026年5月29日） | https://www.mext.go.jp/content/20250430-mxt_kotokoku02-000027891_1.pdf | c7b7ee2ebe46 |
| nenji_02_enrollment.xlsx | 学校基本調査 年次統計 総括表2 在学者数（昭和23年～） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031852302&fileKind=0 | 817eaea086fb |

出典：独立行政法人日本学生支援機構「日本人学生留学状況調査」（https://www.studyinjapan.go.jp/ja/statistics/japanese-students/）、
文部科学省「日本人の海外留学者数」（https://www.mext.go.jp/a_menu/koutou/ryugaku/1412692_00003.htm）、
文部科学省「学校基本調査」年次統計（e-Stat）。
注：文部科学省の PDF は、URL の日付と中身の公表日が違うものがある（ページのリンクのとおりに取った）。
PDF の表は src/01b_extract.py（pdftotext）で data/extract_*.csv に読み取って同梱している。
