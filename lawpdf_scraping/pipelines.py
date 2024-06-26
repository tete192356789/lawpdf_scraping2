# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import datetime
import os
import urllib.parse

import mysql.connector
import requests
import scrapy
from dotenv import load_dotenv
from itemadapter import ItemAdapter
from scrapy.pipelines.files import FilesPipeline


class LawpdfScrapingPipeline:
    thai_to_arabic = {
        "๐": "0",
        "๑": "1",
        "๒": "2",
        "๓": "3",
        "๔": "4",
        "๕": "5",
        "๖": "6",
        "๗": "7",
        "๘": "8",
        "๙": "9",
    }

    def thai_num_to_arabic(self, thai_num_str):
        arabic_num_str = "".join(
            self.thai_to_arabic.get(char, char) for char in thai_num_str
        )
        return arabic_num_str

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        ##Date Transform

        th_date = adapter.get("post_date")
        original_date = self.thai_num_to_arabic(th_date)

        if "post_date" in item and isinstance(item["post_date"], str):
            split_date = original_date.split(" ")
            thai_months = {
                "ม.ค.": "01",
                "ก.พ.": "02",
                "มี.ค.": "03",
                "เม.ย.": "04",
                "พ.ค.": "05",
                "มิ.ย.": "06",
                "ก.ค.": "07",
                "ส.ค.": "08",
                "ก.ย.": "09",
                "ต.ค.": "10",
                "พ.ย.": "11",
                "ธ.ค.": "12",
            }

            # if len(split_date) == 3:
            #     month = thai_months.get(split_date[1])
            #     day = split_date[0]
            #     year = split_date[2]
            # else:
            month = thai_months.get(split_date[2])
            day = split_date[1]
            year = str(int(split_date[3]) - 543)

            date = f"{year}{month}{day}"
            print("##################")
            print(date)
            date = datetime.datetime.strptime(date, "%Y%m%d").date()
            item["post_date"] = date

            ##Post Category Transform
            post_category = adapter.get("post_category")
            item["post_category"] = post_category.replace("\n", "").strip()

        return item


class PDFDownloadPipeline(FilesPipeline):
    def get_media_requests(self, item, info):
        if item["file_urls"]:
            yield scrapy.Request(item["file_urls"])

    def file_path(self, request, response=None, info=None, *, item=None):
        # Extract filename from URL
        return os.path.basename(urllib.parse.urlparse(request.url).path)

    # def item_completed(self, results, item, info):
    #     file_paths = [x['path'] for ok, x in results if ok]
    #     if file_paths:
    #         item['pdf_filename'] = file_paths[0]
    #     return item


class DownloadFilesPipeline:
    def file_path(self, request, item, spider, response=None, info=None):
        # file_name: str = request.url.split("/")[-1]

        load_dotenv()

        adapter = ItemAdapter(item)
        url = adapter.get("file_urls")
        pdf_filename = url.split("/")[-1]
        response_url = requests.get(url)

        file_path = os.getenv("FILES_STORE")
        with open(os.path.join(file_path, pdf_filename), "wb") as f:
            f.write(response_url.body)


class SaveToMySQL:
    def __init__(self):
        load_dotenv()
        self.conn = mysql.connector.connect(
            host=os.getenv("HOST"),
            user=os.getenv("USER"),
            database=os.getenv("DATABASE"),
            password=os.getenv("PASSWORD"),
        )

        self.cur = self.conn.cursor()
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS lawpdf(
            id int NOT NULL auto_increment, 
            name text,
            file_urls text,
            law_type VARCHAR(10),
            release_date DATE,
            PRIMARY KEY (id)
        )
        """)

    def process_item(self, item, spider):
        self.cur.execute(
            "SELECT * FROM lawpdf WHERE file_urls = %s", (item["file_urls"][0],)
        )
        result = self.cur.fetchone()

        if result:
            spider.logger.warn("file urls already in database: %s" % item["file_urls"])
        else:
            self.cur.execute(
                """
                        INSERT INTO lawpdf (name , file_urls , law_type , release_date) 
                        VALUES (%s,%s,%s,%s)
            """,
                (
                    item["name"],
                    item["file_urls"][0],
                    item["law_type"],
                    item["release_date"],
                ),
            )
            self.conn.commit()
        return item

    def close_spider(self, spider):
        self.cur.close()
        self.conn.close()
