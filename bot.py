import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config_reader import config
from paarser import get_data_from_last_script, get_price, change_price
import threading
from concurrent.futures import ThreadPoolExecutor

# Enable logging to capture important messages
logging.basicConfig(level=logging.INFO)

check_prices_lock = threading.Lock()

# Initialize ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=1)

# Create the bot and dispatcher
bot = Bot(token='8053355193:AAHIXLq3hKEfcTPsdTPRZJ_C7k2aR_C9Sgg')
dp = Dispatcher()

# Create inline keyboard buttons
sleep_duration = 180
button_add_item = InlineKeyboardButton(text="🛍️ Добавить товар", callback_data="add_item")
button_my_items = InlineKeyboardButton(text="🛒 Список моих товаров", callback_data="my_items")
button_remove_item = InlineKeyboardButton(text="🗑️ Удалить товар", callback_data="remove_item")
button_help = InlineKeyboardButton(text="🆘 Помощь", callback_data="help")
button_change_item = InlineKeyboardButton(text="✏️ Внести изменения в товар", callback_data="change_item")

button_login = InlineKeyboardButton(text="🔑 Ввести данные аккаунта", callback_data="log_in")

button_change_first_url = InlineKeyboardButton(text="✏️ Изменить первую ссылку", callback_data="change_first_url")
button_change_second_url = InlineKeyboardButton(text="✏️ Изменить вторую ссылку", callback_data="change_second_url")
button_change_min_price = InlineKeyboardButton(text="✏️ Изменить минимальную цену", callback_data="change_min_price")
button_change_min_index = InlineKeyboardButton(text="✏️ Изменить минимальный индекс", callback_data="change_min_index")
button_change_nothing = InlineKeyboardButton(text="❌ Я передумал", callback_data="change_nothing")

button_go_to_page = InlineKeyboardButton(text="📄 Ввести номер страницы", callback_data="go_to_page")

menu = InlineKeyboardMarkup(inline_keyboard=[
    [button_add_item],
    [button_change_item],
    [button_my_items],
    [button_remove_item, button_help],   
])

login_menu = InlineKeyboardMarkup(inline_keyboard=[
    [button_login], 
    [button_help],
])

change_item_menu = InlineKeyboardMarkup(inline_keyboard=[
    [button_change_first_url],
    [button_change_second_url],
    [button_change_min_price],
    [button_change_min_index],
    [button_change_nothing],
])

# Greeting message
greet = "Привет {name}, я бот, который поможет тебе следить за ценами на [omarket.kz](https://omarket.kz), Только тсс.... 🤫"

greet_again = "Привет еще раз {name}, я всё тот же бот, а ниже команды которые я умею 🧑‍💻:"

# Dictionaries to hold user data and state
user_items = {}
user_states = {}
user_login_status = {}
pagination_data = {}
user_sleep_durations = {}


def item_exists(user_id, url):
    items = user_items.get(user_id, [])
    return any(url in [item['first_url'], item['second_url']] for item in items)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    formatted_greet = greet.format(name=message.from_user.full_name)
    markup = login_menu
    user_id = message.from_user.id
    if user_id in user_login_status:
        markup = menu
    else:
        markup = login_menu
    await message.answer(formatted_greet, parse_mode='Markdown', reply_markup=markup)

@dp.message(Command("commands"))
async def cmd_start(message: Message):
    formatted_greet = greet_again.format(name=message.from_user.full_name)
    user_id = message.from_user.id
    if user_id in user_login_status:
        await message.answer(formatted_greet, parse_mode='Markdown', reply_markup=menu)
    else:
        await message.answer("Пожалуйста сначала войдите в аккаунт:", reply_markup=login_menu)

async def start_change_process(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]["step"] = "waiting_for_change_selection"
    await message.answer("Что вы хотите изменить?", reply_markup=change_item_menu)

async def show_items(user_id: int, page: int = 0, search_query: str = None):
    items = user_items.get(user_id, [])
    if search_query:
        items = [item for item in items if search_query.lower() in item['first_url'].lower() or search_query.lower() in item['second_url'].lower()]

    pagination_data[user_id] = {
        'page': page,
        'search_query': search_query,
        'items': items
    }

    items_to_display = items[page * 3: (page + 1) * 3]
    if not items_to_display:
        await bot.send_message(user_id, "Товары не найдены.")
        return

    item_list = "\n".join([f"{i + 1 + page * 3}. Первый URL: {item['first_url']}\n"
                           f"Второй URL: {item['second_url']}\n"
                           f"Цена: {item['price']}\n"
                           f"Ваша минимальная цена: {item['min_price']}\n"
                           f"Пороговая цена на товар: {item['porog']}\n"
                           f"Минимальный индекс: {item.get('min_index', 'Не указан')}\n"
                           for i, item in enumerate(items_to_display)])

    navigation_buttons = []
    total_pages = (len(items) - 1) // 3 + 1
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{user_id}"))
        navigation_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data=f"do_nothing"))    

    if len(items) > (page + 1) * 3:
        navigation_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"next_{user_id}"))

    if navigation_buttons:
        navigation_markup = InlineKeyboardMarkup(inline_keyboard=[navigation_buttons, [button_go_to_page]])
        await bot.send_message(user_id, f"Ваши товары:\n{item_list}", reply_markup=navigation_markup)
    else:
        await bot.send_message(user_id, f"Ваши товары:\n{item_list}")

@dp.callback_query(lambda c: c.data == "do_nothing")
async def do_nothing_callback(callback_query: types.CallbackQuery):
    pass

@dp.callback_query(lambda c: c.data.startswith('next_'))
async def next_page(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])
    page = pagination_data[user_id]['page'] + 1
    search_query = pagination_data[user_id]['search_query']
    await callback_query.message.delete()
    await show_items(user_id, page, search_query)

@dp.callback_query(lambda c: c.data.startswith('prev_'))
async def prev_page(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split('_')[1])
    page = pagination_data[user_id]['page'] - 1
    search_query = pagination_data[user_id]['search_query']
    await callback_query.message.delete()
    await show_items(user_id, page, search_query)

@dp.callback_query(lambda c: c.data == "go_to_page")
async def go_to_page_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_states[user_id] = {"step": "awaiting_page_number"}
    await callback_query.message.delete()
    await bot.send_message(user_id, "Введите номер страницы, на которую хотите перейти:")

@dp.callback_query()
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    try:
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except:
        pass

    if data == "log_in":
        await callback_query.message.answer("Пожалуйста введите свою почту от аккаунта на Omarket:")
        user_states[user_id] = {"step": "waiting_for_account"}

    elif data == "change_first_url":
        await bot.answer_callback_query(callback_query.id)  # Acknowledge the callback
        await bot.send_message(user_id, "Введите новую первую ссылку:")
        user_states[user_id]["step"] = "waiting_for_new_first_url"

    elif data == "change_second_url":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(user_id, "Введите новую вторую ссылку:")
        user_states[user_id]["step"] = "waiting_for_new_second_url"

    elif data == "change_min_price":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(user_id, "Введите новую минимальную цену:")
        user_states[user_id]["step"] = "waiting_for_new_min_price"

    elif data == "change_min_index":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(user_id, "Введите новый минимальный индекс:")
        user_states[user_id]["step"] = "waiting_for_new_min_index"

    elif data == "change_nothing":
        message = "Хорошо {name}, хоть я и робот, я понимаю тебя 💁‍♂️. Посмотрим, что я еще могу тебе предложить...".format(name=message.from_user.full_name)
        await bot.send_message(user_id, message, parse_mode='Markdown', reply_markup=menu)

    elif data == "help":
        await callback_query.message.answer(
            "Этот бот помогает следить за ценами на товары в магазине Omarket.\n\n"
            "Вот доступные команды:\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение помощи\n"
            "/commands - Показать существующие команды\n"
            "Используйте кнопки в меню для добавления товаров и просмотра списка ваших товаров.\n\n"
            "Свяжитесь с @nurba_zh для любых вопросов."
        )
    
    elif user_login_status.get(user_id):
        if data == "add_item":
            await callback_query.message.answer("Введите первую ссылку = URL страницы товара:")
            user_states[user_id] = {"step": "waiting_for_first_url"}
        elif data == "my_items":
            items = user_items.get(user_id, [])
            if items:
                await show_items(user_id=user_id, page=0, search_query='')
            else:
                await callback_query.message.answer("Ваш список товаров пуст 😔.", reply_markup=menu)
        elif data == "remove_item":
            items = user_items.get(user_id, [])
            if items:
                await show_items(user_id=user_id, page=0, search_query='')
                await callback_query.message.answer("Введите номер товара, который хотите удалить:\n")
                user_states[user_id] = {"step": "waiting_for_remove_index"}
            else:
                await callback_query.message.answer("Ваш список товаров пуст 😔.", reply_markup=menu)
        elif data == "change_item":
            items = user_items.get(user_id, [])
            if items:
                await show_items(user_id=user_id, page=0, search_query='')
                await callback_query.message.answer("Введите номер товара или одну из двух ссылок, который хотите изменить:\n")
                user_states[user_id] = {"step": "waiting_for_change_item_selection"}
            else:
                await callback_query.message.answer("Ваш список товаров пуст 😔.", reply_markup=menu)

        await callback_query.answer()


@dp.message(Command("time"))
async def set_sleep_time(message: Message):
    user_id = message.from_user.id
    await message.answer("Введите количество секунд для задержки (например, '5' для 5 секунд):")
    user_states[user_id] = {"step": "waiting_for_sleep_duration"}
 
@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    if user_id in user_states:
        state = user_states[user_id]
        
        if state["step"] == "awaiting_page_number":
            page_input = message.text.strip()

            if page_input.isdigit():
                page_number = int(page_input) - 1
                items = user_items.get(user_id, [])
                
                if 0 <= page_number <= (len(items) // 3):
                    await message.delete()
                    await show_items(user_id, page=page_number)
                else:
                    await message.answer("Неверный номер страницы.")
            else:
                await message.answer("Пожалуйста, введите корректный номер страницы.")

            user_states.pop(user_id)

        if "last_message" not in state:
            state["last_message"] = None

        if state["step"] == "waiting_for_account":
            user_states[user_id]["account"] = message.text
            await message.answer("Введите теперь ваш пароль пожалуйста🙈🙈🙈:")
            state["step"] = "waiting_for_password"
        
        elif state["step"] == "waiting_for_password":
            user_states[user_id]["password"] = message.text
            await message.answer("Поздравляю со входом в аккаунт!", reply_markup=menu)
            user_login_status[user_id] = {"account": user_states[user_id]["account"], "password": user_states[user_id]["password"]}  
            user_states.pop(user_id)

        if state["step"] == "waiting_for_first_url":
            first_url = message.text
            if item_exists(user_id, first_url):
                await message.answer("Этот товар уже добавлен. Пожалуйста, введите другой товар.")
                state["step"] = ""
                return
            state["first_url"] = first_url
            last_message = await message.answer("Введите вторую ссылку = URL страницы изменения товара с вашего личного кабинета (P.S: где есть пороговая цена):")
            state["last_message"] = last_message 
            state["step"] = "waiting_for_second_url"  # Move to the next state
            
        elif state["step"] == "waiting_for_second_url":
            second_url = message.text
            if item_exists(user_id, second_url):
                await message.answer("Этот товар уже добавлен. Пожалуйста, введите другой товар.")
                state["step"] = ""
                return
            state["second_url"] = second_url
            if state["last_message"]:
                await state["last_message"].delete()
            last_message = await message.answer("Ага, записал. Интересный товар! А теперь, введите вашу МИНИМАЛЬНУЮ цену товара, ниже которой вы продавать не будете. Мы же все таки здесь, чтобы заработать 💵:")
            state["last_message"] = last_message
            state["step"] = "waiting_for_min_price"  # Move to the next state
        
        elif state["step"] == "waiting_for_min_price":
            try:
                state["min_price"] = int(message.text)
                if state["last_message"]:
                    await state["last_message"].delete()
                last_message = await message.answer("У какого по счету продавца смотреть минимальную цену? <i>(обычно это первый, но вдруг тут чел будет продавать за 5 тг, и с ним нет смысла бороться):</i>", parse_mode='HTML')
                state["last_message"] = last_message
                state["step"] = "waiting_for_minimal_index"  # Move to the next state
            except ValueError:
                state["last_message"] = None
                await message.answer("Пожалуйста, введите корректную цену.")
                
        elif state["step"] == "waiting_for_minimal_index":
            try:
                state["min_index"] = int(message.text)
                
                if state["last_message"] and state["last_message"] != None:
                    await state["last_message"].delete()
                else:
                    print("nothing")    

                loading_message = await message.answer("Загрузка цены... Пожалуйста, подождите примерно 5 секунд. ⏳")
                
                price_and_porog = get_data_from_last_script(
                    user_login_status[user_id]["account"],
                    user_login_status[user_id]["password"],
                    state["second_url"], state["first_url"], 
                    state["min_index"]
                )
                 
                if user_id not in user_items:
                    user_items[user_id] = []
                
                await loading_message.delete()

                user_items[user_id].append({
                    "first_url": state["first_url"], 
                    "second_url": state["second_url"], 
                    "min_price": int(state["min_price"]), 
                    "min_price_possible": int(price_and_porog["Минимальная цена"]) + 1, 
                    "price": int(price_and_porog["Минимальная цена"]), 
                    "porog": price_and_porog["Пороговая цена для товара"], 
                    "min_index": state["min_index"],
                })
                
                await message.answer(f"Товар добавлен. \nПервый URL: {state['first_url']}\n" 
                    + f"Второй URL: {state['second_url']}\n" 
                    + f"Ваша минимальная цена: {state['min_price']}\n"
                    + f"Цена: {price_and_porog['Минимальная цена']}\n"
                    + f"Пороговая цена на товар: {price_and_porog['Пороговая цена для товара']}\n"
                    + f"Минимальный индекс: {state.get('min_index', 'Не указан')}", reply_markup=menu)
                user_states.pop(user_id) 
                
            except ValueError:
                state["last_message"] = None
                await message.answer("Пожалуйста, введите корректный номер продавца (число).")
                
        elif state["step"] == "waiting_for_change_index":
            try:
                index = int(message.text) - 1
                items = user_items.get(user_id, [])
                if 0 <= index < len(items):
                    shown_item = items[index]
                    await message.answer(f"Вот ваш товар. \nПервый URL: {shown_item['first_url']}\n" 
                    + f"Второй URL: {shown_item['second_url']}\n" 
                    + f"Ваша минимальная цена: {shown_item['min_price']}\n"
                    + f"Пороговая цена на товар: {shown_item['porog']}\n"
                    + f"Минимальный индекс: {shown_item.get('min_index', 'Не указан')}", reply_markup=menu)
                else:
                    await message.answer("Неправильный номер товара. Пожалуйста, попробуйте снова.")
                user_states.pop(user_id)  # Clear state after handling change
            except ValueError:
                await message.answer("Пожалуйста, введите корректный номер товара.")
                
        elif state["step"] == "waiting_for_remove_index":
            try:
                index = int(message.text) - 1
                items = user_items.get(user_id, [])
                if 0 <= index < len(items):
                    removed_item = items.pop(index)
                    await message.answer(f"Попрощайтесь с товаром ниже, вы его удалили 💀. \nПервый URL: {removed_item['first_url']}\n" 
                    + f"Второй URL: {removed_item['second_url']}\n" 
                    + f"Ваша минимальная цена: {removed_item['min_price']}\n"
                    + f"Пороговая цена на товар: {removed_item['porog']}\n"
                    + f"Минимальный индекс: {removed_item.get('min_index', 'Не указан')}", reply_markup=menu)
                else:
                    await message.answer("Неправильный номер товара. Пожалуйста, попробуйте снова.")
                user_states.pop(user_id)  # Clear state after handling remove
            except ValueError:
                await message.answer("Пожалуйста, введите корректный номер товара.")

        if state["step"] == "waiting_for_change_item_selection":
            items = user_items.get(user_id, [])
            user_input = message.text

            # Try to match by URL first
            selected_item = next((item for item in items if item["first_url"] == user_input or item["second_url"] == user_input), None)
            
            # If not matched by URL, try by index number
            if selected_item is None:
                try:
                    index = int(user_input) - 1
                    if 0 <= index < len(items):
                        selected_item_index = index
                    else:
                        await message.answer("Неверный номер товара. Пожалуйста, попробуйте снова.")
                        return
                except ValueError:
                    await message.answer("Неверный ввод. Пожалуйста, введите корректную ссылку или номер товара.")
                    return

            state['last_selected_index'] = selected_item_index
            await start_change_process(message)  
        
        # Process changes for each selected field
        elif state["step"] == "waiting_for_new_first_url":
            last_selected_index = state.get('last_selected_index')
            user_items[user_id][last_selected_index]["first_url"] = message.text
            await message.answer("Первая ссылка успешно обновлена!", reply_markup=menu)
            user_states.pop(user_id)

        elif state["step"] == "waiting_for_new_second_url":
            last_selected_index = state.get('last_selected_index')
            user_items[user_id][last_selected_index]["second_url"] = message.text
            await message.answer("Вторая ссылка успешно обновлена!", reply_markup=menu)
            user_states.pop(user_id)

        elif state["step"] == "waiting_for_new_min_price":
            try:
                new_price = int(message.text)
                last_selected_index = state.get('last_selected_index')
                user_items[user_id][last_selected_index]["min_price"] = new_price
                await message.answer(f"Ваша минимальная цена успешно обновлена на {new_price}!", reply_markup=menu)
                user_states.pop(user_id)
            except ValueError:
                await message.answer("Пожалуйста, введите корректное число для цены.")

        elif state["step"] == "waiting_for_new_min_index":
            try:
                new_index = int(message.text)
                last_selected_index = state.get('last_selected_index')
                user_items[user_id][last_selected_index]["min_index"] = new_index
                await message.answer(f"Минимальный индекс успешно обновлён на {new_index}!", reply_markup=menu)
                user_states.pop(user_id)
            except ValueError:
                await message.answer("Пожалуйста, введите корректное число для индекса.")  

        if state["step"] == "waiting_for_sleep_duration":
            try:
                # Get the user-defined sleep duration
                sleep_duration = int(message.text.strip())
                user_sleep_durations[user_id] = sleep_duration
                await message.answer(f"Время задержки установлено на {sleep_duration} секунд.")
                user_states.pop(user_id)
            except ValueError:
                await message.answer("Пожалуйста, введите число для задержки (в секундах).")
              
    else:
        markup = login_menu
        user_id = message.from_user.id
        if user_id in user_login_status:
            markup = menu
        else:
            markup = login_menu
        await message.answer("Я не понимаю это сообщение. Пожалуйста, используйте меню для взаимодействия со мной.", reply_markup=markup)

async def check_prices():
    while True:
        counter = 0
        print(user_id, items)
        for user_id, items in user_items.items():
            for item in items:
                if counter%10 == 0:
                    print(counter, "\n")
                current_price = get_price(
                    user_login_status[user_id]["account"], 
                    user_login_status[user_id]["password"], 
                    item["second_url"], 
                    item["first_url"], 
                    item["min_index"]
                )
                counter += 1
                if isinstance(current_price, (int, float)) and current_price < item["min_price_possible"]:
                    if (current_price - 1 < item["min_price"]):
                        await bot.send_message(user_id, f"Цена на товар {item['first_url']} снизилась до {current_price}! но она ниже, чем наша минимальная цена, и я не буду обновлять ее")
                        item["min_price_possible"] = current_price
                    else:
                        change_price(user_login_status[user_id]["account"], user_login_status[user_id]["password"], item["second_url"], current_price - 1)
                        if isinstance(item["porog"], (int, float)) and current_price - 1 < int(item["porog"]):
                            await bot.send_message(user_id, f"Цена на товар {item['first_url']} снизилась до {current_price}! Обновляем цену на {current_price - 1}. НО ОНА НИЖЕ ПОРОГОВОЙ - {item['porog']}")
                            item["min_price_possible"] = current_price - 1 
                        else:  
                            await bot.send_message(user_id, f"Цена на товар {item['first_url']} снизилась до {current_price}! Обновляем цену на {current_price - 1}.")
                            item["min_price_possible"] = current_price - 1 
                # elif isinstance(current_price, (int, float)) and current_price > item["min_price_possible"]:    
                #     print('here2')
                #     if (item["min_price"] - current_price > 0):
                #         await bot.send_message(user_id, f"Цена на товар {item['first_url']} поднялась до {current_price}! но она ниже, чем наша минимальная цена, и я не буду обновлять ее")
                #         item["min_price_possible"] = current_price
                #     elif (item["min_price"] - current_price < 0):
                #         if isinstance(item["porog"], (int, float)) and current_price - 1 < int(item["porog"]):
                #             await bot.send_message(user_id, f"Цена на товар {item['first_url']} поднялась до {current_price}! Обновляем цену на {current_price - 1}. НО ОНА НИЖЕ ПОРОГОВОЙ - {item['porog']}")
                #             item["min_price_possible"] = current_price - 1 
                #         else:    
                #             await bot.send_message(user_id, f"Цена на товар {item['first_url']} поднялась до {current_price}! Обновляем цену на {current_price - 1}.")
                #             item["min_price_possible"] = current_price - 1 

        new_sleep_duration = user_sleep_durations.get(user_id, sleep_duration)
        await asyncio.sleep(new_sleep_duration)


def start_check_prices():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(check_prices())
    loop.close()

async def main():
    executor.submit(start_check_prices)
    # Start the bot polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
