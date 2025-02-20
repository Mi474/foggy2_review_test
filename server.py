from fastapi import FastAPI
import sqlite3
import qrcode
import os
from fastapi.staticfiles import StaticFiles

app = FastAPI()

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
