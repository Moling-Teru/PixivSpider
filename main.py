import picgetter
import tagsearcher
import json
from typing import Dict, Generator, Tuple, Optional, Iterator
import datetime

def read_config(arg) -> str:
    with open('config.json', 'r', encoding='utf-8') as f:
        config:dict = json.load(f)
    
    return config.get(arg, "")

def create_folder(folder_name: str) -> str:
    import os
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"[INFO] 创建文件夹: {folder_name}")
    else:
        print(f"[INFO] 文件夹已存在: {folder_name}")
    return folder_name

if __name__ == "__main__":
    dest_folder = create_folder(read_config("dest_folder")) if read_config("dest_folder") != None else "pic"
    folder_path = create_folder(f"{dest_folder}/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    # 读取配置
    json_info = tagsearcher.try_get_tagsearch(page=4)
    pic_info: Iterator = tagsearcher.try_resolve_pic_info(json_info)
    url_generator = picgetter.try_get_url_combine(pic_info)
    content = picgetter.try_get_pic(url_generator)

    for idx,data in enumerate(content):
        if data[1][0]:  # ifGif
            with open(f"{folder_path}/image_{idx}_{data[2]}.zip", "wb") as f:
                f.write(data[0])
                print(f"[INFO] 保存动图文件: {folder_path}/image_{idx}_{data[2]}.zip")
        else:
            with open(f"{folder_path}/image_{idx}_{data[2]}{data[1][1]}", "wb") as f:
                f.write(data[0])
                print(f"[INFO] 保存图片文件: {folder_path}/image_{idx}_{data[2]}{data[1][1]}")
