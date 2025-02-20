from fastapi import FastAPI, Request
import sqlite3
import qrcode
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI()

# Подключаем базу данных SQLite
DATABASE = "staff.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Создаём таблицу, если её нет
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        user_id TEXT PRIMARY KEY,
        name TEXT
    )
    """)
    
    # Проверяем, есть ли колонка review_count
    cursor.execute("PRAGMA table_info(staff)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "review_count" not in columns:
        cursor.execute("ALTER TABLE staff ADD COLUMN review_count INTEGER DEFAULT 0")
    
    conn.commit()
    conn.close()

# Инициализируем БД
init_db()

# Создаём папку для хранения QR-кодов
if not os.path.exists("qr_codes"):
    os.makedirs("qr_codes")

# Делаем папку с QR-кодами доступной для браузера
app.mount("/qr_codes", StaticFiles(directory="qr_codes"), name="qr_codes")

# Делаем папку web доступной для фронтенда
app.mount("/web", StaticFiles(directory="web"), name="web")

# Отдаём index.html как главную страницу
@app.get("/")
async def root():
    return FileResponse("web/index.html")

# 📌 API для регистрации сотрудника
@app.get("/register/{user_id}/{name}")
def register_user(user_id: str, name: str):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM staff WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if user:
        return {"message": "Пользователь уже зарегистрирован"}

    # Генерация QR-кода с уникальной ссылкой
    review_url = f"https://g.page/r/YOUR_PLACE_ID/review?staff={user_id}"
    qr = qrcode.make(review_url)
    qr_path = f"qr_codes/{user_id}.png"
    qr.save(qr_path)

    cursor.execute("INSERT INTO staff (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()

    return {"message": "Пользователь зарегистрирован", "qr_code": qr_path}

# 📌 API для получения информации о сотруднике
@app.get("/user/{user_id}")
def get_user(user_id: str):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, reviews FROM staff WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return {"name": user[0], "reviews": user[1]}
    return {"error": "Пользователь не найден"}

# 📌 API для получения лидерборда
@app.get("/leaderboard")
async def get_leaderboard():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, reviews FROM staff ORDER BY reviews DESC")
    users = [{"name": row[0], "reviews": row[1]} for row in cursor.fetchall()]
    conn.close()

    print("Leaderboard Data:", users)  # Отладка
    return users

# 📌 API для добавления отзыва
@app.post("/submit_review")
async def submit_review(request: Request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        name = data.get("name")

        if not user_id or not name:
            return JSONResponse({"error": "Отсутствуют данные пользователя"}, status_code=400)

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("SELECT reviews FROM staff WHERE user_id=?", (user_id,))
        row = cursor.fetchone()

        if row:
            cursor.execute("UPDATE staff SET reviews = reviews + 1 WHERE user_id=?", (user_id,))
        else:
            print(f"Новый пользователь {name} добавлен в базу с ID {user_id}")  # Отладка
            cursor.execute("INSERT INTO staff (user_id, name, reviews) VALUES (?, ?, 1)", (user_id, name))

        conn.commit()
        conn.close()

        response = {"message": "Отзыв успешно добавлен!"}
        print("Response:", response)  # Отладка
        return JSONResponse(response)
    except Exception as e:
        print("Error:", str(e))  # Отладка
        return JSONResponse({"error": str(e)}, status_code=500)

# 📌 Запуск FastAPI-сервера
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)