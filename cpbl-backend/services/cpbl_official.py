import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup


NEWS_SOURCE_URL = "https://www.cpbl.com.tw/xmdoc"
TOP_STATS_SOURCE_URL = "https://www.cpbl.com.tw/stats/toplist"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

NEWS_FALLBACK = [
    {
        "title": "歡迎使用 GoBase 中職數據平台",
        "date": str(datetime.now().year),
        "category": "系統公告",
        "tag": "系統",
        "type": "系統",
        "summary": "本平台提供賽程查詢、球隊戰績、數據統計、球員抽卡與打線收藏功能。",
        "url": NEWS_SOURCE_URL,
    },
    {
        "title": "新聞來源暫時無法連線",
        "date": "-",
        "category": "資料狀態",
        "tag": "備援",
        "type": "系統",
        "summary": "請稍後重新整理，或確認網路與 CPBL 官網是否正常回應。",
        "url": NEWS_SOURCE_URL,
    },
]


def extract_background_image(style_text):
    if not style_text:
        return ""
    match = re.search(r"url\(['\"]?([^'\")]+)", style_text)
    if not match:
        return ""
    return match.group(1)


def absolute_cpbl_url(path):
    if not path:
        return ""
    if path.startswith("http"):
        return path
    return f"https://www.cpbl.com.tw{path}"


def fetch_cpbl_news(limit=12):
    res = requests.get(NEWS_SOURCE_URL, headers=DEFAULT_HEADERS, timeout=12)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    news_items = []

    for item in soup.select(".NewsList .item"):
        title_node = item.select_one(".title a")
        if not title_node:
            continue

        title = title_node.get("title") or title_node.get_text(strip=True)
        date = item.select_one(".date")
        tags = [tag.get_text(strip=True) for tag in item.select(".tags a") if tag.get_text(strip=True)]
        image_node = item.select_one(".img a")
        image_url = absolute_cpbl_url(extract_background_image(image_node.get("style", "")) if image_node else "")

        news_items.append({
            "title": title.strip(),
            "date": date.get_text(strip=True) if date else "",
            "category": "賽事新聞",
            "tag": " / ".join(tags) if tags else "CPBL",
            "type": "賽事新聞",
            "summary": "、".join(tags) if tags else "中華職棒官方最新賽事新聞",
            "url": absolute_cpbl_url(title_node.get("href", "")),
            "image": image_url,
            "source": "CPBL",
        })

        if len(news_items) >= limit:
            break

    return news_items


def fetch_cpbl_top_stats(limit=10):
    res = requests.get(TOP_STATS_SOURCE_URL, headers=DEFAULT_HEADERS, timeout=12)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    cards = []

    for item in soup.select(".TopFiveList .item"):
        title_node = item.select_one(".title")
        if not title_node:
            continue

        title = "".join(title_node.find_all(string=True, recursive=False)).strip()
        abbr_node = title_node.select_one(".en")
        abbr = abbr_node.get_text(strip=True) if abbr_node else ""
        photo_node = item.select_one(".photo_player_1st a")
        photo_url = absolute_cpbl_url(extract_background_image(photo_node.get("style", "")) if photo_node else "")
        more_node = item.select_one(".btn_more a")

        leaders = []
        for row in item.select("li"):
            rank = row.select_one(".rank")
            name = row.select_one(".player .name")
            team = row.select_one(".player .team")
            value = row.select_one(".num")

            if not name or not value:
                continue

            leaders.append({
                "rank": rank.get_text(strip=True) if rank else str(len(leaders) + 1),
                "name": name.get_text(strip=True),
                "team": team.get_text(strip=True).strip("()") if team else "",
                "value": value.get_text(strip=True),
                "url": absolute_cpbl_url(name.get("href", "")),
            })

        if leaders:
            cards.append({
                "title": title,
                "abbr": abbr,
                "photo": photo_url,
                "leaders": leaders,
                "more_url": absolute_cpbl_url(more_node.get("href", "")) if more_node else TOP_STATS_SOURCE_URL,
                "source": "CPBL",
            })

        if len(cards) >= limit:
            break

    return cards
