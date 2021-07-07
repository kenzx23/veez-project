import re
from io import BytesIO
from typing import Optional, List

from telegram import MAX_MESSAGE_LENGTH, ParseMode, InlineKeyboardMarkup
from telegram import Message, Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, RegexHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown

import tg_bot.modules.sql.notes_sql as sql
from tg_bot import dispatcher, MESSAGE_DUMP, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.misc import build_keyboard, revert_buttons
from tg_bot.modules.helper_funcs.msg_types import get_note_type

from tg_bot.modules.connection import connected

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


# Do not async
def get(bot, update, notename, show_none=True, no_format=False):
    chat_id = update.effective_chat.id
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    conn = connected(bot, update, chat, user.id, need_admin=False)
    if not conn == False:
        chat_id = conn
        send_id = user.id
    else:
        chat_id = update.effective_chat.id
        send_id = chat_id

    note = sql.get_note(chat_id, notename)
    message = update.effective_message  # type: Optional[Message]

    if note:
        # If we're replying to a message, reply to that message (unless it's an error)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id

        if note.is_reply:
            if MESSAGE_DUMP:
                try:
                    bot.forward_message(chat_id=chat_id, from_chat_id=MESSAGE_DUMP, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "pesan untuk diteruskan tidak ditemukan!":
                        message.reply_text("pesan ini sepertinya sudah hilang - saya akan menghapusnya "
                                           "dari daftar catatan anda.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
            else:
                try:
                    bot.forward_message(chat_id=chat_id, from_chat_id=chat_id, message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "pesan untuk diteruskan tidak ditemukan!":
                        message.reply_text("sepertinya pengirim asli catatan ini telah menghapus "
                                           "pesan mereka - maaf, minta admin bot anda untuk mulai melakukan "
                                           "penghapusan pesan untuk menghindari hal ini, saya akan menghapus catatan ini dari "
                                           "catatan yang anda simpan.")
                        sql.rm_note(chat_id, notename)
                    else:
                        raise
        else:
            text = note.value
            keyb = []
            parseMode = ParseMode.MARKDOWN
            buttons = sql.get_buttons(chat_id, notename)
            should_preview_disabled = True
            if no_format:
                parseMode = None
                text += revert_buttons(buttons)
            else:
                keyb = build_keyboard(buttons)
                if "telegra.ph" in text or "youtu.be" in text:
                    should_preview_disabled = False

            keyboard = InlineKeyboardMarkup(keyb)

            try:
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    bot.send_message(chat_id, text, reply_to_message_id=reply_id,
                                     parse_mode=parseMode, disable_web_page_preview=should_preview_disabled,
                                     reply_markup=keyboard)
                else:
                    ENUM_FUNC_MAP[note.msgtype](chat_id, note.file, caption=text, reply_to_message_id=reply_id,
                                                parse_mode=parseMode, disable_web_page_preview=should_preview_disabled,
                                                reply_markup=keyboard)

            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    message.reply_text("Sepertinya Anda mencoba menyebut seseorang yang belum pernah saya lihat sebelumnya. Jika Anda benar-benar"
                                       "ingin menyebutkan mereka, meneruskan salah satu pesan mereka kepada saya, dan saya akan bisa"
                                       "untuk menandai mereka!")
                elif FILE_MATCHER.match(note.value):
                    message.reply_text("Catatan ini adalah file yang diimpor dengan tidak benar dari bot lain - saya tidak dapat menggunakan"
                                       "itu. Jika Anda benar-benar membutuhkannya, Anda harus menyimpannya lagi. Dalam"
                                       "Sementara itu, saya akan menghapusnya dari daftar catatan Anda.")
                    sql.rm_note(chat_id, notename)
                else:
                    message.reply_text("Catatan ini tidak dapat dikirim, karena formatnya salah. Tanyakan dalam"
                                       "@levinachannel jika Anda tidak tahu mengapa!")
                    LOGGER.exception("Could not parse message #%s in chat %s", notename, str(chat_id))
                    LOGGER.warning("Message was: %s", str(note.value))
        return
    elif show_none:
        message.reply_text("note ini tidak tersedia")


@run_async
def cmd_get(bot: Bot, update: Update, args: List[str]):
    if len(args) >= 2 and args[1].lower() == "noformat":
        get(bot, update, args[0], show_none=True, no_format=True)
    elif len(args) >= 1:
        get(bot, update, args[0], show_none=True)
    else:
        update.effective_message.reply_text("Get rekt")


@run_async
def hash_get(bot: Bot, update: Update):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:]
    get(bot, update, no_hash, show_none=False)


@run_async
@user_admin
def save(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    conn = connected(bot, update, chat, user.id)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "local notes"
        else:
            chat_name = chat.title

    msg = update.effective_message  # type: Optional[Message]

    note_name, text, data_type, content, buttons = get_note_type(msg)

    if data_type is None:
        msg.reply_text("Dude, there's no note")
        return

    if len(text.strip()) == 0:
        text = note_name

    sql.add_note_to_db(chat_id, note_name, text, data_type, buttons=buttons, file=content)

    msg.reply_text(
        "OK, Added {note_name} in *{chat_name}*.\nGet it with /get {note_name}, or #{note_name}".format(note_name=note_name, chat_name=chat_name), parse_mode=ParseMode.MARKDOWN)

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        if text:
            msg.reply_text("Seems like you're trying to save a message from a bot. Unfortunately, "
                           "bots can't forward bot messages, so I can't save the exact message. "
                           "\nI'll save all the text I can, but if you want more, you'll have to "
                           "forward the message yourself, and then save it.")
        else:
            msg.reply_text("Bots are kinda handicapped by telegram, making it hard for bots to "
                           "interact with other bots, so I can't save this message "
                           "like I usually would - do you mind forwarding it and "
                           "then saving that new message? Thanks!")
        return


@run_async
@user_admin
def clear(bot: Bot, update: Update, args: List[str]):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    conn = connected(bot, update, chat, user.id)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "local notes"
        else:
            chat_name = chat.title

    if len(args) >= 1:
        notename = args[0]

        if sql.rm_note(chat_id, notename):
            update.effective_message.reply_text("catatan berhasil dihapus.")
        else:
            update.effective_message.reply_text("itu bukan catatan di database saya!")


@run_async
def list_notes(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    conn = connected(bot, update, chat, user.id, need_admin=False)
    if not conn == False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        msg = "*catatan di {}:*\n"
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = ""
            msg = "*catatan lokal:*\n"
        else:
            chat_name = chat.title
            msg = "*catatan di {}:*\n"

    note_list = sql.get_all_chat_notes(chat_id)

    for note in note_list:
        note_name = escape_markdown(" - {}\n".format(note.name))
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if msg == "*catatan dalam obrolan:*\n":
        update.effective_message.reply_text("tidak ada catatan dalam obrolan ini!")

    elif len(msg) != 0:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get('extra', {}).items():
        match = FILE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            notedata = notedata[match.end():].strip()
            if notedata:
                sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(chat_id, document=output, filename="failed_imports.txt",
                                         caption="These files/photos failed to import due to originating "
                                                 "from another bot. This is a telegram API restriction, and can't "
                                                 "be avoided. Sorry for the inconvenience!")


def __stats__():
    return "{} notes, across {} chats.".format(sql.num_notes(), sql.num_chats())


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return "There are `{}` notes in this chat.".format(len(notes))


__help__ = """
 - /get <notename>: dapatkan catatan dengan nama note
 - #<notename> : sama seperti /get
 - /notes or /saved: daftar semua catatan yang disimpan dalam obrolan ini

Jika Anda ingin mengambil konten catatan tanpa pemformatan apa pun, gunakan `/ get <notename> noformat`. Ini bisa \
berguna saat memperbarui catatan saat ini.

*Admin only:*
 - /save <notename> <notedata>: menyimpan notedata sebagai catatan dengan nama notename
Tombol dapat ditambahkan ke catatan dengan menggunakan sintaks tautan penurunan harga standar - tautannya harus diawali dengan \
`buttonurl:` bagian, seperti: `[somelink](buttonurl:example.com)`. Memeriksa /markdownhelp untuk info lebih lanjut.
 - /save <notename>: simpan pesan balasan sebagai catatan dengan nama notename
 - /clear <notename>: hapus catatan dengan nama ini
"""

__mod_name__ = "notes"

GET_HANDLER = CommandHandler("get", cmd_get, pass_args=True)
HASH_GET_HANDLER = RegexHandler(r"^#[^\s]+", hash_get)

SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear, pass_args=True)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"], list_notes, admin_ok=True)

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
