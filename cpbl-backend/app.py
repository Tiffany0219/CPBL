import os
import re, time, json, traceback
import random
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import or_, text
from extensions import db
from models import Game, User, UserCard, UserLineup, UserTicket
from services.cpbl_official import (
    NEWS_FALLBACK,
    TOP_STATS_SOURCE_URL,
    fetch_cpbl_news,
    fetch_cpbl_top_stats,
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = Path(os.environ.get("CPBL_DATA_DIR", BASE_DIR)).resolve()
SEASON_YEAR = int(os.environ.get("CPBL_SEASON_YEAR", datetime.now().year))
STANDINGS_PATH = DATA_DIR / "standings.json"
PLAYERS_POOL_PATH = DATA_DIR / "players_pool.json"
SYNC_STATUS_PATH = DATA_DIR / "sync_status.json"
SEED_GAMES_PATH = BASE_DIR / "seed_games.json"
DEFAULT_DATABASE_PATH = BASE_DIR / "instance" / "cpbl_data.db"
DEFAULT_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
AI_RATE_LIMIT_WINDOW_SECONDS = 10 * 60
AI_RATE_LIMIT_REQUESTS = 8
AI_REQUEST_LOG = {}
TAIPEI_TIMEZONE = ZoneInfo("Asia/Taipei")
WEATHER_CACHE = {}
WEATHER_CACHE_SECONDS = 10 * 60

VENUE_WEATHER_LOCATIONS = {
    "大巨蛋": {"city": "台北市", "latitude": 25.0419, "longitude": 121.5611},
    "天母": {"city": "台北市", "latitude": 25.1137, "longitude": 121.5306},
    "新莊": {"city": "新北市", "latitude": 25.0417, "longitude": 121.4467},
    "桃園": {"city": "桃園市", "latitude": 25.0015, "longitude": 121.1985},
    "洲際": {"city": "台中市", "latitude": 24.1997, "longitude": 120.6843},
    "台中": {"city": "台中市", "latitude": 24.1997, "longitude": 120.6843},
    "台南": {"city": "台南市", "latitude": 22.9801, "longitude": 120.2088},
    "澄清湖": {"city": "高雄市", "latitude": 22.6568, "longitude": 120.3529},
    "嘉義": {"city": "嘉義市", "latitude": 23.4816, "longitude": 120.4491},
    "亞太": {"city": "台南市", "latitude": 23.0575, "longitude": 120.2447},
    "花蓮": {"city": "花蓮縣", "latitude": 23.9936, "longitude": 121.6021},
    "台東": {"city": "台東縣", "latitude": 22.7553, "longitude": 121.1467},
}

WEATHER_CODE_TEXT = {
    0: "晴",
    1: "晴時多雲",
    2: "多雲",
    3: "陰",
    45: "霧",
    48: "霧",
    51: "毛毛雨",
    53: "毛毛雨",
    55: "毛毛雨",
    61: "小雨",
    63: "雨",
    65: "大雨",
    66: "凍雨",
    67: "凍雨",
    71: "降雪",
    73: "降雪",
    75: "大雪",
    80: "陣雨",
    81: "陣雨",
    82: "強陣雨",
    95: "雷雨",
    96: "雷雨",
    99: "雷雨",
}

app = Flask(__name__)
CORS(app)

database_url = os.environ.get("DATABASE_URL") or f"sqlite:///{DEFAULT_DATABASE_PATH}"
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

GAME_EXTRA_COLUMNS = {
    "winning_pitcher": "VARCHAR(50) DEFAULT ''",
    "losing_pitcher": "VARCHAR(50) DEFAULT ''",
    "save_pitcher": "VARCHAR(50) DEFAULT ''",
    "mvp": "VARCHAR(50) DEFAULT ''",
    "mvp_team": "VARCHAR(100) DEFAULT ''",
    "mvp_note": "VARCHAR(120) DEFAULT ''",
}

USER_EXTRA_COLUMNS = {
    "favorite_team": "VARCHAR(100) DEFAULT ''",
    "last_daily_reward_date": "VARCHAR(10) DEFAULT ''",
    "daily_streak": "INTEGER DEFAULT 0",
    "card_points": "INTEGER DEFAULT 0",
}

USER_CARD_EXTRA_COLUMNS = {
    "rarity": "VARCHAR(20) DEFAULT 'common'",
}

TEAMS = ['中信兄弟', '味全龍', '樂天桃猿', '統一7-ELEVEn獅', '富邦悍將', '台鋼雄鷹']
RARITIES = {"common", "rare", "holo", "legend"}
PACK_COSTS = {"standard": 18, "premium": 60}
BROTHERS_RARE_NAMES = {
    "江坤宇",
    "王威晨",
    "許基宏",
    "陳俊秀",
    "岳政華",
    "詹子賢",
    "曾頌恩",
    "高宇杰",
    "勝騎士",
}
RAKUTEN_RARE_NAMES = {
    "林立",
    "林子偉",
    "梁家榮",
    "林承飛",
    "林泓育",
    "陳晨威",
    "成晉",
    "何品室融",
    "陳冠宇",
    "威能帝",
}
LIONS_RARE_NAMES = {
    "陳傑憲",
    "蘇智傑",
    "邱智呈",
    "林子豪",
    "潘傑楷",
    "陳重羽",
    "布雷克",
}
DRAGONS_RARE_NAMES = {
    "郭天信",
    "李凱威",
    "張政禹",
    "劉基鴻",
    "陳子豪",
    "林孝程",
    "林辰勳",
    "鋼龍",
    "魔神龍",
}
GUARDIANS_RARE_NAMES = {
    "申皓瑋",
    "林哲瑄",
    "王正棠",
    "范國宸",
    "李宗賢",
    "王念好",
    "戴培峰",
    "張進德",
    "江國豪",
    "張奕",
}
HAWKS_RARE_NAMES = {
    "王柏融",
    "藍寅倫",
    "紀慶然",
    "葉保弟",
    "郭阜林",
    "吳念庭",
    "曾子祐",
    "江承諺",
    "黃子鵬",
}
TEAM_RARE_NAMES = {
    "中信兄弟": BROTHERS_RARE_NAMES,
    "樂天桃猿": RAKUTEN_RARE_NAMES,
    "統一7-ELEVEn獅": LIONS_RARE_NAMES,
    "統一7-11獅": LIONS_RARE_NAMES,
    "統一獅": LIONS_RARE_NAMES,
    "味全龍": DRAGONS_RARE_NAMES,
    "富邦悍將": GUARDIANS_RARE_NAMES,
    "台鋼雄鷹": HAWKS_RARE_NAMES,
}

def ensure_game_schema():
    existing = {
        row[1]
        for row in db.session.execute(text("PRAGMA table_info(game)")).fetchall()
    }
    for column, column_type in GAME_EXTRA_COLUMNS.items():
        if column not in existing:
            db.session.execute(text(f"ALTER TABLE game ADD COLUMN {column} {column_type}"))
    db.session.commit()

def ensure_columns(table, columns):
    existing = {
        row[1]
        for row in db.session.execute(text(f"PRAGMA table_info({table})")).fetchall()
    }
    for column, column_type in columns.items():
        if column not in existing:
            db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"))
    db.session.commit()

def seed_games_if_empty():
    if Game.query.count() > 0 or not SEED_GAMES_PATH.exists():
        return

    with open(SEED_GAMES_PATH, "r", encoding="utf-8") as f:
        games = json.load(f)

    if not isinstance(games, list):
        return

    allowed_columns = {
        "game_date", "game_sno", "game_time", "away_team", "away_score", "away_pitcher",
        "home_team", "home_score", "home_pitcher", "winning_pitcher", "losing_pitcher",
        "save_pitcher", "mvp", "mvp_team", "mvp_note", "location", "game_status",
        "away_line", "home_line", "away_rhe", "home_rhe"
    }

    for item in games:
        if isinstance(item, dict):
            db.session.add(Game(**{key: item.get(key, "") for key in allowed_columns}))

    db.session.commit()

with app.app_context():
    db.create_all()
    ensure_game_schema()
    ensure_columns("user", USER_EXTRA_COLUMNS)
    ensure_columns("user_card", USER_CARD_EXTRA_COLUMNS)
    seed_games_if_empty()

def make_driver():
    def cached_chrome_pair():
        cache_root = Path.home() / ".cache" / "selenium"
        chrome_root = cache_root / "chrome" / "mac-arm64"
        driver_root = cache_root / "chromedriver" / "mac-arm64"
        chrome_by_version = {
            path.parent.parent.parent.parent.name: path
            for path in chrome_root.glob(
                "*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
            )
            if path.is_file()
        }
        driver_by_version = {
            path.parent.name: path
            for path in driver_root.glob("*/chromedriver")
            if path.is_file()
        }
        matching_versions = set(chrome_by_version) & set(driver_by_version)
        if not matching_versions:
            return None, None

        latest = max(
            matching_versions,
            key=lambda value: tuple(int(part) for part in value.split(".")),
        )
        return chrome_by_version[latest], driver_by_version[latest]

    opts = Options()
    chrome_bin = os.environ.get("CHROME_BIN", "").strip()
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "").strip()
    if not chrome_bin or not chromedriver_path:
        cached_chrome, cached_driver = cached_chrome_pair()
        chrome_bin = chrome_bin or (str(cached_chrome) if cached_chrome else "")
        chromedriver_path = chromedriver_path or (str(cached_driver) if cached_driver else "")

    if chrome_bin:
        opts.binary_location = chrome_bin

    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-extensions')
    opts.add_argument('--no-proxy-server')
    opts.add_argument('--remote-debugging-port=9222')
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    service = Service(chromedriver_path) if chromedriver_path else None
    return webdriver.Chrome(service=service, options=opts)

def fetch_page_soup(url, click_list_tab=False, force_selenium=False):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    # 1. 嘗試以 requests 抓取。動態頁可指定 force_selenium，避免空 HTML 被當成成功。
    if not force_selenium:
        try:
            print(f"嘗試使用 requests 快速抓取網頁: {url}")
            session = requests.Session()
            session.trust_env = False
            res = session.get(url, headers=headers, timeout=12)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, 'html.parser')
            
            if click_list_tab:
                # 檢查是否含有 schedule 清單元素，如果有就直接使用，免開 Selenium
                rows = soup.select('.ScheduleTableList table tbody tr, .game_item')
                if len(rows) > 2:
                    print("預設網頁已含有賽程列表結構，免用 Selenium。")
                    return soup, None
                else:
                    print("預設網頁賽程列數不足，改用 Selenium 切換模式...")
            else:
                return soup, None
        except Exception as req_err:
            print(f"⚠️ requests 抓取失敗: {req_err}，嘗試使用 Selenium 備援...")
    else:
        print(f"使用 Selenium 抓取動態網頁: {url}")

    # 2. 嘗試以 Selenium 抓取
    driver = None
    try:
        driver = make_driver()
        driver.get(url)
        if click_list_tab:
            try:
                from selenium.webdriver.common.by import By
                driver.find_element(By.CSS_SELECTOR, "li[data-id='list']").click()
                time.sleep(3)
            except:
                time.sleep(5)
        else:
            time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        return soup, driver
    except Exception as sel_err:
        print(f"❌ Selenium 備援也失敗: {sel_err}")
        if driver:
            try: driver.quit()
            except: pass
        raise sel_err

def cpbl_box_url(game_sno, year=None):
    target_year = year or SEASON_YEAR
    return f"https://www.cpbl.com.tw/box/index?gameSno={game_sno}&year={target_year}&kindCode=A"

def read_json_file(path, fallback):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return fallback

def write_json_file(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def record_sync_status(key, label, result=None, status="success"):
    data = read_json_file(SYNC_STATUS_PATH, {})
    data[key] = {
        "key": key,
        "label": label,
        "status": status,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": result or {},
    }
    write_json_file(SYNC_STATUS_PATH, data)
    return data[key]

def parse_date(txt):
    m = re.search(r'(\d{1,2})/(\d{1,2})', txt)
    if m:
        parts = txt.split('/')
        # 如果是 YYYY/MM/DD
        if len(parts) >= 3: return f"{parts[1].zfill(2)}/{parts[2][:2].zfill(2)}"
        # 如果是 04/16
        return f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}"
    return ""

def clean_player_name(value):
    if value is None:
        return ""
    value = str(value).replace("\u3000", " ").strip()
    value = re.sub(r'\s+', '', value)
    return "" if value in {"", "-", "--", "None", "null"} else value

def intish(value, default=0):
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default

def format_pitching_innings(outs, third_outs):
    outs = intish(outs)
    third_outs = intish(third_outs)
    if third_outs:
        return f"{outs} {third_outs}/3"
    return str(outs)

def parse_json_payload(value, fallback):
    if not value:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback

def fetch_cpbl_game_payload(game_sno, year=None, kind_code="A"):
    target_year = year or SEASON_YEAR
    url = cpbl_box_url(game_sno, target_year)
    session = requests.Session()
    session.trust_env = False
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": url,
        "X-Requested-With": "XMLHttpRequest",
    }
    page = session.get(url, headers=headers, timeout=20)
    page.raise_for_status()

    soup = BeautifulSoup(page.text, 'html.parser')
    token_node = soup.find('input', {'name': '__RequestVerificationToken'})
    token = token_node.get('value') if token_node else ""
    post_data = {
        "__RequestVerificationToken": token,
        "GameSno": str(game_sno),
        "KindCode": kind_code,
        "Year": str(target_year),
        "PrevOrNext": "",
        "PresentStatus": "",
    }
    res = session.post(
        "https://www.cpbl.com.tw/box/getlive",
        headers=headers,
        data=post_data,
        timeout=25,
    )
    res.raise_for_status()
    payload = res.json()
    if not payload.get("Success"):
        raise ValueError("CPBL 官方 getlive 回傳失敗")

    return {
        "game_details": parse_json_payload(payload.get("GameDetailJson"), []),
        "curt_game_detail": parse_json_payload(payload.get("CurtGameDetailJson"), {}),
        "scoreboards": parse_json_payload(payload.get("ScoreboardJson"), []),
        "live_logs": parse_json_payload(payload.get("LiveLogJson"), []),
        "battings": parse_json_payload(payload.get("BattingJson"), []),
        "pitchings": parse_json_payload(payload.get("PitchingJson"), []),
        "raw": payload,
        "source": url,
    }

def find_pitcher_by_role(pitchings, visiting_home_type, role="先發"):
    side = str(visiting_home_type)
    candidates = [p for p in pitchings if str(p.get("VisitingHomeType")) == side]
    for pitcher in candidates:
        if pitcher.get("RoleType") == role:
            return clean_player_name(pitcher.get("PitcherName"))
    return clean_player_name(candidates[0].get("PitcherName")) if candidates else ""

def mvp_note_from_detail(detail):
    if clean_player_name(detail.get("PitcherName")):
        innings = format_pitching_innings(
            detail.get("InningPitchedCnt"),
            detail.get("InningPitchedDiv3Cnt"),
        )
        strikeouts = intish(detail.get("StrikeOutCnt"))
        runs = intish(detail.get("RunCnt"))
        return f"投球 {innings} 局 / {strikeouts}K / {runs} 失分"

    hits = intish(detail.get("HittingCnt"))
    rbi = intish(detail.get("RunBattedInCnt"))
    runs = intish(detail.get("ScoreCnt"))
    homers = intish(detail.get("HomeRunCnt"))
    parts = []
    if hits:
        parts.append(f"{hits} 安")
    if rbi:
        parts.append(f"{rbi} 打點")
    if runs:
        parts.append(f"{runs} 得分")
    if homers:
        parts.append(f"{homers} 轟")
    return " / ".join(parts) or "官方 MVP"

def build_line_data_from_scoreboards(scoreboards):
    line_data = {"away": [], "home": [], "away_rhe": [], "home_rhe": []}
    for side, key in (("1", "away"), ("2", "home")):
        rows = [row for row in scoreboards if str(row.get("VisitingHomeType")) == side]
        rows.sort(key=lambda row: intish(row.get("InningSeq")))
        if not rows:
            continue
        scores = [str(intish(row.get("ScoreCnt"))) for row in rows]
        hits = sum(intish(row.get("HittingCnt")) for row in rows)
        errors = sum(intish(row.get("ErrorCnt")) for row in rows)
        runs = sum(intish(row.get("ScoreCnt")) for row in rows)
        line_data[key] = scores
        line_data[f"{key}_rhe"] = [str(runs), str(hits), str(errors)]
    return line_data

def players_from_battings(battings, visiting_home_type):
    rows = [b for b in battings if str(b.get("VisitingHomeType")) == str(visiting_home_type)]
    return [{
        "name": clean_player_name(b.get("HitterName")),
        "ab": str(intish(b.get("HitCnt"))),
        "h": str(intish(b.get("HittingCnt"))),
        "rbi": str(intish(b.get("RunBattedINCnt") or b.get("RunBattedInCnt"))),
    } for b in rows if clean_player_name(b.get("HitterName"))]

SIMPLE_PITCH_TEXT = {
    "好球沒揮棒。",
    "壞球。",
    "揮棒落空。",
    "擊出界外球。",
}

PLAY_BY_PLAY_KEYWORDS = [
    "安打", "全壘打", "二壘打", "三壘打", "保送", "觸身", "三振",
    "出局", "上壘", "得分", "打點", "跑者", "盜壘", "牽制",
    "暴投", "捕逸", "失誤", "殘壘", "換", "犧牲", "高飛球", "滾地球",
]

def clean_live_text(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()

def inning_label(row):
    half = "上" if str(row.get("VisitingHomeType")) == "1" else "下"
    return f"{intish(row.get('InningSeq'))}局{half}"

def build_runner_maps(live_logs):
    maps = {"1": {}, "2": {}}
    for row in live_logs:
        side = str(row.get("VisitingHomeType") or "")
        order = str(row.get("BattingOrder") or row.get("HitterLineup") or "")
        name = clean_player_name(row.get("HitterName"))
        if side in maps and order and name:
            maps[side][order] = name
    return maps

def resolve_base_runner(value, side, runner_maps):
    value = str(value or "").strip()
    if not value:
        return ""
    return runner_maps.get(side, {}).get(value, value)

def base_state_from_row(row, runner_maps):
    side = str(row.get("VisitingHomeType") or "")
    return {
        "first": resolve_base_runner(row.get("FirstBase"), side, runner_maps),
        "second": resolve_base_runner(row.get("SecondBase"), side, runner_maps),
        "third": resolve_base_runner(row.get("ThirdBase"), side, runner_maps),
    }

def same_half_inning(a, b):
    return (
        b
        and intish(a.get("InningSeq")) == intish(b.get("InningSeq"))
        and str(a.get("VisitingHomeType")) == str(b.get("VisitingHomeType"))
    )

def should_keep_play_log(row):
    content = clean_live_text(row.get("Content"))
    if not content:
        return False
    if str(row.get("IsChangePlayer")) == "1":
        return True
    if content not in SIMPLE_PITCH_TEXT:
        return True
    return any(keyword in content for keyword in PLAY_BY_PLAY_KEYWORDS)

def build_play_by_play(payload, game=None):
    live_logs = payload.get("live_logs") or []
    runner_maps = build_runner_maps(live_logs)
    events = []

    for index, row in enumerate(live_logs):
        if not should_keep_play_log(row):
            continue

        next_row = live_logs[index + 1] if index + 1 < len(live_logs) else None
        batting_side = str(row.get("VisitingHomeType") or "")
        batting_team = game.away_team if batting_side == "1" and game else game.home_team if game else ""
        if not batting_team:
            batting_team = "客隊" if batting_side == "1" else "主隊"

        bases_after = base_state_from_row(next_row, runner_maps) if same_half_inning(row, next_row) else {
            "first": "",
            "second": "",
            "third": "",
        }
        score = {
            "away": intish(row.get("VisitingScore")),
            "home": intish(row.get("HomeScore")),
        }

        events.append({
            "id": row.get("Pkno") or row.get("MainEventNo") or f"play-{index}",
            "inning": inning_label(row),
            "inning_seq": intish(row.get("InningSeq")),
            "half": "top" if batting_side == "1" else "bottom",
            "team": batting_team,
            "hitter": clean_player_name(row.get("HitterName")),
            "pitcher": clean_player_name(row.get("PitcherName")),
            "result": clean_live_text(row.get("BattingActionName") or row.get("ActionName")),
            "content": clean_live_text(row.get("Content")),
            "count": f"{intish(row.get('BallCnt'))}-{intish(row.get('StrikeCnt'))}",
            "outs": intish(row.get("OutCnt")),
            "pitch_count": intish(row.get("PitchCnt")),
            "score": score,
            "score_text": f"{score['away']}:{score['home']}",
            "bases_before": base_state_from_row(row, runner_maps),
            "bases_after": bases_after,
            "is_scoring": str(row.get("IsScoreCnt")) != "0" or "得分" in clean_live_text(row.get("Content")),
        })

    return events

def extract_official_game_extras(payload, game=None):
    detail = payload.get("curt_game_detail") or {}
    pitchings = payload.get("pitchings") or []
    mvp_side = str(detail.get("MvpVisitingHomeType") or "")
    away_team = game.away_team if game else clean_player_name(detail.get("VisitingTeamName"))
    home_team = game.home_team if game else clean_player_name(detail.get("HomeTeamName"))

    mvp_name = clean_player_name(detail.get("HitterName")) or clean_player_name(detail.get("PitcherName"))
    mvp_team = ""
    if mvp_side == "1":
        mvp_team = away_team
    elif mvp_side == "2":
        mvp_team = home_team

    return {
        "away_pitcher": clean_player_name(detail.get("VisitingFirstMover")) or find_pitcher_by_role(pitchings, "1"),
        "home_pitcher": clean_player_name(detail.get("HomeFirstMover")) or find_pitcher_by_role(pitchings, "2"),
        "winning_pitcher": clean_player_name(detail.get("WinningPitcherName")),
        "losing_pitcher": clean_player_name(detail.get("LosePitcherName")),
        "save_pitcher": clean_player_name(detail.get("CloserPitcherName")),
        "mvp": mvp_name,
        "mvp_team": mvp_team,
        "mvp_note": mvp_note_from_detail(detail) if mvp_name else "",
        "away_score": str(intish(detail.get("VisitingTotalScore"), "")) if detail.get("VisitingTotalScore") is not None else "",
        "home_score": str(intish(detail.get("HomeTotalScore"), "")) if detail.get("HomeTotalScore") is not None else "",
        "status": "FINISH" if intish(detail.get("GameStatus")) == 3 else "",
    }

def apply_game_extras(game, extras):
    for field in [
        "away_pitcher", "home_pitcher", "winning_pitcher", "losing_pitcher",
        "save_pitcher", "mvp", "mvp_team", "mvp_note"
    ]:
        value = extras.get(field)
        if value:
            setattr(game, field, value)
    if extras.get("away_score") != "":
        game.away_score = extras["away_score"]
    if extras.get("home_score") != "":
        game.home_score = extras["home_score"]
    if extras.get("status"):
        game.game_status = extras["status"]
        game.game_time = "Final"

def user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "favorite_team": user.favorite_team or "",
        "last_daily_reward_date": user.last_daily_reward_date or "",
        "daily_streak": intish(user.daily_streak),
        "card_points": intish(user.card_points),
    }

def card_to_dict(card):
    return {
        "name": card.name,
        "team": card.team,
        "position": card.position,
        "description": card.description,
        "rarity": card.rarity or "common",
        "count": card.count,
    }

def datetime_to_utc_iso(value):
    if not value:
        return ""
    if value.tzinfo is None:
        return f"{value.isoformat()}Z"
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def ticket_to_dict(ticket):
    return {
        "id": ticket.id,
        "gameId": ticket.game_id,
        "date": ticket.game_date,
        "location": ticket.location,
        "away": ticket.away_team,
        "home": ticket.home_team,
        "away_score": ticket.away_score,
        "home_score": ticket.home_score,
        "status": ticket.game_status,
        "note": ticket.note,
        "image": ticket.image,
        "createdAt": datetime_to_utc_iso(ticket.created_at),
    }

def lineup_to_dict(lineup):
    return {
        "slots": parse_json_payload(lineup.slots if lineup else "[]", []),
        "updatedAt": datetime_to_utc_iso(lineup.updated_at) if lineup else "",
    }

def get_auth_user():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "", 1).strip() if auth.startswith("Bearer ") else ""
    if not token:
        return None
    return User.query.filter_by(api_token=token).first()

def require_auth_user():
    user = get_auth_user()
    if not user:
        return None, (jsonify({"error": "請先登入"}), 401)
    return user, None

def ai_request_allowed():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    client_key = forwarded_for.split(",", 1)[0].strip() or request.remote_addr or "unknown"
    now = time.time()
    cutoff = now - AI_RATE_LIMIT_WINDOW_SECONDS
    recent_requests = [
        timestamp
        for timestamp in AI_REQUEST_LOG.get(client_key, [])
        if timestamp >= cutoff
    ]
    if len(recent_requests) >= AI_RATE_LIMIT_REQUESTS:
        AI_REQUEST_LOG[client_key] = recent_requests
        return False
    recent_requests.append(now)
    AI_REQUEST_LOG[client_key] = recent_requests
    return True

def match_weather_location(venue):
    venue_text = str(venue or "").strip()
    if not venue_text:
        return None
    for keyword, info in VENUE_WEATHER_LOCATIONS.items():
        if keyword in venue_text:
            return {"venue": venue_text, "matched": keyword, **info}
    return None

def parse_cpbl_game_datetime(date_text, time_text=""):
    match = re.search(r"(\d{1,2})/(\d{1,2})", str(date_text or ""))
    if not match:
        return None

    now = datetime.now(TAIPEI_TIMEZONE)
    month = int(match.group(1))
    day = int(match.group(2))
    hour = 18
    minute = 35
    time_match = re.search(r"(\d{1,2}):(\d{2})", str(time_text or ""))
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
    try:
        return datetime(now.year, month, day, hour, minute, tzinfo=TAIPEI_TIMEZONE)
    except ValueError:
        return None

def weather_code_label(code):
    try:
        return WEATHER_CODE_TEXT.get(int(code), "天氣")
    except (TypeError, ValueError):
        return "天氣"

def is_rainy_weather_code(code):
    try:
        return int(code) in {51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
    except (TypeError, ValueError):
        return False

def fetch_open_meteo_weather(location):
    cache_key = f"{location['latitude']:.4f},{location['longitude']:.4f}"
    cached = WEATHER_CACHE.get(cache_key)
    now_ts = time.time()
    if cached and now_ts - cached["created_at"] < WEATHER_CACHE_SECONDS:
        return cached["data"]

    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": "temperature_2m,weather_code,precipitation,rain",
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "forecast_days": 7,
        "timezone": "Asia/Taipei",
    }
    session = requests.Session()
    session.trust_env = False
    response = session.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    WEATHER_CACHE[cache_key] = {"created_at": now_ts, "data": data}
    return data

def pick_weather_hour(weather_data, target_dt):
    hourly = weather_data.get("hourly") if isinstance(weather_data, dict) else {}
    times = hourly.get("time") if isinstance(hourly, dict) else []
    if not target_dt or not times:
        return None

    target = target_dt.replace(minute=0, second=0, microsecond=0)
    best_index = None
    best_delta = None
    for index, time_text in enumerate(times):
        try:
            current = datetime.fromisoformat(str(time_text)).replace(tzinfo=TAIPEI_TIMEZONE)
        except ValueError:
            continue
        delta = abs((current - target).total_seconds())
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_index = index

    if best_index is None or best_delta is None or best_delta > 4 * 3600:
        return None

    def hourly_value(key):
        values = hourly.get(key) or []
        return values[best_index] if best_index < len(values) else None

    return {
        "temperature": hourly_value("temperature_2m"),
        "precipitation_probability": hourly_value("precipitation_probability"),
        "weather_code": hourly_value("weather_code"),
    }

def weather_summary_for_game(venue, date_text="", time_text=""):
    location = match_weather_location(venue)
    if not location:
        return None

    target_dt = parse_cpbl_game_datetime(date_text, time_text)
    now = datetime.now(TAIPEI_TIMEZONE)
    if target_dt and target_dt.date() < now.date():
        return None
    if target_dt and target_dt.date() > (now + timedelta(days=6)).date():
        return None

    try:
        weather_data = fetch_open_meteo_weather(location)
        selected = pick_weather_hour(weather_data, target_dt) or {}
        current = weather_data.get("current") or {}
        temperature = selected.get("temperature", current.get("temperature_2m"))
        weather_code = selected.get("weather_code", current.get("weather_code"))
        precipitation_probability = selected.get("precipitation_probability")
        condition = weather_code_label(weather_code)
        rain_risk = intish(precipitation_probability) >= 60 or is_rainy_weather_code(weather_code)

        if temperature is None:
            temperature_label = ""
        else:
            temperature_label = f"{round(float(temperature))}°C"

        if precipitation_probability is None:
            display = f"{condition} {temperature_label}".strip()
        elif rain_risk:
            display = f"可能延賽｜降雨 {intish(precipitation_probability)}%"
        else:
            display = f"{condition} {temperature_label}".strip()

        return {
            "venue": location["venue"],
            "matched_venue": location["matched"],
            "city": location["city"],
            "condition": condition,
            "temperature": round(float(temperature), 1) if temperature is not None else None,
            "precipitation_probability": precipitation_probability,
            "rain_risk": rain_risk,
            "display": display or "天氣同步中",
            "source": "Open-Meteo",
        }
    except Exception as e:
        print(f"天氣抓取失敗：{venue} {e}")
        return {
            "venue": location["venue"],
            "matched_venue": location["matched"],
            "city": location["city"],
            "condition": "天氣同步中",
            "temperature": None,
            "precipitation_probability": None,
            "rain_risk": False,
            "display": "天氣同步中",
            "source": "Open-Meteo",
        }

def weather_context_from_question(question):
    text = str(question or "")
    if not text:
        return []

    now = datetime.now(TAIPEI_TIMEZONE)
    date_text = now.strftime("%m/%d")
    time_text = now.strftime("%H:00")
    if "明天" in text:
        tomorrow = now + timedelta(days=1)
        date_text = tomorrow.strftime("%m/%d")
        time_text = "18:35"

    summaries = []
    seen = set()
    for keyword in VENUE_WEATHER_LOCATIONS:
        if keyword in text and keyword not in seen:
            weather = weather_summary_for_game(keyword, date_text, time_text)
            if weather:
                summaries.append(weather)
                seen.add(keyword)
    return summaries

def game_to_dict(game, include_weather=True):
    data = {
        "id": game.id,
        "date": game.game_date,
        "game_sno": game.game_sno,
        "game_time": game.game_time,
        "current_inning": infer_current_inning(game),
        "away": game.away_team,
        "home": game.home_team,
        "away_score": game.away_score,
        "home_score": game.home_score,
        "away_pitcher": game.away_pitcher,
        "home_pitcher": game.home_pitcher,
        "winning_pitcher": game.winning_pitcher,
        "losing_pitcher": game.losing_pitcher,
        "save_pitcher": game.save_pitcher,
        "mvp": game.mvp,
        "mvp_team": game.mvp_team,
        "mvp_note": game.mvp_note,
        "location": game.location,
        "status": game.game_status,
    }
    if include_weather:
        data["weather"] = weather_summary_for_game(game.location, game.game_date, game.game_time)
    return data

def game_ai_summary(game):
    summary = {
        "date": game.game_date,
        "time": game.game_time,
        "status": game.game_status,
        "location": game.location,
        "away": game.away_team,
        "away_score": game.away_score,
        "away_pitcher": game.away_pitcher,
        "home": game.home_team,
        "home_score": game.home_score,
        "home_pitcher": game.home_pitcher,
        "inning": infer_current_inning(game),
        "winning_pitcher": game.winning_pitcher,
        "losing_pitcher": game.losing_pitcher,
        "save_pitcher": game.save_pitcher,
        "mvp": game.mvp,
        "mvp_team": game.mvp_team,
        "mvp_note": game.mvp_note,
    }
    weather = weather_summary_for_game(game.location, game.game_date, game.game_time)
    if weather:
        summary["weather"] = weather
    return summary

def member_ai_summary(cards, lineup_slots):
    rarity_values = {"common": 4, "rare": 8, "holo": 14, "legend": 24}
    rarity_counts = {"common": 0, "rare": 0, "holo": 0, "legend": 0}
    team_counts = {}

    for card in cards:
        rarity = card.rarity or "common"
        rarity_counts[rarity] = rarity_counts.get(rarity, 0) + intish(card.count, 1)
        if card.team:
            team_counts[card.team] = team_counts.get(card.team, 0) + intish(card.count, 1)

    lineup_players = [
        slot.get("player")
        for slot in lineup_slots
        if isinstance(slot, dict) and isinstance(slot.get("player"), dict)
    ]
    lineup_team_counts = {}
    for player in lineup_players:
        team = player.get("team") or "未知球隊"
        lineup_team_counts[team] = lineup_team_counts.get(team, 0) + 1

    pitcher_ready = any(
        isinstance(slot, dict)
        and (slot.get("role") == "pitcher" or slot.get("order") == "P")
        and isinstance(slot.get("player"), dict)
        for slot in lineup_slots
    )
    batter_count = sum(
        1
        for slot in lineup_slots[:9]
        if isinstance(slot, dict) and isinstance(slot.get("player"), dict)
    )
    defense_count = len({
        slot.get("defense")
        for slot in lineup_slots[:9]
        if isinstance(slot, dict) and slot.get("defense")
    })
    top_lineup_team, top_lineup_count = ("", 0)
    if lineup_team_counts:
        top_lineup_team, top_lineup_count = sorted(lineup_team_counts.items(), key=lambda item: item[1], reverse=True)[0]

    rarity_score = sum(
        rarity_values.get(str(player.get("rarity") or "common"), 4)
        for player in lineup_players
    )
    lineup_score = (
        rarity_score
        + batter_count * 4
        + (12 if pitcher_ready else 0)
        + min(defense_count, 9) * 2
        + max(0, top_lineup_count - 2) * 5
    )

    return {
        "unique_cards": len(cards),
        "total_cards": sum(intish(card.count, 1) for card in cards),
        "team_card_counts": team_counts,
        "rarity_counts": rarity_counts,
        "lineup_score": lineup_score,
        "lineup_batters": batter_count,
        "lineup_pitcher_ready": pitcher_ready,
        "lineup_top_team": top_lineup_team,
        "lineup_top_team_count": top_lineup_count,
    }

def build_ai_context(user=None, active_page="", user_question=""):
    now = datetime.now(TAIPEI_TIMEZONE)
    today = now.strftime("%m/%d")
    today_games = Game.query.filter_by(game_date=today).order_by(Game.game_time.asc()).limit(6).all()
    recent_games = (
        Game.query
        .filter(Game.game_status.in_(["FINISH", "FINAL"]))
        .order_by(Game.game_date.desc(), Game.id.desc())
        .limit(6)
        .all()
    )
    upcoming_games = (
        Game.query
        .filter(Game.game_status.notin_(["FINISH", "FINAL", "延賽", "POSTPONED"]))
        .order_by(Game.game_date.asc(), Game.game_time.asc())
        .limit(6)
        .all()
    )

    standings_data = read_json_file(STANDINGS_PATH, {})
    standings_rows = standings_data.get("h2h", []) if isinstance(standings_data, dict) else []
    standings = [
        {
            "team": re.sub(r"^\d+", "", str(row.get("排名球隊", ""))),
            "games": row.get("出賽數", ""),
            "record": row.get("勝-和-敗", ""),
            "pct": row.get("勝率", ""),
            "gb": row.get("勝差", ""),
            "streak": row.get("連勝/連敗", ""),
            "last10": row.get("近十場戰績", ""),
        }
        for row in standings_rows[:6]
        if isinstance(row, dict)
    ]

    context = {
        "server_date": now.strftime("%Y-%m-%d"),
        "timezone": "Asia/Taipei",
        "active_page": str(active_page or "")[:40],
        "today_games": [game_ai_summary(game) for game in today_games],
        "recent_finished_games": [game_ai_summary(game) for game in recent_games],
        "upcoming_games": [game_ai_summary(game) for game in upcoming_games],
        "standings": standings,
        "asked_venue_weather": weather_context_from_question(user_question),
    }

    if user:
        all_cards = UserCard.query.filter_by(user_id=user.id).all()
        cards = sorted(all_cards, key=lambda card: (card.rarity or "", card.name or ""), reverse=True)[:30]
        lineup = UserLineup.query.filter_by(user_id=user.id).first()
        lineup_slots = lineup_to_dict(lineup).get("slots", [])
        context["member"] = {
            "username": user.username,
            "favorite_team": user.favorite_team,
            "card_points": user.card_points,
            "summary": member_ai_summary(all_cards, lineup_slots),
            "cards": [
                {
                    "name": card.name,
                    "team": card.team,
                    "position": card.position,
                    "rarity": card.rarity,
                    "count": card.count,
                }
                for card in cards
            ],
            "lineup": lineup_slots,
        }

    return context

def clean_username(value):
    value = re.sub(r'\s+', '', str(value or '')).strip()
    return value[:40]

def normalize_card_payload(payload):
    name = clean_player_name(payload.get("name"))
    if not name:
        raise ValueError("缺少球員姓名")
    rarity = str(payload.get("rarity") or "").lower()
    if rarity not in RARITIES:
        rarity = "legend" if name == "頌恩" else "common"
    return {
        "name": name,
        "team": str(payload.get("team") or "")[:100],
        "position": str(payload.get("position") or "")[:50],
        "description": str(payload.get("description") or "")[:300],
        "rarity": rarity,
        "count": max(1, intish(payload.get("count"), 1)),
    }

def normalize_ticket_payload(payload):
    game = payload.get("game") or {}
    game_id = intish(game.get("id") or payload.get("gameId"))
    if not game_id:
        raise ValueError("缺少比賽 ID")
    return {
        "game_id": game_id,
        "game_date": str(game.get("date") or payload.get("date") or "")[:10],
        "location": str(game.get("location") or payload.get("location") or "")[:100],
        "away_team": str(game.get("away") or payload.get("away") or "")[:100],
        "home_team": str(game.get("home") or payload.get("home") or "")[:100],
        "away_score": str(game.get("away_score") if game.get("away_score") is not None else payload.get("away_score") or "")[:10],
        "home_score": str(game.get("home_score") if game.get("home_score") is not None else payload.get("home_score") or "")[:10],
        "game_status": str(game.get("status") or payload.get("status") or "")[:20],
        "note": str(payload.get("note") or "")[:1000],
        "image": str(payload.get("image") or ""),
    }

def normalize_lineup_payload(payload):
    slots = payload.get("slots") if isinstance(payload, dict) else payload
    if not isinstance(slots, list):
        raise ValueError("打線格式錯誤")

    normalized = []
    for index in range(10):
        raw = slots[index] if index < len(slots) and isinstance(slots[index], dict) else {}
        player = raw.get("player")
        is_pitcher_slot = index == 9
        normalized.append({
            "order": "P" if is_pitcher_slot else index + 1,
            "role": "pitcher" if is_pitcher_slot else "batter",
            "defense": "投手" if is_pitcher_slot else str(raw.get("defense") or "")[:20],
            "player": normalize_card_payload(player) if isinstance(player, dict) and clean_player_name(player.get("name")) else None,
        })
    return normalized

def infer_current_inning(game):
    if game.game_status != "LIVE":
        return ""
    time_text = clean_player_name(game.game_time)
    if "局" in time_text:
        return time_text

    def line_len(value):
        if not value:
            return 0
        return len([item for item in str(value).split(",") if item != ""])

    inning = max(line_len(game.away_line), line_len(game.home_line))
    if inning > 0:
        return f"{inning}局"
    return "局數同步中"

def today_key():
    return datetime.now().strftime("%Y-%m-%d")

def yesterday_key():
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

def next_streak_value(user):
    if user.last_daily_reward_date == yesterday_key():
        return intish(user.daily_streak) + 1
    return 1

def rarity_point_value(rarity):
    return {
        "common": 6,
        "rare": 12,
        "holo": 28,
        "legend": 60,
    }.get(rarity or "common", 6)

def rarity_from_player(player):
    name = clean_player_name(player.get("name"))
    team = clean_player_name(player.get("team"))
    if team in TEAM_RARE_NAMES:
        return "rare" if name in TEAM_RARE_NAMES[team] else "common"
    if name == "頌恩":
        return "legend"
    token = sum(ord(ch) for ch in name)
    if token % 19 == 0:
        return "legend"
    if token % 11 == 0:
        return "holo"
    if token % 5 == 0:
        return "rare"
    return "common"

def team_rare_pool(players, team):
    rare_names = TEAM_RARE_NAMES.get(team, set())
    return [
        player for player in players
        if isinstance(player, dict)
        and clean_player_name(player.get("team")) == team
        and clean_player_name(player.get("name")) in rare_names
    ]

def keep_team_rare_on_new_list(player, players, rarity):
    if rarity != "rare":
        return player
    team = clean_player_name(player.get("team"))
    if team not in TEAM_RARE_NAMES:
        return player
    if clean_player_name(player.get("name")) in TEAM_RARE_NAMES[team]:
        return player
    pool = team_rare_pool(players, team)
    return dict(random.choice(pool)) if pool else player

def choose_reward_player(guaranteed_holo=False):
    players = read_json_file(PLAYERS_POOL_PATH, [])
    if not isinstance(players, list) or not players:
        return None
    usable = [
        player for player in players
        if isinstance(player, dict) and clean_player_name(player.get("name")) and "二軍" not in str(player.get("team") or "")
    ]
    pool = usable or players
    if guaranteed_holo:
        rare_pool = [player for player in pool if rarity_from_player(player) in {"holo", "legend"}]
        if rare_pool:
            pool = rare_pool
    index = int(datetime.now().strftime("%j")) % len(pool)
    player = dict(pool[index])
    player["rarity"] = rarity_from_player(player)
    if guaranteed_holo and player["rarity"] in {"common", "rare"}:
        player["rarity"] = "holo"
    return player

def roll_pack_rarity(pack_type):
    value = random.random()
    if pack_type == "premium":
        if value < 0.06:
            return "legend"
        if value < 0.20:
            return "holo"
        if value < 0.55:
            return "rare"
        return "common"
    if value < 0.03:
        return "legend"
    if value < 0.10:
        return "holo"
    if value < 0.30:
        return "rare"
    return "common"

def choose_pack_player(pack_type="standard"):
    players = read_json_file(PLAYERS_POOL_PATH, [])
    if not isinstance(players, list) or not players:
        return None
    pool = [
        attach_player_card_meta(player) for player in players
        if isinstance(player, dict) and
        clean_player_name(player.get("name")) and
        "二軍" not in str(player.get("team") or "") and
        player_has_card(player)
    ] or players
    player = dict(random.choice(pool))
    rarity = roll_pack_rarity(pack_type)
    player = keep_team_rare_on_new_list(player, pool, rarity)
    player["rarity"] = rarity
    if clean_player_name(player.get("name")) == "頌恩":
        player["rarity"] = "legend"
    return player

def player_card_path(player):
    name = clean_player_name(player.get("name") if isinstance(player, dict) else player)
    if not name:
        return None
    return BASE_DIR / "static" / "image" / "players" / f"{name}_card.png"

def player_has_card(player):
    path = player_card_path(player)
    return bool(path and path.exists())

def attach_player_card_meta(player):
    item = dict(player)
    name = clean_player_name(item.get("name"))
    has_card = player_has_card(item)
    item["has_card"] = has_card
    item["card_image"] = f"/static/image/players/{name}_card.png" if has_card else ""
    return item

# --- 格式化輔助函數：確保數據轉成陣列 ---
# --- 格式化輔助函數：增加球員參數 ---
def format_game_detail(game, away_players=None, home_players=None):
    def to_list(val):
        # 統一處理資料庫讀出來的字串
        if not val or val in ["", "-", "None"]: 
            return []
        return val.split(',')

    return {
        "away_team": game.away_team,
        "home_team": game.home_team,
        "away_line": to_list(game.away_line),
        "home_line": to_list(game.home_line),
        "away_rhe": to_list(game.away_rhe),
        "home_rhe": to_list(game.home_rhe),
        "away_pitcher": game.away_pitcher,
        "home_pitcher": game.home_pitcher,
        "winning_pitcher": game.winning_pitcher,
        "losing_pitcher": game.losing_pitcher,
        "save_pitcher": game.save_pitcher,
        "mvp": game.mvp,
        "mvp_team": game.mvp_team,
        "mvp_note": game.mvp_note,
        # 🟢 重點：如果呼叫時有給球員名單就用它，沒有就給空陣列
        "away_players": away_players if away_players is not None else [],
        "home_players": home_players if home_players is not None else []
    }

def parse_game_box(soup):
    line_data = {"away": [], "home": [], "away_rhe": [], "home_rhe": []}
    away_p, home_p = [], []
    
    # --- 1. 抓取上方比分 (縫合拆分式表格) ---
    score_wrap = soup.select_one('.linescore_wrap')
    
    if score_wrap:
        for side in ['away', 'home']:
            # 🟢 A. 從中間捲動區 (scrollable) 抓取 1~9 局分數
            # 這裡的 td 全部都是分數，不包含隊名或總分
            scroll_tr = score_wrap.select_one(f'.linescore.scrollable tr.{side}')
            if scroll_tr:
                line_data[side] = [td.get_text(strip=True) or "0" for td in scroll_tr.select('td')]

            # 🟢 B. 從右邊固定區 (fixed) 抓取 R-H-E 總分
            # 這裡精確抓取最後的三個數據
            fixed_tr = score_wrap.select_one(f'.linescore.fixed tr.{side}')
            if fixed_tr:
                rhe_values = [td.get_text(strip=True) or "0" for td in fixed_tr.select('td')]
                # 有時候官網會有空白或"-"，我們統一轉為數字
                line_data[f"{side}_rhe"] = [v if v.isdigit() else "0" for v in rhe_values]
                
                # 🕵️ 自動校正：如果總分(R)欄位是 0，但前面局數加總有分數，幫它補上
                total_r_calc = sum(int(x) for x in line_data[side] if x.isdigit())
                if int(line_data[f"{side}_rhe"][0]) == 0 and total_r_calc > 0:
                    line_data[f"{side}_rhe"][0] = str(total_r_calc)

    # --- 2. 抓取球員 (維持精確的數字過濾邏輯) ---
    all_tables = soup.select('.RecordTable table')
    valid_numeric_tables = []
    
    for t in all_tables:
        headers = [th.get_text(strip=True) for th in t.select('th')]
        if "打數" in headers:
            rows = t.select('tbody tr')
            p_list = []
            is_numeric_table = True
            for row in rows:
                cols = row.select('td')
                if len(cols) < 5 or "小計" in row.get_text(): continue
                
                ab_val = cols[1].get_text(strip=True)
                # 檢查打數是否為純數字，排除「右飛/三滾」那張文字描述表
                if not ab_val.isdigit():
                    is_numeric_table = False
                    break
                
                p_list.append({
                    "name": cols[0].get_text(strip=True).split('(')[0],
                    "ab": ab_val,
                    "h": cols[3].get_text(strip=True),
                    "rbi": cols[4].get_text(strip=True)
                })
            
            if is_numeric_table and p_list:
                valid_numeric_tables.append(p_list)
    
    if len(valid_numeric_tables) >= 1: away_p = valid_numeric_tables[0]
    if len(valid_numeric_tables) >= 2: home_p = valid_numeric_tables[1]
                
    return line_data, away_p, home_p

# --- 路由：增加強制等待與 JS 點擊 ---
@app.route('/api/game/detail/<int:game_id>')
def get_game_detail(game_id):
    game = db.session.get(Game, game_id)
    if not game:
        return jsonify({"error": "找不到比賽"}), 404
    if not game.game_sno:
        detail = format_game_detail(game)
        detail["source"] = "cache"
        detail["message"] = "這場比賽缺少 game_sno，請先同步該月份賽程。"
        return jsonify(detail)

    try:
        payload = fetch_cpbl_game_payload(game.game_sno)
        line = build_line_data_from_scoreboards(payload["scoreboards"])
        a_p = players_from_battings(payload["battings"], "1")
        h_p = players_from_battings(payload["battings"], "2")
        extras = extract_official_game_extras(payload, game)
        play_by_play = build_play_by_play(payload, game)

        if any(line.values()) or extras.get("mvp") or extras.get("away_pitcher") or extras.get("home_pitcher"):
            if line["away"]:
                game.away_line = ",".join(line["away"])
            if line["home"]:
                game.home_line = ",".join(line["home"])
            if line["away_rhe"]:
                game.away_rhe = ",".join(line["away_rhe"])
            if line["home_rhe"]:
                game.home_rhe = ",".join(line["home_rhe"])
            apply_game_extras(game, extras)
            db.session.commit()

        detail = format_game_detail(game, a_p, h_p)
        detail["play_by_play"] = play_by_play
        detail["source"] = payload["source"]
        return jsonify(detail)
    except Exception as e:
        print(f"⚠️ 官方 JSON 解析失敗，回退使用資料庫快取: {e}")
        detail = format_game_detail(game)
        detail["play_by_play"] = []
        detail["source"] = "cache"
        detail["message"] = f"官方數據暫時無法取得，改用本機快取顯示。({e})"
        return jsonify(detail)

@app.route('/api/update/schedule')
def update_schedule():
    target_m = request.args.get('m', default=datetime.now().month, type=int)
    target_year = request.args.get('year', default=SEASON_YEAR, type=int)
    if not 1 <= target_m <= 12:
        return jsonify({"status": "error", "message": "月份必須介於 1 到 12"}), 400

    driver = None
    try:
        url = f"https://www.cpbl.com.tw/schedule?&GameType=1&Month={target_m:02d}&Year={target_year}"
        soup, driver = fetch_page_soup(url)
        
        # 同時支援賽程表 (tr) 和 可能出現在清單中的 game_item
        rows = soup.select('.ScheduleTableList table tbody tr, .game_item')
        
        last_date = ""; count = 0
        for row in rows:
            if row.select_one('th') or "無比賽" in row.text: continue
            
            # 1. 抓日期
            d_node = row.select_one('td.date')
            if d_node and d_node.get_text(strip=True):
                # 這裡使用你原本的 parse_date 函數
                last_date = parse_date(d_node.get_text(strip=True))
            if not last_date: continue

            game_sno = ""
            no_link = row.select_one('td.game_no a, a[href*="gameSno="]')
            if no_link and 'href' in no_link.attrs:
                match = re.search(r'gameSno=(\d+)', no_link['href'])
                if match:
                    game_sno = match.group(1)

            # 2. 抓隊伍與地點
            team_td = row.select_one('td.team')
            if not team_td:
                # 備援：針對首頁結構 (.game_item)
                teams = row.select('.team_name, .name')
                if len(teams) < 2: continue
                aw, ho = teams[0].get_text(strip=True), teams[1].get_text(strip=True)
                loc = row.select_one('.place').get_text(strip=True) if row.select_one('.place') else "未知"
            else:
                # 針對賽程表結構 (tr)
                aw = team_td.select_one('.name.away').get_text(strip=True)
                ho = team_td.select_one('.name.home').get_text(strip=True)
                loc = (row.select_one('td.venue') or row.select_one('.place')).get_text(strip=True)

            if any(x in loc for x in ["青埔", "園區"]): continue

            # 🧢 抓取投手資訊 (精準對應你的截圖路徑)
            aw_p_node = row.select_one('.PlayerMatchup.away_sp .name')
            ho_p_node = row.select_one('.PlayerMatchup.home_sp .name')
            aw_p = aw_p_node.get_text(strip=True) if aw_p_node else ""
            ho_p = ho_p_node.get_text(strip=True) if ho_p_node else ""
                # ... 其他欄位更新 ...
            # 3. 🚩 智能狀態與時間判定 (整合 .time 標籤與 .final 類別)
            row_classes = row.get('class', [])
            raw_text = row.get_text(" ", strip=True)
            
            st, ascore, hscore, gtime = "", "--", "--", ""
            
            # 優先檢查是否為結束 (Class 包含 final 或文字包含 比賽結束)
            is_finish = "final" in row_classes or any(x in raw_text for x in ["比賽結束", "Final", "結束"])
            # 檢查是否為比賽中
            is_live = "live" in row_classes or any(x in raw_text for x in ["比賽中", "live"]) or "局" in raw_text

            if is_finish:
                st, gtime = "FINISH", "Final"
                # 嘗試抓比分
                score_node = row.select_one('.score, .score_wrap')
                if score_node and ":" in score_node.get_text():
                    pts = score_node.get_text(strip=True).split(":")
                    ascore, hscore = pts[0].strip(), pts[1].strip()
            
            elif is_live:
                st = "LIVE"
                # 嘗試抓比分
                score_node = row.select_one('.score, .score_wrap')
                if score_node and ":" in score_node.get_text():
                    pts = score_node.get_text(strip=True).split(":")
                    ascore, hscore = pts[0].strip(), pts[1].strip()
                # 抓局數
                m_inning = re.search(r'(\d+局[上下]?)', raw_text)
                gtime = m_inning.group(1) if m_inning else "LIVE"
                
            else:
                # 🟡 尚未開賽：針對你截圖中的 .time 標籤
                st = ""
                time_node = row.select_one('.time')
                if time_node:
                    gtime = time_node.get_text(strip=True)
                else:
                    # 備援：如果沒找到 .time 標籤，看比分欄位有沒有時間格式
                    score_node = row.select_one('.score')
                    score_txt = score_node.get_text(strip=True) if score_node else ""
                    if ":" in score_txt:
                        gtime = score_txt

            # 4. DB 更新或新增
            exist = Game.query.filter_by(game_date=last_date, away_team=aw, home_team=ho).first()
            if not exist:
                db.session.add(Game(
                    game_date=last_date, game_sno=game_sno, game_time=gtime,
                    away_team=aw, away_score=ascore, away_pitcher=aw_p,
                    home_team=ho, home_score=hscore, home_pitcher=ho_p,
                    location=loc, game_status=st
                ))
            else:
                exist.game_sno = game_sno or exist.game_sno
                exist.away_score, exist.home_score = ascore, hscore
                exist.game_time, exist.game_status = gtime, st
                if aw_p:
                    exist.away_pitcher = aw_p
                if ho_p:
                    exist.home_pitcher = ho_p
            count += 1
            
        db.session.commit()
        result = {"status": "success", "year": target_year, "month": target_m, "count": count}
        record_sync_status("schedule", "賽程同步", result)
        return jsonify(result)
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if driver: driver.quit()

@app.route('/api/update/today')
def update_today():
    driver = None
    try:
        soup, driver = fetch_page_soup("https://www.cpbl.com.tw/")
        
        # 1. 確認日期
        d_node = soup.select_one('.date_selected .date, .date_select .date')
        anchor_date = parse_date(d_node.get_text()) if d_node else datetime.now().strftime("%m/%d")

        # 🟢 2. 使用你提供的正確對照表
        team_map = {
            'ADD011': '統一',
            'AAA011': '味全',
            'ACN011': '中信',
            'AJL011': '樂天',
            'AEO011': '富邦',
            'AKP011': '台鋼'
        }

        items = soup.select('.game_item, .IndexScheduleList .item, .item')
        print(f"\n[DEBUG] --- 🕵️ ID 識別同步：{anchor_date} ---")
        count = 0

        for i, item in enumerate(items):
            # 只有包含先發資訊的才處理
            if "先發" not in item.get_text(): continue

            # 🟢 3. 透過 URL 中的 teamNo 識別隊伍
            def get_team_by_id(selector):
                a_tag = item.select_one(selector)
                if a_tag and 'href' in a_tag.attrs:
                    href = a_tag['href']
                    # 抓取 teamNo= 後面的 ID
                    match = re.search(r'teamNo=([^&?]+)', href)
                    if match:
                        tid = match.group(1)
                        name = team_map.get(tid, "")
                        if not name: 
                            # 如果 ID 沒在表裡，就抓 a 標籤的 title 當備援
                            name = (a_tag.get('title') or "")[:2]
                        return name
                return ""

            aw_n = get_team_by_id('.team.away .team_name a')
            ho_n = get_team_by_id('.team.home .team_name a')

            # 🟢 4. 抓取並清洗投手姓名
            aw_p_node = item.select_one('.away_sp .name, [class*="away_sp"] .name')
            ho_p_node = item.select_one('.home_sp .name, [class*="home_sp"] .name')
            
            def clean_p(txt):
                if not txt: return ""
                for s in ["客場先發", "主場先發", "P:", "先發", " "]: txt = txt.replace(s, "")
                return txt.strip()

            aw_p = clean_p(aw_p_node.get_text(strip=True)) if aw_p_node else ""
            ho_p = clean_p(ho_p_node.get_text(strip=True)) if ho_p_node else ""

            print(f"📍 鎖定區塊 #{i}: {aw_n}({aw_p}) vs {ho_n}({ho_p})")

            # 🟢 5. 更新 DB (模糊比對)
            if aw_n and ho_n:
                # 使用 contains 確保「味全」能對上資料庫裡的「味全龍」
                game = Game.query.filter(
                    Game.game_date == anchor_date,
                    Game.away_team.contains(aw_n),
                    Game.home_team.contains(ho_n)
                ).first()

                if game:
                    if aw_p:
                        game.away_pitcher = aw_p
                    if ho_p:
                        game.home_pitcher = ho_p
                    
                    # 🟢 6. 安全抓取比分 (不再用 int 轉型，防止 VS. 澄清湖 報錯)
                    score_node = item.select_one('.score, .num')
                    if score_node and ":" in score_node.get_text():
                        s_text = score_node.get_text(strip=True)
                        if "VS" not in s_text: # 排除掉 "VS.澄清湖18:35" 這種格式
                            parts = s_text.split(":")
                            game.away_score, game.home_score = parts[0].strip(), parts[1].strip()
                    
                    # 處理狀態
                    full_txt = item.get_text()
                    if "結束" in full_txt:
                        game.game_status, game.game_time = "FINISH", "Final"
                    elif "比賽" in full_txt:
                        game.game_status = "LIVE"
                        m = re.search(r'(\d+局[上下]?)', full_txt)
                        game.game_time = m.group(1) if m else "LIVE"

                    count += 1
                    print(f"✅ 更新成功！")
                else:
                    print(f"❌ DB找不到 {anchor_date} 的 {aw_n} vs {ho_n}")

        db.session.commit()
        result = {"status": "success", "count": count}
        record_sync_status("today", "今日狀態", result)
        return jsonify(result)
    finally:
        if driver: driver.quit()

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.get_json(silent=True) or {}
    username = clean_username(data.get("username"))
    password = str(data.get("password") or "")
    favorite_team = str(data.get("favorite_team") or "")

    if len(username) < 3:
        return jsonify({"error": "帳號至少需要 3 個字"}), 400
    if len(password) < 4:
        return jsonify({"error": "密碼至少需要 4 個字"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "這個帳號已經存在"}), 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        api_token=secrets.token_urlsafe(32),
        favorite_team=favorite_team if favorite_team in TEAMS else "",
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"status": "success", "user": user_to_dict(user), "token": user.api_token})

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.get_json(silent=True) or {}
    username = clean_username(data.get("username"))
    password = str(data.get("password") or "")
    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "帳號或密碼錯誤"}), 401

    return jsonify({"status": "success", "user": user_to_dict(user), "token": user.api_token})

@app.route('/api/auth/me')
def auth_me():
    user, error = require_auth_user()
    if error:
        return error
    return jsonify({"status": "success", "user": user_to_dict(user)})

@app.route('/api/auth/me', methods=['PATCH'])
def update_auth_me():
    user, error = require_auth_user()
    if error:
        return error
    data = request.get_json(silent=True) or {}
    favorite_team = str(data.get("favorite_team") or "")
    user.favorite_team = favorite_team if favorite_team in TEAMS else ""
    db.session.commit()
    return jsonify({"status": "success", "user": user_to_dict(user)})

@app.route('/api/profile')
def get_profile():
    user, error = require_auth_user()
    if error:
        return error

    cards = UserCard.query.filter_by(user_id=user.id).order_by(UserCard.count.desc(), UserCard.name.asc()).all()
    tickets = UserTicket.query.filter_by(user_id=user.id).order_by(UserTicket.created_at.desc()).limit(6).all()
    total_cards = sum(intish(card.count, 1) for card in cards)
    rarity_counts = {"common": 0, "rare": 0, "holo": 0, "legend": 0}
    team_counts = {}
    for card in cards:
        rarity_counts[card.rarity or "common"] = rarity_counts.get(card.rarity or "common", 0) + intish(card.count, 1)
        if card.team:
            team_counts[card.team] = team_counts.get(card.team, 0) + intish(card.count, 1)

    leaderboard = sorted([card_to_dict(card) for card in cards], key=lambda item: (-intish(item.get("count"), 1), item.get("name", "")))[:5]
    top_team = sorted(team_counts.items(), key=lambda item: item[1], reverse=True)[0][0] if team_counts else ""

    return jsonify({
        "user": user_to_dict(user),
        "summary": {
            "unique_cards": len(cards),
            "total_cards": total_cards,
            "ticket_count": UserTicket.query.filter_by(user_id=user.id).count(),
            "top_team": top_team,
            "rarities": rarity_counts,
            "daily_claimed": user.last_daily_reward_date == today_key(),
            "daily_streak": intish(user.daily_streak),
            "next_daily_streak": intish(user.daily_streak) + 1 if user.last_daily_reward_date == today_key() else next_streak_value(user),
            "next_daily_guarantee": ((intish(user.daily_streak) + 1 if user.last_daily_reward_date == today_key() else next_streak_value(user)) % 7 == 0),
            "card_points": intish(user.card_points),
        },
        "recent_cards": [card_to_dict(card) for card in cards[:6]],
        "leaderboard": leaderboard,
        "recent_tickets": [ticket_to_dict(ticket) for ticket in tickets],
    })

def upsert_user_card(user, payload):
    card = UserCard.query.filter_by(user_id=user.id, name=payload["name"]).first()
    if card:
        card.count = intish(card.count, 1) + payload["count"]
        card.team = payload["team"] or card.team
        card.position = payload["position"] or card.position
        card.description = payload["description"] or card.description
        if payload.get("rarity") in RARITIES:
            card.rarity = payload["rarity"]
    else:
        card = UserCard(user_id=user.id, **payload)
        db.session.add(card)
    return card

@app.route('/api/rewards/daily', methods=['POST'])
def claim_daily_reward():
    user, error = require_auth_user()
    if error:
        return error
    if user.last_daily_reward_date == today_key():
        return jsonify({"error": "今天已經領過每日獎勵"}), 409

    streak = next_streak_value(user)
    guaranteed_holo = streak % 7 == 0
    player = choose_reward_player(guaranteed_holo=guaranteed_holo)
    if not player:
        return jsonify({"error": "球員池沒有資料，請先同步球員資料"}), 400

    payload = normalize_card_payload({ **player, "count": 1 })
    card = upsert_user_card(user, payload)
    user.last_daily_reward_date = today_key()
    user.daily_streak = streak
    db.session.commit()
    return jsonify({
        "status": "success",
        "card": card_to_dict(card),
        "user": user_to_dict(user),
        "streak": streak,
        "guaranteed_bonus": guaranteed_holo,
    })

@app.route('/api/shop/packs', methods=['POST'])
def buy_point_pack():
    user, error = require_auth_user()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    pack_type = str(data.get("pack_type") or data.get("type") or "standard")
    if pack_type not in PACK_COSTS:
        return jsonify({"error": "未知的球員包"}), 400

    cost = PACK_COSTS[pack_type]
    if intish(user.card_points) < cost:
        return jsonify({"error": f"收藏點數不足，需要 {cost} 點"}), 400

    player = choose_pack_player(pack_type)
    if not player:
        return jsonify({"error": "球員池沒有資料，請先同步球員資料"}), 400

    user.card_points = intish(user.card_points) - cost
    card = upsert_user_card(user, normalize_card_payload({ **player, "count": 1 }))
    db.session.commit()
    return jsonify({
        "status": "success",
        "pack_type": pack_type,
        "cost": cost,
        "card": card_to_dict(card),
        "user": user_to_dict(user),
    })

@app.route('/api/cards', methods=['GET'])
def get_user_cards():
    user, error = require_auth_user()
    if error:
        return error
    cards = UserCard.query.filter_by(user_id=user.id).order_by(UserCard.name.asc()).all()
    return jsonify([card_to_dict(card) for card in cards])

@app.route('/api/cards', methods=['POST'])
def save_user_card():
    user, error = require_auth_user()
    if error:
        return error

    try:
        payload = normalize_card_payload(request.get_json(silent=True) or {})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    card = upsert_user_card(user, payload)

    db.session.commit()
    return jsonify({"status": "success", "card": card_to_dict(card)})

@app.route('/api/cards/<path:player_name>', methods=['DELETE'])
def delete_user_card(player_name):
    user, error = require_auth_user()
    if error:
        return error
    card = UserCard.query.filter_by(user_id=user.id, name=clean_player_name(player_name)).first()
    if card:
        db.session.delete(card)
        db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/cards', methods=['DELETE'])
def clear_user_cards():
    user, error = require_auth_user()
    if error:
        return error
    UserCard.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/cards/<path:player_name>/convert', methods=['POST'])
def convert_user_card(player_name):
    user, error = require_auth_user()
    if error:
        return error
    card = UserCard.query.filter_by(user_id=user.id, name=clean_player_name(player_name)).first()
    if not card or intish(card.count, 1) <= 1:
        return jsonify({"error": "這張卡沒有可分解的重複卡"}), 400

    data = request.get_json(silent=True) or {}
    max_convert = intish(card.count, 1) - 1
    amount = min(max(1, intish(data.get("count"), max_convert)), max_convert)
    points = amount * rarity_point_value(card.rarity)
    card.count = intish(card.count, 1) - amount
    user.card_points = intish(user.card_points) + points
    db.session.commit()
    return jsonify({"status": "success", "points": points, "card": card_to_dict(card), "user": user_to_dict(user)})

@app.route('/api/cards/convert-duplicates', methods=['POST'])
def convert_duplicate_cards():
    user, error = require_auth_user()
    if error:
        return error

    cards = UserCard.query.filter_by(user_id=user.id).all()
    total_points = 0
    converted = 0
    for card in cards:
        extra = max(0, intish(card.count, 1) - 1)
        if not extra:
            continue
        converted += extra
        total_points += extra * rarity_point_value(card.rarity)
        card.count = 1

    if converted == 0:
        return jsonify({"error": "目前沒有可分解的重複卡"}), 400

    user.card_points = intish(user.card_points) + total_points
    db.session.commit()
    return jsonify({
        "status": "success",
        "converted": converted,
        "points": total_points,
        "cards": [card_to_dict(card) for card in cards],
        "user": user_to_dict(user),
    })

@app.route('/api/cards/fuse', methods=['POST'])
def fuse_cards():
    user, error = require_auth_user()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    materials = payload.get("materials")
    slots = intish(payload.get("slots"), 3)

    if slots not in {3, 5}:
        return jsonify({"error": "合成插槽數量必須為 3 或 5"}), 400

    if not isinstance(materials, list) or len(materials) != slots:
        return jsonify({"error": f"必須提供剛好 {slots} 張球員卡作為材料"}), 400

    material_counts = {}
    for name in materials:
        if not isinstance(name, str) or not name.strip():
            continue
        cleaned = clean_player_name(name)
        material_counts[cleaned] = material_counts.get(cleaned, 0) + 1

    user_cards = {card.name: card for card in UserCard.query.filter_by(user_id=user.id).all()}
    
    for name, required_count in material_counts.items():
        card = user_cards.get(name)
        if not card:
            return jsonify({"error": f"你沒有球員「{name}」的卡片"}), 400
        if card.rarity != "common":
            return jsonify({"error": f"球員「{name}」不是一般稀有度，無法作為合成材料"}), 400
        if intish(card.count, 1) < required_count:
            return jsonify({"error": f"球員「{name}」的卡片數量不足（需要 {required_count} 張，目前有 {card.count} 張）"}), 400

    for name, count_to_deduct in material_counts.items():
        card = user_cards[name]
        card.count = intish(card.count, 1) - count_to_deduct
        if card.count <= 0:
            db.session.delete(card)

    value = random.random()
    if slots == 5:
        if value < 0.10:
            new_rarity = "legend"
        elif value < 0.35:
            new_rarity = "holo"
        else:
            new_rarity = "rare"
    else:
        if value < 0.05:
            new_rarity = "legend"
        elif value < 0.20:
            new_rarity = "holo"
        else:
            new_rarity = "rare"

    players = read_json_file(PLAYERS_POOL_PATH, [])
    if not isinstance(players, list) or not players:
        return jsonify({"error": "球員池沒有資料，請先同步球員資料"}), 400
        
    usable_players = [
        p for p in players 
        if isinstance(p, dict) and clean_player_name(p.get("name")) and "二軍" not in str(p.get("team") or "")
    ] or players
    
    selected_player = dict(random.choice(usable_players))
    selected_player = keep_team_rare_on_new_list(selected_player, usable_players, new_rarity)
    selected_player["rarity"] = new_rarity
    player_name = clean_player_name(selected_player.get("name"))
    if player_name == "頌恩":
        selected_player["rarity"] = "legend"

    new_card_payload = {
        "name": player_name,
        "team": selected_player.get("team") or "",
        "position": selected_player.get("position") or "",
        "description": selected_player.get("description") or "在熔煉爐中誕生的全新卡牌！",
        "rarity": selected_player["rarity"],
        "count": 1
    }
    
    new_card = upsert_user_card(user, new_card_payload)
    db.session.commit()

    updated_cards = UserCard.query.filter_by(user_id=user.id).order_by(UserCard.name.asc()).all()

    return jsonify({
        "status": "success",
        "new_card": card_to_dict(new_card),
        "cards": [card_to_dict(c) for c in updated_cards],
        "user": user_to_dict(user)
    })

@app.route('/api/lineup', methods=['GET'])
def get_user_lineup():
    user, error = require_auth_user()
    if error:
        return error
    lineup = UserLineup.query.filter_by(user_id=user.id).first()
    return jsonify(lineup_to_dict(lineup))

@app.route('/api/lineup', methods=['PUT'])
def save_user_lineup():
    user, error = require_auth_user()
    if error:
        return error

    try:
        slots = normalize_lineup_payload(request.get_json(silent=True) or {})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    lineup = UserLineup.query.filter_by(user_id=user.id).first()
    if not lineup:
        lineup = UserLineup(user_id=user.id)
        db.session.add(lineup)
    lineup.slots = json.dumps(slots, ensure_ascii=False)
    db.session.commit()
    return jsonify({"status": "success", **lineup_to_dict(lineup)})

@app.route('/api/tickets')
def get_user_tickets():
    user, error = require_auth_user()
    if error:
        return error
    game_id = request.args.get('game_id', type=int)
    q = UserTicket.query.filter_by(user_id=user.id)
    if game_id:
        q = q.filter_by(game_id=game_id)
    tickets = q.order_by(UserTicket.created_at.desc()).all()
    return jsonify([ticket_to_dict(ticket) for ticket in tickets])

@app.route('/api/tickets', methods=['POST'])
def save_user_ticket():
    user, error = require_auth_user()
    if error:
        return error
    try:
        payload = normalize_ticket_payload(request.get_json(silent=True) or {})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    ticket = UserTicket(user_id=user.id, **payload)
    db.session.add(ticket)
    db.session.commit()
    return jsonify({"status": "success", "ticket": ticket_to_dict(ticket)})

@app.route('/api/tickets/<int:ticket_id>', methods=['DELETE'])
def delete_user_ticket(ticket_id):
    user, error = require_auth_user()
    if error:
        return error
    ticket = UserTicket.query.filter_by(user_id=user.id, id=ticket_id).first()
    if ticket:
        db.session.delete(ticket)
        db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/update/game_extras')
def update_game_extras():
    target_m = request.args.get('m', type=int)
    target_year = request.args.get('year', default=SEASON_YEAR, type=int)
    limit = request.args.get('limit', default=30, type=int)
    limit = max(1, min(limit, 90))

    q = Game.query.filter(Game.game_status == "FINISH").order_by(Game.game_date.asc())
    if target_m:
        prefix = f"{target_m:02d}/"
        q = q.filter(Game.game_date.like(f"{prefix}%"))

    games = q.limit(limit).all()
    updated = 0
    skipped = 0
    failed = []

    for game in games:
        if not game.game_sno:
            skipped += 1
            continue
        try:
            payload = fetch_cpbl_game_payload(game.game_sno, target_year)
            extras = extract_official_game_extras(payload, game)
            line = build_line_data_from_scoreboards(payload["scoreboards"])

            if line["away"]:
                game.away_line = ",".join(line["away"])
            if line["home"]:
                game.home_line = ",".join(line["home"])
            if line["away_rhe"]:
                game.away_rhe = ",".join(line["away_rhe"])
            if line["home_rhe"]:
                game.home_rhe = ",".join(line["home_rhe"])
            apply_game_extras(game, extras)
            updated += 1
            print(f"✅ 補抓完成：{game.game_date} {game.away_team} vs {game.home_team} MVP={game.mvp}")
        except Exception as e:
            failed.append({
                "id": game.id,
                "game_sno": game.game_sno,
                "matchup": f"{game.away_team} vs {game.home_team}",
                "message": str(e),
            })

    db.session.commit()
    result = {
        "status": "success" if not failed else "partial",
        "year": target_year,
        "month": target_m,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
    }
    record_sync_status("game_extras", "投手與 MVP", result, result["status"])
    return jsonify(result)

@app.route('/api/games')
def get_games():
    # 1. 接收前端傳來的參數
    date = request.args.get('date', '')
    team = request.args.get('team', '') # 🟢 接收球隊參數
    
    # 2. 基本查詢：按日期排序
    q = Game.query.order_by(Game.game_date.asc())
    
    # 3. 條件篩選：日期
    if date: 
        q = q.filter(Game.game_date == date)
        
    # 4. 條件篩選：球隊 (只要是主隊或客隊其中之一符合就抓出來)
    if team:
        q = q.filter(or_(Game.away_team == team, Game.home_team == team))
    
    # 5. 回傳資料 (包含投手、MVP 與球場天氣)
    return jsonify([game_to_dict(g) for g in q.all()])

@app.route('/api/update/month')
def update_specific_month():
    target_m = request.args.get('m', type=int)
    if not target_m: return jsonify({"status": "error", "message": "月份缺失"}), 400
    if not 1 <= target_m <= 12:
        return jsonify({"status": "error", "message": "月份必須介於 1 到 12"}), 400
    target_year = request.args.get('year', default=SEASON_YEAR, type=int)
    
    print(f"--- 🚀 執行升級版同步：目標 {target_year}/{target_m:02d} ---")
    driver = None
    try:
        url = f"https://www.cpbl.com.tw/schedule?&GameType=1&Month={target_m:02d}&Year={target_year}"
        soup, driver = fetch_page_soup(url, click_list_tab=True)

        # 確保切換到列表模式。若 CPBL 調整頁面結構，後續解析仍會嘗試使用目前頁面。
        if driver:
            try:
                driver.find_element(By.CSS_SELECTOR, "li[data-id='list']").click()
                time.sleep(3)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
            except: pass

        # 開始解析
        rows = soup.select('.ScheduleTableList table tbody tr')
        
        last_date = ""
        count = 0
        for row in rows:
            # 排除標題或無比賽
            if row.select_one('th') or "無比賽" in row.get_text(): 
                continue
            
            # --- 1. 抓日期 ---
            d_node = row.select_one('td.date')
            if d_node and d_node.get_text(strip=True):
                raw_d = d_node.get_text(strip=True).split('(')[0]
                last_date = parse_date(raw_d)
            
            if not last_date: continue

            game_sno = ""
            no_link = row.select_one('td.game_no a')
            if no_link and 'href' in no_link.attrs:
                href = no_link['href']
                match = re.search(r'gameSno=(\d+)', href)
                if match:
                    game_sno = match.group(1)

            # --- 2. 抓隊伍與地點 ---
            team_td = row.select_one('td.team')
            if not team_td: continue 

            aw_node = team_td.select_one('.name.away')
            ho_node = team_td.select_one('.name.home')
            if not aw_node or not ho_node: continue
            
            aw = aw_node.get_text(strip=True)
            ho = ho_node.get_text(strip=True)
            loc = (row.select_one('td.venue') or row.select_one('.place')).get_text(strip=True)

            # --- 🧢 抓取投手資訊 ---
            aw_p_node = row.select_one('.PlayerMatchup.away_sp .name')
            ho_p_node = row.select_one('.PlayerMatchup.home_sp .name')
            aw_p = aw_p_node.get_text(strip=True) if aw_p_node else ""
            ho_p = ho_p_node.get_text(strip=True) if ho_p_node else ""

            # --- 3. 🚩 狀態與比分判定 ---
            row_classes = row.get('class', [])
            raw_text = row.get_text(" ", strip=True)
            st, ascore, hscore, gtime = "WAIT", "--", "--", ""
            
            # 🟢 這裡加入了延賽判定：檢查整列文字是否包含「延賽」
            is_postponed = "延賽" in raw_text
            is_finish = "final" in row_classes or any(x in raw_text for x in ["比賽結束", "Final", "結束"])
            is_live = "live" in row_classes or any(x in raw_text for x in ["比賽中", "live"]) or "局" in raw_text

            # 🟢 判斷順序：優先處理延賽
            if is_postponed:
                st, gtime = "延賽", "延賽"
                ascore, hscore = "--", "--"
            
            elif is_finish:
                st, gtime = "FINISH", "Final"
                score_node = row.select_one('.score, .score_wrap')
                if score_node:
                    txt = score_node.get_text(strip=True)
                    if ":" in txt:
                        pts = txt.split(":")
                        ascore, hscore = pts[0].strip(), pts[1].strip()
                    elif "VS" in txt:
                        pts = txt.split("VS")
                        ascore, hscore = pts[0].strip(), pts[1].strip()
            
            elif is_live:
                st = "LIVE"
                score_node = row.select_one('.score, .score_wrap')
                if score_node and ":" in score_node.get_text():
                    pts = score_node.get_text(strip=True).split(":")
                    ascore, hscore = pts[0].strip(), pts[1].strip()
                m_inning = re.search(r'(\d+局[上下]?)', raw_text)
                gtime = m_inning.group(1) if m_inning else "LIVE"
            
            else:
                time_node = row.select_one('.time')
                gtime = time_node.get_text(strip=True) if time_node else "18:35"

            # --- 4. 存入/更新資料庫 ---
            exist = Game.query.filter_by(game_date=last_date, away_team=aw, home_team=ho).first()
            if not exist:
                db.session.add(Game(
                    game_date=last_date, game_sno=game_sno, game_time=gtime, 
                    away_team=aw, away_score=ascore, away_pitcher=aw_p,
                    home_team=ho, home_score=hscore, home_pitcher=ho_p,
                    location=loc, game_status=st
                ))
            else:
                exist.game_sno = game_sno
                exist.away_score = ascore
                exist.home_score = hscore
                exist.game_time = gtime
                exist.game_status = st  # 🔴 更新狀態 (包含 延賽)
                if aw_p:
                    exist.away_pitcher = aw_p
                if ho_p:
                    exist.home_pitcher = ho_p
            
            count += 1
            print(f"✅ {last_date}: {aw} VS {ho} ({st})")

        db.session.commit()
        result = {"status": "success", "year": target_year, "month": target_m, "count": count}
        record_sync_status("month", "月份賽程", result)
        return jsonify(result)

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if driver: driver.quit()

@app.route('/api/update/standings')
def update_standings():
    driver = None
    try:
        soup, driver = fetch_page_soup("https://www.cpbl.com.tw/standings/season", force_selenium=True)
        
        # ✅ 改用明確等待，等到 table 真的出現才繼續
        if driver:
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
                )
                soup = BeautifulSoup(driver.page_source, 'html.parser')
            except:
                # 如果等不到，印出頁面源碼幫助偵錯
                print("⚠️ 等待逾時，頁面源碼片段：")
                print(driver.page_source[:3000])
                return jsonify({"status": "error", "message": "頁面等待逾時"}), 500
        
        # ✅ 偵錯：先印出頁面裡找到哪些東西
        all_tables = soup.select('table')
        print(f"🔍 找到 {len(all_tables)} 張表格")
        for i, t in enumerate(all_tables):
            headers = [th.get_text(strip=True) for th in t.select('th')]
            print(f"  表格 {i}: headers = {headers[:5]}")

        # ✅ 改為直接抓所有 table，不依賴外層容器
        all_tables = soup.select('table')
        categories = ["h2h", "pitching", "batting"]
        all_data = {}

        for i, cat_key in enumerate(categories):
            if i >= len(all_tables):
                all_data[cat_key] = []
                continue
                
            table = all_tables[i]
            headers = [th.get_text(strip=True) for th in table.select('th')]
            
            rows_data = []
            for tr in table.select('tbody tr'):
                cells = [td.get_text(strip=True) for td in tr.select('td')]
                if cells and len(cells) == len(headers):
                    rows_data.append(dict(zip(headers, cells)))
            
            print(f"✅ {cat_key}: {len(rows_data)} 列, headers={headers}")
            all_data[cat_key] = rows_data

        has_valid_standings = all(
            isinstance(all_data.get(key), list) and len(all_data.get(key)) > 0
            for key in categories
        )
        if not has_valid_standings:
            cached = read_json_file(STANDINGS_PATH, {})
            result = {
                "status": "fallback",
                "message": "官方戰績頁暫時沒有解析到完整資料，已保留目前本機快取。",
                "data": cached,
                "parsed_counts": {key: len(all_data.get(key, [])) for key in categories},
            }
            record_sync_status("standings", "球隊戰績", {
                "status": "fallback",
                "parsed_counts": result["parsed_counts"],
            })
            return jsonify(result)

        write_json_file(STANDINGS_PATH, all_data)
        result = {"status": "success", "data": all_data}
        record_sync_status("standings", "球隊戰績", {"groups": len(all_data)})
        return jsonify(result)

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if driver: driver.quit()

# 提供前端讀取戰績的 API
@app.route('/api/get_standings')
def get_standings_data():
    return jsonify(read_json_file(STANDINGS_PATH, {}))

@app.route('/api/sync/status')
def get_sync_status():
    return jsonify(read_json_file(SYNC_STATUS_PATH, {}))

def parse_generic_table(table_node):
    """通用工具：將 HTML 表格轉為 List[Dict]"""
    if not table_node: return []
    headers = [th.get_text(strip=True) for th in table_node.select('thead th')]
    rows = []
    for tr in table_node.select('tbody tr'):
        # 排除包含 <th> 的行（通常是小計或換投說明）
        if tr.select('th') and len(tr.select('td')) == 0: continue
        cells = [td.get_text(strip=True) for td in tr.select('td')]
        if len(cells) > 0:
            # 如果 cells 長度跟 headers 不對等，補齊標頭或過濾
            rows.append(dict(zip(headers, cells)))
    return rows

def parse_line_score(soup):
    """專門解析最上方的局數比分表 (Line Score)"""
    # CPBL 的比分表通常在 .ScoreTable 或 table.score_table
    table = soup.select_one('.ScoreTable') or soup.select_one('.score_table')
    if not table: return []
    
    headers = [th.get_text(strip=True) for th in table.select('thead th')]
    lines = []
    for tr in table.select('tbody tr'):
        team_name = tr.select_one('td.team, td:first-child').get_text(strip=True)
        scores = [td.get_text(strip=True) for td in tr.select('td')]
        # 我們要把隊名跟每一局的分數配對
        lines.append(dict(zip(headers, scores)))
    return lines

@app.route('/api/game/box')
def get_game_box():
    sno = request.args.get('sno')
    if not sno: return jsonify({"error": "No SNO"}), 400
    
    url = cpbl_box_url(sno)
    print(f"📊 正在解析詳細數據：{url}")
    
    driver = None
    try:
        soup, driver = fetch_page_soup(url)
        
        # 🟢 1. 解析比分板 (截圖最上方那塊)
        line_score = parse_line_score(soup)
        
        # 🟢 2. 解析數據表 (RecordTable)
        # tables[0]: 客隊打擊, [1]: 主隊打擊, [2]: 客隊投球, [3]: 主隊投球
        tables = soup.select('.RecordTable')
        
        box_data = {
            "line_score": line_score,
            "away_batting": parse_generic_table(tables[0]) if len(tables) > 0 else [],
            "home_batting": parse_generic_table(tables[1]) if len(tables) > 1 else [],
            "away_pitching": parse_generic_table(tables[2]) if len(tables) > 2 else [],
            "home_pitching": parse_generic_table(tables[3]) if len(tables) > 3 else []
        }
        
        return jsonify({
            "status": "success", 
            "url": url, 
            "data": box_data
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if driver: driver.quit()

@app.route('/api/init_pool')
def init_player_pool():
    url = "https://www.cpbl.com.tw/player"
    driver = None
    try:
        soup, driver = fetch_page_soup(url)
        player_links = soup.select('.PlayersList a')
        print(f"--- 偵錯資訊：抓到 {len(player_links)} 個球員連結 ---")

        # 讀取已存的進度，避免中斷後重頭來
        if PLAYERS_POOL_PATH.exists():
            master_pool = read_json_file(PLAYERS_POOL_PATH, [])
            done_names = {p['name'] for p in master_pool}
            print(f"--- 繼續上次進度，已有 {len(master_pool)} 筆 ---")
        else:
            master_pool = []
            done_names = set()

        for item in player_links:
            name = item.get_text(strip=True)
            
            # 已抓過就跳過
            if name in done_names:
                print(f"⏭️ 跳過 {name}")
                continue

            href = item.get('href', '')
            if href and not href.startswith('http'):
                href = "https://www.cpbl.com.tw" + href

            team = ''
            position = ''
            if href:
                try:
                    # 1. 優先用 requests.get 獲取個別球員頁面
                    try:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        }
                        session = requests.Session()
                        session.trust_env = False
                        res = session.get(href, headers=headers, timeout=10)
                        res.raise_for_status()
                        player_soup = BeautifulSoup(res.text, 'html.parser')
                    except Exception as req_err:
                        print(f"⚠️ requests 抓取球員 {name} 失敗: {req_err}，改用 Selenium...")
                        # 2. 備援：確保 driver 已啟動
                        if not driver:
                            driver = make_driver()
                        driver.get(href)
                        time.sleep(2)
                        player_soup = BeautifulSoup(driver.page_source, 'html.parser')

                    h2 = player_soup.select_one('#Content .PageTitle h2')
                    if h2:
                        for span in h2.select('span'):
                            span.decompose()
                        team = h2.get_text(strip=True)

                    pos_tag = player_soup.select_one('dd.pos .desc')
                    position = pos_tag.get_text(strip=True) if pos_tag else ''

                except Exception as e:
                    print(f"抓 {name} 失敗：{e}")

            if name:
                master_pool.append({
                    "name": name,
                    "team": team,
                    "position": position,
                })
                done_names.add(name)
                
                # 每抓一筆就存一次，中斷也不怕
                write_json_file(PLAYERS_POOL_PATH, master_pool)

            print(f"✅ {name} | {team} | {position}")

        result = {"status": "success", "total": len(master_pool)}
        record_sync_status("players", "球員池", result)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if driver: driver.quit()

@app.route('/api/get_player_pool')
def get_player_pool():
    if not PLAYERS_POOL_PATH.exists():
        return jsonify({"error": "找不到球員池檔案，請先執行初始化"}), 404
    players = read_json_file(PLAYERS_POOL_PATH, [])
    if not isinstance(players, list):
        return jsonify([])
    return jsonify([attach_player_card_meta(player) for player in players if isinstance(player, dict)])

@app.route('/api/top_stats')
def get_top_stats():
    limit = request.args.get("limit", default=10, type=int)
    limit = max(1, min(limit, 20))

    try:
        return jsonify({
            "status": "success",
            "source": TOP_STATS_SOURCE_URL,
            "data": fetch_cpbl_top_stats(limit),
        })
    except Exception as e:
        print(f"排行榜抓取失敗：{e}")
        return jsonify({
            "status": "error",
            "source": TOP_STATS_SOURCE_URL,
        "data": [],
        "message": str(e),
    }), 200

@app.route('/api/weather/venue')
def get_venue_weather():
    venue = request.args.get("venue", "")
    date_text = request.args.get("date", "")
    time_text = request.args.get("time", "")
    if not venue:
        return jsonify({"error": "缺少球場名稱"}), 400
    weather = weather_summary_for_game(venue, date_text, time_text)
    if not weather:
        return jsonify({
            "venue": venue,
            "display": "尚無球場天氣",
            "rain_risk": False,
            "source": "Open-Meteo",
        })
    return jsonify(weather)

@app.route('/api/get_news')
def get_news():
    limit = request.args.get("limit", default=12, type=int)
    limit = max(1, min(limit, 30))

    try:
        news_data = fetch_cpbl_news(limit)
        if news_data:
            return jsonify(news_data)
    except Exception as e:
        print(f"新聞抓取失敗，改用備援資料：{e}")

    try:
        local_news = read_json_file(DATA_DIR / 'news.json', [])
        if isinstance(local_news, list) and local_news:
            return jsonify(local_news[:limit])
    except Exception:
        pass

    return jsonify(NEWS_FALLBACK[:limit])

@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return jsonify({
            "error": "AI 尚未設定，請在後端環境變數加入 GROQ_API_KEY。"
        }), 503

    if not ai_request_allowed():
        return jsonify({
            "error": "AI 詢問得有點快，請過幾分鐘再試。"
        }), 429

    payload = request.get_json(silent=True) or {}
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        return jsonify({"error": "對話格式錯誤"}), 400

    messages = []
    for item in raw_messages[-10:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content[:2000]})

    if not messages or messages[-1]["role"] != "user":
        return jsonify({"error": "請輸入想問的問題"}), 400

    context = build_ai_context(get_auth_user(), payload.get("active_page"), messages[-1]["content"])
    system_prompt = (
        "你是 GoBase AI，一位熟悉中華職棒的繁體中文球迷助理。"
        "回答要親切、精簡、容易閱讀。你可以解釋棒球規則、分析提供的賽事資料、"
        "整理比分與戰績、依球場天氣提醒是否要帶雨具，以及在會員資料存在時協助卡牌與打線建議。"
        "只能把下方 CONTEXT 當成 GoBase 內的即時資料；資料沒有提供時要明確說目前查不到，"
        "不可捏造球員、比分、賽程、傷勢或官方公告。"
        "若使用者詢問醫療、賭博或投注，只提供一般資訊並提醒自行判斷。"
        f"\n\nCONTEXT:\n{json.dumps(context, ensure_ascii=False, separators=(',', ':'))}"
    )

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "system", "content": system_prompt}, *messages],
                "temperature": 0.35,
                "max_completion_tokens": 700,
            },
            timeout=45,
        )
        response.raise_for_status()
        result = response.json()
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        if not answer:
            raise ValueError("Groq 未回傳回答")
        return jsonify({
            "answer": answer,
            "model": result.get("model") or GROQ_MODEL,
        })
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else 502
        detail = ""
        if e.response is not None:
            try:
                detail = e.response.json().get("error", {}).get("message", "")
            except Exception:
                detail = ""
        print(f"Groq API error ({status}): {detail or e}")
        if status == 401:
            return jsonify({"error": "Groq API Key 無效，請重新確認後端環境變數。"}), 502
        if status == 429:
            return jsonify({"error": "AI 使用量暫時達到限制，請稍後再試。"}), 429
        return jsonify({"error": "Groq AI 暫時無法回應，請稍後再試。"}), 502
    except requests.RequestException as e:
        print(f"Groq connection error: {e}")
        return jsonify({"error": "目前無法連線到 Groq AI。"}), 502
    except Exception as e:
        print(f"AI response error: {e}")
        return jsonify({"error": "AI 回答處理失敗，請稍後再試。"}), 500

@app.route('/api/health')
def health():
    game_count = Game.query.count()
    return jsonify({
        "status": "ok",
        "season_year": SEASON_YEAR,
        "database": app.config['SQLALCHEMY_DATABASE_URI'].split("@")[-1],
        "data_dir": str(DATA_DIR),
        "games": game_count,
        "standings_ready": STANDINGS_PATH.exists(),
        "players_ready": PLAYERS_POOL_PATH.exists(),
        "ai_ready": bool(os.environ.get("GROQ_API_KEY", "").strip()),
    })

@app.route('/api/selenium/health')
def selenium_health():
    driver = None
    try:
        driver = make_driver()
        driver.get("data:text/html,<title>selenium-ok</title><h1>ok</h1>")
        return jsonify({
            "status": "ok",
            "title": driver.title,
            "chrome_bin": os.environ.get("CHROME_BIN", ""),
            "chromedriver_path": os.environ.get("CHROMEDRIVER_PATH", ""),
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "chrome_bin": os.environ.get("CHROME_BIN", ""),
            "chromedriver_path": os.environ.get("CHROMEDRIVER_PATH", ""),
        }), 500
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    # debug=True 可以在你改代碼時自動重啟，非常方便
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
        host=os.environ.get("CPBL_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT") or os.environ.get("CPBL_PORT", 5101)),
        use_reloader=False
    )
