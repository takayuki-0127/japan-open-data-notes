"""書き出したメールの HTML を、ブラウザで開いたときの見た目として画像にする（playwright）"""
from playwright.sync_api import sync_playwright
from common import ROOT, FIG
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 620, "height": 600}, device_scale_factor=2)
    pg.goto((ROOT / "output" / "preview.html").as_uri()); pg.wait_for_timeout(300)
    pg.add_style_tag(content="body{margin:0;background:#fff} body>div{padding:18px 22px}")
    pg.locator("body > div").first.screenshot(path=str(FIG / "a280_email.png")); b.close()
print("ok")
