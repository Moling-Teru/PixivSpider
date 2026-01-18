import json
import playwright
from playwright.sync_api import sync_playwright
from requests.cookies import cookiejar_from_dict
from requests.cookies import RequestsCookieJar
import time
import os

class CookieException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message
    

def run_login_capture(target_url):
    with sync_playwright() as pl:
        # 启动浏览器
        # TODO: 处理浏览器异常
        browser = pl.chromium.launch(channel="msedge", headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(target_url)

        # 等待手动登录
        print("请在弹出的浏览器中手动完成登录操作。")
        print("登录成功并跳转后，请回到这里按 [回车键] 继续...")
        print("------------------------------------------------")
        input()

        cookies = context.cookies() # 获取Cookie
        save_path = "json/cookies.json"
        if not os.path.exists("json"):
            os.makedirs("json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=4, ensure_ascii=False)
            
        print(f"获取 {len(cookies)} 个 Cookie，并保存至 {save_path}")
        browser.close()


def clear_useless_cookies():
    cookies: list = json.loads(open("json/cookies.json", "r", encoding="utf-8").read())
    cookies = [cookie for cookie in cookies if cookie['domain'] == '.pixiv.net']
    with open("json/cookies.json", "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=4, ensure_ascii=False)

def check_verification():
    import time,os

    if not os.path.exists("json/cookies.json"):
        raise CookieException("未找到 cookies.json 文件，请先获取 Cookie。")
    
    cookies: list = json.loads(open("json/cookies.json", "r", encoding="utf-8").read())
    names = [cookie['name'] for cookie in cookies if cookie['expires'] > time.time() or cookie['expires'] == -1]
    if "a_type" not in names:
        raise CookieException("获取的并非登录Cookie，请重新获取 Cookie。")
    
    for cookie in cookies:
        if cookie['name'] == 'PHPSESSID':
            if cookie["expires"] == -1 or cookie["expires"] > time.time():
                print(f"当前PHPSESSID为: {cookie['value']}")
                timestamp: float = cookie["expires"]
                if timestamp != -1:
                    expire_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
                    print(f"PHPSESSID 有效期至: {expire_time}")
                return
            else: 
                print("PHPSESSID已过期，请重新获取Cookie。")
                raise CookieException("PHPSESSID已过期。")
        
        else:
            if cookie['expires'] != -1 and cookie['expires'] < time.time():
                print(f"[WARNING] Cookie {cookie['name']} 已过期。但这并不重要。")
            
    print("未找到PHPSESSID，请重新获取Cookie。")
    raise CookieException("未找到PHPSESSID。")

def request_cookies() -> RequestsCookieJar:

    cookies: list = json.loads(open("json/cookies.json", "r", encoding="utf-8").read())
    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies if cookie['expires'] > time.time() or cookie['expires'] == -1}
    jar: RequestsCookieJar = cookiejar_from_dict(cookie_dict)
    return jar

def main():
    target_site = "https://www.pixiv.net/" 
    run_login_capture(target_site)
    clear_useless_cookies()
    try:
        check_verification()
    except CookieException as e:
        print(f"[ERROR] Cookie验证失败: {e}")
        main()

if __name__ == "__main__":
    main()