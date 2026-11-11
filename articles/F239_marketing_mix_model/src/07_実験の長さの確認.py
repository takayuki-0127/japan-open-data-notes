# 07：地域実験だけを150回くり返し、止める週数（8週・12週）でずれがどう変わるかを見る（README の頑健性の数字）
import runpy, numpy as np, sys
src=open('src/03_分析.py').read().split('# ---------------------------------------------------------------- B. 架空の会社のシミュレーション')
g={}
exec(src[0].split('import json')[0]+'import json\nimport numpy as np\nimport pandas as pd\nfrom pathlib import Path\n',g)
body=src[1].split('rng0 = np.random.default_rng(239)')[0]
exec(body,g)
tr=g['roi_at_mean'](g['TRUE']['decay'],g['TRUE']['K'],g['TRUE']['beta'])[1]
for L in (8,12):
  e=np.array([g['geo_experiment'](np.random.default_rng(9000+i),length=L) for i in range(150)])/tr-1
  print(L, 'mean',e.mean().round(3),'med',np.median(e).round(3),'sd',e.std().round(3),'mad',np.median(abs(e)).round(3))
