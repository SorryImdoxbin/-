import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode

# Настройки
BOT_TOKEN = "8371672396:AAFAVqP2zruJp1_WkDDYQCsr5Oehit3cMPk"  # <-- ВАЖНО: замените на реальный токен!
# ADMIN_IDS удалено - теперь будем проверять права через Telegram API

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранение данных о мутах
user_mutes: Dict[int, Dict[str, Any]] = {}

# Свободные айулауд аккаунты (пример данных)
available_accounts = [
    {"id": 1, "username": "account1", "status": "свободен"},
    {"id": 2, "username": "account2", "status": "свободен"},
    {"id": 3, "username": "account3", "status": "занят"},
    {"id": 4, "username": "account4", "status": "свободен"},
]

async def is_admin(user_id: int, chat_id: int) -> bool:
    """Проверяет, является ли пользователь администратором чата"""
    try:
        chat_member = await bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ["creator", "administrator"]
    except Exception as e:
        logger.error(f"Ошибка при проверке прав: {e}")
        return False

# ========== КОМАНДА /rules ==========
@dp.message(Command("rules"))
async def cmd_rules(message: Message):
    rules_text = """⛔️ <b>Правила поведения в чате</b>

1. Запрещена дискриминация.
2. Запрещена реклама без согласования.
3. Запрещён перелив трафика.
4. Запрещена ложная информация.
5. Запрещён 18+ / жесть.
6. Запрещено обсуждение наркотиков и оружия.
7. Мошенничество = бан.
8. Сделки на свой страх и риск.
9. Конфликт = мут всем.
10. Запрещены массовые упоминания.
11. Запрещено распространять личную инфу.
12. Запрещено прикидываться админами.
13. Репорт багов обязателен.
14. Вредоносы запрещены.

👨‍💼 <b>Администраторы:</b>
• onion_kroky (https://t.me/onion_kroky)

🧰 <b>Отработка логов:</b>
• onion_kroky (https://t.me/onion_kroky)"""
    
    await message.answer(rules_text, parse_mode=ParseMode.HTML)

# ========== КОМАНДА /mute ==========
@dp.message(Command("mute"))
async def cmd_mute(message: Message):
    # Проверка что команда в группе/супергруппе
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("⚠️ Эта команда работает только в группах!")
        return
    
    # Проверка прав администратора через Telegram API
    if not await is_admin(message.from_user.id, message.chat.id):
        await message.reply("⛔ У вас нет прав для использования этой команды!")
        return
    
    # Проверка что команда ответ на сообщение
    if not message.reply_to_message:
        await message.reply("⚠️ Команда должна быть отправлена в ответ на сообщение пользователя!\n\nИспользуйте: <code>/mute 1h спам</code>", parse_mode=ParseMode.HTML)
        return
    
    target_user = message.reply_to_message.from_user
    command_parts = message.text.split()
    
    if len(command_parts) < 3:
        await message.reply("❌ Неправильный формат!\n\nИспользуйте: <code>/mute &lt;время&gt; &lt;причина&gt;</code>\n\nПример: <code>/mute 1h спам</code>\nДоступно: 30m, 1h, 2d", parse_mode=ParseMode.HTML)
        return
    
    time_str = command_parts[1].lower()
    reason = " ".join(command_parts[2:])
    
    # Парсинг времени
    try:
        if time_str.endswith('m'):  # минуты
            minutes = int(time_str[:-1])
            mute_duration = timedelta(minutes=minutes)
            time_display = f"{minutes} мин."
        elif time_str.endswith('h'):  # часы
            hours = int(time_str[:-1])
            mute_duration = timedelta(hours=hours)
            time_display = f"{hours} час."
        elif time_str.endswith('d'):  # дни
            days = int(time_str[:-1])
            mute_duration = timedelta(days=days)
            time_display = f"{days} дн."
        else:
            minutes = int(time_str)
            mute_duration = timedelta(minutes=minutes)
            time_display = f"{minutes} мин."
    except ValueError:
        await message.reply("❌ Неверный формат времени!\n\nИспользуйте: <code>30m</code> (минуты), <code>1h</code> (часы), <code>2d</code> (дни)", parse_mode=ParseMode.HTML)
        return
    
    # Проверяем, что время не слишком большое
    if mute_duration > timedelta(days=366):
        await message.reply("❌ Слишком большой срок мута! Максимум 366 дней.")
        return
    
    mute_until = datetime.now() + mute_duration
    
    # Сохраняем информацию о муте
    user_mutes[target_user.id] = {
        'until': mute_until,
        'reason': reason,
        'admin': message.from_user.username or f"ID: {message.from_user.id}",
        'chat_id': message.chat.id
    }
    
    # Ограничиваем права пользователя
    try:
        until_timestamp = int(mute_until.timestamp())
        permissions = types.ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            permissions=permissions,
            until_date=until_timestamp
        )
        
        # Уведомление в чат
        target_name = f"@{target_user.username}" if target_user.username else f"Пользователь (ID: {target_user.id})"
        admin_name = f"@{message.from_user.username}" if message.from_user.username else f"Админ (ID: {message.from_user.id})"
        
        mute_message = f"""
🔇 <b>Пользователь получил мут!</b>

👤 {target_name}
⏰ <b>Срок:</b> {time_display}
📝 <b>Причина:</b> {reason}
👮‍♂️ <b>Администратор:</b> {admin_name}
🕐 <b>Мут до:</b> {mute_until.strftime('%d.%m.%Y %H:%M')}
        """
        await message.reply(mute_message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Ошибка при выдаче мута: {e}")
        await message.reply(f"❌ Произошла ошибка: {str(e)}")

# ========== КОМАНДА /unmute ==========
@dp.message(Command("unmute"))
async def cmd_unmute(message: Message):
    # Проверка что команда в группе/супергруппе
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("⚠️ Эта команда работает только в группах!")
        return
    
    # Проверка прав администратора через Telegram API
    if not await is_admin(message.from_user.id, message.chat.id):
        await message.reply("⛔ У вас нет прав для использования этой команды!")
        return
    
    # Проверка что команда ответ на сообщение
    if not message.reply_to_message:
        await message.reply("⚠️ Команда должна быть отправлена в ответ на сообщение пользователя!")
        return
    
    target_user = message.reply_to_message.from_user
    
    # Восстанавливаем права пользователя
    try:
        permissions = types.ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            permissions=permissions
        )
        
        # Удаляем информацию о муте
        if target_user.id in user_mutes:
            del user_mutes[target_user.id]
        
        # Уведомление в чат
        target_name = f"@{target_user.username}" if target_user.username else f"Пользователь (ID: {target_user.id})"
        admin_name = f"@{message.from_user.username}" if message.from_user.username else f"Админ (ID: {message.from_user.id})"
        
        unmute_message = f"""
🔊 <b>Пользователь размучен!</b>

👤 {target_name}
👮‍♂️ <b>Администратор:</b> {admin_name}
        """
        await message.reply(unmute_message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Ошибка при снятии мута: {e}")
        await message.reply(f"❌ Произошла ошибка: {str(e)}")

# ========== КОМАНДА /check ==========
@dp.message(Command("check"))
async def cmd_check(message: Message):
    # Проверка прав администратора через Telegram API
    if not await is_admin(message.from_user.id, message.chat.id):
        await message.reply("⛔ У вас нет прав для использования этой команды!")
        return
    
    # Фильтруем свободные аккаунты
    free_accounts = [acc for acc in available_accounts if acc["status"] == "свободен"]
    
    if not free_accounts:
        response = "❌ <b>Нет свободных айулауд аккаунтов.</b>"
    else:
        response = "✅ <b>Свободные айулауд аккаунты:</b>\n\n"
        for acc in free_accounts:
            response += f"• <b>ID:</b> {acc['id']}\n"
            response += f"  <b>Имя:</b> {acc['username']}\n"
            response += f"  <b>Статус:</b> {acc['status']}\n\n"
    
    await message.reply(response, parse_mode=ParseMode.HTML)

# ========== ПРОВЕРКА МУТОВ ПРИ НАПИСАНИИ СООБЩЕНИЯ ==========
@dp.message()
async def check_mute(message: Message):
    # Пропускаем команды и сообщения в личных чатах
    if message.chat.type == "private" or message.text.startswith('/'):
        return
    
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Проверяем есть ли мут для этого пользователя в этом чате
    if user_id in user_mutes:
        mute_info = user_mutes[user_id]
        
        # Проверяем что мут для этого чата
        if mute_info.get('chat_id') != chat_id:
            return
        
        # Проверяем не истек ли мут
        if datetime.now() >= mute_info['until']:
            # Мут истек, удаляем
            del user_mutes[user_id]
            return
        
        # Пользователь в муте, удаляем его сообщение
        try:
            await message.delete()
            
            # Информируем пользователя (если возможно)
            try:
                time_left = mute_info['until'] - datetime.now()
                hours_left = time_left.total_seconds() // 3600
                minutes_left = (time_left.total_seconds() % 3600) // 60
                
                warning = f"""
⛔ <b>Вы в муте!</b>

📝 <b>Причина:</b> {mute_info['reason']}
⏳ <b>Осталось времени:</b> {int(hours_left)}ч {int(minutes_left)}м
👮‍♂️ <b>Администратор:</b> {mute_info['admin']}
                """
                
                await bot.send_message(
                    chat_id=user_id,
                    text=warning,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.debug(f"Не удалось отправить сообщение пользователю: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения: {e}")

# ========== ФУНКЦИЯ ДЛЯ ДОБАВЛЕНИЯ БОТА В ГРУППУ ==========
async def setup_bot_commands():
    commands = [
        types.BotCommand(command="/rules", description="Показать правила чата"),
        types.BotCommand(command="/mute", description="Выдать мут пользователю"),
        types.BotCommand(command="/unmute", description="Снять мут с пользователя"),
        types.BotCommand(command="/check", description="Проверить свободные аккаунты"),
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Команды бота установлены")
    except Exception as e:
        logger.error(f"Ошибка при установке команд: {e}")

# ========== ЗАПУСК БОТА ==========
async def main():
    try:
        # Проверяем токен бота
        bot_info = await bot.get_me()
        logger.info(f"Бот запущен: @{bot_info.username} ({bot_info.id})")
        
        await setup_bot_commands()
        logger.info("Бот готов к работе!")
        
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
