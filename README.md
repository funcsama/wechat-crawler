# wechat-crawler
微信公众号文章爬取工具 & 科技资讯聚合系统

## 状态：微信文章爬取暂停

**微信公众号对服务器 IP 实施了人机验证码墙**，暂时无法绕过。详情见 [research.md](./research.md)。

**不死磕微信，换信源**。详细调研见 [research.md](./research.md)。

## 目录结构

```
wechat-crawler/
├── research.md          # 调研报告（信源方案、工具选型、GitHub repos）
├── README.md            # 本文件
├── sources/            # 信源配置
│   └── tech_rss.yaml   # 科技 RSS 订阅源列表
├── scripts/            # 工具脚本
│   ├── fetch_rss.py    # RSS 爬取 + 解析
│   ├── summarize.py    # 文章摘要生成
│   └── daily_report.py # 每日报告生成
└── reports/            # 输出报告
```

## 快速开始

```bash
# 安装依赖
pip3 install feedparser requests beautifulsoup4 pyyaml

# 抓取 RSS 源列表
python3 scripts/fetch_rss.py

# 生成每日报告
python3 scripts/daily_report.py
```

## 已调研的主要信源

### 英文科技 RSS（高质量，无反爬）

| 源 | URL | 说明 |
|---|---|---|
| TechCrunch | https://techcrunch.com/feed/ | 全球科技创业 |
| The Verge | https://www.theverge.com/rss/index.xml | 消费科技 |
| Ars Technica | https://feeds.arstechnica.com/arstechnica/index | 深度科技 |
| Wired | https://www.wired.com/feed/rss | 科技文化 |
| MIT Tech Review | https://www.technologyreview.com/feed/ | 深度技术 |
| Hacker News | https://news.ycombinator.com/rss | 工程师必读 |
| VentureBeat AI | https://venturebeat.com/category/ai/feed/ | AI 资讯 |
| Ars Technica AI | https://feeds.arstechnica.com/arstechnica/technology-lab | AI 深度 |

### 中文科技 RSS

| 源 | URL | 说明 |
|---|---|---|
| 36氪 | https://36kr.com/feed | 科技创投 |
| 极客公园 | http://www.geekpark.net/rss | 科技产品 |
| 爱范儿 | https://www.ifanr.com/feed | 科技生活 |
| 少数派 | https://sspai.com/feed | 高质量数字生活 |

### 调研过的 GitHub 项目

| 项目 | 地址 | 说明 |
|---|---|---|
| BestBlogs | github.com/hailynch/BestBlogs | 400+ RSS 源 + AI 摘要评分 |
| ai-news-aggregator | github.com/SuYxh/ai-news-aggregator | 80+ AI/科技源，中文 |
| news-aggregator-skill | github.com/cclank/news-aggregator-skill | OpenClaw skill，零配置，支持 deep fetch |
| FreshRSS | github.com/FreshRSS/FreshRSS | 自托管 RSS 聚合器 |

### 调研过的 ClawHub Skills

| Skill | 安装命令 | 说明 |
|---|---|---|
| news-aggregator-skill | `clawhub install news-aggregator-skill` | 全网新闻聚合，28+ 信源，零配置，playwright 深度获取 |
| skill-vetter | `clawhub install skill-vetter` | 安全检测，评估 skill 风险 |

## 下一步计划

1. 安装 news-aggregator-skill（`clawhub install news-aggregator-skill`）
2. 配置 cron 每天自动抓取
3. 用 LLM 生成中文摘要
4. 输出每日科技简报到飞书
