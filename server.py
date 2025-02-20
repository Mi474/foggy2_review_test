from fastapi import FastAPI, Request
import sqlite3
import qrcode
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Имитация базы данных (можно заменить на SQLite)
leaderboard = {}

# Создаём папку для хранения QR-кодов
if not os.path.exists("qr_codes"):
    os.makedirs("qr_codes")

# Делаем папку qr_codes доступной для браузера
app.mount("/qr_codes", StaticFiles(directory="qr_codes"), name="qr_codes")

# Подключаем базу данных SQLite
conn = sqlite3.connect("staff.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        name TEXT,
        qr_code TEXT,
        review_count INTEGER DEFAULT 0
    )
""")
conn.commit()

# 📌 API для регистрации сотрудника
@app.get("/register/{user_id}/{name}")
def register_user(user_id: int, name: str):
    cursor.execute("SELECT * FROM staff WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if user:
        return {"message": "Пользователь уже зарегистрирован", "qr_code": user[3]}

    # Генерируем QR-код
    review_url = f"https://g.page/r/YOUR_PLACE_ID/review?staff={user_id}"
    qr = qrcode.make(review_url)
    qr_path = f"qr_codes/{user_id}.png"
    qr.save(qr_path)

    # Сохраняем пользователя в базу данных
    cursor.execute("INSERT INTO staff (user_id, name, qr_code) VALUES (?, ?, ?)", (user_id, name, qr_path))
    conn.commit()

    return {"message": "Пользователь зарегистрирован", "qr_code": qr_path}

# 📌 API для получения информации о сотруднике
@app.get("/user/{user_id}")
def get_user(user_id: int):
    cursor.execute("SELECT * FROM staff WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        return {"id": user[0], "name": user[2], "qr_code": user[3], "reviews": user[4]}
    
    return {"error": "Пользователь не найден"}

# 📌 API для отображения лидерборда
@app.get("/leaderboard")
def get_leaderboard():
    cursor.execute("SELECT name, review_count FROM staff ORDER BY review_count DESC LIMIT 10")
    leaderboard = cursor.fetchall()

    return [{"name": row[0], "reviews": row[1]} for row in leaderboard]

# 📌 Запуск FastAPI-сервера
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

app.mount("/web", StaticFiles(directory="web"), name="web")

# Отдаём index.html как главную страницу
@app.get("/")
async def root():
    return FileResponse("web/index.html")

# Подключение к базе данных
DATABASE = "staff.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        user_id TEXT PRIMARY KEY,
        name TEXT,
        reviews INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

init_db()

@app.get("/leaderboard")
async def get_leaderboard():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, reviews FROM staff ORDER BY reviews DESC")
    users = [{"name": row[0], "reviews": row[1]} for row in cursor.fetchall()]
    conn.close()
    return users

@app.post("/review/{user_id}/{name}")
async def leave_review(user_id: str, name: str):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT reviews FROM staff WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    if row:
        cursor.execute("UPDATE staff SET reviews = reviews + 1 WHERE user_id=?", (user_id,))
    else:
        cursor.execute("INSERT INTO staff (user_id, name, reviews) VALUES (?, ?, 1)", (user_id, name))

    conn.commit()
    conn.close()
    return {"message": "Отзыв успешно добавлен!"}

@app.post("/submit_review")
async def submit_review(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    name = data.get("name")

    if not user_id or not name:
        return JSONResponse(content={"error": "Нет user_id или name"}, status_code=400)

    # Увеличиваем количество отзывов пользователя
    if user_id in leaderboard:
        leaderboard[user_id]["reviews"] += 1
    else:
        leaderboard[user_id] = {"name": name, "reviews": 1}

    return {"message": "Отзыв добавлен", "leaderboard": leaderboard}
