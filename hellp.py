import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройки
BOT_TOKEN = "8371672396:AAFbLOfBkm0Q2L31tDSCPhM3jo_59_O2D7s"
ADMIN_IDS = [7908573959]  # Сюда добавьте ID администраторов (например, [123456789, 987654321])

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранение данных о мутах
user_mutes = {}

# Свободные айулауд аккаунты (пример данных)
available_accounts = [
    {"id": 1, "username": "account1", "status": "свободен"},
    {"id": 2, "username": "account2", "status": "свободен"},
    {"id": 3, "username": "account3", "status": "занят"},
    {"id": 4, "username": "account4", "status": "свободен"},
]

# ========== КОМАНДА /rules ==========
@dp.message(Command("rules"))
async def cmd_rules(message: Message):
    rules_text = """⛔️ Правила поведения в чате

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

👨‍💼 Администраторы:
• cfg (https://t.me/cfgsp)
• angelmaycry (https://t.me/gothboyclicue)
• wheres (https://t.me/ghoul_001)

🧰 Отработка логов:
• plague (https://t.me/Plag1ue)
• cfg (https://t.me/cfgsp)"""
    
    await message.answer(rules_text)

# ========== КОМАНДА /mute ==========
@dp.message(Command("mute"))
async def cmd_mute(message: Message):
    # Проверка прав администратора
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("⛔ У вас нет прав для использования этой команды!")
        return
    
    # Проверка что команда ответ на сообщение
    if not message.reply_to_message:
        await message.reply("⚠️ Команда должна быть отправлена в ответ на сообщение пользователя!")
        return
    
    target_user = message.reply_to_message.from_user
    command_parts = message.text.split()
    
    if len(command_parts) < 3:
        await message.reply("❌ Неправильный формат!\nИспользуйте: /mute <время> <причина>\nПример: /mute 1h спам")
        return
    
    time_str = command_parts[1].lower()
    reason = " ".join(command_parts[2:])
    
    # Парсинг времени
    try:
        if time_str.endswith('m'):  # минуты
            minutes = int(time_str[:-1])
            mute_duration = timedelta(minutes=minutes)
        elif time_str.endswith('h'):  # часы
            hours = int(time_str[:-1])
            mute_duration = timedelta(hours=hours)
        elif time_str.endswith('d'):  # дни
            days = int(time_str[:-1])
            mute_duration = timedelta(days=days)
        else:
            minutes = int(time_str)
            mute_duration = timedelta(minutes=minutes)
    except ValueError:
        await message.reply("❌ Неверный формат времени!\nИспользуйте: 30m, 1h, 2d или просто число (в минутах)")
        return
    
    mute_until = datetime.now() + mute_duration
    
    # Сохраняем информацию о муте
    user_mutes[target_user.id] = {
        'until': mute_until,
        'reason': reason,
        'admin': message.from_user.username or message.from_user.id
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
        mute_message = f"""
🔇 Пользователь @{target_user.username or target_user.id} получил мут!
⏰ Срок: {time_str}
📝 Причина: {reason}
👮‍♂️ Администратор: @{message.from_user.username or message.from_user.id}
🕐 Мут действует до: {mute_until.strftime('%d.%m.%Y %H:%M')}
        """
        await message.reply(mute_message)
        
    except Exception as e:
        logger.error(f"Ошибка при выдаче мута: {e}")
        await message.reply("❌ Произошла ошибка при выдаче мута")

# ========== КОМАНДА /unmute ==========
@dp.message(Command("unmute"))
async def cmd_unmute(message: Message):
    # Проверка прав администратора
    if message.from_user.id not in ADMIN_IDS:
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
        unmute_message = f"""
🔊 Пользователь @{target_user.username or target_user.id} размучен!
👮‍♂️ Администратор: @{message.from_user.username or message.from_user.id}
        """
        await message.reply(unmute_message)
        
    except Exception as e:
        logger.error(f"Ошибка при снятии мута: {e}")
        await message.reply("❌ Произошла ошибка при снятии мута")

# ========== КОМАНДА /check ==========
@dp.message(Command("check"))
async def cmd_check(message: Message):
    # Проверка прав администратора
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("⛔ У вас нет прав для использования этой команды!")
        return
    
    # Фильтруем свободные аккаунты
    free_accounts = [acc for acc in available_accounts if acc["status"] == "свободен"]
    
    if not free_accounts:
        response = "❌ Нет свободных айулауд аккаунтов."
    else:
        response = "✅ Свободные айулауд аккаунты:\n\n"
        for acc in free_accounts:
            response += f"• ID: {acc['id']}\n"
            response += f"  Имя: {acc['username']}\n"
            response += f"  Статус: {acc['status']}\n\n"
    
    await message.reply(response)

# ========== ПРОВЕРКА МУТОВ ПРИ НАПИСАНИИ СООБЩЕНИЯ ==========
@dp.message()
async def check_mute(message: Message):
    user_id = message.from_user.id
    
    if user_id in user_mutes:
        mute_info = user_mutes[user_id]
        
        # Проверяем не истек ли мут
        if datetime.now() >= mute_info['until']:
            # Мут истек, удаляем
            del user_mutes[user_id]
        else:
            # Пользователь в муте, удаляем его сообщение
            try:
                await message.delete()
                
                # Информируем пользователя (если возможно)
                try:
                    time_left = mute_info['until'] - datetime.now()
                    hours_left = time_left.total_seconds() // 3600
                    minutes_left = (time_left.total_seconds() % 3600) // 60
                    
                    warning = f"""
⛔ Вы в муте!
⏰ Причина: {mute_info['reason']}
⏳ Осталось времени: {int(hours_left)}ч {int(minutes_left)}м
👮‍♂️ Администратор: {mute_info['admin']}
                    """
                    
                    await bot.send_message(
                        chat_id=user_id,
                        text=warning
                    )
                except:
                    pass  # Не смогли отправить сообщение пользователю
                    
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
    await bot.set_my_commands(commands)

# ========== ЗАПУСК БОТА ==========
async def main():
    await setup_bot_commands()
    logger.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
