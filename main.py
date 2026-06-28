import os
import requests
import feedparser
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import re

NEWS_COUNT = 20

AI_KEYWORDS = [
    'AI', '人工智能', '大模型', 'ChatGPT', 'GPT', 'LLM',
    '机器学习', '深度学习', '神经网络', 'AI模型', 'AI生成',
    'AIGC', 'AI绘画', 'AI写作', '语音助手', '自动驾驶',
    'NLP', '计算机视觉', 'Transformer', 'BERT',
    '扩散模型', 'Stable Diffusion', 'Midjourney', 'DALL·E',
    'Gemini', 'Claude', '文心一言', '通义千问', '讯飞星火',
    'AI芯片', 'GPU', '英伟达', 'prompt', '提示词', '微调',
    '大语言模型', '生成式AI', 'AI应用', 'AI工具', 'AI助手',
    'AI编程', 'AI搜索', 'AI语音', 'AI视频', 'AI对话',
    'AI开发', 'AI框架', 'AI平台', 'AI服务', 'AI技术',
    '智能', '机器人', '自动化',
]

NON_AI_KEYWORDS = [
    '手机', '电脑', '笔记本', '平板', '智能手表', '智能手环',
    '汽车', '手机游戏', '手游', '硬件', '处理器',
    '软件', '操作系统', 'iOS', 'Android', 'Windows',
    '互联网', '电商', '社交', '视频', '直播', '短视频',
    '微信', '支付宝', '腾讯', '阿里巴巴', '字节跳动',
    '股价', '投资', '上市', '融资', '创业', '商业',
    '科技', '数码', '消费', '评测', '开箱', '体验',
    'AIE', 'AIR', 'AIO', 'AIP', 'AIB', 'AIC', 'AID',
]

SMTP_CONFIG = {
    'host': 'smtp.qq.com',
    'port': 465,
    'sender': os.environ.get('MAIL_SENDER', ''),
    'password': os.environ.get('MAIL_PASSWORD', ''),
    'receiver': os.environ.get('MAIL_RECEIVER', ''),
}

ZHIQI_API_KEY = os.environ.get('ZHIQI_API_KEY', '')
ZHIQI_API_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'

def contains_ai_keyword(title):
    title_lower = title.lower()
    for kw in NON_AI_KEYWORDS:
        if kw.lower() in title_lower:
            return False
    for kw in AI_KEYWORDS:
        if kw.lower() in title_lower:
            return True
    return False

def polish_news_titles(news_list):
    if not ZHIQI_API_KEY:
        print("未配置智谱API密钥，跳过润色")
        return news_list
    
    titles = [news['title'] for news in news_list]
    titles_str = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])
    
    prompt = f"""请把下面这些新闻标题改成口语化的表达方式，像朋友聊天一样自然亲切，但不要添加额外信息，只润色标题本身：

{titles_str}

请直接给出润色后的标题，每行一个，保持序号不变，不要添加任何其他内容。"""
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {ZHIQI_API_KEY}'
        }
        
        payload = {
            'model': 'glm-4-flash',
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7
        }
        
        resp = requests.post(ZHIQI_API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        polished_text = data['choices'][0]['message']['content']
        polished_lines = polished_text.strip().split('\n')
        
        for i, news in enumerate(news_list):
            if i < len(polished_lines):
                line = polished_lines[i].strip()
                if '.' in line:
                    line = line.split('.', 1)[1].strip()
                news['title'] = line
        
        print(f"成功润色 {len(news_list)} 条新闻标题")
    except Exception as e:
        print(f"润色失败: {e}")
    
    return news_list

def fetch_hackernews_ai():
    news = []
    try:
        url = 'https://hnrss.org/newest?q=AI+LLM+machine+learning'
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            if contains_ai_keyword(entry.title):
                news.append({
                    'title': entry.title,
                    'link': entry.link,
                    'source': 'Hacker News',
                    'date': entry.published if hasattr(entry, 'published') else '',
                    'lang': 'en'
                })
            if len(news) >= 8:
                break
    except Exception as e:
        print(f"Error fetching Hacker News: {e}")
    return news

def fetch_reddit_ai():
    news = []
    try:
        url = 'https://www.reddit.com/r/artificial/top/.json?limit=15&t=day'
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        for item in data['data']['children'][:15]:
            post = item['data']
            if contains_ai_keyword(post['title']):
                news.append({
                    'title': post['title'],
                    'link': 'https://reddit.com' + post['permalink'],
                    'source': 'Reddit AI',
                    'date': '',
                    'lang': 'en'
                })
            if len(news) >= 8:
                break
    except Exception as e:
        print(f"Error fetching Reddit: {e}")
    return news

def fetch_36kr():
    news = []
    try:
        url = 'https://36kr.com/feed'
        feed = feedparser.parse(url)
        for entry in feed.entries[:30]:
            if contains_ai_keyword(entry.title):
                news.append({
                    'title': entry.title,
                    'link': entry.link,
                    'source': '36氪',
                    'date': entry.published if hasattr(entry, 'published') else '',
                    'lang': 'zh'
                })
            if len(news) >= 8:
                break
    except Exception as e:
        print(f"Error fetching 36氪: {e}")
    return news

def fetch_jqnews():
    news = []
    try:
        url = 'https://www.jiqizhixin.net/rss'
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            news.append({
                'title': entry.title,
                'link': entry.link,
                'source': '机器之心',
                'date': entry.published if hasattr(entry, 'published') else '',
                'lang': 'zh'
            })
            if len(news) >= 8:
                break
    except Exception as e:
        print(f"Error fetching 机器之心: {e}")
    return news

def fetch_qbitai():
    news = []
    try:
        url = 'https://www.qbitai.com/feed'
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            news.append({
                'title': entry.title,
                'link': entry.link,
                'source': '量子位',
                'date': entry.published if hasattr(entry, 'published') else '',
                'lang': 'zh'
            })
            if len(news) >= 8:
                break
    except Exception as e:
        print(f"Error fetching 量子位: {e}")
    return news

def fetch_aifrontline():
    news = []
    try:
        url = 'https://www.aifrontline.com/feed'
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            news.append({
                'title': entry.title,
                'link': entry.link,
                'source': 'AI前线',
                'date': entry.published if hasattr(entry, 'published') else '',
                'lang': 'zh'
            })
            if len(news) >= 6:
                break
    except Exception as e:
        print(f"Error fetching AI前线: {e}")
    return news

def fetch_techcrunch():
    news = []
    try:
        url = 'https://techcrunch.com/feed/'
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            if contains_ai_keyword(entry.title):
                news.append({
                    'title': entry.title,
                    'link': entry.link,
                    'source': 'TechCrunch',
                    'date': entry.published if hasattr(entry, 'published') else '',
                    'lang': 'en'
                })
            if len(news) >= 5:
                break
    except Exception as e:
        print(f"Error fetching TechCrunch: {e}")
    return news

def fetch_leiphone():
    news = []
    try:
        url = 'https://www.leiphone.com/feed'
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            if contains_ai_keyword(entry.title):
                news.append({
                    'title': entry.title,
                    'link': entry.link,
                    'source': '雷锋网',
                    'date': entry.published if hasattr(entry, 'published') else '',
                    'lang': 'zh'
                })
            if len(news) >= 6:
                break
    except Exception as e:
        print(f"Error fetching 雷锋网: {e}")
    return news

def fetch_aihuo():
    news = []
    try:
        url = 'https://www.aichatfire.com/feed'
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            news.append({
                'title': entry.title,
                'link': entry.link,
                'source': 'AI火',
                'date': entry.published if hasattr(entry, 'published') else '',
                'lang': 'zh'
            })
            if len(news) >= 5:
                break
    except Exception as e:
        print(f"Error fetching AI火: {e}")
    return news

def fetch_geekpark():
    news = []
    try:
        url = 'https://www.geekpark.net/rss'
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            if contains_ai_keyword(entry.title):
                news.append({
                    'title': entry.title,
                    'link': entry.link,
                    'source': '极客公园',
                    'date': entry.published if hasattr(entry, 'published') else '',
                    'lang': 'zh'
                })
            if len(news) >= 6:
                break
    except Exception as e:
        print(f"Error fetching 极客公园: {e}")
    return news

def fetch_tmtpost():
    news = []
    try:
        url = 'https://www.tmtpost.com/feed'
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            if contains_ai_keyword(entry.title):
                news.append({
                    'title': entry.title,
                    'link': entry.link,
                    'source': '钛媒体',
                    'date': entry.published if hasattr(entry, 'published') else '',
                    'lang': 'zh'
                })
            if len(news) >= 6:
                break
    except Exception as e:
        print(f"Error fetching 钛媒体: {e}")
    return news

def fetch_all_news():
    all_news = []
    all_news.extend(fetch_36kr())
    all_news.extend(fetch_jqnews())
    all_news.extend(fetch_qbitai())
    all_news.extend(fetch_aifrontline())
    all_news.extend(fetch_leiphone())
    all_news.extend(fetch_geekpark())
    all_news.extend(fetch_tmtpost())
    
    seen_titles = set()
    unique_news = []
    for news in all_news:
        title_clean = re.sub(r'[^\w\s]', '', news['title']).lower()
        if title_clean not in seen_titles:
            seen_titles.add(title_clean)
            unique_news.append(news)
    
    return unique_news[:NEWS_COUNT]

def generate_email_content(news_list):
    today = datetime.now().strftime('%Y年%m月%d日')
    
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>AI日报 - {today}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 20px; color: #333; }}
        .header p {{ margin: 5px 0 0; font-size: 12px; color: #999; }}
        .news-list {{ list-style: none; padding: 0; }}
        .news-item {{ padding: 8px 0; border-bottom: 1px dashed #eee; }}
        .news-item:last-child {{ border-bottom: none; }}
        .news-item a {{ font-size: 14px; color: #333; text-decoration: none; line-height: 1.6; }}
        .news-item a:hover {{ color: #667eea; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI日报 {today}</h1>
        <p>今日精选 {len(news_list)} 条</p>
    </div>
    <ol class="news-list">
"""
    
    for i, news in enumerate(news_list, 1):
        html += f"<li class='news-item'><span style='color:#667eea;font-weight:bold;margin-right:8px;'>{i}.</span><a href='{news['link']}' target='_blank'>{news['title']}</a></li>\n"
    
    html += """
    </ol>
</body>
</html>
"""
    return html

def send_email(html_content):
    if not SMTP_CONFIG['sender'] or not SMTP_CONFIG['password'] or not SMTP_CONFIG['receiver']:
        raise ValueError("请配置邮箱环境变量: MAIL_SENDER, MAIL_PASSWORD, MAIL_RECEIVER")
    
    today = datetime.now().strftime('%Y-%m-%d')
    msg = MIMEMultipart()
    msg['From'] = SMTP_CONFIG['sender']
    msg['To'] = SMTP_CONFIG['receiver']
    msg['Subject'] = f"🤖 AI日报 {today}"
    
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    with smtplib.SMTP_SSL(SMTP_CONFIG['host'], SMTP_CONFIG['port']) as server:
        server.login(SMTP_CONFIG['sender'], SMTP_CONFIG['password'])
        server.sendmail(SMTP_CONFIG['sender'], SMTP_CONFIG['receiver'], msg.as_string())
    
    print(f"邮件发送成功: {SMTP_CONFIG['receiver']}")

def main():
    print(f"开始抓取 AI 新闻 ({datetime.now()})...")
    
    news_list = fetch_all_news()
    if not news_list:
        print("未获取到任何新闻")
        return
    
    print(f"获取到 {len(news_list)} 条新闻")
    
    news_list = polish_news_titles(news_list)
    
    html = generate_email_content(news_list)
    
    send_email(html)
    print("任务完成!")

if __name__ == '__main__':
    main()
