"""Optional helper (not run by poc.py): drives out/index.html in headless Chromium."""
from pathlib import Path
from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.goto((here / "out" / "index.html").as_uri())
    print("initial", pg.inner_text("#count"))
    pg.fill("#ptitle", "Test studio")
    pg.fill("#pprice", "320")
    pg.select_option("#pcity", "Riverside")
    pg.click("#pbtn")
    print("post", pg.inner_text("#msg"), pg.inner_text("#count"))
    pg.select_option("#fcat", "student")
    pg.fill("#fmax", "400")
    pg.select_option("#fcity", "Riverside")
    pg.click("#fbtn")
    print("filter", pg.inner_text("#count"))
    card = pg.locator(".card").first
    card.locator("textarea").fill("Is it available?")
    card.locator("button").click()
    print("inquiry", pg.inner_text("#msg"))
    pg.screenshot(path=str(here / "screenshot.png"), full_page=True)
    b.close()
