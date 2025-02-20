from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo
from aiogram.utils import executor

TOKEN = "ТВОЙ_ТОКЕН_БОТА"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton(
        "Открыть лидерборд",
        web_app=WebAppInfo(url="https://foggy2reviewtest-production.up.railway.app/web/index.html")
    )
    keyboard.add(button)
    await message.answer("Нажми кнопку, чтобы открыть лидерборд", reply_markup=keyboard)

if __name__ == "__main__":
    executor.start_polling(dp)
