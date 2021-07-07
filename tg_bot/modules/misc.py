import html
import json
import random
from datetime import datetime
from typing import Optional, List

import requests
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from tg_bot.__main__ import STATS, USER_INFO
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters

RUN_STRINGS = (
    "Ke mana Anda pikir Anda akan pergi??",
    "Hah? apa? apakah mereka lolos?",
    "ZZzzZZzz... Hah? apa? oh, hanya mereka lagi, tidak apa-apa.",
    "Kembali kesini!",
    "Tidak begitu cepat...",
    "Perhatikan tembok!",
    "Jangan tinggalkan aku sendiri bersama mereka!!",
    "Kamu lari, kamu mati.",
    "Lelucon tentangmu, aku ada di mana-mana",
    "Kamu akan menyesalinya...",
    "Anda juga bisa mencoba /kickme, saya dengar itu menyenangkan.",
    "Pergi ganggu orang lain, tidak ada yang peduli.",
    "Kamu bisa lari, tapi kamu tidak bisa bersembunyi.",
    "Apakah itu semua yang Anda punya?",
    "saya di belakang Anda...",
    "Anda punya teman!",
    "Kita bisa melakukan ini dengan cara yang mudah, atau dengan cara yang sulit.",
    "Anda hanya tidak mengerti, bukan?",
    "Ya, lebih baik kamu lari!",
    "Tolong, ingatkan saya betapa saya peduli?",
    "Aku akan berlari lebih cepat jika aku jadi kamu.",
    "Itu pasti droid yang kita cari.",
    "Semoga peluang selalu menguntungkan Anda.",
    "Kata-kata terakhir yang terkenal.",
    "Dan mereka menghilang selamanya, tidak pernah terlihat lagi.",
    "\"Oh, lihat aku! Saya sangat keren, saya bisa lari dari bot!\" - orang ini",
    "Ya ya, cukup ketuk /kickme sudah.",
    "Di sini, ambil cincin ini dan pergi ke Mordor saat Anda melakukannya.",
    "Legenda mengatakan, mereka masih berlari...",
    "Tidak seperti Harry Potter, orang tuamu tidak bisa melindungimu dariku.",
    "Ketakutan menyebabkan kemarahan. Kemarahan mengarah pada kebencian. Kebencian menyebabkan penderitaan. Jika kamu terus berlari dalam ketakutan, kamu mungkin "
    "jadilah Vader berikutnya.",
    "Beberapa perhitungan kemudian, saya telah memutuskan minat saya pada kejahatan Anda persis 0.",
    "Legenda mengatakan, mereka masih berlari.",
    "Pertahankan, tidak yakin kami ingin Anda di sini.",
    "Anda seorang wiza- Oh. Tunggu. Kamu bukan Harry, teruslah bergerak.",
    "TIDAK BERLARI DI LOrong!",
    "Hasta la vista, sayang.",
    "Siapa yang membiarkan anjing keluar??",
    "Lucu, karena tidak ada yang peduli.",
    "Ah, sia-sia. Saya suka yang itu.",
    "Terus terang, sayangku, aku tidak peduli.",
    "Milkshake saya membawa semua anak laki-laki ke halaman... So run faster!",
    "Anda tidak bisa MENANGANI kebenaran!",
    "Dahulu kala, di galaksi yang sangat jauh... Seseorang akan peduli tentang itu. Sekarang tidak lagi.",
    "Han menembak lebih dulu. Aku juga.",
    "Apa yang kamu kejar, kelinci putih?",
    "Seperti yang akan dikatakan The Doctor... LARI!",
)

SLAP_TEMPLATES = (
    "{user1} {hits} {user2} dengan {item}.",
    "{user1} {hits} {user2} di wajah dengan {item}.",
    "{user1} {hits} {user2} sekitar sedikit dengan {item}.",
    "{user1} {throws} Sebuah {item} di {user2}.",
    "{user1} meraih {item} dan {throws} itu di {user2}'wajah.",
    "{user1} meluncurkan {item} di {user2}'s arahan umum.",
    "{user1} mulai menampar {user2} konyol dengan {item}.",
    "{user1} pin {user2} turun dan berulang-ulang {hits} mereka dengan {item}.",
    "{user1} meraih {item} dan {hits} {user2} dengan itu.",
    "{user1} dasi {user2} ke kursi dan {throws} Sebuah {item} pada mereka.",
    "{user1} memberikan dorongan ramah untuk membantu {user2} belajar berenang di lava."
)

ITEMS = (
    "wajan besi cor",
    "trout besar",
    "tongkat pemukul baseball",
    "tongkat pemukul kriket",
    "tongkat kayu",
    "kuku",
    "pencetak",
    "sekop",
    "Kontol",
    "buku teks fisika",
    "pemanggang roti",
    "potret Richard Stallman",
    "televisi",
    "truk lima ton",
    "gulungan lakban",
    "Buku",
    "laptop",
    "televisi lama",
    "sekarung batu",
    "ikan trout pelangi",
    "ayam karet",
    "pemukul berduri",
    "alat pemadam Api",
    "batu berat",
    "bongkahan kotoran",
    "sarang lebah",
    "sepotong daging busuk",
    "kontol",
    "ton batu bata",
)

THROW = (
    "throws",
    "flings",
    "chucks",
    "hurls",
)

HIT = (
    "hits",
    "whacks",
    "slaps",
    "smacks",
    "bashes",
)

GMAPS_LOC = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_TIME = "https://maps.googleapis.com/maps/api/timezone/json"


@run_async
def runs(bot: Bot, update: Update):
    update.effective_message.reply_text(random.choice(RUN_STRINGS))


@run_async
def slap(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id:
        slapped_user = bot.get_chat(user_id)
        user1 = curr_user
        if slapped_user.username:
            user2 = "@" + escape_markdown(slapped_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(slapped_user.first_name,
                                                   slapped_user.id)

    # if no target found, bot targets the sender
    else:
        user1 = "[{}](tg://user?id={})".format(bot.first_name, bot.id)
        user2 = curr_user

    temp = random.choice(SLAP_TEMPLATES)
    item = random.choice(ITEMS)
    hit = random.choice(HIT)
    throw = random.choice(THROW)

    repl = temp.format(user1=user1, user2=user2, item=item, hits=hit, throws=throw)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)


@run_async
def get_bot_ip(bot: Bot, update: Update):
    """ Sends the bot's IP address, so as to be able to ssh in if necessary.
        OWNER ONLY.
    """
    res = requests.get("http://ipinfo.io/ip")
    update.message.reply_text(res.text)


@run_async
def get_id(bot: Bot, update: Update, args: List[str]):
    user_id = extract_user(update.effective_message, args)
    if user_id:
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.forward_from:
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            update.effective_message.reply_text(
                "The original sender, {}, has an ID of `{}`.\nThe forwarder, {}, has an ID of `{}`.".format(
                    escape_markdown(user2.first_name),
                    user2.id,
                    escape_markdown(user1.first_name),
                    user1.id),
                parse_mode=ParseMode.MARKDOWN)
        else:
            user = bot.get_chat(user_id)
            update.effective_message.reply_text("{}'s id is `{}`.".format(escape_markdown(user.first_name), user.id),
                                                parse_mode=ParseMode.MARKDOWN)
    else:
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == "private":
            update.effective_message.reply_text("Your id is `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)

        else:
            update.effective_message.reply_text("This group's id is `{}`.".format(chat.id),
                                                parse_mode=ParseMode.MARKDOWN)


@run_async
def info(bot: Bot, update: Update, args: List[str]):
    msg = update.effective_message  # type: Optional[Message]
    user_id = extract_user(update.effective_message, args)

    if user_id:
        user = bot.get_chat(user_id)

    elif not msg.reply_to_message and not args:
        user = msg.from_user

    elif not msg.reply_to_message and (not args or (
            len(args) >= 1 and not args[0].startswith("@") and not args[0].isdigit() and not msg.parse_entities(
        [MessageEntity.TEXT_MENTION]))):
        msg.reply_text("I can't extract a user from this.")
        return

    else:
        return

    text = "<b>User info</b>:" \
           "\nID: <code>{}</code>" \
           "\nFirst Name: {}".format(user.id, html.escape(user.first_name))

    if user.last_name:
        text += "\nLast Name: {}".format(html.escape(user.last_name))

    if user.username:
        text += "\nUsername: @{}".format(html.escape(user.username))

    text += "\nPermanent user link: {}".format(mention_html(user.id, "link"))

    if user.id == OWNER_ID:
        text += "\n\nThis person is my owner - I would never do anything against them!"
    else:
        if user.id in SUDO_USERS:
            text += "\nThis person is one of my sudo users! " \
                    "Nearly as powerful as my owner - so watch it."
        else:
            if user.id in SUPPORT_USERS:
                text += "\nThis person is one of my support users! " \
                        "Not quite a sudo user, but can still gban you off the map."

            if user.id in WHITELIST_USERS:
                text += "\nThis person has been whitelisted! " \
                        "That means I'm not allowed to ban/kick them."

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@run_async
def get_time(bot: Bot, update: Update, args: List[str]):
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text("Its always banhammer time for me!")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    res = requests.get(GMAPS_LOC, params=dict(address=location))

    if res.status_code == 200:
        loc = json.loads(res.text)
        if loc.get('status') == 'OK':
            lat = loc['results'][0]['geometry']['location']['lat']
            long = loc['results'][0]['geometry']['location']['lng']

            country = None
            city = None

            address_parts = loc['results'][0]['address_components']
            for part in address_parts:
                if 'country' in part['types']:
                    country = part.get('long_name')
                if 'administrative_area_level_1' in part['types'] and not city:
                    city = part.get('long_name')
                if 'locality' in part['types']:
                    city = part.get('long_name')

            if city and country:
                location = "{}, {}".format(city, country)
            elif country:
                location = country

            timenow = int(datetime.utcnow().timestamp())
            res = requests.get(GMAPS_TIME, params=dict(location="{},{}".format(lat, long), timestamp=timenow))
            if res.status_code == 200:
                offset = json.loads(res.text)['dstOffset']
                timestamp = json.loads(res.text)['rawOffset']
                time_there = datetime.fromtimestamp(timenow + timestamp + offset).strftime("%H:%M:%S on %A %d %B")
                update.message.reply_text("It's {} in {}".format(time_there, location))


@run_async
def echo(bot: Bot, update: Update):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)
    message.delete()


@run_async
def gdpr(bot: Bot, update: Update):
    update.effective_message.reply_text("Deleting identifiable data...")
    for mod in GDPR:
        mod.__gdpr__(update.effective_user.id)

    update.effective_message.reply_text("Your personal data has been deleted.\n\nNote that this will not unban "
                                        "you from any chats, as that is telegram data, not Marie data. "
                                        "Flooding, warns, and gbans are also preserved, as of "
                                        "[this](https://ico.org.uk/for-organisations/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/), "
                                        "which clearly states that the right to erasure does not apply "
                                        "\"for the performance of a task carried out in the public interest\", as is "
                                        "the case for the aforementioned pieces of data.",
                                        parse_mode=ParseMode.MARKDOWN)


MARKDOWN_HELP = """
Markdown adalah alat pemformatan yang sangat kuat yang didukung oleh telegram. {} has some enhancements, to make sure that \
pesan yang disimpan diurai dengan benar, dan untuk memungkinkan Anda membuat tombol.

- <code>_italic_</code>: membungkus teks dengan '_' akan menghasilkan teks miring
- <code>*bold*</code>: membungkus teks dengan '*' akan menghasilkan teks tebal
- <code>`code`</code>: membungkus teks dengan '`' akan menghasilkan teks monospace, juga dikenal sebagai 'kode'
- <code>[sometext](someURL)</code>: ini akan membuat tautan - pesan hanya akan muncul <code>sometext</code>, \
dan mengetuknya akan membuka halaman di <code>someURL</code>.
EG: <code>[test](example.com)</code>

- <code>[buttontext](buttonurl:someURL)</code>: ini adalah peningkatan khusus untuk memungkinkan pengguna memiliki telegram \
tombol di markdown mereka. <code>buttontext</code> akan menjadi apa yang ditampilkan pada tombol, dan <code>someurl</code> \
akan menjadi url yang dibuka.
EG: <code>[Ini adalah tombol](buttonurl:example.com)</code>

Jika Anda ingin beberapa tombol pada baris yang sama, gunakan :sama, seperti itu:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
Ini akan membuat dua tombol pada satu baris, bukan satu tombol per baris.

berada dalam huruf kecil. Jika Anda ingin kata kunci Anda menjadi kalimat, gunakan tanda kutip. dalam pikiran bahwa pesan Anda <b>MUST</b> berisi beberapa teks selain hanya sebuah tombol!
""".format(dispatcher.bot.first_name)


@run_async
def markdown_help(bot: Bot, update: Update):
    update.effective_message.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    update.effective_message.reply_text("Try forwarding the following message to me, and you'll see!")
    update.effective_message.reply_text("/save test This is a markdown test. _italics_, *bold*, `code`, "
                                        "[URL](example.com) [button](buttonurl:github.com) "
                                        "[button2](buttonurl://google.com:same)")


@run_async
def stats(bot: Bot, update: Update):
    update.effective_message.reply_text("Current stats:\n" + "\n".join([mod.__stats__() for mod in STATS]))

@run_async
def stickerid(bot: Bot, update: Update):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.sticker:
        update.effective_message.reply_text("Hello " +
                                            "[{}](tg://user?id={})".format(msg.from_user.first_name, msg.from_user.id)
                                            + ", The sticker id you are replying is :\n```" + 
                                            escape_markdown(msg.reply_to_message.sticker.file_id) + "```",
                                            parse_mode=ParseMode.MARKDOWN)
    else:
        update.effective_message.reply_text("Hello " + "[{}](tg://user?id={})".format(msg.from_user.first_name,
                                            msg.from_user.id) + ", Please reply to sticker message to get id sticker",
                                            parse_mode=ParseMode.MARKDOWN)
@run_async
def getsticker(bot: Bot, update: Update):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    if msg.reply_to_message and msg.reply_to_message.sticker:
        bot.sendChatAction(chat_id, "typing")
        update.effective_message.reply_text("Hello " + "[{}](tg://user?id={})".format(msg.from_user.first_name,
                                            msg.from_user.id) + ", Please check the file you requested below."
                                            "\nPlease use this feature wisely!",
                                            parse_mode=ParseMode.MARKDOWN)
        bot.sendChatAction(chat_id, "upload_document")
        file_id = msg.reply_to_message.sticker.file_id
        newFile = bot.get_file(file_id)
        newFile.download('sticker.png')
        bot.sendDocument(chat_id, document=open('sticker.png', 'rb'))
        bot.sendChatAction(chat_id, "upload_photo")
        bot.send_photo(chat_id, photo=open('sticker.png', 'rb'))
        
    else:
        bot.sendChatAction(chat_id, "typing")
        update.effective_message.reply_text("Hello " + "[{}](tg://user?id={})".format(msg.from_user.first_name,
                                            msg.from_user.id) + ", Please reply to sticker message to get sticker image",
                                            parse_mode=ParseMode.MARKDOWN)

# /ip is for private use
__help__ = """
 - /id: get the current group id. If used by replying to a message, gets that user's id.
 - /runs: reply a random string from an array of replies.
 - /slap: slap a user, or get slapped if not a reply.
 - /time <place>: gives the local time at the given place.
 - /info: get information about a user.
 - /gdpr: deletes your information from the bot's database. Private chats only.
 - /markdownhelp: quick summary of how markdown works in telegram - can only be called in private chats.
 - /stickerid: reply to a sticker and get sticker id of that.
 - /getsticker: reply to a sticker and get that sticker as .png and image. 
"""

__mod_name__ = "Misc"

ID_HANDLER = DisableAbleCommandHandler("id", get_id, pass_args=True)
IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=Filters.chat(OWNER_ID))

TIME_HANDLER = CommandHandler("time", get_time, pass_args=True)

RUNS_HANDLER = DisableAbleCommandHandler("runs", runs)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, pass_args=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, pass_args=True)

ECHO_HANDLER = CommandHandler("echo", echo, filters=Filters.user(OWNER_ID))
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help, filters=Filters.private)

STATS_HANDLER = CommandHandler("stats", stats, filters=CustomFilters.sudo_filter)
GDPR_HANDLER = CommandHandler("gdpr", gdpr, filters=Filters.private)

STICKERID_HANDLER = DisableAbleCommandHandler("stickerid", stickerid)
GETSTICKER_HANDLER = DisableAbleCommandHandler("getsticker", getsticker)


dispatcher.add_handler(ID_HANDLER)
dispatcher.add_handler(IP_HANDLER)
dispatcher.add_handler(TIME_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
dispatcher.add_handler(GDPR_HANDLER)
dispatcher.add_handler(STICKERID_HANDLER)
dispatcher.add_handler(GETSTICKER_HANDLER)
