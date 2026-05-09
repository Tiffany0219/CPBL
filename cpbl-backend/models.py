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
    location = db.Column(db.String(100), default="未知")
    game_status = db.Column(db.String(20), default="")
    away_line = db.Column(db.String(200), default="")
    home_line = db.Column(db.String(200), default="")
    away_rhe = db.Column(db.String(20), default="0,0,0")
    home_rhe = db.Column(db.String(20), default="0,0,0")
