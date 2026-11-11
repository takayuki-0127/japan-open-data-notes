# 06：ダッシュボード（dashboard/index.html）の画像を撮る（本当の曲線も表示した状態）
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 760}, device_scale_factor=1.5)
    pg.goto((ROOT / "dashboard" / "index.html").as_uri())
    pg.check("#truth")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(ROOT / "figures" / "fig6_dashboard.png"), full_page=True)
    b.close()
