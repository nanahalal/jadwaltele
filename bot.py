import logging
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from typing import List, Dict

# Konfigurasi log
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Token Bot
BOT_TOKEN = '7204772490:AAG7iQf2O05b5Lu7W3ISCbf5Np1z91OD-Tg'

# ID Grup
GROUP_IDS = [-1001266140927, -1001337513198]

# Penyimpanan tugas
tasks: Dict[str, Dict[str, Dict[str, List[str]]]] = {}

# Inisialisasi scheduler
scheduler = BackgroundScheduler()
scheduler.start()

def start(update: Update, context: CallbackContext):
    """Handle the /start command."""
    update.message.reply_text("Selamat datang! Gunakan /addtask untuk menambahkan tugas.")

def add_task(update: Update, context: CallbackContext):
    """Handle the /addtask command."""
    if len(context.args) < 2:
        update.message.reply_text("Gunakan format: /addtask <deskripsi_tugas> <username1> <username2> ...")
        return

    task_description = context.args[0]
    usernames = context.args[1:]

    # Simpan tugas
    tasks[task_description] = {
        "assigned": usernames,
        "completed": []
    }

    for group_id in GROUP_IDS:
        context.bot.send_message(
            chat_id=group_id,
            text=f"Tugas '{task_description}' telah ditambahkan untuk {', '.join(usernames)}. "
                 "Silakan klik tombol di bawah ini untuk menyelesaikan atau mengingatkan pengguna.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Ingatkan 30 menit lagi", callback_data=f"remind_{task_description}_{update.message.from_user.username}")],
                [InlineKeyboardButton("Sudah menyelesaikan", callback_data=f"complete_{task_description}_{update.message.from_user.username}")]
            ])
        )

def button(update: Update, context: CallbackContext):
    """Handle button presses."""
    query = update.callback_query
    data = query.data.split('_')
    action, task_description, username = data[0], data[1], data[2]

    if action == "remind":
        # Ingatkan pengguna
        for group_id in GROUP_IDS:
            context.bot.send_message(
                chat_id=group_id,
                text=f"Baik {username}, saya akan mengingatkan dalam 30 menit lagi."
            )
        # Jadwalkan pengingat
        scheduler.add_job(
            remind_user,
            'date',
            run_date=datetime.now() + timedelta(minutes=30),
            args=[group_id, username, task_description]
        )
    
    elif action == "complete":
        if username in tasks.get(task_description, {}).get("assigned", []):
            if username not in tasks.get(task_description, {}).get("completed", []):
                tasks[task_description]["completed"].append(username)
                remaining_users = [u for u in tasks.get(task_description, {}).get("assigned", []) if u not in tasks.get(task_description, {}).get("completed", [])]
                if remaining_users:
                    remaining_mentions = ' '.join(f'@{u}' for u in remaining_users)
                    for group_id in GROUP_IDS:
                        context.bot.send_message(
                            chat_id=group_id,
                            text=f"Terima kasih {username} telah menyelesaikan tugas '{task_description}'. Silakan selesaikan tugas {remaining_mentions}."
                        )
                else:
                    for group_id in GROUP_IDS:
                        context.bot.send_message(
                            chat_id=group_id,
                            text=f"Terima kasih {username}, semua tugas sudah selesai!"
                        )
            else:
                query.answer("Anda sudah menyelesaikan tugas ini.")
        else:
            query.answer("Anda tidak terdaftar untuk tugas ini.")

    query.answer()

async def remind_user(chat_id: int, username: str, task_description: str) -> None:
    """Send a reminder to the user."""
    for group_id in GROUP_IDS:
        await context.bot.send_message(
            chat_id=group_id,
            text=f"@{username}, Anda masih memiliki tugas '{task_description}' yang perlu diselesaikan!"
        )

async def daily_reminder(bot) -> None:
    """Send a daily reminder to all groups."""
    for group_id in GROUP_IDS:
        await bot.send_message(chat_id=group_id, text="Ini adalah pengingat harian: Pastikan semua tugas sudah di-update!")

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Tambahkan job scheduler untuk pengingat rutin
    scheduler.add_job(daily_reminder, CronTrigger(hour=8, minute=0), args=[application.bot])

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('addtask', add_task))
    application.add_handler(CommandHandler('edittask', edit_task))
    application.add_handler(CallbackQueryHandler(button))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
