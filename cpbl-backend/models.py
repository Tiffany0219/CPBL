from extensions import db


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_date = db.Column(db.String(10))
    game_sno = db.Column(db.String(10))
    game_time = db.Column(db.String(20), default="")
    away_team = db.Column(db.String(100))
    away_score = db.Column(db.String(10), default="--")
    away_pitcher = db.Column(db.String(50), default="")
    home_team = db.Column(db.String(100))
    home_score = db.Column(db.String(10), default="--")
    home_pitcher = db.Column(db.String(50), default="")
    winning_pitcher = db.Column(db.String(50), default="")
    losing_pitcher = db.Column(db.String(50), default="")
    save_pitcher = db.Column(db.String(50), default="")
    mvp = db.Column(db.String(50), default="")
    mvp_team = db.Column(db.String(100), default="")
    mvp_note = db.Column(db.String(120), default="")
    location = db.Column(db.String(100), default="未知")
    game_status = db.Column(db.String(20), default="")
    away_line = db.Column(db.String(200), default="")
    home_line = db.Column(db.String(200), default="")
    away_rhe = db.Column(db.String(20), default="0,0,0")
    home_rhe = db.Column(db.String(20), default="0,0,0")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    api_token = db.Column(db.String(80), unique=True, nullable=False)
    favorite_team = db.Column(db.String(100), default="")
    last_daily_reward_date = db.Column(db.String(10), default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class UserCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    team = db.Column(db.String(100), default="")
    position = db.Column(db.String(50), default="")
    description = db.Column(db.String(300), default="")
    rarity = db.Column(db.String(20), default="common")
    count = db.Column(db.Integer, default=1)

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_user_card_name"),)


class UserTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    game_id = db.Column(db.Integer, nullable=False)
    game_date = db.Column(db.String(10), default="")
    location = db.Column(db.String(100), default="")
    away_team = db.Column(db.String(100), default="")
    home_team = db.Column(db.String(100), default="")
    away_score = db.Column(db.String(10), default="")
    home_score = db.Column(db.String(10), default="")
    game_status = db.Column(db.String(20), default="")
    note = db.Column(db.Text, default="")
    image = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
