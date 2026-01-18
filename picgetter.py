import requests
import time
from typing import Dict, Tuple, Generator, Iterator, List
import json
import requests_cache
import asyncio
import aiohttp
import cookie

headers = {
        "User-Agent": "PixivAndroidApp/6.167.0 (Android 12; SM-S9080)",
        "Connection": "keep-alive",
        "referer": "https://app-api.pixiv.net/",
        "accept-encoding": "gzip"
}

def headers_windows(id:int | None = None) -> Dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
        "Connection": "keep-alive",
        "referer": f"https://www.pixiv.net/artworks/{id}",
        "accept-encoding": "gzip",
        "Accept": "application/json",
        "Accpept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
}

sess = requests_cache.CachedSession(
    cache_name='pixiv_gif_cache',
    backend='memory',
    expire_after=300,
    allowable_codes=[200],
    allowable_methods=('GET', 'POST', 'HEAD')
)

def read_config(arg) -> str:
    with open('json/config.json', 'r', encoding='utf-8') as f:
        config:dict = json.load(f)
    
    return config.get(arg, "")


def try_get_url_combine(base_info:Iterator[Tuple | None], max_per_post: int) -> Iterator[Tuple[str, Tuple[bool, str]]]:

    for info in base_info:
        if info is None:
            continue
        id = info[0]
        url_custom = info[1]
        pageCount = info[3]
        ifGif = info[4]

        url_parts = url_custom.split('/img/')[-1].split("_")[0] #提取img/后部分并去掉页码、custom、后缀名

        #处理一般图片url
        if not ifGif:
            url_origin_withoutpage = f"https://i.pximg.net/img-original/img/{url_parts}_p&@" #&表示页码位置，@表示后缀名位置
            
            def url(suffix: str) -> Iterator[Tuple[str, Tuple[bool, str]]]:
                for page in range(min(pageCount, max_per_post)):
                    final_url = url_origin_withoutpage.replace("&", str(page)).replace("@", suffix)
                    print(f"[INFO] 组合图片URL成功: {final_url}")
                    yield final_url, (ifGif, suffix)
            
            # 先测试PNG后测试JPG
            test_url = url_origin_withoutpage.replace("&", "0").replace("@", ".png")
            
            try:
                response = requests.head(test_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    yield from url(".png")
                elif response.status_code == 404:
                    yield from url(".jpg")
                else:
                    print(f"[WARNING] 无法获取图片后缀名(URL:{test_url})，状态码: {response.status_code}")
                    continue
            except requests.RequestException as e:
                print(f"[ERROR] 请求失败(URL:{test_url}): {e}")
                continue
            except Exception:
                print(f"[WARNING] 组合图片URL失败，跳过ID: {id}")
                continue
            # 目前看来没有其他后缀名了
        # https://www.pixiv.net/ajax/illust/139819674/ugoira_meta?lang=zh
        # 获取更详细GIF信息

        elif ifGif:
            #处理动图url
            gif_result = gif_further(id, ifGif, "src")
            if gif_result is not None:
                print(f"[INFO] 组合动图URL成功: {gif_result[0]}")
                yield gif_result
            else:
                print(f"[WARNING] 组合动图URL失败，跳过ID: {id}")
                continue
    
    # Example: https://i.pximg.net/c/250x250_80_a2/custom-thumb/img/2026/01/07/00/17/43/139616054_p0_custom1200.jpg
    # --> https://i.pximg.net/img-original/img/2025/12/24/18/41/49/138988019_p0.png

    # https://i.pximg.net/c/250x250_80_a2/img-master/img/2026/01/11/05/06/14/139783639_square1200.jpg
    # GIF Example: https://i.pximg.net/img-zip-ugoira/img/2026/01/11/05/06/14/139783639_ugoira600x600.zip


def try_get_pic_origin_url(urls: Iterator[Tuple[str, Tuple[bool, str]]]) -> Iterator[Tuple[bytes, Tuple[bool, str], str]]:
    """同步版本 - 保留以保持向后兼容"""
    for url in urls:
        try:
            response = requests.get(url[0], headers=headers, timeout=15)
            if response.status_code == 200:
                yield response.content, url[1], url[0].split("/")[-1].split(".")[0] #explaination: id_page, example:138988019_p0
            else:
                print(f"[WARNING] 无法获取图片(URL:{url})，状态码: {response.status_code}")
        except requests.RequestException as e:
            print(f"[ERROR] 请求失败(URL:{url}): {e}")
            continue


async def try_get_pic_origin_url_async(urls: Iterator[Tuple[str, Tuple[bool, str]]], max_concurrent: int = 5):
    
    semaphore = asyncio.Semaphore(max_concurrent)  # 限制并发数
    queue = asyncio.Queue()  # 用于传递下载结果
    
    async def download_one(session: aiohttp.ClientSession, url_tuple: Tuple[str, Tuple[bool, str]]):
        """下载单个文件并放入队列"""
        url = url_tuple[0]
        metadata = url_tuple[1]
        
        async with semaphore:  # 控制并发
            try:
                async with session.get(url, headers=headers_windows(id=None), timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        content = await response.read()
                        filename = url.split("/")[-1].split(".")[0]  # id_page, example:138988019_p0
                        print(f"[INFO] 下载成功: {filename}")
                        await queue.put((content, metadata, filename))
                    else:
                        print(f"[WARNING] 无法获取图片(URL:{url})，状态码: {response.status}")
            except asyncio.TimeoutError:
                print(f"[ERROR] 请求超时(URL:{url})")
            except aiohttp.ClientError as e:
                print(f"[ERROR] 请求失败(URL:{url}): {e}")
            except Exception as e:
                print(f"[ERROR] 未知错误(URL:{url}): {e}")
    
    async def producer(session: aiohttp.ClientSession):
        tasks = []
        for url_tuple in urls:
            task = asyncio.create_task(download_one(session, url_tuple))
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)
        # 发送结束信号
        await queue.put(None)
    
    # 创建aiohttp会话
    async with aiohttp.ClientSession() as session:
        producer_task = asyncio.create_task(producer(session))
        while True:
            result = await queue.get()
            if result is None:  # 收到结束信号
                break
            yield result
        await producer_task

def gif_further(id: int, ifGif: bool, mode: str) -> Tuple[str, Tuple[bool, str]] | list | None:

    url_base = f"https://www.pixiv.net/ajax/illust/{id}/ugoira_meta?lang=zh"
    
    try:
        response = sess.get(url_base, headers=headers_windows(id=id), cookies=cookie.request_cookies(), timeout=15) # 使用缓存的session
        if response.status_code != 200:
            print(f"[WARNING] 无法下载动图详细信息(URL:{url_base})，状态码: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"[ERROR] 请求失败(URL:{url_base}): {e}")
        return None
    
    if mode == "src": # 先调用
        try:
            origin_src = response.json()['body']['originalSrc']
            return origin_src, (ifGif, ".zip")
        except (KeyError, json.JSONDecodeError) as e:
            print(f"[ERROR] 解析动图信息失败(URL:{url_base}): {e}")
            return None

    elif mode == "frames": # 后调用
        try:
            frames: list = response.json()['body']['frames']
            return frames
        except (KeyError, json.JSONDecodeError) as e:
            print(f"[ERROR] 解析动图帧信息失败(URL:{url_base}): {e}")
            return None
    
    else:
        print(f"[ERROR] gif_further函数调用时mode参数错误: {mode}")
        return None
        