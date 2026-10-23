# japan-open-data-notes

日本の政府統計・オープンデータを分析して、note に書いた記事のコードとデータを置いているリポジトリです。

- 135番以降の記事は `articles/<番号>_<名前>/` に1記事1フォルダで置いています（README・データ・図・集計結果・コード）
- 134番までの記事は、記事ごとのリポジトリにあります（下の表のリンク先）
- 以前の記事で使った図は [note-figures](https://github.com/takayuki-0127/note-figures) にあります

## まず見てほしい記事
| # | 記事 | 見どころ |
|---|---|---|
| 95 | 就業者は13年で550万人増えた。増えたのは女性と65歳以上で、人口が減る分を「働く人の割合」が912万人押し上げた | 就業者の増加を「人口」と「働く人の割合」に分解（要因分解） |
| 102 | 食料自給率73%→38%の低下、半分強は「米を食べなくなった」など食べるものの変化だった | 食料自給率の低下を、食べるものの構成と品目に分ける |
| 110 | 東南アジアは12月、欧米は4月と10月、韓国は1月。外国人が日本に来る季節は国籍で4つの形に分かれた | 国籍ごとの月別入国をクラスタリングで4つの形に分類 |
| 137 | 市区町村の歳出の4割は福祉（民生費）。12年で1.5倍になり、伸びが大きかったのは子どもと障害者福祉など | e-Stat の CSV から必要な行だけを抜き出して市区町村×年度の表を作るところからコード化 |

## 記事の一覧（85番以降）
| # | 記事のタイトル | コードとデータ |
|---|---|---|
| 85 | 食品の値上げで、米は2倍でも量は減らず、魚や果物は大きく減った。家計調査の127品目で見る | [household-spending-japan](https://github.com/takayuki-0127/household-spending-japan) |
| 86 | 同じ値上げでも、年収の低い世帯は支出の6.3%、高い世帯は3.6%。エンゲル係数は34.9%まで上がった | [household-spending-japan](https://github.com/takayuki-0127/household-spending-japan) |
| 87 | 実質賃金は1997年から18%下がった。でも1時間当たりでは3%減。物価と同じくらい「働く時間」が効いていた | [monthly-labour-survey-japan](https://github.com/takayuki-0127/monthly-labour-survey-japan) |
| 88 | ボーナスは基本給の3倍振れる。2009年は製造業、2020年は宿泊・飲食と娯楽で大きく減った | [monthly-labour-survey-japan](https://github.com/takayuki-0127/monthly-labour-survey-japan) |
| 89 | 建設躯体工事は7.9倍、一般事務は0.34倍。人手不足は職業で20倍以上の差があった | [job-openings-japan](https://github.com/takayuki-0127/job-openings-japan) |
| 90 | 都道府県の求人倍率の差は50年で縮んだが、2019年から止まった。東京都は働く場所で数えると42位 | [job-openings-japan](https://github.com/takayuki-0127/job-openings-japan) |
| 91 | 新築の家は1戸当たり97.5㎡から76.8㎡に。持家は1996年の141㎡から112㎡へ小さくなっていた | [housing-starts-japan](https://github.com/takayuki-0127/housing-starts-japan) |
| 92 | 木造の割合は43%に戻った。でも住宅以外の木造は8%どまりで、伸びたのは病院・診療所と事務所だった | [housing-starts-japan](https://github.com/takayuki-0127/housing-starts-japan) |
| 93 | 裸眼視力1.0未満の小学生は46年で18%→36%に倍増。高校生は7割を超えた | [school-health-japan](https://github.com/takayuki-0127/school-health-japan) |
| 94 | 17歳の身長は1994年度が最高で、30年ほぼ横ばい。それでも中学生男子は今が一番高い | [school-health-japan](https://github.com/takayuki-0127/school-health-japan) |
| 95 | 就業者は13年で550万人増えた。増えたのは女性と65歳以上で、人口が減る分を「働く人の割合」が912万人押し上げた | [labour-force-japan](https://github.com/takayuki-0127/labour-force-japan) |
| 96 | 非正規の割合はほとんどの年齢で下がっていた。全体が横ばいに見えるのは、65歳以上の働く人が増えたから | [labour-force-japan](https://github.com/takayuki-0127/labour-force-japan) |
| 97 | ドラッグストアの売上は11年で約1.9倍。伸びの中心は食品で、売上の3分の1を超えた | [retail-sales-japan](https://github.com/takayuki-0127/retail-sales-japan) |
| 98 | 2019年より売上が多いのはスーパーやドラッグストア。でもコロナ前の伸び方には、コンビニとドラッグストアが届いていなかった | [retail-sales-japan](https://github.com/takayuki-0127/retail-sales-japan) |
| 99 | 日本の海面は約40年で10cm上がった。でも120年で見ると、1950年頃にも今と同じくらい高い時期があった | [jma-sea-level-sst](https://github.com/takayuki-0127/jma-sea-level-sst) |
| 100 | 日本近海の海水温は世界平均の約2倍の速さで上がっていた。同じ期間でそろえると2.0倍、最近40年は2.3倍 | [jma-sea-level-sst](https://github.com/takayuki-0127/jma-sea-level-sst) |
| 101 | 米は1人年114.9kgから53.4kgへ半分以下に。肉は6.6倍、牛乳・乳製品は4.1倍になった60年余り | [food-balance-japan](https://github.com/takayuki-0127/food-balance-japan) |
| 102 | 食料自給率73%→38%の低下、半分強は「米を食べなくなった」など食べるものの変化だった | [food-balance-japan](https://github.com/takayuki-0127/food-balance-japan) |
| 103 | 大人の1日の歩数は20年で男性7%・女性12%減った。減ったのは20〜60代で、70歳以上はほぼ横ばい | [health-nutrition-survey-japan](https://github.com/takayuki-0127/health-nutrition-survey-japan) |
| 104 | 睡眠6時間未満は50代で5割に。朝食を抜く40〜50代男性は、若いころから抜いていた世代だった | [health-nutrition-survey-japan](https://github.com/takayuki-0127/health-nutrition-survey-japan) |
| 105 | 牛乳1Lは那覇364円・長岡214円。同じ品目の値段の都市差は、16年でははっきり縮まっていなかった | [retail-prices-japan](https://github.com/takayuki-0127/retail-prices-japan) |
| 106 | 値上げは「幅」より「回数」が増えた。外食の値上げ頻度は2.7倍、牛乳は98.8%の市が同じ月に上げた | [retail-prices-japan](https://github.com/takayuki-0127/retail-prices-japan) |
| 107 | 外国人の宿泊は2017年までは地方に広がった。でもコロナ後は東京に集まり、地方の割合は2011年並みの34% | [accommodation-stats-japan](https://github.com/takayuki-0127/accommodation-stats-japan) |
| 108 | 宿泊者数の回復、日本人は29都道府県でまだ2019年以下。外国人は1.6倍でも、京都・東北は日本人が戻らない | [accommodation-stats-japan](https://github.com/takayuki-0127/accommodation-stats-japan) |
| 109 | 外国人の入国は羽田と福岡が2019年の1.7倍に。成田の割合は38%から28%へ下がった | [immigration-entries-japan](https://github.com/takayuki-0127/immigration-entries-japan) |
| 110 | 東南アジアは12月、欧米は4月と10月、韓国は1月。外国人が日本に来る季節は国籍で4つの形に分かれた | [immigration-entries-japan](https://github.com/takayuki-0127/immigration-entries-japan) |
| 111 | 米の収量は涼しい夏に大きく落ちた。暑い夏ではほとんど落ちないが、2000年以降は豊作にもならなくなった | [rice-yield-japan](https://github.com/takayuki-0127/rice-yield-japan) |
| 112 | 米の作付面積は1969年から55%減った。西日本ほど大きく減り、北海道・東北・北陸の割合は48%に | [rice-yield-japan](https://github.com/takayuki-0127/rice-yield-japan) |
| 113 | さんまはピークの7%、するめいかは3%に。魚種別の漁獲量69年で、減り始めた年と増えた魚を探した | [marine-fisheries-japan](https://github.com/takayuki-0127/marine-fisheries-japan) |
| 114 | ブリの漁獲で北海道の割合は2%→12%に。重心は0.8度北へ動いたが、海水温との年ごとの連動は弱かった | [marine-fisheries-japan](https://github.com/takayuki-0127/marine-fisheries-japan) |
| 115 | 狩猟で獲られたクマは年400頭前後。出没が多い年度も増えず、岩手・群馬・福島で4割 | [wildlife-capture-japan](https://github.com/takayuki-0127/wildlife-capture-japan) |
| 116 | 獣の捕獲は「狩猟」から「許可」へ。許可による捕獲は24年で9倍、わな猟の免状は銃を上回った | [wildlife-capture-japan](https://github.com/takayuki-0127/wildlife-capture-japan) |
| 117 | 生活保護を受ける世帯は2017年度まで増え、その後は横ばい。半分は1人で暮らす高齢の方の世帯になった | [public-assistance-japan](https://github.com/takayuki-0127/public-assistance-japan) |
| 118 | 生活保護の申請は2020年2月を底に増加。2020年4月は前年より25%多く、都道府県の差は少しずつ縮まった | [public-assistance-japan](https://github.com/takayuki-0127/public-assistance-japan) |
| 119 | 空き家率20%以上の市区町村は159→215に。上がったのは住む人のいる住宅が減った所だった | [vacant-houses-japan](https://github.com/takayuki-0127/vacant-houses-japan) |
| 120 | 賃貸用の空き家は大きな市、使い道のない空き家は小さな町に。使い道のない空き家は40年で3.1倍の386万戸 | [vacant-houses-japan](https://github.com/takayuki-0127/vacant-houses-japan) |
| 121 | 子どもの体力は1980〜85年度が最高。その後5%落ちて横ばい、2019年度からもう一段下がった | [physical-fitness-japan](https://github.com/takayuki-0127/physical-fitness-japan) |
| 122 | いまの70代前半の合計点は、20年前の60代後半とほぼ同じ。ただ握力や片足立ちは届いていない | [physical-fitness-japan](https://github.com/takayuki-0127/physical-fitness-japan) |
| 123 | 辞める人が多い産業ほど入る人も多い（相関0.97）。転職で賃金が1割以上増えた人は15%から28%に | [labor-turnover-japan](https://github.com/takayuki-0127/labor-turnover-japan) |
| 124 | 辞める理由の4分の3は「個人的理由」。女性の結婚・出産による離職は14%から3%に減った | [labor-turnover-japan](https://github.com/takayuki-0127/labor-turnover-japan) |
| 125 | 昼夜間人口比率1位は千代田区の1,355。でも30年でほぼ半分に下がり、住む人が増えた | [daytime-population-japan](https://github.com/takayuki-0127/daytime-population-japan) |
| 126 | 副業をする人は年収の低い人と高い人に多いU字型。正規は2.6%、役員・自営業主は9%前後 | [side-jobs-japan](https://github.com/takayuki-0127/side-jobs-japan) |
| 127 | 物価が高い県は13年ずっと東京都。ただ家賃を除くと、2023年から北海道が1位になった | [regional-price-index-japan](https://github.com/takayuki-0127/regional-price-index-japan) |
| 128 | ピアノは静岡県が100%、眼鏡枠は福井県が92%。1県に生産が集中する製造品は全体の1割 | [product-concentration-japan](https://github.com/takayuki-0127/product-concentration-japan) |
| 129 | 住まいの不満、多いのは断熱・地震・高齢者への配慮。治安への不満は10年で半分に、断熱はほぼ変わらず | [housing-satisfaction-japan](https://github.com/takayuki-0127/housing-satisfaction-japan) |
| 130 | 日本人観光客の日帰りは埼玉98%、和歌山51%。人数では9割が日帰りでも、お金では半分ほど | [tourism-daytrip-japan](https://github.com/takayuki-0127/tourism-daytrip-japan) |
| 131 | 入院患者の平均年齢は60年で36歳から73歳に。4人に3人が65歳以上、それでも年齢ごとの入院は半分に | [inpatient-age-japan](https://github.com/takayuki-0127/inpatient-age-japan) |
| 132 | 高齢者1人あたりの介護給付費は全国31.2万円。大阪府37.6万円、栃木県26.4万円で、差の3分の1は年齢構成で説明できた | [ltc-benefits-japan](https://github.com/takayuki-0127/ltc-benefits-japan) |
| 133 | 私立小学校の学習費は公立の4.8倍。差の大部分は授業料や入学金で、公立中学生は塾代のほうが多かった | [school-expenses-japan](https://github.com/takayuki-0127/school-expenses-japan) |
| 134 | 光化学オキシダントの環境基準は1,137局中1局しか達成していない。原因物質は減ったのに、濃度は上がって横ばい | [photochemical-oxidant-japan](https://github.com/takayuki-0127/photochemical-oxidant-japan) |
| 135 | 竜巻の半分以上は8〜10月。いちばん多いのは9月の昼過ぎで、海の上の竜巻は10月に多かった | [articles/135_tornado](articles/135_tornado) |
| 136 | 茶畑はピークから4割減。でも10aあたりの荒茶は増え、せん茶が減る一方で番茶と抹茶の原料などは増えていた | [articles/136_tea](articles/136_tea) |
| 137 | 市区町村の歳出の4割は福祉（民生費）。12年で1.5倍になり、伸びが大きかったのは子どもと障害者福祉など | [articles/137_welfare_spending](articles/137_welfare_spending) |
| 138 | 刑法犯は2021年までに7割減。減った分の8割は窃盗で、2022年からは自転車盗と詐欺が増えた | [articles/138_crime](articles/138_crime) |
| 139 | 企業の研究者は12年で7.8万人増えた。増えた分の7割近くは製造業の外で、情報科学の研究者は2.1倍に | [articles/139_researchers](articles/139_researchers) |
| 140 | 人口ピラミッドの裾がいちばん広かったのは1953年まで。1981年から0〜4歳は40〜44歳より少なくなった | [articles/140_population_pyramid](articles/140_population_pyramid) |
| 141 | 賃上げ率の大企業と中小企業の差は2025年に1.5ポイントと、51年で最大。1990年代まではほぼ差がなかった | [articles/141_wage_increase](articles/141_wage_increase) |
| 142 | エアコンは27年、薄型テレビは7年で広がった。家電と車の普及率のS字と、ピーク後に下がった品目 | [articles/142_durable_goods](articles/142_durable_goods) |
| 143 | 内部留保は17年で2.2倍の555兆円。現預金の増加はその半分で、大企業では株式などの投資が増えていた | [articles/143_retained_earnings](articles/143_retained_earnings) |
| 144 | 住宅の価格指数は3月に高く12月に低い。季節の差は2.8%で、取引件数も3月に25〜38%増えていた | [articles/144_housing_price_seasonality](articles/144_housing_price_seasonality) |

## 共通の方針
- データは e-Stat などの公開データだけを使い、出典は各フォルダの README に書いています（政府標準利用規約 第2.0版などに沿って「〇〇をもとに作成者が加工して作成」）
- 各フォルダの `src/` のスクリプトは、フォルダの中の `data/` を読んで `figures/` と `results/` を作り直します
- 図の日本語フォントは Noto Sans CJK JP を使っています

コード：MIT License
