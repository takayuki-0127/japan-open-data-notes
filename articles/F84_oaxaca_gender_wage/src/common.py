from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/'data'/'raw'; DATA = ROOT/'data'; RES = ROOT/'results'; FIG = ROOT/'figures'
for c in ['Noto Sans CJK JP','Noto Sans JP','IPAexGothic']:
    if any(c in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams['font.family'] = c; break
plt.rcParams['axes.unicode_minus'] = False
AGES = ['～19歳','20～24歳','25～29歳','30～34歳','35～39歳','40～44歳','45～49歳','50～54歳','55～59歳','60～64歳','65～69歳','70歳～']
AGE_MID = [18.5,22,27,32,37,42,47,52,57,62,67,72]
EDUS = ['中学','高校','専門学校','高専・短大','大学','大学院']
TENS = ['0年','1～2年','3～4年','5～9年','10～14年','15～19年','20～24年','25～29年','30年以上']
TEN_MID = [0.5,1.5,3.5,7,12,17,22,27,33]
