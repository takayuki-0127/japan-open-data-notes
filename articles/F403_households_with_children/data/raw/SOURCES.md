# SOURCES（元データの取得元）

取得日：2026-11-16（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字 |
|---|---|---|---|
| kiso2025_t014_children_by_year.csv | 国民生活基礎調査 令和7年 第14表 世帯数－構成割合－平均児童数，児童の有－児童数－無・年次別（1975〜2025年） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040473979&fileKind=1 | bc812573188b |
| kiso2025_t089_children_by_structure.csv | 国民生活基礎調査 令和7年 第89表 児童のいる世帯数，児童数・世帯構造別 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040474054&fileKind=1 | 6bc3c7f84d45 |
| kiso2013_t075_children_by_structure.csv | 国民生活基礎調査 平成25年 第75表 児童のいる世帯数，児童数・世帯構造別 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000025674640&fileKind=1 | e7d48c99c52b |
| kiso2025_t153_children_by_pref.csv | 国民生活基礎調査 令和7年 第153表 世帯数，児童の有－児童数－無・都道府県別 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040474118&fileKind=1 | 09cfca7d0cb1 |
| kiso2013_t015_children_by_pref.csv | 国民生活基礎調査 平成25年 第3巻 第15表 世帯数，児童の有－児童数－無・都道府県別 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000025674723&fileKind=1 | a5a09af32a43 |
| kiso2025_t155_children_structure_by_pref.csv | 国民生活基礎調査 令和7年 第155表 児童のいる世帯数，世帯構造・都道府県別 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040474120&fileKind=1 | 7c8e65ba8dab |
| kiso2013_t017_children_structure_by_pref.csv | 国民生活基礎調査 平成25年 第3巻 第17表 児童のいる世帯数，世帯構造・都道府県別 | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000025674725&fileKind=1 | e87e409ebc59 |
| census2025_t9_1.xlsx | 国勢調査 令和7年 人口等基本集計 第9-1表 世帯の家族類型、世帯員の年齢による世帯の種類別一般世帯数（原数値） | https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040506456&fileKind=0 | e0d5153cbad4 |

出典：厚生労働省「国民生活基礎調査」、総務省「国勢調査」（e-Stat）。CSV は Shift_JIS。
児童の定義：2023年以前は「18歳未満の未婚の者」、2024年以降は「18歳未満の者」（厚生労働省「2024（令和6）年 国民生活基礎調査の概況」用語の解説 https://www.mhlw.go.jp/toukei/saikin/hw/k-tyosa/k-tyosa24/dl/10.pdf ）。
