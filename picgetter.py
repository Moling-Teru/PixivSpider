import requests
import time
from typing import Dict, Tuple, Generator, Iterator
import json

def read_config(arg) -> str:
    with open('config.json', 'r', encoding='utf-8') as f:
        config:dict = json.load(f)
    
    return config.get(arg, "")
    

def try_get_url_combine(base_info:Iterator[Tuple | None]) -> Iterator[Tuple[str, Tuple[bool, str]]]:
    headers = {
        "User-Agent": "PixivAndroidApp/6.167.0 (Android 12; SM-S9080)",
        "Connection": "keep-alive",
        "referer": "https://app-api.pixiv.net/",
        "accept-encoding": "gzip"
    }
    for info in base_info:
        if info is None:
            continue
        url_custom = info[1]
        pageCount = info[3]
        ifGif = info[4]

        url_parts = url_custom.split('/img/')[-1].split("_")[0] #提取img/后部分并去掉页码、custom、后缀名
        #处理一般图片url
        if not ifGif:
            url_origin_withoutpage = f"https://i.pximg.net/img-original/img/{url_parts}_p&@" #&表示页码位置，@表示后缀名位置
            exist_suffix = [".png", ".jpg"]
            for suffix in exist_suffix:
                test_url = url_origin_withoutpage.replace("&", "0").replace("@", suffix)
                try:
                    response = requests.head(test_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        #找到正确后缀名
                        for page in range(pageCount):
                            final_url = url_origin_withoutpage.replace("&", str(page)).replace("@", suffix)
                            print(f"[INFO] 组合图片URL成功: {final_url}")
                            yield final_url, (ifGif, suffix)
                        break
                except requests.RequestException as e:
                    print(f"[ERROR] 请求失败(URL:{test_url}): {e}")
                    continue
        
        elif ifGif:
            #处理动图url
            url_ugoira = f"https://i.pximg.net/img-zip-ugoira/img/{url_parts}_ugoira600x600.zip"
            try:
                response = requests.head(url_ugoira, timeout=10)
                if response.status_code == 200:
                    yield url_ugoira, (ifGif, ".zip")
            except requests.RequestException as e:
                print(f"[ERROR] 请求失败(URL:{url_ugoira}): {e}")
                continue
    
    # Example: https://i.pximg.net/c/250x250_80_a2/custom-thumb/img/2026/01/07/00/17/43/139616054_p0_custom1200.jpg
    # --> https://i.pximg.net/img-original/img/2025/12/24/18/41/49/138988019_p0.png

    # https://i.pximg.net/c/250x250_80_a2/img-master/img/2026/01/11/05/06/14/139783639_square1200.jpg
    # GIF Example: https://i.pximg.net/img-zip-ugoira/img/2026/01/11/05/06/14/139783639_ugoira600x600.zip


def try_get_pic(urls: Iterator[Tuple[str, Tuple[bool, str]]]) -> Iterator[Tuple[bytes, Tuple[bool, str], str]]:
    headers = {
        "User-Agent": "PixivAndroidApp/6.167.0 (Android 12; SM-S9080)",
        "Connection": "keep-alive",
        "referer": "https://app-api.pixiv.net/",
        "accept-encoding": "gzip"
    }
    for url in urls:
        try:
            response = requests.get(url[0], headers=headers, timeout=15)
            if response.status_code == 200:
                yield response.content, url[1], url[0].split("/")[-1].split(".")[0]
            else:
                print(f"[WARNING] 无法获取图片(URL:{url})，状态码: {response.status_code}")
        except requests.RequestException as e:
            print(f"[ERROR] 请求失败(URL:{url}): {e}")
            continue