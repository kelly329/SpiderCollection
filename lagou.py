# coding: utf-8

import time
import re
import urllib.parse

import requests
from lxml import etree

KEY = "PHP"  # 抓取的关键字
CITY = "深圳"  # 目标城市
# 0:[0, 2k), 1: [2k, 5k), 2: [5k, 10k), 3: [10k, 15k), 4: [15k, 25k), 5: [25k, 50k), 6: [50k, +inf)
SALARY_OPTION = 3  # 薪资范围，值范围 0 ~ 6，其他值代表无范围
# 进入『拉勾网』任意页面，无需登录
# 打开 Chrome / Firefox 的开发者工具，从中复制一个 Cookie 放在此处
# 防止被封，若无法拉取任何信息，首先考虑换 Cookie
# COOKIE = "JSESSIONID=ABAAABAACBHABBI7B238FB0BC8B6139070838B4D2D31CED; _ga=GA1.2.201890914.1522471658; _gat=1; Hm_lvt_4233e74dff0ae5bd0a3d81c6ccf756e6=1522471658; Hm_lpvt_4233e74dff0ae5bd0a3d81c6ccf756e6=1522471674; user_trace_token=20180331124738-a3407f45-349e-11e8-a62b-525400f775ce; LGSID=20180331124738-a34080db-349e-11e8-a62b-525400f775ce; PRE_UTM=; PRE_HOST=; PRE_SITE=; PRE_LAND=https%3A%2F%2Fwww.lagou.com%2F; LGRID=20180331124753-ac447493-349e-11e8-b664-5254005c3644; LGUID=20180331124738-a3408251-349e-11e8-a62b-525400f775ce; _gid=GA1.2.24217288.1522471661; index_location_city=%E6%88%90%E9%83%BD; TG-TRACK-CODE=index_navigation"
COOKIE = "JSESSIONID=ABAAABAAAGGABCB6208A6C590B77795264726FD4E00D101; _ga=GA1.2.1521403249.1522635836; _gid=GA1.2.1863696920.1522635836; user_trace_token=20180402102356-e4e76522-361c-11e8-ac89-525400f775ce; LGSID=20180402102356-e4e76677-361c-11e8-ac89-525400f775ce; PRE_UTM=; PRE_HOST=link.zhihu.com; PRE_SITE=https%3A%2F%2Flink.zhihu.com%2F%3Ftarget%3Dhttps%253A%2F%2Fwww.lagou.com%2F; PRE_LAND=https%3A%2F%2Fwww.lagou.com%2F; LGUID=20180402102356-e4e767f7-361c-11e8-ac89-525400f775ce; index_location_city=%E5%85%A8%E5%9B%BD; TG-TRACK-CODE=index_navigation; _gat=1; Hm_lvt_4233e74dff0ae5bd0a3d81c6ccf756e6=1522635836,1522636528,1522636989; Hm_lpvt_4233e74dff0ae5bd0a3d81c6ccf756e6=1522636989; LGRID=20180402104308-93e48297-361f-11e8-b6d5-5254005c3644; SEARCH_ID=463be8b6f23b40bdb16fe5bd9635bd4c"

def init_segment():
    # 按照 4.4 的方式，申请百度云分词，并填写到下面
    APP_ID = "11033091"
    API_KEY = "tSkph8iBxX4fGmRvLf5WSVhN"
    SECRET_KEY = "FxEzuzLcXiG4j506zTefnTlPREuQgGWr"

    from aip import AipNlp
    # 保留如下词性的词 https://cloud.baidu.com/doc/NLP/NLP-FAQ.html#NLP-FAQ
    retains = set(["n", "nr", "ns", "s", "nt", "an", "t", "nw", "vn"])

    client = AipNlp(APP_ID, API_KEY, SECRET_KEY)

    def segment(text):
        '''
        对『任职信息』进行切分，提取信息，并进行一定处理
        '''
        try:
            result = []
            # 调用分词和词性标注服务，这里使用正则过滤下输入，是因为有特殊字符的存在
            items = client.lexer(re.sub('\s', '', text))["items"]

            cur = ""
            for item in items:
                # 将连续的 retains 中词性的词合并起来
                if item["pos"] in retains:
                    cur += item["item"]
                    continue

                if cur:
                    result.append(cur)
                    cur = ""
                # 如果是 命名实体类型 或 其它专名 则保留
                if item["ne"] or item["pos"] == "nz":
                    result.append(item["item"])
            if cur:
                result.append(cur)

            return result
        except Exception as e:
            print("fail to call service of baidu nlp.")
            return []

    return segment


# 以下无需修改，拉取『拉勾网』的固定参数
SALARY_INTERVAL = ("2k以下", "2k-5k", "5k-10k", "10k-15k", "15k-25k", "25k-50k", "50k以上")
if SALARY_OPTION < len(SALARY_INTERVAL) and SALARY_OPTION >= 0:
    SALARY = SALARY_INTERVAL[SALARY_OPTION]
else:
    SALARY = None
USER_AGENT = "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/534.55.3 (KHTML, like Gecko) Version/5.1.5 Safari/534.55.3"
REFERER = "https://www.lagou.com/jobs/list_" + urllib.parse.quote(KEY)
BASE_URL = "https://www.lagou.com/jobs/positionAjax.json"
DETAIL_URL = "https://www.lagou.com/jobs/{0}.html"


# 抓取职位详情页
def fetch_detail(id):
    headers = {"User-Agent": USER_AGENT, "Referer": REFERER, "Cookie": COOKIE}
    try:
        url = DETAIL_URL.format(id)
        print(url)
        s = requests.get(url, headers=headers)

        return s.text
    except Exception as e:
        print("fetch job detail fail. " + url)
        print(e)
        raise e


# 抓取职位列表页
def fetch_list(page_index):
    headers = {"User-Agent": USER_AGENT, "Referer": REFERER, "Cookie": COOKIE}
    params = {"px": "default", "city": CITY, "yx": SALARY}
    data = {"first": page_index == 1, "pn": page_index, "kd": KEY}
    try:
        s = requests.post(BASE_URL, headers=headers, params=params, data=data)

        return s.json()
    except Exception as e:
        print("fetch job list fail. " + data)
        print(e)
        raise e


# 根据 ID 抓取详情页，并提取『任职信息』
def fetch_requirements(result, segment):
    time.sleep(2)

    requirements = {}
    content = fetch_detail(result["positionId"])
    details = [detail.strip() for detail in etree.HTML(content).xpath('//dd[@class="job_bt"]/div/p/text()')]

    is_requirement = False
    for detail in details:
        if not detail:
            continue
        if is_requirement:
            m = re.match("([0-9]+|-)\s*[\.:：、]?\s*", detail)
            if m:
                words = segment(detail[m.end():])
                for word in words:
                    if word not in requirements:
                        requirements[word] = 1
                    else:
                        requirements[word] += 1
            else:
                break
        elif re.match("\w?[\.、 :：]?(任职要求|任职资格|我们希望你|任职条件|岗位要求|要求：|职位要求|工作要求|职位需求)", detail):
            is_requirement = True

    return requirements


# 循环请求职位列表
def scrapy_jobs(segment):
    # 用于过滤相同职位
    duplications = set()
    # 从页 1 开始请求
    page_index = 1
    job_count = 0

    print("key word {0}, salary {1}, city {2}".format(KEY, SALARY, CITY))
    stat = {}
    while True:
        print("current page {0}, {1}".format(page_index, KEY))
        time.sleep(2)

        content = fetch_list(page_index)["content"]

        # 全部页已经被请求
        if content["positionResult"]["resultSize"] == 0:
            break

        results = content["positionResult"]["result"]
        total = content["positionResult"]["totalCount"]
        print("total job {0}".format(total))

        # 处理该页所有职位信息
        for result in results:
            if result["positionId"] in duplications:
                continue
            duplications.add(result["positionId"])

            job_count += 1
            print("{0}. {1}, {2}, {3}".format(job_count, result["positionName"], result["salary"], CITY))
            requirements = fetch_requirements(result, segment)
            print("/".join(requirements.keys()) + "\n")
            # 把『任职信息』数据统计到 stat 中
            for key in requirements:
                if key not in stat:
                    stat[key] = requirements[key]
                else:
                    stat[key] += requirements[key]

        page_index += 1
    return stat


segment = init_segment()
stat = scrapy_jobs(segment)

# 将所有『任职信息』根据提及次数排序，输出前 10 位
import operator

sorted_stat = sorted(stat.items(), key=operator.itemgetter(1))
print(sorted_stat[-10:])