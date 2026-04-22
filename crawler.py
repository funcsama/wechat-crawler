#!/usr/bin/env python3
"""
WeChat Article Crawler - 完整解决方案
全自动微信公众号文章爬取工具

核心策略:
1. 搜索: 通过 Sogou 搜索公众号文章 (无需验证，完全可用)
2. 验证码识别: Tesseract OCR 自动识别 WeChat 验证码
3. 内容提取: BeautifulSoup 解析文章正文

依赖:
    pip install requests beautifulsoup4 lxml Pillow
    yum install -y tesseract  # 或 apt-get install tesseract-ocr

用法:
    python crawler.py search <关键词>    # 搜索文章
    python crawler.py article <URL>     # 获取单篇文章
"""

import sys
import os
import time
import re
import io
import tempfile
import subprocess
import requests
from lxml import etree
from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse, parse_qs
from PIL import Image, ImageEnhance, ImageFilter

# ============================================================================
# werkzeug.contrib.cache 兼容层 (Python 3.6 + werkzeug 2.x)
# ============================================================================
import types
try:
    import werkzeug.contrib.cache as wc
    # 已经有了
except ImportError:
    class FakeCache:
        def __init__(self, *a, **kw): pass
        def get(self, k): return None
        def set(self, k, v, t=None): pass
    m = types.ModuleType('werkzeug.contrib.cache')
    m.BaseCache = FakeCache
    m.FileSystemCache = FakeCache
    sys.modules['werkzeug.contrib.cache'] = m


# ============================================================================
# OCR 验证码识别
# ============================================================================

def ocr_captcha(img_bytes):
    """
    用 Tesseract OCR 识别 WeChat 验证码图片
    返回识别的字符（4位字母数字）
    """
    try:
        img = Image.open(io.BytesIO(img_bytes))
        
        # 尝试多种预处理方案
        candidates = []
        
        # 方案1: 直接识别（灰色图）
        gray = img.convert('L')
        for psm in [7, 8, 13]:
            for scale in [2, 3, 4]:
                resized = gray.resize((gray.width * scale, gray.height * scale), Image.LANCZOS)
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                    resized.save(f.name, 'PNG')
                    path = f.name
                
                proc = subprocess.Popen(
                    ['tesseract', path, 'stdout', '--psm', str(psm), '-l', 'eng',
                     '--tessdata-dir', '/usr/share/tesseract/tessdata'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, _ = proc.communicate()
                text = stdout.decode().strip()
                os.unlink(path)
                
                # 清理结果：只保留字母和数字
                cleaned = re.sub(r'[^A-Za-z0-9]', '', text)
                if 3 <= len(cleaned) <= 6:
                    candidates.append(cleaned)
        
        # 方案2: 对比度增强 + 二值化
        for scale in [3, 4]:
            enhanced = ImageEnhance.Contrast(gray).enhance(4.0)
            resized = enhanced.resize((enhanced.width * scale, enhanced.height * scale), Image.LANCZOS)
            
            # 自适应二值化
            resized_arr = list(resized.getdata())
            avg = sum(resized_arr) / len(resized_arr)
            binary = resized.point(lambda x: 0 if x < avg else 255, 'L')
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                binary.save(f.name, 'PNG')
                path = f.name
            
            proc = subprocess.Popen(
                ['tesseract', path, 'stdout', '--psm', '7', '-l', 'eng',
                 '--tessdata-dir', '/usr/share/tesseract/tessdata'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, _ = proc.communicate()
            text = stdout.decode().strip()
            os.unlink(path)
            
            cleaned = re.sub(r'[^A-Za-z0-9]', '', text)
            if 3 <= len(cleaned) <= 6:
                candidates.append(cleaned)
        
        # 选择最佳候选（出现次数最多的）
        if candidates:
            from collections import Counter
            counter = Counter(candidates)
            best = counter.most_common(1)[0][0]
            return best.upper()
        
        return None
        
    except Exception as e:
        print(f"[OCR ERROR] {e}", file=sys.stderr)
        return None


# ============================================================================
# 核心爬取引擎
# ============================================================================

PROXY = {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


class WechatCrawler:
    """微信公众号文章爬取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def search(self, keyword, limit=10):
        """通过 Sogou 搜索微信公众号文章（无需验证）"""
        url = f'https://weixin.sogou.com/weixin?type=2&query={quote(keyword)}&ie=utf8'
        
        resp = self.session.get(url, proxies=PROXY, timeout=15)
        resp.raise_for_status()
        
        page = etree.HTML(resp.text)
        lis = page.xpath('//ul[@class="news-list"]/li')
        
        results = []
        for li in lis[:limit]:
            # 获取标题和链接
            title_els = li.xpath('.//a[contains(@href, "link?url=")]')
            if not title_els:
                continue
            
            # 取第一个包含 link?url= 的链接作为文章链接
            article_link = None
            for a in title_els:
                href = a.get('href', '')
                if 'link?url=' in href:
                    article_link = a
                    break
            
            if not article_link is None:
                title = ''.join(article_link.itertext()).strip()
                title = title.replace('<!--red_beg-->', '').replace('<!--red_end-->', '')
                
                href = article_link.get('href')
                if not href.startswith('http'):
                    href = 'https://weixin.sogou.com' + href
                
                # 摘要
                p_els = li.xpath('div[2]/p')
                abstract = ''.join(p_els[0].itertext()).strip() if p_els else ''
                abstract = abstract.replace('<!--red_beg-->', '').replace('<!--red_end-->', '')
                
                results.append({
                    'title': title,
                    'url': href,
                    'abstract': abstract[:200],
                    'sogou_url': href,
                })
        
        return results
    
    def _get_captcha(self):
        """获取验证码图片"""
        captcha_url = f'https://mp.weixin.qq.com/mp/verifycode?cert={int(time.time() * 1000)}'
        r = self.session.get(captcha_url, proxies=PROXY)
        return r.content if r.ok else None
    
    def _submit_captcha(self, url, captcha_text):
        """提交验证码"""
        data = {'cert': int(time.time() * 1000), 'input': captcha_text}
        headers = {
            'Host': 'mp.weixin.qq.com',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': url
        }
        r = self.session.post(
            'https://mp.weixin.qq.com/mp/verifycode',
            data=data, headers=headers, proxies=PROXY
        )
        return r.json() if r.ok else {'ret': -1}
    
    def get_article(self, url, max_captcha_attempts=3):
        """
        获取文章内容，自动处理验证码
        """
        for attempt in range(max_captcha_attempts):
            resp = self.session.get(url, proxies=PROXY, timeout=15)
            resp.encoding = 'utf-8'
            
            # 检查验证码墙
            if '环境异常' not in resp.text and 'wappoc_appmsgcaptcha' not in resp.url:
                break
            
            print(f"[INFO] 检测到验证码墙 (尝试 {attempt + 1}/{max_captcha_attempts})", file=sys.stderr)
            
            # 获取验证码
            img_bytes = self._get_captcha()
            if not img_bytes:
                print("[ERROR] 无法获取验证码图片", file=sys.stderr)
                continue
            
            # OCR 识别
            captcha_text = ocr_captcha(img_bytes)
            if not captcha_text:
                # 保存验证码让用户识别
                debug_path = os.path.join(tempfile.gettempdir(), 'wechat_captcha_debug.png')
                with open(debug_path, 'wb') as f:
                    f.write(img_bytes)
                print(f"[WARN] OCR 失败，图片已保存: {debug_path}", file=sys.stderr)
                captcha_text = input("[INPUT] 请打开图片输入验证码: ").strip()
            
            print(f"[INFO] 识别结果: {captcha_text}", file=sys.stderr)
            
            result = self._submit_captcha(url, captcha_text)
            print(f"[INFO] 提交结果: {result}", file=sys.stderr)
            
            if result.get('ret') == 0:
                # 成功，重新获取页面
                resp = self.session.get(url, proxies=PROXY, timeout=15)
                resp.encoding = 'utf-8'
                if '环境异常' not in resp.text:
                    break
            
            time.sleep(1)
        
        # 解析内容
        return self._parse_article(resp.text, resp.url)
    
    def _parse_article(self, html, url):
        """解析文章 HTML"""
        soup = BeautifulSoup(html, 'lxml')
        
        # 标题
        og_title = soup.find('meta', {'property': 'og:title'})
        title = og_title['content'] if og_title else ''
        
        # 作者
        author = ''
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta:
            author = author_meta.get('content', '')
        
        # 正文区域
        content_div = soup.find('div', {'id': 'js_content'}) or \
                      soup.find('div', {'class': 'rich_media_content'})
        
        if not content_div:
            return {
                'success': False,
                'error': 'no_content',
                'message': '无法找到文章正文'
            }
        
        # 清理
        for tag in content_div.find_all(['script', 'style']):
            tag.decompose()
        
        # 图片列表
        imgs = [img.get('data-src') or img.get('src') 
                for img in content_div.find_all('img')
                if img.get('src')]
        
        return {
            'success': True,
            'title': title,
            'author': author,
            'content_html': str(content_div),
            'content_text': content_div.get_text(separator='\n', strip=True),
            'imgs': imgs,
            'url': url,
        }
    
    def fetch(self, url_or_keyword):
        """通用获取接口"""
        if url_or_keyword.startswith('http'):
            return self.get_article(url_or_keyword)
        return self.search(url_or_keyword)


def cmd_search(keyword, limit=10):
    crawler = WechatCrawler()
    results = crawler.search(keyword, limit)
    
    print(f"\n找到 {len(results)} 篇相关文章:\n")
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['title']}")
        print(f"    摘要: {r.get('abstract', 'N/A')[:100]}...")
        print()
    
    return results


def cmd_article(url):
    crawler = WechatCrawler()
    result = crawler.get_article(url)
    
    if result.get('success'):
        print("=" * 60)
        print(f"标题: {result.get('title', 'N/A')}")
        print(f"作者: {result.get('author', 'N/A')}")
        print(f"URL: {result.get('url', url)}")
        print("=" * 60)
        text = result.get('content_text', '')
        print(f"\n正文预览（前800字）:\n{text[:800]}\n\n...")
        print(f"\n正文总长度: {len(text)} 字符")
        print(f"图片数量: {len(result.get('imgs', []))}")
        return result
    else:
        print(f"\n获取失败: {result.get('error')} - {result.get('message', 'Unknown')}")
        
        if result.get('error') in ('no_content', 'captcha_failed'):
            keyword = input("\n尝试搜索相关内容? 请输入关键词: ").strip()
            if keyword:
                cmd_search(keyword)
        
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n用法:")
        print("  python crawler.py search <关键词>")
        print("  python crawler.py article <URL>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'search':
        keyword = ' '.join(sys.argv[2:]) or '量子位智库AI周报'
        cmd_search(keyword)
    elif cmd == 'article':
        if len(sys.argv) < 3:
            print("错误: 请提供文章URL")
            sys.exit(1)
        cmd_article(sys.argv[2])
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == '__main__':
    main()