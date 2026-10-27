"""03a_埋め込み：月×（現状・先行き）ごとに150件ずつ無作為に選んだコメントを ruri-v3-30m でベクトルにし、
強気の基準文5つとの近さ − 弱気の基準文5つとの近さ を埋め込みスコアにする（CPU で約10〜20分）。
結果は results/embed_scores.csv（コメントの id とスコアだけ。本文は含まない）。
"""
import numpy as np
import pandas as pd
from common import COMMENTS, RES, MODEL, ANCHOR_POS, ANCHOR_NEG, SEED

N_PER = 150
c = pd.read_parquet(COMMENTS)
s = (c.groupby(["ym", "kind"], group_keys=False)
       .apply(lambda g: g.sample(min(N_PER, len(g)), random_state=SEED)))
from sentence_transformers import SentenceTransformer
m = SentenceTransformer(MODEL, device="cpu")
pre = "トピック: "
E = m.encode([pre + t for t in s.text.tolist()], batch_size=128, normalize_embeddings=True, show_progress_bar=False)
P = m.encode([pre + t for t in ANCHOR_POS], normalize_embeddings=True)
N = m.encode([pre + t for t in ANCHOR_NEG], normalize_embeddings=True)
s["emb"] = (E @ P.T).mean(1) - (E @ N.T).mean(1)
s[["id", "ym", "kind", "emb"]].to_csv(RES / "embed_scores.csv", index=False)
print(len(s), s.emb.describe())
