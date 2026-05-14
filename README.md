# GoBase CPBL

中職賽程、戰績、新聞、排行榜、球員抽卡與收藏冊工具。

## 啟動後端

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r cpbl-backend/requirements.txt
cd cpbl-backend
python app.py
```

預設 API 位址是 `http://127.0.0.1:5100/api`，可用這個端點確認連線：

```bash
curl http://127.0.0.1:5100/api/health
```

## 啟動前端

```bash
cd cpbl-vue
npm install
npm run dev
```

預設前端網址是 `http://127.0.0.1:5180/`。

前端預設會連到 `http://127.0.0.1:5100/api`。如需調整，複製 `cpbl-vue/.env.example` 為 `.env` 後修改：

```env
VITE_API_BASE=http://127.0.0.1:5100/api
VITE_CPBL_SEASON_YEAR=2026
```

## 後端設定

如需調整球季年份或 JSON 資料檔位置，可複製 `cpbl-backend/.env.example` 參考設定環境變數：

```env
CPBL_PORT=5100
CPBL_SEASON_YEAR=2026
CPBL_DATA_DIR=/Users/tiffany/Projects/CPBL/cpbl-backend
```
