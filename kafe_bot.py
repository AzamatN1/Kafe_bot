import json
from pathlib import Path

import telebot
from telebot import custom_filters, types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage

from config import TOKEN


MENYU = {
    "pitsa": ("🍕 Pitsa", 45000),
    "burger": ("🍔 Burger", 30000),
    "lavash": ("🌯 Lavash", 25000),
    "choy": ("🍵 Choy", 5000),
}
FAYL = Path(__file__).with_name("buyurtmalar.json")
bot = telebot.TeleBot(TOKEN, state_storage=StateMemoryStorage())


class Buyurtma(StatesGroup):
    taom = State()
    soni = State()
    tasdiq = State()


def asosiy_menyu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row("🍽 Buyurtma berish", "🧾 Mening buyurtmam")
    markup.row("📋 Menyu", "ℹ️ Yordam")
    return markup


def taom_tugmalari():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*(
        types.InlineKeyboardButton(
            f"{nom} — {narx} so'm", callback_data=f"taom_{kod}"
        )
        for kod, (nom, narx) in MENYU.items()
    ))
    return markup


def tasdiq_tugmalari():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Ha", callback_data="ha"),
        types.InlineKeyboardButton("❌ Yo'q", callback_data="yoq"),
    )
    return markup


def bekor_tugmalari(royxat):
    markup = types.InlineKeyboardMarkup(row_width=5)
    markup.add(*(
        types.InlineKeyboardButton(f"❌ {i + 1}", callback_data=f"bekor_{i}")
        for i in range(len(royxat))
    ))
    return markup


def yukla():
    try:
        with FAYL.open("r", encoding="utf-8") as fayl:
            return json.load(fayl)
    except FileNotFoundError:
        return {}


def saqla(data):
    with FAYL.open("w", encoding="utf-8") as fayl:
        json.dump(data, fayl, ensure_ascii=False, indent=2)


def buyurtma_saqla(chat_id, matn):
    data = yukla()
    data.setdefault(str(chat_id), []).append(matn)
    saqla(data)


def buyurtmalar_ol(chat_id):
    return yukla().get(str(chat_id), [])


def buyurtma_ochir(chat_id, i):
    data = yukla()
    royxat = data.get(str(chat_id), [])
    if not 0 <= i < len(royxat):
        return None
    ochirilgan = royxat.pop(i)
    saqla(data)
    return ochirilgan


def royxat_matni(royxat):
    qatorlar = [f"{i}. {matn}" for i, matn in enumerate(royxat, 1)]
    return "🧾 Sizning buyurtmalaringiz:\n" + "\n".join(qatorlar) + "\n\nBekor qilish — raqamni bosing 👇"


@bot.message_handler(commands=["start"])
def start(message):
    bot.delete_state(message.from_user.id, message.chat.id)
    ism = message.from_user.first_name or "do'stim"
    bot.send_message(
        message.chat.id,
        f"Salom, {ism}! ☕ Ustudy kafega xush kelibsiz.\n"
        "Pastdagi tugmalardan tanlang 👇",
        reply_markup=asosiy_menyu(),
    )


@bot.message_handler(commands=["help"])
@bot.message_handler(func=lambda m: m.text == "ℹ️ Yordam")
def yordam(message):
    bot.send_message(
        message.chat.id,
        "🍽 Buyurtma berish — taom → soni → tasdiqlash\n"
        "🧾 Mening buyurtmam — buyurtmalarim, ❌ bekor qilish\n"
        "📋 Menyu — taomlar va narxlar\n"
        "/cancel — dialogni bekor qilish",
    )


@bot.message_handler(commands=["menyu"])
@bot.message_handler(func=lambda m: m.text == "📋 Menyu")
def menyu(message):
    qatorlar = [f"{nom} — {narx} so'm" for nom, narx in MENYU.values()]
    bot.send_message(message.chat.id, "📋 Menyu:\n" + "\n".join(qatorlar))


@bot.message_handler(commands=["mening"])
@bot.message_handler(func=lambda m: m.text == "🧾 Mening buyurtmam")
def mening(message):
    royxat = buyurtmalar_ol(message.chat.id)
    if not royxat:
        bot.send_message(message.chat.id, "Hali buyurtma yo'q. 🍽 Buyurtma berish tugmasini bosing")
        return
    bot.send_message(
        message.chat.id, royxat_matni(royxat), reply_markup=bekor_tugmalari(royxat)
    )


@bot.message_handler(state="*", commands=["cancel"])
def cancel(message):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, "❌ Bekor qilindi", reply_markup=asosiy_menyu())


@bot.message_handler(commands=["buyurtma"])
@bot.message_handler(func=lambda m: m.text == "🍽 Buyurtma berish")
def buyurtma(message):
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.set_state(message.from_user.id, Buyurtma.taom, message.chat.id)
    xabar = bot.send_message(
        message.chat.id,
        "Nima buyurasiz? 👇 (/cancel — bekor qilish)",
        reply_markup=taom_tugmalari(),
    )
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["taom_message_id"] = xabar.message_id


@bot.callback_query_handler(func=lambda c: c.data.startswith("taom_"), state=Buyurtma.taom)
def taom_tanlandi(call):
    kod = call.data.removeprefix("taom_")
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        if kod not in MENYU or data.get("taom_message_id") != call.message.message_id:
            bot.answer_callback_query(call.id, "Bu tugma eskirgan. 🍽 Buyurtma berish'dan boshlang")
            return
        nom, narx = MENYU[kod]
        data["taom"] = nom
        data["narx"] = narx
    bot.set_state(call.from_user.id, Buyurtma.soni, call.message.chat.id)
    bot.answer_callback_query(call.id)
    bot.edit_message_text(f"Tanlandi: {nom}", call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Nechta? (1–10)")


@bot.message_handler(state=Buyurtma.taom)
def taom_matn(message):
    bot.send_message(message.chat.id, "Tugmalardan birini bosing 👆 (yoki /cancel)")


@bot.message_handler(state=Buyurtma.soni)
def soni_qabul(message):
    if not message.text or not message.text.isdigit() or not 1 <= int(message.text) <= 10:
        bot.send_message(message.chat.id, "1 dan 10 gacha son kiriting")
        return
    soni = int(message.text)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["soni"] = soni
        data["jami"] = data["narx"] * soni
        matn = f"{data['taom']} × {soni} = {data['jami']} so'm"
    bot.set_state(message.from_user.id, Buyurtma.tasdiq, message.chat.id)
    xabar = bot.send_message(
        message.chat.id, f"🧾 {matn}\nTasdiqlaysizmi?", reply_markup=tasdiq_tugmalari()
    )
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["tasdiq_message_id"] = xabar.message_id


@bot.callback_query_handler(func=lambda c: c.data in ("ha", "yoq"), state=Buyurtma.tasdiq)
def tasdiq(call):
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        if data.get("tasdiq_message_id") != call.message.message_id:
            bot.answer_callback_query(call.id, "Bu tugma eskirgan. 🍽 Buyurtma berish'dan boshlang")
            return
        matn = f"{data['taom']} × {data['soni']} = {data['jami']} so'm"
    if call.data == "ha":
        buyurtma_saqla(call.message.chat.id, matn)
        bot.answer_callback_query(call.id, "Qabul qilindi ✅")
        javob = f"✅ Buyurtma qabul qilindi:\n{matn}\n⏱ 15 daqiqada tayyor!"
    else:
        bot.answer_callback_query(call.id, "Bekor qilindi")
        javob = "❌ Buyurtma bekor qilindi"
    bot.delete_state(call.from_user.id, call.message.chat.id)
    bot.edit_message_text(javob, call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Yana nimadir kerakmi? 👇", reply_markup=asosiy_menyu())


@bot.message_handler(state=Buyurtma.tasdiq)
def tasdiq_matn(message):
    bot.send_message(message.chat.id, "✅ Ha yoki ❌ Yo'q tugmasini bosing 👆")


@bot.callback_query_handler(func=lambda c: c.data.startswith("bekor_"))
def bekor(call):
    try:
        i = int(call.data.removeprefix("bekor_"))
    except ValueError:
        i = -1
    ochirilgan = buyurtma_ochir(call.message.chat.id, i)
    if ochirilgan is None:
        bot.answer_callback_query(call.id, "Bu buyurtma topilmadi. 🧾 Ro'yxatni qayta oching")
        return
    bot.answer_callback_query(call.id, f"❌ Bekor qilindi: {ochirilgan}")
    royxat = buyurtmalar_ol(call.message.chat.id)
    if royxat:
        bot.edit_message_text(
            royxat_matni(royxat), call.message.chat.id, call.message.message_id,
            reply_markup=bekor_tugmalari(royxat),
        )
    else:
        bot.edit_message_text("🧾 Buyurtma qolmadi", call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda c: True)
def eski_tugma(call):
    bot.answer_callback_query(call.id, "Bu tugma eskirgan. 🍽 Buyurtma berish'dan boshlang")


@bot.message_handler(func=lambda m: True)
def boshqa(message):
    bot.send_message(
        message.chat.id, "Tushunmadim 🤔 Pastdagi tugmalardan foydalaning",
        reply_markup=asosiy_menyu(),
    )


if __name__ == "__main__":
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.infinity_polling()
