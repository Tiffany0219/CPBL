import os
import re, time, json, traceback
import random
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from werkzeug.security import check_password_hash, generate_password_hash
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
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
DATA_DIR = Path(os.environ.get("CPBL_DATA_DIR", BASE_DIR)).resolve()
SEASON_YEAR = int(os.environ.get("CPBL_SEASON_YEAR", datetime.now().year))
STANDINGS_PATH = DATA_DIR / "standings.json"
PLAYERS_POOL_PATH = DATA_DIR / "players_pool.json"
SYNC_STATUS_PATH = DATA_DIR / "sync_status.json"

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{BASE_DIR / 'instance' / 'cpbl_data.db'}"
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

with app.app_context():
    db.create_all()
    ensure_game_schema()
    ensure_columns("user", USER_EXTRA_COLUMNS)
    ensure_columns("user_card", USER_CARD_EXTRA_COLUMNS)

def make_driver():
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    return webdriver.Chrome(options=opts)

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
        "createdAt": ticket.created_at.isoformat() if ticket.created_at else "",
    }

def lineup_to_dict(lineup):
    return {
        "slots": parse_json_payload(lineup.slots if lineup else "[]", []),
        "updatedAt": lineup.updated_at.isoformat() if lineup and lineup.updated_at else "",
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
    for index in range(9):
        raw = slots[index] if index < len(slots) and isinstance(slots[index], dict) else {}
        player = raw.get("player")
        normalized.append({
            "order": index + 1,
            "defense": str(raw.get("defense") or "")[:20],
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
        if value < 0.07:
            return "legend"
        if value < 0.25:
            return "holo"
        if value < 0.62:
            return "rare"
        return "common"
    if value < 0.03:
        return "legend"
    if value < 0.12:
        return "holo"
    if value < 0.34:
        return "rare"
    return "common"

def choose_pack_player(pack_type="standard"):
    players = read_json_file(PLAYERS_POOL_PATH, [])
    if not isinstance(players, list) or not players:
        return None
    pool = [
        player for player in players
        if isinstance(player, dict) and clean_player_name(player.get("name")) and "二軍" not in str(player.get("team") or "")
    ] or players
    player = dict(random.choice(pool))
    player["rarity"] = roll_pack_rarity(pack_type)
    if clean_player_name(player.get("name")) == "頌恩":
        player["rarity"] = "legend"
    return player

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
        print(f"⚠️ 官方 JSON 解析失敗，改用 Selenium 備援: {e}")

    driver = None
    try:
        driver = make_driver()
        url = cpbl_box_url(game.game_sno)
        driver.get(url)

        # 🟢 強制點擊「詳細紀錄」標籤
        driver.execute_script("""
            var links = document.querySelectorAll('.tabs li a');
            for(var i=0; i<links.length; i++){
                if(links[i].innerText.includes('詳細紀錄')){
                    links[i].click();
                    break;
                }
            }
        """)
        
        # 🟢 關鍵等待：RecordTable 需要時間載入
        import time
        time.sleep(10) 
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        line, a_p, h_p = parse_game_box(soup)
        
        # 🕵️ 核心邏輯：判斷比賽是否已經開始
        # 檢查 RHE 是否有任何得分或安打，或者是否已經抓到球員名單
        is_started = any(int(x) > 0 for x in line.get('away_rhe', ['0']) if x.isdigit()) or \
                     any(int(x) > 0 for x in line.get('home_rhe', ['0']) if x.isdigit()) or \
                     len(a_p) > 0

        # 🟢 存入資料庫 (只有在比賽已經開始且抓到球員時才更新)
        if is_started and a_p:
            game.away_line = ",".join(line["away"])
            game.home_line = ",".join(line["home"])
            game.away_rhe = ",".join(line["away_rhe"])
            game.home_rhe = ",".join(line["home_rhe"])
            db.session.commit()
            print(f"✅ 成功更新資料庫：客隊 {len(a_p)} 人")

        # 🟢 回傳 JSON 給前端
        detail = {
            "away_team": game.away_team,
            "home_team": game.home_team,
            # 如果還沒開始，回傳空陣列讓前端顯示「尚未開始」
            "away_line": line["away"] if is_started else [],
            "home_line": line["home"] if is_started else [],
            "away_rhe": line["away_rhe"] if is_started else ["0", "0", "0"],
            "home_rhe": line["home_rhe"] if is_started else ["0", "0", "0"],
            "away_players": a_p, # 若沒開始，parse_game_box 會回傳 []
            "home_players": h_p,
            "away_pitcher": game.away_pitcher,
            "home_pitcher": game.home_pitcher,
            "winning_pitcher": game.winning_pitcher,
            "losing_pitcher": game.losing_pitcher,
            "save_pitcher": game.save_pitcher,
            "mvp": game.mvp,
            "mvp_team": game.mvp_team,
            "mvp_note": game.mvp_note,
            "play_by_play": [],
            "source": "selenium",
        }
        return jsonify(detail)

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if driver: driver.quit()

@app.route('/api/update/schedule')
def update_schedule():
    target_m = request.args.get('m', default=datetime.now().month, type=int)
    target_year = request.args.get('year', default=SEASON_YEAR, type=int)
    if not 1 <= target_m <= 12:
        return jsonify({"status": "error", "message": "月份必須介於 1 到 12"}), 400

    driver = None
    try:
        driver = make_driver()
        driver.get(f"https://www.cpbl.com.tw/schedule?&GameType=1&Month={target_m:02d}&Year={target_year}")
        time.sleep(10)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
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
        driver = make_driver()
        driver.get("https://www.cpbl.com.tw/")
        time.sleep(12) 
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
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
    
    # 5. 回傳資料 (包含你剛補上的投手欄位)
    return jsonify([{
        "id": g.id,
        "date": g.game_date,
        "game_sno": g.game_sno,
        "game_time": g.game_time,
        "current_inning": infer_current_inning(g),
        "away": g.away_team,
        "home": g.home_team,
        "away_score": g.away_score,
        "home_score": g.home_score,
        "away_pitcher": g.away_pitcher, 
        "home_pitcher": g.home_pitcher, 
        "winning_pitcher": g.winning_pitcher,
        "losing_pitcher": g.losing_pitcher,
        "save_pitcher": g.save_pitcher,
        "mvp": g.mvp,
        "mvp_team": g.mvp_team,
        "mvp_note": g.mvp_note,
        "location": g.location,
        "status": g.game_status
    } for g in q.all()])

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
        driver = make_driver()
        driver.get(f"https://www.cpbl.com.tw/schedule?&GameType=1&Month={target_m:02d}&Year={target_year}")
        time.sleep(5)

        # 確保切換到列表模式。若 CPBL 調整頁面結構，後續解析仍會嘗試使用目前頁面。
        try:
            driver.find_element(By.CSS_SELECTOR, "li[data-id='list']").click()
            time.sleep(3)
        except: pass

        # 開始解析
        soup = BeautifulSoup(driver.page_source, 'html.parser')
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
        driver = make_driver()
        driver.get("https://www.cpbl.com.tw/standings/season")
        
        # ✅ 改用明確等待，等到 table 真的出現才繼續
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
            )
        except:
            # 如果等不到，印出頁面源碼幫助偵錯
            print("⚠️ 等待逾時，頁面源碼片段：")
            print(driver.page_source[:3000])
            return jsonify({"status": "error", "message": "頁面等待逾時"}), 500

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
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
        driver = make_driver()
        driver.get(url)
        time.sleep(3) 
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
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
        driver = make_driver()
        driver.get(url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
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
                    driver.get(href)
                    time.sleep(2)  # 可以改成 random.uniform(1.5, 3.5) 更安全
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
    return jsonify(read_json_file(PLAYERS_POOL_PATH, []))

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
        }), 500

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

@app.route('/api/health')
def health():
    game_count = Game.query.count()
    return jsonify({
        "status": "ok",
        "season_year": SEASON_YEAR,
        "database": str(BASE_DIR / 'instance' / 'cpbl_data.db'),
        "data_dir": str(DATA_DIR),
        "games": game_count,
        "standings_ready": STANDINGS_PATH.exists(),
        "players_ready": PLAYERS_POOL_PATH.exists(),
    })

if __name__ == '__main__':
    # debug=True 可以在你改代碼時自動重啟，非常方便
    app.run(debug=True, port=int(os.environ.get("CPBL_PORT", 5101)), use_reloader=False)
