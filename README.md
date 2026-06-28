# AI日报自动推送

每天早上9点自动抓取最新AI新闻，推送到你的邮箱。

## 功能特点

- 🤖 **多源聚合**: Hacker News、Reddit、36氪、机器之心、TechCrunch
- 📧 **邮件推送**: 精美的HTML格式，中英双语标签
- ☁️ **云端执行**: GitHub Actions免费定时执行，无需本地运行
- 🔄 **自动去重**: 避免重复新闻

## 快速开始

### 1. Fork 本仓库

点击 GitHub 右上角的 "Fork" 按钮。

### 2. 配置邮箱密钥

进入你的仓库 → Settings → Secrets and variables → Actions → New repository secret

添加以下3个密钥：

| 密钥名称 | 说明 | 示例 |
|---------|------|------|
| MAIL_SENDER | 发送邮箱（QQ邮箱） | `123456789@qq.com` |
| MAIL_PASSWORD | QQ邮箱授权码 | `abcdefghijklmn` |
| MAIL_RECEIVER | 接收邮箱 | `youremail@example.com` |

**如何获取QQ邮箱授权码？**

1. 登录 QQ邮箱 → 设置 → 账户
2. 找到 "POP3/SMTP服务" → 开启
3. 按照提示发送短信获取授权码

### 3. 启用 GitHub Actions

进入你的仓库 → Actions → I understand my workflows, go ahead and enable them

## 运行时间

- **北京时间**: 每天早上 9:00
- **UTC时间**: 每天凌晨 1:00

可在 `.github/workflows/daily-news.yml` 中修改 `cron` 表达式。

## 手动触发

进入 Actions → daily-news → Run workflow

## 项目结构

```
ai-news-daily/
├── main.py          # 主脚本（爬虫+邮件发送）
├── requirements.txt # 依赖包
└── .github/
    └── workflows/
        └── daily-news.yml # GitHub Actions 工作流
```

## 新闻源

| 来源 | 语言 | 说明 |
|------|------|------|
| Hacker News | English | AI相关最新资讯 |
| Reddit r/artificial | English | 每日热门AI讨论 |
| 36氪 | 中文 | AI相关报道 |
| 机器之心 | 中文 | AI技术深度报道 |
| TechCrunch | English | 科技新闻 |

## 本地测试

```bash
pip install -r requirements.txt

# 设置环境变量
set MAIL_SENDER=your-email@qq.com
set MAIL_PASSWORD=your-auth-code
set MAIL_RECEIVER=your-receiver@example.com

python main.py
```
