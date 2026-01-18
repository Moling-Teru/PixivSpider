import picgetter
import tagsearcher
import cookie
import json
from typing import Any, Optional, Iterator
import datetime
import zipfile
import os
import tempfile
import asyncio

use_cookie = False

def read_config(arg) -> str:
    with open('json/config.json', 'r', encoding='utf-8') as f:
        config:dict = json.load(f)
    
    return config.get(arg, "")


def create_folder(folder_name: str) -> str:

    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"[INFO] 创建文件夹: {folder_name}")
    else:
        print(f"[INFO] 文件夹已存在: {folder_name}")
    return folder_name

def cookie_check():
    global use_cookie
    t = input("是否检查登录有效性？不登录可能导致部分图片无法获取。(y/n): ")
    if t.lower() == 'y':
        use_cookie = True
        try:
            cookie.check_verification()
        except cookie.CookieException as e:
            print(f"[ERROR] Cookie验证失败: {e}")
            cookie.main() # 已经在Cookie.main中处理了重试机制
    elif t.lower() == 'n':
        print("跳过登录有效性检查。")
        use_cookie = False
    else:
        cookie_check()


def zip_gif_to_video(data: Any, dest_path: str, idx: int) -> None:
    zip_file = f"{dest_path}/image_{idx}_{data[2]}.zip"  #TODO: 是否保留zip文件
    output_path = f"{dest_path}/gif_{idx}_{data[2]}.mp4"

    with open(zip_file, "wb") as f:
        f.write(data[0])
        print(f"[INFO] 保存动图文件: {zip_file}")
    
    tempfile.tempdir = dest_path
    with tempfile.TemporaryDirectory() as tmpdir:
        # 解压zip文件
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)
            print(f"[INFO] 解压动图文件到: {tmpdir}")

        # 生成视频文件
        from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

        frames_info: list = picgetter.gif_further(data[2].split("_")[0], True, "frames")
        img_paths = [os.path.join(tmpdir, item["file"]) for item in frames_info]
        durations = [item["delay"] / 1000 for item in frames_info]

        assert len(img_paths) == len(durations), "帧数与持续时间数量不匹配"
        clip = ImageSequenceClip(img_paths, durations=durations)
        clip.write_videofile(output_path, fps=30, audio=False, logger=None)
        print(f"[INFO] 生成视频文件: {output_path}")

if __name__ == "__main__":
    # Cookie会影响部分图片的获取，已经加入Cookie支持
    # 最核心的Cookie为PHPSESSID
    cookie_check()
    cookie.clear_useless_cookies()
    dest_folder = create_folder(read_config("dest_folder")) if read_config("dest_folder") != "" else "pic" #最外层文件夹
    folder_path = create_folder(f"{dest_folder}/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}") #按时间创建子文件夹

    # 读取配置
    page, max_page = read_config("page"), read_config("max_pictures_per_post")

    def check_int(value: str, default: int) -> int:
        try:
            return int(value)
        except (ValueError, TypeError):
            print(f"[WARNING] 配置值错误，使用默认值: {default}")
            return default
    page = check_int(page, 1)
    max_page = check_int(max_page, 2)

    json_info = tagsearcher.try_get_tagsearch(page=page, useCookie=use_cookie)
    pic_info: Iterator = tagsearcher.try_resolve_pic_info(json_info)
    url_generator = picgetter.try_get_url_combine(pic_info, max_per_post=max_page)
    
    async def process_and_save():
        idx = 0
        async for data in picgetter.try_get_pic_origin_url_async(url_generator, max_concurrent=5):
            if data[1][0]:  # ifGif
                zip_gif_to_video(data, folder_path, idx)
            else:
                with open(f"{folder_path}/image_{idx}_{data[2]}{data[1][1]}", "wb") as f:
                    f.write(data[0])
                    print(f"[INFO] 保存图片文件: {folder_path}/image_{idx}_{data[2]}{data[1][1]}")
            idx += 1
    
    asyncio.run(process_and_save())
