import requests
from urllib.parse import quote, unquote
import json
from typing import Dict, Tuple, Optional, Generator, Iterator
import time
import cookie

def read_config(*args) -> Tuple | Dict | str:

    with open('json/config.json', 'r', encoding='utf-8') as f:
        config:dict = json.load(f)

    content = []

    if args is None:
        return config
    elif len(args) != 1:
        for key in args:
            content.append(config.get(key, ""))
        return tuple(content)
    else:
        return config.get(args[0], "")

def try_get_tagsearch(page: int = 1, useCookie = False) -> Dict: #转投网页端API的大手

    tag:str = read_config("tag")
    tag = quote(tag)

    url = f"https://www.pixiv.net/ajax/search/artworks/{tag}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
        "Connection": "keep-alive",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "sec-ch-ua-platform": "\"Windows\"",
        "referer": f"https://www.pixiv.net/tags/{tag}/artworks",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "priority": "u=1, i"
    }

    params = {
        "word": tag,
        "order": "date_d",
        "mode": "all",
        "p": str(page),
        "csw": "0",
        "s_mode": "s_tag_full",
        "type": "all",
        "lang": "zh"
    }
    cookies = cookie.request_cookies() if useCookie else None
    try:
        response = requests.get(url, headers=headers, params=params, cookies=cookies, timeout=15)
    except requests.RequestException as e:
        print(f"[ERROR] 请求失败: {e}")
        return {}
    
    print(f"[INFO] 成功获取Tag搜索结果，状态码: {response.status_code}")
    return response.json()

def try_resolve_pic_info(json_data: Dict) -> Iterator[Tuple[int, str, str, int, bool] | None]:
    """
    :param json_data: API返回的JSON数据
    :type json_data: Dict
    :return: (id, url, title, pageCount, ifGif)
        Example:(139616054, https://i.pximg.net/c/250x250_80_a2/custom-thumb/img/2026/01/07/00/17/43/139616054_p0_custom1200.jpg, "示例标题", 3, False)
    :rtype: Generator[Tuple[int, str, str, int, bool] | None]
    """
    # Part.1 重试机制
    _retry = 0
    while json_data.get("error", True) and _retry < 5:
        _retry += 1
        print(f"[WARNING] API返回错误，正在重试 {_retry}/5...")
        time.sleep(1)
        json_data = try_get_tagsearch()

    if json_data.get("error", True):
        raise requests.exceptions.InvalidJSONError("API返回错误。") #最终失败
    
    # 新增帖子数量显示
    # body/illustManga/total
    print(f"[INFO] 总帖子数量: {json_data.get('body', {}).get('illustManga', {}).get('total', '未知')}")

    # Part.2 解析图片URL-数据
    try: #/body/illustManga/data
        post_list:list = json_data["body"]["illustManga"]["data"]
    except KeyError:
        raise KeyError("无法在API返回的数据中找到图片信息。")
    
    for post in post_list:
        try:
            id:int = post["id"]
            url:str = post["url"]
            title:str = post["alt"]
            pageCount:int = post["pageCount"]
            ifGif:bool = True if "动图" in title else False
            print(f"[INFO] 解析到图片 - ID:{id} 页数:{pageCount}")
            yield (id, url, title, pageCount, ifGif)
        
        except KeyError:
            print(f"[WARNING] 无法解析某个图片的信息，跳过该图片。")
            yield None