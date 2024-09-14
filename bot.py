import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import pytz

# Konfigurasi logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Token Bot dan ID Grup
BOT_TOKEN = '7204772490:AAG7iQf2O05b5Lu7W3ISCbf5Np1z91OD-Tg'
GROUP_ID = -1001266140927

# Scheduler untuk pengingat otomatis
scheduler = BackgroundScheduler()
scheduler.start()

# Simpan tugas dalam dictionary
tasks = {}

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Cek Tugas", callback_data='check')],
        [InlineKeyboardButton("Buat Tugas", callback_data='add')],
        [InlineKeyboardButton("Edit Tugas", callback_data='edit')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Pilih opsi:', reply_markup=reply_markup)

async def add_task(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Format perintah salah. Gunakan: /addtask <deskripsi_tugas> <username1> <username2> ...")
        return

    task_description = args[0]
    assigned_users = args[1:]

    if task_description in tasks:
        await update.message.reply_text("Tugas dengan deskripsi ini sudah ada.")
        return

    tasks[task_description] = {
        'assigned': [u.lstrip('@') for u in assigned_users],
        'completed': []
    }

    keyboard = [
        [InlineKeyboardButton("Ingatkan 30 menit lagi", callback_data=f"remind_{task_description}")],
        [InlineKeyboardButton("Sudah mengerjakan", callback_data=f"complete_{task_description}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"Tugas '{task_description}' telah ditambahkan untuk {', '.join(assigned_users)}."
    await context.bot.send_message(chat_id=GROUP_ID, text=message, reply_markup=reply_markup)

async def edit_task(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Format perintah salah. Gunakan: /edittask <deskripsi_tugas> <username1> <username2> ...")
        return

    task_description = args[0]
    assigned_users = args[1:]

    if task_description not in tasks:
        await update.message.reply_text("Tugas dengan deskripsi ini tidak ditemukan.")
        return

    tasks[task_description]['assigned'] = [u.lstrip('@') for u in assigned_users]

    message = f"Tugas '{task_description}' telah diperbarui untuk {', '.join(assigned_users)}."
    await context.bot.send_message(chat_id=GROUP_ID, text=message)

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query_data = query.data
    user = query.from_user.username

    if '_' not in query_data:
        await query.answer("Data callback tidak valid.")
        return

    action, task_name = query_data.split('_', 1)

    if task_name not in tasks:
        await query.answer("Tugas tidak ditemukan.")
        return

    if action == 'remind':
        if user in tasks[task_name]['assigned']:
            # Hanya ingatkan pengguna yang menekan tombol
            scheduler.add_job(remind_user, 'date', run_date=datetime.now(pytz.UTC) + timedelta(minutes=30), args=[context.bot, GROUP_ID, user, task_name])
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"Baik @{user}, saya akan mengingatkan Anda dalam 30 menit lagi."
            )
        else:
            await query.answer("Anda tidak terdaftar untuk tugas ini.")

    elif action == 'complete':
        if user in tasks[task_name]['assigned']:
            if user not in tasks[task_name]['completed']:
                tasks[task_name]['completed'].append(user)
                remaining_users = [u for u in tasks[task_name]['assigned'] if u not in tasks[task_name]['completed']]
                if remaining_users:
                    remaining_mentions = ' '.join(f'@{u}' for u in remaining_users)
                    await context.bot.send_message(
                        chat_id=GROUP_ID,
                        text=f"Terima kasih @{user} telah menyelesaikan tugas. Silakan selesaikan tugas @{remaining_mentions}."
                    )
                else:
                    await context.bot.send_message(
                        chat_id=GROUP_ID,
                        text=f"Terima kasih @{user}, semua tugas sudah selesai!"
                    )
            else:
                await query.answer("Anda sudah menyelesaikan tugas ini.")
        else:
            await query.answer("Anda tidak terdaftar untuk tugas ini.")

    await query.answer()

async def remind_user(bot, chat_id: int, user: str, task_name: str) -> None:
    await bot.send_message(
        chat_id=chat_id,
        text=f"@{user}, Anda masih memiliki tugas '{task_name}' yang perlu diselesaikan!"
    )

async def daily_reminder(bot) -> None:
    chat_id = GROUP_ID
    message = "Ini adalah pengingat harian: Pastikan semua tugas sudah di-update!"
    await bot.send_message(chat_id=chat_id, text=message)

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    # Tambahkan job scheduler untuk pengingat rutin
    scheduler.add_job(daily_reminder, CronTrigger(hour=8, minute=0), args=[application.bot])

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('addtask', add_task))
    application.add_handler(CommandHandler('edittask', edit_task))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
