import telebot
from telebot import types 
from config import * 
from logic import DB_Map 
import os 

if not TOKEN:
    raise ValueError("Необходимо установить TOKEN в config.py")
if not DATABASE:
    raise ValueError("Необходимо установить DATABASE в config.py")

bot = telebot.TeleBot(TOKEN)
manager = DB_Map(DATABASE)
manager.create_user_settings_table()

CALLBACK_PREFIX_DELETE_CITY = "del_city_"
CALLBACK_PREFIX_COLOR_CHOICE = "set_color_"

MARKER_COLORS = {
    "Красный ❤️": "red",
    "Синий 💙": "blue",
    "Зеленый 💚": "green",
    "Фиолетовый 💜": "purple",
    "Оранжевый 🧡": "orange",
    "Черный ⚫": "black"
}

def get_city_name_from_args(message_text, command_name):
    try:
        return message_text.split(f'/{command_name}', 1)[1].strip()
    except IndexError:
        return None

def create_cities_inline_keyboard(user_id, prefix):
    cities = manager.select_cities(user_id)
    markup = types.InlineKeyboardMarkup(row_width=1) 
    
    if not cities:
        return None

    buttons = []
    for city_name in cities:
        buttons.append(types.InlineKeyboardButton(text=f"❌ {city_name}", 
                                                  callback_data=f"{prefix}{city_name}"))
    markup.add(*buttons)
    return markup

def create_color_inline_keyboard(prefix):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for display_name, color_code in MARKER_COLORS.items():
        buttons.append(types.InlineKeyboardButton(text=display_name, callback_data=f"{prefix}{color_code}"))
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.send_message(message.chat.id, "👋 Привет! Я бот, который может показывать города на карте. Напиши /help для списка команд.")

@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = (
        "📚 Доступные команды:\n"
        "/start - Приветствие\n"
        "/help - Показать это сообщение\n"
        "/remember_city <НазваниеГорода> - Сохранить город в твой список (пиши на английском, например, New York).\n"
        "/show_city <НазваниеГорода> - Показать карту с указанным городом (на английском).\n"
        "/show_my_cities - Показать карту со всеми твоими сохраненными городами.\n"
        "/delete_my_city - Удалить город из списка сохраненных.\n"
        "/set_marker_color - Выбрать цвет маркеров на карте."
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['show_city'])
def handle_show_city(message):
    city_name = get_city_name_from_args(message.text, 'show_city')
    
    if not city_name:
        bot.send_message(message.chat.id, "❓ Пожалуйста, укажи название города после команды. Например: /show_city London")
        return

    if not manager.get_coordinates(city_name):
        bot.send_message(message.chat.id, f"🤷 Город '{city_name}' не найден в моей базе. Убедись, что он написан на английском!")
        return
    
    status_message = bot.send_message(message.chat.id, f"🗺️ Генерирую карту для города {city_name}... Это может занять несколько секунд.")
    
    image_path = f"map_{message.chat.id}_{city_name.replace(' ', '_')}.png"
    
    user_marker_color = manager.get_user_marker_color(message.chat.id)

    if manager.create_grapf(image_path, [city_name], marker_color=user_marker_color):
        try:
            with open(image_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=f"✅ Карта для города: {city_name}")
        except Exception as e:
            print(f"Ошибка при отправке фото {image_path}: {e}")
            bot.send_message(message.chat.id, "❌ Произошла ошибка при отправке карты.")
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)
        bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)
    else:
        bot.edit_message_text(f"❌ Не удалось сгенерировать карту для города '{city_name}'. Возможно, для него нет координатных данных в базе.",
                              chat_id=status_message.chat.id, message_id=status_message.message_id)


@bot.message_handler(commands=['remember_city'])
def handle_remember_city(message):
    user_id = message.chat.id
    city_name = get_city_name_from_args(message.text, 'remember_city')

    if not city_name:
        bot.send_message(message.chat.id, "❓ Пожалуйста, укажи название города после команды. Например: /remember_city Paris")
        return
    
    result = manager.add_city(user_id, city_name)
    if result == 1:
        bot.send_message(message.chat.id, f'✅ Город {city_name} успешно сохранен!')
    elif result == 2:
        bot.send_message(message.chat.id, f'ℹ️ Город {city_name} уже был сохранен ранее.')
    else:
        bot.send_message(message.chat.id, f'🤷 Город "{city_name}" не найден в моей базе. Убедись, что он написан на английском!')

@bot.message_handler(commands=['show_my_cities'])
def handle_show_my_cities(message):
    user_id = message.chat.id
    cities = manager.select_cities(user_id)

    if not cities:
        bot.send_message(message.chat.id, "😞 Ты еще не сохранил ни одного города. Используй команду /remember_city <НазваниеГорода>.")
        return
    
    status_message = bot.send_message(message.chat.id, "🌍 Генерирую карту для всех твоих сохраненных городов... Это может занять несколько секунд.")

    image_path = f"map_{user_id}_my_cities.png"
    
    user_marker_color = manager.get_user_marker_color(message.chat.id)

    if manager.create_grapf(image_path, cities, marker_color=user_marker_color):
        try:
            with open(image_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption="✅ Карта твоих сохраненных городов")
        except Exception as e:
            print(f"Ошибка при отправке фото {image_path}: {e}")
            bot.send_message(message.chat.id, "❌ Произошла ошибка при отправке карты.")
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)
        bot.delete_message(chat_id=status_message.chat.id, message_id=status_message.message_id)
    else:
        bot.edit_message_text("❌ Не удалось сгенерировать карту. Возможно, для сохраненных городов нет данных.",
                              chat_id=status_message.chat.id, message_id=status_message.message_id)

@bot.message_handler(commands=['delete_my_city'])
def command_delete_my_city(message):
    user_id = message.chat.id
    markup = create_cities_inline_keyboard(user_id, CALLBACK_PREFIX_DELETE_CITY)
    if markup:
        bot.send_message(user_id, "🗑️ Выбери город, который хочешь удалить из списка:", reply_markup=markup)
    else:
        bot.send_message(user_id, "🗑️ У тебя нет сохраненных городов для удаления.")

@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PREFIX_DELETE_CITY))
def callback_delete_city(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    chat_id = call.message.chat.id

    city_to_delete = call.data[len(CALLBACK_PREFIX_DELETE_CITY):]

    if manager.delete_city_from_user_list(user_id, city_to_delete):
        bot.answer_callback_query(call.id, text=f"✅ Город {city_to_delete} удален.")
        
        new_markup = create_cities_inline_keyboard(user_id, CALLBACK_PREFIX_DELETE_CITY)
        if new_markup:
            try:
                bot.edit_message_text("🗑️ Список обновлен. Выбери следующий город для удаления:",
                                      chat_id=chat_id,
                                      message_id=message_id,
                                      reply_markup=new_markup)
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e).lower():
                    pass 
                else:
                    print(f"Ошибка при редактировании сообщения: {e}") 
        else:
            bot.edit_message_text("✨ Все сохраненные города удалены.",
                                  chat_id=chat_id,
                                  message_id=message_id,
                                  reply_markup=None) 
    else:
        bot.answer_callback_query(call.id, text=f"❌ Не удалось удалить {city_to_delete}. Возможно, он уже был удален.", show_alert=True)
        current_markup = create_cities_inline_keyboard(user_id, CALLBACK_PREFIX_DELETE_CITY)
        if current_markup:
             bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=current_markup)
        else:
             bot.edit_message_text("🗑️ Нет городов для удаления.", chat_id=chat_id, message_id=message_id, reply_markup=None)

@bot.message_handler(commands=['set_marker_color'])
def command_set_marker_color(message):
    markup = create_color_inline_keyboard(CALLBACK_PREFIX_COLOR_CHOICE)
    current_color = manager.get_user_marker_color(message.chat.id)
    current_color_display = next((name for name, code in MARKER_COLORS.items() if code == current_color), current_color)
    bot.send_message(message.chat.id, f"🎨 Выбери цвет для маркеров на карте. Текущий цвет: {current_color_display}.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(CALLBACK_PREFIX_COLOR_CHOICE))
def callback_set_marker_color(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    chat_id = call.message.chat.id

    chosen_color_code = call.data[len(CALLBACK_PREFIX_COLOR_CHOICE):]
    
    if chosen_color_code not in MARKER_COLORS.values():
        bot.answer_callback_query(call.id, text="⚠️ Неизвестный цвет.", show_alert=True)
        return

    manager.set_user_marker_color(user_id, chosen_color_code)
    
    chosen_color_display = next((name for name, code in MARKER_COLORS.items() if code == chosen_color_code), chosen_color_code)

    bot.answer_callback_query(call.id, text=f"✅ Цвет маркеров установлен на {chosen_color_display}.")
    
    try:
        bot.edit_message_text(f"🎨 Цвет маркеров успешно установлен на {chosen_color_display}.",
                              chat_id=chat_id,
                              message_id=message_id,
                              reply_markup=None)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            print(f"Ошибка при редактировании сообщения: {e}")


if __name__=="__main__":
    print("Бот запускается...")
    bot.polling(none_stop=True)