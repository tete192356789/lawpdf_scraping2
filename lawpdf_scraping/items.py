# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class LawpdfScrapingItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    name = scrapy.Field()
    post_date = scrapy.Field()
    extract_date = scrapy.Field()
    post_category = scrapy.Field()
    file_urls = scrapy.Field()
    files = scrapy.Field
