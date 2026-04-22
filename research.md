# 调研报告：科技资讯日报系统

**调研时间：2026-04-22**
**目标：每天一份高质量科技资讯报告**

---

## 一、微信公众号爬取结论

### 问题
微信对服务器 IP（47.98.163.187）实施了 TenCent tcaptcha 人机验证码墙（拖动验证）。

### 尝试过的方法
| 方法 | 结果 | 说明 |
|---|---|---|
| HTTP 直接请求 | ❌ | 触发验证码页 |
| Playwright 浏览器渲染 | ❌ | 验证码页 |
| Sogou 搜索跳转 | ❌ | Sogou 反爬虫页 |
| 无代理直连 | ❌ | 验证码页 |
| 搜狗微信 wechatsogou | ⚠️ | 只能10条，链接临时失效 |
| 公众号后台 API | ❌ | 需要 cookie+token |

### 根本原因
验证码在 JS 执行前就触发，cookie 在验证码通过之前根本用不上。属于 IP 级别的人机验证，不是应用层问题。

### 解决方案
Cearlz 决定：**不死磕微信，换信源**。

---

## 二、信源调研

### 推荐信源（高质量、无反爬）

#### 英文科技 RSS（首选）

| 源 | Feed URL | 特点 |
|---|---|---|
| TechCrunch | https://techcrunch.com/feed/ | 全球科技创业，覆盖广 |
| The Verge | https://www.theverge.com/rss/index.xml | 消费科技，产品导向 |
| Ars Technica | https://feeds.arstechnica.com/arstechnica/index | 深度技术，工程师最爱 |
| Wired | https://www.wired.com/feed/rss | 科技文化，社会影响 |
| MIT Tech Review | https://www.technologyreview.com/feed/ | 深度技术研究 |
| VentureBeat AI | https://venturebeat.com/category/ai/feed/ | AI 专项 |
| Hacker News | https://news.ycombinator.com/rss | 工程师必读，社区智慧 |
| The Information | https://www.theinformation.com/feed | 深度科技商业报道 |

#### 中文科技 RSS

| 源 | Feed URL | 特点 |
|---|---|---|
| 36氪 | https://36kr.com/feed | 科技创投，最大 |
| 爱范儿 | https://www.ifanr.com/feed | 科技生活，质量高 |
| 极客公园 | http://www.geekpark.net/rss | 科技产品 |
| 少数派 | https://sspai.com/feed | 数字生活，高质量 |
| 钛媒体 | https://www.tmtpost.com/rss | 科技财经 |

#### GitHub Trending（程序员专属）

| 源 | URL | 特点 |
|---|---|---|
| GitHub Trending | https://github.com/trending.rss | 每日热门项目 |
| GitHub Trending AI | https://github.com/trending?l=python&since=daily | Python 每日热门 |

---

## 三、GitHub 现有工具调研

### BestBlogs（强烈推荐参考）
- **地址**：github.com/hailynch/BestBlogs
- **星标**：~
- **原理**：400+ RSS 源 → 无头浏览器抓全文 → GPT-4 摘要评分翻译
- **亮点**：有 OPML 订阅源列表，直接可用
- **微信公众号 RSS**：用 wewe-rss 转换了 200 个公众号
- **可借鉴**：Dify Workflow 文章分析流程

### ai-news-aggregator
- **地址**：github.com/SuYxh/ai-news-aggregator
- **星标**：~
- **功能**：80+ AI/科技源，支持过滤 + 双语标题翻译
- **状态**：活跃（2026-04-18 仍有更新）

### news-aggregator-skill（OpenClaw Skill）
- **地址**：github.com/cclank/news-aggregator-skill
- **功能**：全网新闻聚合，28+ 信源，零配置，内置 Playwright 绕过 Cloudflare
- **亮点**：OpenClaw 原生支持，一键安装，多套早报预设
- **安装**：`npx clawhub@latest install news-aggregator-skill`
- **注意**：需要先登录 ClawHub（`clawhub login`）

### FreshRSS
- **地址**：github.com/FreshRSS/FreshRSS
- **星标**：12k+
- **功能**：自托管 RSS 聚合器，多用户，API 支持
- **适合**：搭建长期 RSS 阅读服务

---

## 四、ClawHub Skills 调研

### news-aggregator-skill ⭐推荐
- 全网新闻聚合，零配置
- 支持 deep fetch（playwright 绕过防爬）
- 多套早报预设（综合早报、财经早报、科技早报、AI深度日报）
- **问题**：需要先登录 ClawHub

### skill-vetter
- 安全检测 skill
- 扫描恶意代码、危险权限
- 建议安装，批量安装 skill 前先检测

---

## 五、实现方案

### 方案 A：直接安装 news-aggregator-skill（推荐）
```bash
npm install -g clawhub
clawhub login  # 需要浏览器授权
clawhub install news-aggregator-skill
```
**优点**：零配置，多信源，内置报告生成
**缺点**：需要登录 ClawHub

### 方案 B：自建 RSS 抓取管道（备选）
1. 用 `feedparser` 抓 RSS
2. 用 `requests + BeautifulSoup` 抓正文
3. 用 LLM 生成摘要
4. 输出 Markdown 报告

### 方案 C：参考 BestBlogs 架构
- 用 RSSHub 生成动态 RSS（万物皆可 RSS）
- 用 wewe-rss 转换微信公众号
- 用 Dify Workflow 做文章分析
- **优点**：最完整
- **缺点**：需要较多服务（RSSHub + wewe-rss + Dify）

---

## 六、GitHub 仓库管理

已创建：**github.com/chess99/wechat-crawler**

```bash
cd /root/.openclaw/workspace/wechat-crawler
git add -A
git commit -m "docs: 调研报告 + 信源配置 + 脚本框架"
git push origin main
```

---

## 七、下一步行动计划

- [ ] 登录 ClawHub，安装 news-aggregator-skill
- [ ] 测试该 skill 是否能正常抓取并生成报告
- [ ] 配置 cron 每天定时触发
- [ ] 报告输出到飞书或本地文件
