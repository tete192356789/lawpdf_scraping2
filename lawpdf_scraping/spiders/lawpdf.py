import datetime
import os

import scrapy
from playwright.async_api import async_playwright
from scrapy_playwright.page import PageMethod

from lawpdf_scraping.items import LawpdfScrapingItem


class LawpdfSpider(scrapy.Spider):
    name = "lawpdf"
    allowed_domains = ["ratchakitcha.soc.go.th"]
    start_urls = ["https://ratchakitcha.soc.go.th/search-result#result"]
    current_page = 1
    page_limit = 2

    def __init__(self, date_from=None, date_to=None):
        # super(LawpdfSpider, self).__init__(*args, **kwargs)
        # self.date_from = date_from or (datetime.now() - timedelta(days=30)).strftime(
        #     "%d/%m/%Y"
        # )
        # self.date_to = date_to or datetime.now().strftime("%d/%m/%Y")
        self.date_from = date_from
        self.date_to = date_to

    def thai_num_to_arabic(self, thai_num_str):
        arabic_num_str = "".join(
            self.thai_to_arabic.get(char, char) for char in thai_num_str
        )
        return arabic_num_str

    def start_requests(self):
        url = "https://ratchakitcha.soc.go.th/search-result#result"

        yield scrapy.Request(
            url,
            meta=dict(
                playwright=True,
                playwright_include_page=True,
                playwright_page_methods=[
                    PageMethod(
                        "wait_for_selector",
                        "div.tab-pane.fade.show.active div.form-group.row div.col-lg-12.p-t-15.m-b-0 button#btn-search1.btn.btn-tab-search.btn-red.pull-right",
                    )
                ],
                errback=self.errback,
            ),
        )

    async def parse(self, response):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto(response.url)

            print("########################################################")
            print("########################################################")
            print(self.date_from)
            print(self.date_to)

            if self.date_from:
                await page.fill(
                    "div.tab-pane.fade.show.active div.form-group.row.p-15.m-b-0.p-t-0 div.col-lg-5.col-sm-5.no-padding input#search1-date-from.form-control",
                    self.date_from,
                )
            if self.date_to:
                await page.fill(
                    "div.tab-pane.fade.show.active div.form-group.row.p-15.m-b-0.p-t-0 div.col-lg-5.col-sm-5.no-padding input#search1-date-to.form-control",
                    self.date_to,
                )

            await page.evaluate("""
                document.querySelector("div.tab-pane.fade.show.active div.form-group.row div.col-lg-12.p-t-15.m-b-0 button#btn-search1.btn.btn-tab-search.btn-red.pull-right").click();
            """)

            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(5000)

            while self.current_page <= self.page_limit:
                # Use Playwright to extract data
                blogs = await page.query_selector_all(
                    "div.col-lg-8.no-padding div.announce100.m-b-0.p-b-20.m-t-5 div.post-thumbnail-list.p-b-40 div.post-thumbnail-entry.blogBox.moreBox"
                )

                for blog in blogs:
                    item = LawpdfScrapingItem()

                    name = await blog.query_selector(
                        "div.post-thumbnail-content a.m-b-10"
                    )
                    post_date = await blog.query_selector(
                        "div.post-thumbnail-content div.m-t-10 span.post-date"
                    )
                    post_category = await blog.query_selector(
                        "div.post-thumbnail-content div.m-t-10 span.post-category"
                    )
                    file_urls = await blog.query_selector(
                        "div.post-thumbnail-content  a.m-b-10"
                    )
                    extract_date = datetime.datetime.now()

                    item["name"] = await name.inner_text() if name else None
                    item["post_date"] = (
                        await post_date.inner_text() if post_date else None
                    )
                    item["post_category"] = (
                        await post_category.inner_text() if post_category else None
                    )
                    item["file_urls"] = (
                        await file_urls.get_attribute("href") if file_urls else None
                    )
                    item["extract_date"] = extract_date
                    yield item

                # Click "Next" button if available
                next_button = await page.query_selector(
                    "xpath=//div[@class='announce100 m-b-0 p-b-20 m-t-5']/div[@class='row pull-right p-b-20']/ul[@class='page-numbers pagination pagination-flat']/li[@class='page-item current']/following-sibling::li[1]"
                )
                if next_button:
                    is_visible = await next_button.is_visible()
                    is_enabled = await next_button.is_enabled()

                    if is_visible and is_enabled:
                        await next_button.click()
                        await page.wait_for_load_state("networkidle")
                        await page.wait_for_timeout(2000)
                    else:
                        print("END OF PAGES.")
                        break
                else:
                    print("NEXT BUTTON IS NOT AVAILABLE.")
                    break

                self.current_page += 1

            await browser.close()

    def save_pdf(self, response):
        item = response.meta["item"]

        filename = os.path.basename(response.url)

        os.makedirs("pdfs", exist_ok=True)

        with open(os.path.join("pdfs", filename), "wb") as f:
            f.write(response.body)

        item["files"] = filename  # Store the filename instead of the content
        yield item

    async def errback(self, failure):
        page = failure.request.meta["playwright_page"]
        await page.close()
