#!/usr/bin/env python3.11
"""Follow Sogou redirect to see the actual article."""
import re
from urllib.request import Request, urlopen
import ssl

PROXY = "http://127.0.0.1:7890"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/116.0 Safari/537.36 MicroMessenger/8.0"
)

import urllib.request
proxy_handler = urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
ctx = ssl.create_default_context()
opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))

# The redirect URL from Sogou
sogou_redirect = "https://weixin.sogou.com/link?url=dn9a_-gY295K0Rci_xozVXfdMkSQTLW6cwJThYulHEtVjXrGTiVgSwy_Slq3-RF2FeZ5PLXeK73kosKzhXZnr1qXa8Fplpd9vUqSdFlUk03C-gV8tjpPZhVhzE0pXVy9MLyfbe1SCQue3CsGNYUfL-wl9VflXS4Iz5-80cgfhRqY147ZjfI4BIBZaITVymEpBPqvGBJ-2HUBpQxUdts_QRuJ4CCUFmkdq6O7ziIszusa0v7LLtE55-sYbx8OSDnLtJrSifAQC8LzAjcIGepUqA..&type=2&query=hz0SosxuMSHlNgzB3yWrjQ&token=EB7A89B91F06C78AA4A3F4A05F7BA86DA593746969E84EB3"

headers = {
    "User-Agent": UA,
    "Referer": "https://weixin.sogou.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

try:
    # Don't follow redirects automatically - check where it goes
    req = Request(sogou_redirect, headers=headers)
    resp = opener.open(req, timeout=20)
    print("Final URL:", resp.url)
    print("Status:", getattr(resp, "status", 200))
    html = resp.read().decode("utf-8", errors="ignore")
    print("HTML length:", len(html))
    print("Has js_content:", 'id="js_content"' in html)
    print("Has 环境异常:", "环境异常" in html)

    if 'id="js_content"' in html:
        print("SUCCESS! Found article content")
        print("First 300:", html[:300])
    else:
        print("First 300:", html[:300])
        print("Last 300:", html[-300:])

except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()
