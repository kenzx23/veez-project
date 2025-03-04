from io import BytesIO
from time import sleep
from typing import Optional, List
from telegram import TelegramError, Chat, Message
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters, CommandHandler
from telegram.ext.dispatcher import run_async
from tg_bot.modules.helper_funcs.chat_status import is_user_ban_protected, bot_admin

import tg_bot.modules.sql.users_sql as sql
from tg_bot import dispatcher, OWNER_ID, LOGGER
from tg_bot.modules.helper_funcs.filters import CustomFilters

USERS_GROUP = 4


@run_async
def quickscope(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = str(args[1])
        to_kick = str(args[0])
    else:
        update.effective_message.reply_text("anda tampaknya tidak mengacu pada obrolan / pengguna")
    try:
        bot.kick_chat_member(chat_id, to_kick)
        update.effective_message.reply_text("attempted banning " + to_kick + " from" + chat_id)
    except BadRequest as excp:
        update.effective_message.reply_text(excp.message + " " + to_kick)


@run_async
def quickunban(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = str(args[1])
        to_kick = str(args[0])
    else:
        update.effective_message.reply_text("anda tampaknya tidak mengacu pada obrolan / pengguna")
    try:
        bot.unban_chat_member(chat_id, to_kick)
        update.effective_message.reply_text("attempted unbanning " + to_kick + " from" + chat_id)
    except BadRequest as excp:
        update.effective_message.reply_text(excp.message + " " + to_kick)


@run_async
def banall(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = str(args[0])
        all_mems = sql.get_chat_members(chat_id)
    else:
        chat_id = str(update.effective_chat.id)
        all_mems = sql.get_chat_members(chat_id)
    for mems in all_mems:
        try:
            bot.kick_chat_member(chat_id, mems.user)
            update.effective_message.reply_text("Tried banning " + str(mems.user))
            sleep(0.1)
        except BadRequest as excp:
            update.effective_message.reply_text(excp.message + " " + str(mems.user))
            continue


@run_async
def snipe(bot: Bot, update: Update, args: List[str]):
    try:
        chat_id = str(args[0])
        del args[0]
    except TypeError as excp:
        update.effective_message.reply_text("please give me a chat to echo to!")
    to_send = " ".join(args)
    if len(to_send) >= 2:
        try:
            bot.sendMessage(int(chat_id), str(to_send))
        except TelegramError:
            LOGGER.warning("Couldn't send to group %s", str(chat_id))
            update.effective_message.reply_text("tidak dapat mengirim pesan, mungkin saya bukan bagian dari grup itu.")


@run_async
@bot_admin
def getlink(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = int(args[0])
    else:
        update.effective_message.reply_text("anda sepertinya tidak mengacu pada obrolan.")
    chat = bot.getChat(chat_id)
    bot_member = chat.get_member(bot.id)
    if bot_member.can_invite_users:
        invitelink = bot.get_chat(chat_id).invite_link
        update.effective_message.reply_text(invitelink)
    else:
        update.effective_message.reply_text("saya tidak memiliki akses ke tautan undangan!")


@bot_admin
def leavechat(bot: Bot, update: Update, args: List[int]):
    if args:
        chat_id = int(args[0])
        bot.leaveChat(chat_id)
    else:
        update.effective_message.reply_text("anda sepertinya tidak mengacu pada obrolan.")

__help__ = """
**Hanya pemilik:**
- /getlink **chatid**: Dapatkan tautan undangan untuk obrolan tertentu.
- /banall: Larang semua anggota dari obrolan
- /leavechat **chatid** : tinggalkan obrolan
**Sudo/pemilik saja:**
- /quickscope **userid** **chatid**: Larang pengguna dari obrolan.
- /quickunban **userid** **chatid**: Batalkan pemblokiran pengguna dari obrolan.
- /snipe **chatid** **string**: Buat saya mengirim pesan ke obrolan tertentu.
- /rban **userid** **chatid** melarang pengguna dari jarak jauh dari obrolan
- /runban **userid** **chatid** cabut blokir pengguna dari obrolan dari jarak jauh
- /Stats: periksa statistik bot
- /chatlist: dapatkan daftar obrolan
- /gbanlist: dapatkan daftar pengguna yang diblokir
- /gmutelist: dapatkan daftar pengguna yang di-gmuted
- Larangan obrolan melalui /restrict chat_id and /unrestrict chat_id commands
**Support User:**
- /gban : Larangan global pengguna
- /ungban : Ungban pengguna
- /gmute : Menonaktifkan pengguna
- /ungmute : Suarakan pengguna
Sudo/pemilik dapat menggunakan perintah ini juga.
**Pengguna:**
- /listsudo Memberikan daftar pengguna sudo
- /listsupport memberikan daftar pengguna dukungan
"""
__mod_name__ = "✨ Spesial"

SNIPE_HANDLER = CommandHandler("snipe", snipe, pass_args=True, filters=CustomFilters.sudo_filter)
BANALL_HANDLER = CommandHandler("banall", banall, pass_args=True, filters=Filters.user(OWNER_ID))
QUICKSCOPE_HANDLER = CommandHandler("quickscope", quickscope, pass_args=True, filters=CustomFilters.sudo_filter)
QUICKUNBAN_HANDLER = CommandHandler("quickunban", quickunban, pass_args=True, filters=CustomFilters.sudo_filter)
GETLINK_HANDLER = CommandHandler("getlink", getlink, pass_args=True, filters=Filters.user(OWNER_ID))
LEAVECHAT_HANDLER = CommandHandler("leavechat", leavechat, pass_args=True, filters=Filters.user(OWNER_ID))

dispatcher.add_handler(SNIPE_HANDLER)
dispatcher.add_handler(BANALL_HANDLER)
dispatcher.add_handler(QUICKSCOPE_HANDLER)
dispatcher.add_handler(QUICKUNBAN_HANDLER)
dispatcher.add_handler(GETLINK_HANDLER)
dispatcher.add_handler(LEAVECHAT_HANDLER)
