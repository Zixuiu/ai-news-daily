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
    'Gemini', 'Claude', 'DeepSeek', '豆包', 'kimi', '智谱', '文心一言', '通义千问', '讯飞星火',
    'glm', '千问', 'qwen', 'OpenAI', 'Anthropic', 'Grok', 'Llama', 'Gemma', 'Mistral',
    '智能体', 'Agent', '多模态', '生成式', '无人机', 'AI芯片', 'GPU', '英伟达', 'prompt', '提示词', '微调',
    '大语言模型', '生成式AI', 'AI应用', 'AI工具', 'AI助手',
    'AI编程', 'AI搜索', 'AI语音', 'AI视频', 'AI对话',
    'AI开发', 'AI框架', 'AI平台', 'AI服务', 'AI技术',
    '智能', '机器人', '自动化',
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
    """白名单过滤：只有标题命中 AI 关键词才保留，杜绝无关内容混入日报"""
    title_lower = title.lower()
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

    def _call_glm(prompt_text, temperature=0.3):
        """统一封装智谱 GLM 调用，返回纯文本或 None。"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {ZHIQI_API_KEY}'
            }
            payload = {
                'model': 'glm-4-flash',
                'messages': [{'role': 'user', 'content': prompt_text}],
                'temperature': temperature
            }
            resp = requests.post(ZHIQI_API_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"GLM 调用失败: {e}")
            return None

    # 字数安全线：最终务必 <= MAX_LEN，AI 目标压到 TARGET，超长二次压缩到 RETRY
    MAX_LEN, TARGET, RETRY = 20, 16, 14

    prompt = f"""把下列新闻标题改成【超级大白话】，像刷短视频时博主解说那样，让不懂技术的人也能秒懂。

【绝对硬性要求】
1. 每条【最多 {TARGET} 个字】，超过一律算失败，必须压到 {TARGET} 字内
2. 下面这些词【绝对不能出现】，出现就重写：战略合作、底座、梯队、赋能、范式、重磅、深度融合、首发、持续进化、灰测、内测、达成、正式、深度、首批、高端
3. 用大白话：多用"搞、整、卷、杀、上线、开整、整明白、搞事情、来了、试了"
4. 一句话说清：谁 + 干了啥 + 结果咋样，越接地气越好

【正确示范】
原：范式与华为达成重磅算力战略合作，成为首批拥抱国产最高端算力底座的AI企业
改：华为帮一家AI公司用上国产算力

原：GPT-6灰测版下周发布
改：GPT-6下周就要发布了

原：灵犀智涌机器人进工业智能梯队
改：灵犀的机器人进工厂干活了

原：滴滴自动驾驶新一代车型开启载客测试服务
改：滴滴无人车开始拉客了

原：百变身登场出磨APEC活动，分享具身智能开源赋中小企数据转型
改：字节用开源AI帮小公司转型

原标题：
{titles_str}

直接输出改写后的标题，每行一条，不要任何其他说明："""

    try:
        polished_text = _call_glm(prompt, temperature=0.3)
        if not polished_text:
            return news_list

        polished_lines = polished_text.strip().split('\n')

        # 先写入第一遍结果
        for i, news in enumerate(news_list):
            if i < len(polished_lines):
                line = polished_lines[i].strip()
                if '.' in line:
                    line = line.split('.', 1)[1].strip()
                news['title'] = clean_jargon(line)

        # 二次压缩：把第一遍仍超 TARGET 的标题找出来，统一丢回 AI 压到 RETRY 字内
        overlong = [(i, news_list[i]['title'])
                    for i in range(len(news_list))
                    if len(news_list[i]['title']) > TARGET]
        if overlong:
            retry_str = "\n".join([f"{i+1}. {t}" for i, t in overlong])
            retry_prompt = f"""下面这些标题还是太长，请每条压到【最多 {RETRY} 个字】，保留最关键的信息，大白话：
{retry_str}
直接输出压短后的标题，每行一条，不要任何其他说明："""
            retry_text = _call_glm(retry_prompt, temperature=0.1)
            if retry_text:
                retry_lines = retry_text.strip().split('\n')
                for j, (orig_idx, _) in enumerate(overlong):
                    if j < len(retry_lines):
                        line = retry_lines[j].strip()
                        if '.' in line:
                            line = line.split('.', 1)[1].strip()
                        news_list[orig_idx]['title'] = clean_jargon(line)

        # 最终兜底：极少数仍超 MAX_LEN 才截断（正常情况下不会触发）
        for news in news_list:
            if len(news['title']) > MAX_LEN:
                news['title'] = news['title'][:MAX_LEN - 1] + '…'

        print(f"成功润色 {len(news_list)} 条新闻标题"
              f"（其中 {len(overlong)} 条触发二次压缩）")
    except Exception as e:
        print(f"润色失败: {e}")

    return news_list

def filter_ai_news_by_ai(news_list):
    """用 GLM 对标题做 AI 相关性语义过滤，剔除与 AI 无关的新闻（兜底保险）"""
    if not ZHIQI_API_KEY:
        print("未配置智谱API密钥，跳过AI语义过滤")
        return news_list

    if len(news_list) > 40:
        news_list = news_list[:40]

    titles_str = "\n".join(f"{i+1}. {n['title']}" for i, n in enumerate(news_list))

    prompt = (
        "以下是一批新闻标题，请判断每一条是否与人工智能(AI)真正相关"
        "（如大模型、机器学习、AI应用、AI芯片、机器人、AI公司或产品动态等）。\n"
        "凡与AI无关的内容（例如普通手机数码、汽车、明星娱乐、企业融资、"
        "非AI的营销活动等）必须排除。\n\n"
        f"{titles_str}\n\n"
        "请只输出你认为与AI相关的标题序号，用英文逗号分隔（如：1,3,5）。"
        "若没有相关项就输出0。不要输出任何其它内容。"
    )

    try:
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {ZHIQI_API_KEY}'}
        payload = {
            'model': 'glm-4-flash',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.2
        }
        resp = requests.post(ZHIQI_API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
        keep = {int(x) for x in re.findall(r'\d+', content)}
        keep.discard(0)
        result = [n for i, n in enumerate(news_list, 1) if i in keep]
        print(f"AI语义过滤: {len(news_list)} -> {len(result)} 条")
        return result
    except Exception as e:
        print(f"AI语义过滤失败，保留关键词白名单结果: {e}")

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
            if contains_ai_keyword(entry.title):
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
            if contains_ai_keyword(entry.title):
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
            if contains_ai_keyword(entry.title):
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
            if contains_ai_keyword(entry.title):
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


def html_escape(text):
    """转义 HTML 特殊字符，避免标题里的 & < > 破坏邮件结构"""
    if not isinstance(text, str):
        text = str(text)
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))


# 黑话词强制替换表：模型可能漏掉的，由代码兜底清理
_JARGON_REPL = [
    ('灰测版', '测试版'),
    ('灰测', '测试'),
    ('内测版', '测试版'),
    ('内测', '测试'),
    ('算力底座', '国产算力'),
    ('底座', ''),
    ('战略合作', ''),
    ('重磅', ''),
    ('赋能', ''),
    ('范式', ''),
    ('深度融合', ''),
    ('首发', ''),
    ('持续进化', '进化'),
    ('进化', '变强'),
    ('达成', ''),
    ('正式', ''),
    ('深度', ''),
    ('首批', ''),
    ('高端', ''),
    ('最强', ''),
    ('新梯队', '新秀'),
    ('梯队', ''),
]


def clean_jargon(text):
    """代码兜底：把 AI 润色后仍残留的黑话词强制替换/删除，保证标题真正大白话。"""
    for bad, good in _JARGON_REPL:
        text = text.replace(bad, good)
    # 清理替换后可能残留的标点 / 空格
    text = re.sub(r'[，,]\s*[，,]', '，', text)
    text = re.sub(r'^[，,。\s]+', '', text)
    text = re.sub(r'[，,。\s]+$', '', text)
    text = re.sub(r'\s+', '', text)
    return text


def classify_category(title):
    """根据标题关键词粗略分类，用于邮件「分类」列展示（真实新闻无分类字段）。"""
    t = (title or '').lower()
    rules = [
        ('融资', ['融资', '投资', '估值', 'ipo', '收购', '并购', '亿美元', '亿']),
        ('芯片/算力', ['芯片', 'gpu', '算力', '英伟达', '华为', '昇腾', '处理器', '半导体']),
        ('研究/论文', ['论文', '研究', '突破', 'arxiv', 'neurips', 'icml', '成果']),
        ('大模型', ['gpt', 'claude', 'gemini', 'llm', '大模型', '模型', 'deepseek',
                   '智谱', '豆包', '文心', '通义', '千问', 'kimi', 'mistral', 'llama']),
    ]
    for cat, kws in rules:
        if any(k in t for k in kws):
            return cat
    return '应用'


def generate_email_content(news_list):
    """生成【表格版·商务简报】HTML 邮件。
    布局全部使用 <table> + bgcolor 属性，颜色只用 bgcolor + style 里的
    color/font-size/text-decoration，确保 QQ 邮箱能完整渲染。"""
    today = datetime.now().strftime('%Y年%m月%d日')
    count = len(news_list)
    FONT = "'PingFang SC','Microsoft YaHei',Arial,sans-serif"

    rows = []
    for idx, news in enumerate(news_list, 1):
        title = html_escape(news.get('title', ''))
        link = html_escape(news.get('link', '#'))
        source = html_escape(news.get('source', ''))
        cat = classify_category(news.get('title', ''))
        rows.append(
            '<tr bgcolor="#ffffff" style="background:#ffffff;">'
            '<td width="40" align="center" valign="middle" style="padding:14px 12px;border-bottom:1px solid #eef1f5;font-family:' + FONT + ';">'
            '<span style="color:#0b2545;font-weight:700;font-size:14px;font-family:' + FONT + ';">' + str(idx) + '</span></td>'
            '<td valign="middle" style="padding:14px 12px;border-bottom:1px solid #eef1f5;font-family:' + FONT + ';">'
            '<span style="color:#1a2436;font-size:14px;line-height:1.5;font-weight:500;font-family:' + FONT + ';">' + title + '</span></td>'
            '<td align="center" valign="middle" style="padding:14px 12px;border-bottom:1px solid #eef1f5;font-family:' + FONT + ';">'
            '<a href="' + link + '" style="color:#0b2545;font-size:12px;text-decoration:none !important;font-weight:700;font-family:' + FONT + ';">详情 →</a></td>'
            '<td align="center" valign="middle" style="padding:14px 12px;border-bottom:1px solid #eef1f5;font-family:' + FONT + ';">'
            '<span style="font-size:12px;color:#7a8aa0;font-family:' + FONT + ';">' + cat + '</span></td>'
            '</tr>'
        )
    rows_html = ''.join(rows)

    html = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"></head>'
        '<body style="margin:0;padding:0;background:#eef1f5;">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" width="620" style="margin:0 auto;">'
        '<tr><td height="30" style="font-size:1px;line-height:1px;">&nbsp;</td></tr>'
        '<tr>'
        '<td bgcolor="#0b2545" width="620" style="padding:26px 30px;background-color:#0b2545;font-family:' + FONT + ';">'
        '<div style="font-size:20px;color:#ffffff;letter-spacing:1px;font-family:' + FONT + ';">AI 行业日报 · DAILY BRIEF</div>'
        '<div style="font-size:12px;color:#9db4d4;padding-top:5px;letter-spacing:1px;font-family:' + FONT + ';">' + today + ' · ' + str(count) + ' 条要闻</div>'
        '</td></tr>'
        '<tr>'
        '<td bgcolor="#ffffff" style="background:#ffffff;font-family:' + FONT + ';">'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">' + rows_html + '</table>'
        '</td></tr>'
        '<tr><td bgcolor="#f6f8fb" align="center" style="background-color:#f6f8fb;padding:16px 30px;color:#9aa6b8;font-size:12px;font-family:' + FONT + ';">由智能体自动生成 · 感谢阅读</td></tr>'
        '<tr><td height="30" style="font-size:1px;line-height:1px;">&nbsp;</td></tr>'
        '</table></body></html>'
    )
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

    news_list = filter_ai_news_by_ai(news_list)

    news_list = polish_news_titles(news_list)
    
    html = generate_email_content(news_list)
    
    send_email(html)
    print("任务完成!")

if __name__ == '__main__':
    main()
