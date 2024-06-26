from html import unescape
import json
import logging
import re

from dvtag.utils import create_request_session

session = create_request_session()


class DoujinVoice:
    def __init__(self, rjid: str) -> None:
        self.rjid = rjid

        self.dl_count = 0
        self.url = ""
        self.work_name = ""
        self.work_image = ""
        self.seiyus = []
        self.circle = ""
        self.genres = []
        self.sale_date = ""

        self._init_metadata()
        self._add_metadata()
        self._get_cover()

    def _add_metadata(self):
        html = session.get(self.url).text

        try:
            pattern = r"<th>声優</th>[\s\S]*?<td>[\s\S]*?(<a[\s\S]*?>[\s\S]*?)</td>"
            seiyu_list_html = re.search(pattern, html).group(1)

            pattern = r"<a[\s\S]*?>(.*?)<"
            for seiyu_html in re.finditer(pattern, seiyu_list_html):
                self.seiyus.append(unescape(seiyu_html.group(1)))
        except AttributeError as e:
            logging.error("Cannot get artists from {}: {}".format(self.rjid, e))

        try:
            pattern = r"<th>サークル名</th>[\s\S]*?<a[\s\S]*?>(.*?)<"
            circle = re.search(pattern, html)
            if circle:
                self.circle = unescape(circle.group(1))
            pattern_vj = r"<th>ブランド名</th>[\s\S]*?<a[\s\S]*?>(.*?)<"
            circle_vj = re.search(pattern_vj, html)
            if circle_vj:
                self.circle = unescape(circle_vj.group(1))

        except AttributeError as e:
            logging.error("Cannot get circle from {}: {}".format(self.rjid, e))

        pattern = r"work\.genre\">(.*)\</a>"
        self.genres = [unescape(m[1]) for m in re.finditer(pattern, html)]

        # get sale date
        pattern = r"www\.dlsite\.com/maniax/new/=/year/([0-9]{4})/mon/([0-9]{2})/day/([0-9]{2})/"
        match = re.search(pattern, html)
        if match:
            self.sale_date = "{}-{}-{}".format(match.group(1), match.group(2), match.group(3))
        pattern_vj = r"www\.dlsite\.com/pro/new/=/year/([0-9]{4})/mon/([0-9]{2})/day/([0-9]{2})/"
        match_vj = re.search(pattern_vj, html)
        if match_vj:
            self.sale_date = "{}-{}-{}".format(match_vj.group(1), match_vj.group(2), match_vj.group(3))

    def _init_metadata(self):
        rsp = session.get("https://www.dlsite.com/maniax/product/info/ajax?product_id=" + self.rjid)

        try:
            json_data = rsp.json()[self.rjid]

            if json_data["dl_count"] != None:
                self.dl_count = int(json_data["dl_count"])
            self.url = json_data["down_url"].replace("download/split", "work").replace("download", "work")
            self.work_name = json_data["work_name"]
            self.work_image = "https:" + json_data["work_image"]

        except ValueError as e:
            logging.error(f"Cannot convert a response to json or convert dl_count to int with RJ-ID {self.rjid}: {e}")
        except KeyError as e:
            logging.error(e)

    def _get_cover(self):
        """
        Tries to fetch a better cover
        """
        try:
            chobit_api = f"https://chobit.cc/api/v1/dlsite/embed?workno={self.rjid}"

            res = json.loads(session.get(chobit_api).text[9:-1])

            if (work := res["works"][0])["file_type"] == "audio":
                self.work_image = work["thumb"].replace("media.dlsite.com/chobit", "file.chobit.cc", 1)

        except Exception as e:
            logging.warning(f"Cannot fetch cover from chobit for {self.rjid}: {e}")
