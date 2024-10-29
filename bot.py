import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from config_reader import config
from paarser import get_data_from_last_script, get_price

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token='8053355193:AAHIXLq3hKEfcTPsdTPRZJ_C7k2aR_C9Sgg')
# Диспетчер
dp = Dispatcher()

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

button_add_item = InlineKeyboardButton(text="🛍️ Добавить товар", callback_data="add_item")
button_my_items = InlineKeyboardButton(text="🛒  Список моих товаров", callback_data="my_items")
button_remove_item = InlineKeyboardButton(text="🗑️  Удалить товар", callback_data="remove_item")
button_help = InlineKeyboardButton(text="🆘  Помощь", callback_data="help")
button_change_item = InlineKeyboardButton(text="✏️  Внести изменения в товар", callback_data="help")

menu = InlineKeyboardMarkup(inline_keyboard=[
    [button_add_item],
    [button_change_item],
    [button_my_items],
    [button_remove_item, button_help],   
])
user_items = {}
user_states = {}
price_check_task = None

greet = "Привет, {name}, я бот, который поможет тебе следить за ценами на [omarket.kz](https://omarket.kz), Только тсс.... 🤫"

@dp.message(Command("start"))
async def cmd_hello(message: Message):
    formatted_greet = greet.format(name=message.from_user.full_name)
    await message.answer(formatted_greet, parse_mode='Markdown', reply_markup=menu)

@dp.callback_query()
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "add_item":
        await callback_query.message.answer("Введите первую ссылку = URL страницы товара:")
        user_states[user_id] = {"step": "waiting_for_first_url"}
    elif data == "my_items":
        items = user_items.get(user_id, [])
        if items:
            item_list = "\n".join([f"{i+1}. {item['first_url']} - {item['price']}" for i, item in enumerate(items)])
            await callback_query.message.answer("Ваши товары:\n" + item_list)
        else:
            await callback_query.message.answer("Ваш список товаров пуст")
    elif data == "remove_item":
        items = user_items.get(user_id, [])
        if items:
            item_list = "\n".join([f"{i+1}. {item['first_url']} - {item['price']}" for i, item in enumerate(items)])
            await callback_query.message.answer("Введите номер товара, который хотите удалить:\n" + item_list)
            user_states[user_id] = {"step": "waiting_for_remove_index"}
        else:
            await callback_query.message.answer("Ваш список товаров пуст")
    elif data == "change_item":
        items = user_items.get(user_id, [])
        if items:
            item_list = "\n".join([f"{i+1}. {item['first_url']} - {item['price']}" for i, item in enumerate(items)])
            await callback_query.message.answer("Введите номер товара, который хотите посмотреть:\n" + item_list)
            user_states[user_id] = {"step": "waiting_for_change_index"}
        else:
            await callback_query.message.answer("Ваш список товаров пуст")        
    elif data == "help":
        await callback_query.message.answer("Этот бот помогает следить за ценами на товары в магазине Omarket.\n\n"
                                            "Вот доступные команды:\n"
                                            "/start - Начать работу с ботом\n"
                                            "/help - Показать это сообщение помощи\n"
                                            "Используйте кнопки в меню для добавления товаров и просмотра списка ваших товаров.\n\n"
                                            "Свяжитесь с @nurba_zh для любых вопросов.")

    await callback_query.answer()  # Acknowledge the callback query to stop repeating

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    if user_id in user_states:
        state = user_states[user_id]
        if state["step"] == "waiting_for_url":
            state["first_url"] = message.text
            await message.answer("Введите вторую ссылку = URL страницы изменения товара с вашего личного кабинета(P.S: где есть пороговая цена):")
        elif state["step"] == "waiting_for_price":
            state["second_url"] = message.text
            await message.answer("Ага, записал. Интересный товар! А теперь, введите вашу МИНИМАЛЬНУЮ цену товара, ниже которой вы продавать не будете. Мы же все таки здесь, чтобы заработать 💵:")
        elif state["step"] == "waiting_for_price":
            try:
                state["min_price"] = float(message.text)
                await message.answer("У какого по счету продавца смотреть минимальную цену? <i>(обычно это первый, но вдруг тут чел будет продавать за 5тг, и с ним нет смысла бороться):<i>", parse_mode='Markdown')
            except ValueError:
                await message.answer("Пожалуйста, введите корректную цену.")
        elif state["step"] == "waiting_for_minimal_index":
            try:
                min_index = float(message.text)
                price = get_price(state["first_url"], state["second_url"], min_index)
                if user_id not in user_items:
                    user_items[user_id] = []
                user_items[user_id].append({
                    "first_url": state["first_url"], 
                    "second_url": state["second_url"], 
                    "min_price": state["min_price"], 
                    "price": price, 
                    "min_index": min_index,
                    })
                await message.answer(f"Товар добавлен: {state['first_url']} - {price}", reply_markup=menu)
                user_states.pop(user_id) 
            except ValueError:
                await message.answer("Пожалуйста, введите корректную номер продавца(ЧИСЛОООО).1️⃣2️⃣3️⃣")
        elif state["step"] == "waiting_for_change_index":
            try:
                index = int(message.text) - 1
                items = user_items.get(user_id, [])
                if 0 <= index < len(items):
                    shown_item = items[index]
                    await message.answer(f"Вот ваш товар: {shown_item['first_url']} - {shown_item['price']}", reply_markup=menu)
                else:
                    await message.answer("Неправильный номер товара. Пожалуйста, попробуйте снова.")
                user_states.pop(user_id)
            except ValueError:
                await message.answer("Пожалуйста, введите корректный номер товара.")     
        elif state["step"] == "waiting_for_remove_index":
            try:
                index = int(message.text) - 1
                items = user_items.get(user_id, [])
                if 0 <= index < len(items):
                    removed_item = items.pop(index)
                    await message.answer(f"Товар удален: {removed_item['first_url']} - {removed_item['price']}", reply_markup=menu)
                else:
                    await message.answer("Неправильный номер товара. Пожалуйста, попробуйте снова.")
                user_states.pop(user_id)
            except ValueError:
                await message.answer("Пожалуйста, введите корректный номер товара.")
    else:
        await message.answer("Я не понимаю это сообщение. Пожалуйста, используйте меню для взаимодействия со мной.", reply_markup=menu)

async def check_prices():
    while True:
        for user_id, items in user_items.items():
            for item in items:
                current_price = get_data_from_last_script(item["url"], item["url"], 1)
                if isinstance(current_price, (int, float)) and current_price < item["price"]:
                    await bot.send_message(user_id, f"Цена на товар {item['first_url']} снизилась до {current_price}! Обновляем цену на {current_price - 1}!.")
                    item["price"] = current_price - 1 
        await asyncio.sleep(10)

async def main():
    #global price_check_task
    #price_check_task = asyncio.create_task(check_prices())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
