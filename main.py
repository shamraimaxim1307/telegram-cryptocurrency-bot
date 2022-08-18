import telebot
import requests
from telebot import types
from models import User, Crypto
from secretdata import Data

token = Data.api_key
bot = telebot.TeleBot(token)


# States group.
class MyStates:
    # Just name variables differently
    crypto = ""
    count = ""


@bot.message_handler(commands=['start'])
def start(message):
    if User.select().where(User.chat_id == message.chat.id):
        create_main_menu(message, f"Hi, {message.from_user.first_name or ''}"
                                  f" {message.from_user.last_name or ''}\n")
    else:
        User.create(
            chat_id=message.chat.id,
            remain_money=100
        )
        create_main_menu(message, f"Hi, {message.from_user.first_name or ''}"
                                  f" {message.from_user.last_name or ''}\n"
                                  f"Our company gives you $100 bonus to use our services")


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id, "<b>Help with buttons:</b>\n"
                                      "\n💱<b>BUY Crypto</b> - you should enter name of crypto(if you know)"
                                      " and count crypto you want to buy,"
                                      "after that crypto will be in your crypto wallet\n"
                                      "\n💰<b>SELL Crypto</b> - you should enter name of crypto(if you know)"
                                      " and count crypto you want to sell, after that money will be in your wallet\n"
                                      "\n🔍<b>FIND Crypto</b> - you should enter part of name or name of crypto,"
                                      "after that you see available naming of crypto you want to find\n"
                                      "\n📊<b>STATS Crypto</b> - this button displays all crypto that we have on our "
                                      "crypto exchange\n"
                                      "\n🧿<b>SHOW Crypto</b> - this button displays all money and cryptos you have",
                     parse_mode="HTML")


@bot.message_handler(commands=['showmenukeyboard'])
def show_menu_keyboard(message):
    create_main_menu(message, "Keyboard is shown")


@bot.message_handler(commands=['hidemenukeyboard'])
def hide_menu_keyboard(message):
    bot.send_message(message.chat.id, "Keyboard is hidden", reply_markup=types.ReplyKeyboardRemove())


def create_main_menu(message, bot_answer):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    item1 = types.KeyboardButton('💱 BUY Crypto')
    item2 = types.KeyboardButton('💰 SELL Crypto')
    item3 = types.KeyboardButton('🔍 FIND Crypto')
    item4 = types.KeyboardButton('📊 STATS Crypto')
    item5 = types.KeyboardButton('🧿 SHOW Crypto')

    markup.add(item1, item2, item3, item4, item5)
    bot.send_message(message.chat.id,
                     bot_answer,
                     reply_markup=markup)


def enter_name_of_add_crypto(message):
    if message.text == "⬅️ Return back":
        work_with_buttons(message)
    else:
        if message.text.isidentifier():
            crypto = message.text.upper()
            response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={crypto}USDT").json()
            # If response has 'code', that's mean that errors occurred
            if "code" in response:
                bot.send_message(message.chat.id,
                                 "⛔️Err: Invalid crypto")
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton('⬅️ Return back')
                markup.add(item1)
                bot.register_next_step_handler(message, enter_name_of_add_crypto)
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton('⬅️ Return to enter crypto to buy')
                markup.add(item1)
                MyStates.crypto = crypto
                msg = bot.send_message(message.chat.id,
                                       f"Enter count of {crypto}",
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, enter_count_of_add_crypto)
        else:
            bot.send_message(message.chat.id,
                             "⛔️Err: Message must be str\n"
                             "Please enter crypto correct!")
            bot.register_next_step_handler(message, enter_name_of_add_crypto)


def enter_count_of_add_crypto(message):
    response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={MyStates.crypto}USDT").json()
    user = User.get(User.chat_id == message.chat.id)
    if message.text == '⬅️ Return to enter crypto to buy':
        work_with_buttons(message)
    else:
        count = message.text
        if count.isdigit() and user.remain_money >= float(count) * float(response["price"]):
            MyStates.count = count
            submit_buy_data(message)
            bot.send_message(message.chat.id,
                             "Crypto has been added")
            create_main_menu(message, "You are in main menu!")
            print(f"{MyStates.crypto} : {MyStates.count}")
        elif not count.isdigit():
            msg = bot.send_message(message.chat.id,
                                   "⛔️ ERR: Number symbol isn't digit!\n"
                                   f"Enter count of crypto")
            bot.register_next_step_handler(msg, enter_count_of_add_crypto)
        else:
            msg = bot.send_message(message.chat.id,
                                   "⛔️ ERR: Not enough money!\n"
                                   f"Enter count of crypto")
            bot.register_next_step_handler(msg, enter_count_of_add_crypto)


def submit_buy_data(message):
    user = User.get(User.chat_id == message.chat.id)
    response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={MyStates.crypto}USDT").json()
    if Crypto.select().where(Crypto.name_crypto == MyStates.crypto, Crypto.foreign_key == user):
        # Update count, price of crypto and remain money in customer wallet
        query = Crypto.update(count_crypto=Crypto.count_crypto + int(MyStates.count)
                              ).where(Crypto.name_crypto == MyStates.crypto, Crypto.foreign_key == user)
        query.execute()
        query2 = Crypto.update(price_crypto=Crypto.count_crypto * Crypto.price_per_crypto
                               ).where(Crypto.name_crypto == MyStates.crypto, Crypto.foreign_key == user)
        query2.execute()
        query3 = User.update(remain_money=round(float(user.remain_money) -
                                                (float(MyStates.count) * float(response["price"])), 3)
                             ).where(User.chat_id == message.chat.id)
        query3.execute()

    else:
        # If database doesn't have any data about your transaction, it creates new rows
        Crypto.create(
            name_crypto=MyStates.crypto,
            price_per_crypto=response["price"],
            count_crypto=int(MyStates.count),
            price_crypto=round(float(response["price"]) * float(MyStates.count), 3),
            foreign_key=user
        )
        query3 = User.update(remain_money=round(float(user.remain_money) -
                                                (float(MyStates.count) * float(response["price"])), 3)
                             ).where(User.chat_id == message.chat.id)
        query3.execute()


def enter_name_of_sell_crypto(message):
    user = User.get(User.chat_id == message.chat.id)
    cryptos = Crypto.select().where(Crypto.foreign_key == user)
    is_found = False
    if message.text == '⬅️ Return back':
        create_main_menu(message, "You are in main menu")
    else:
        if message.text.isidentifier():
            for crypto in cryptos:
                if message.text.upper() in crypto.name_crypto:
                    MyStates.crypto = message.text.upper()
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    item1 = types.KeyboardButton('⬅️ Return to enter crypto to sell')
                    markup.add(item1)
                    bot.send_message(message.chat.id,
                                     "Enter count you want to sell:", reply_markup=markup)
                    bot.register_next_step_handler(message, enter_count_of_sell_crypto)
                    is_found = True
            if not is_found:
                bot.send_message(message.chat.id,
                                 "⛔️ Error: Crypto isn't found\n"
                                 "Please enter name of crypto correct")
                bot.register_next_step_handler(message, enter_name_of_sell_crypto)
        else:
            bot.send_message(message.chat.id,
                             "⛔️ Error: Message must be string\n"
                             "Please enter name of crypto correct")
            bot.register_next_step_handler(message, enter_name_of_sell_crypto)


def enter_count_of_sell_crypto(message):
    user = User.get(User.chat_id == message.chat.id)
    cryptos = Crypto.get(Crypto.foreign_key == user, Crypto.name_crypto == MyStates.crypto)
    if message.text == '⬅️ Return to enter crypto to sell':
        work_with_buttons(message)

    else:
        if message.text.isdigit():
            if cryptos.count_crypto > int(message.text):
                data = cryptos.count_crypto - int(message.text)
                submit_sell_data(message, data)
                bot.send_message(message.chat.id, "Crypto have been successfully sold!")
                create_main_menu(message, "You are in main menu")

            elif cryptos.count_crypto == int(message.text):
                data = cryptos.count_crypto - int(message.text)
                submit_sell_data(message, data)
                cryptos.delete_instance()
                bot.send_message(message.chat.id, "Crypto have been successfully sold!")
                create_main_menu(message, "You are in main menu")

            else:
                bot.send_message(message.chat.id, "⛔️ Error: the number you specified is higher than you have\n"
                                                  "Please enter count of crypto correct")
                bot.register_next_step_handler(message, enter_count_of_sell_crypto)

        else:
            bot.send_message(message.chat.id, "⛔️ Error: Message must be digit\n"
                                              "Please enter count of crypto correct")
            bot.register_next_step_handler(message, enter_count_of_sell_crypto)


def submit_sell_data(message, data):
    user = User.get(User.chat_id == message.chat.id)
    cryptos = Crypto.get(Crypto.foreign_key == user, Crypto.name_crypto == MyStates.crypto)
    query = Crypto.update(count_crypto=data
                          ).where(Crypto.foreign_key == user, Crypto.name_crypto == MyStates.crypto)
    query2 = Crypto.update(price_crypto=Crypto.price_per_crypto * Crypto.count_crypto
                           ).where(Crypto.foreign_key == user, Crypto.name_crypto == MyStates.crypto)
    query3 = User.update(remain_money=User.remain_money + round(float(message.text) * float(cryptos.price_per_crypto),
                                                                3)
                         ).where(User.chat_id == message.chat.id)
    query.execute()
    query2.execute()
    query3.execute()


def find_crypto(message):
    data = [f"All cryptos at your request '{message.text}':"]
    cryptos = requests.get("https://api.binance.com/api/v3/ticker/price").json()
    markup = types.ReplyKeyboardRemove()
    if message.text == '⬅️ Return back':
        create_main_menu(message, "You are in main menu")
    else:
        if message.text.isidentifier():
            for crypto in cryptos:
                if message.text.upper() + "USDT" in crypto['symbol']:
                    data.append(f"📊 {crypto['symbol'][:len(crypto['symbol']) - 4]} : "
                                f"💰 {round(float(crypto['price']), 3)}")
            if len(data) == 1:
                data.append("No suggests")
            if len("\n".join(data)) > 4095:
                for x in range(0, len("\n".join(data)), 4095):
                    bot.send_message(message.chat.id, text="\n".join(data)[x:x + 4095], reply_markup=markup)
            else:
                bot.send_message(message.chat.id, "\n".join(data), reply_markup=markup)
            create_main_menu(message, bot_answer="You are in main menu")
        else:
            bot.send_message(message.chat.id,
                             "⛔️ Error: Message must be string\n"
                             "Enter name or part of crypto")
            bot.register_next_step_handler(message, find_crypto)


def stats_crypto(message):
    data = ["All cryptos in our crypto exchange:"]
    cryptos = requests.get("https://api.binance.com/api/v3/ticker/price").json()
    for crypto in cryptos:
        if "USDT" in crypto['symbol']:
            data.append(
                f"📊{crypto['symbol'][:len(crypto['symbol']) - 4]}:"
                f"{('%f' % float(crypto['price'])).rstrip('0').rstrip('.')}$")
        else:
            pass
    if len("\n".join(data)) > 4095:
        for x in range(0, len("\n".join(data)), 4095):
            bot.send_message(message.chat.id, text="\n".join(data)[x:x + 4095])
    else:
        bot.send_message(message.chat.id, "\n".join(data))


def show_crypto(message):
    user = User.get(User.chat_id == message.chat.id)
    cryptos = Crypto.select().where(Crypto.foreign_key == user)
    update_price(message)
    user_assets_crypto = 0
    if cryptos:
        for crypto in cryptos:
            user_assets_crypto += crypto.price_crypto
    message_text = [f"👋 Hi, {message.from_user.first_name or ''} {message.from_user.last_name or ''}\n",
                    f"💼 Your assets: {round(user.remain_money + user_assets_crypto, 3)}$\n"
                    f"💵 Remain money: {round(user.remain_money, 3)}$\n"
                    f"📊Your Cryptos: \n\n"]
    if cryptos:
        for crypto in cryptos:
            message_text.append(f"📊 Crypto : {crypto.name_crypto}\n"
                                f"💰 Price per crypto: {round(crypto.price_per_crypto, 3)}$"
                                f"| Count of crypto: {crypto.count_crypto} |"
                                f" 💰 Price of crypto: {round(crypto.price_crypto, 3)}$"
                                f"\n")
    else:
        message_text.append("You haven't any crypto!")
    bot.send_message(message.chat.id,
                     "".join(message_text))


def update_price(message):
    user = User.get(User.chat_id == message.chat.id)
    cryptos = Crypto.select().where(Crypto.foreign_key == user)
    for crypto in cryptos:
        response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={crypto.name_crypto}USDT").json()
        query = Crypto.update(price_per_crypto=round(float(response["price"]), 3)
                              ).where(Crypto.name_crypto == crypto.name_crypto, Crypto.foreign_key == user)
        query2 = Crypto.update(price_crypto=Crypto.price_per_crypto * Crypto.count_crypto
                               ).where(Crypto.name_crypto == crypto.name_crypto, Crypto.foreign_key == user)
        query.execute()
        query2.execute()


@bot.message_handler(content_types=['text'])
def work_with_buttons(message):
    if message.chat.type == 'private':
        if message.text == '💱 BUY Crypto':
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton('⬅️ Return back')
            markup.add(item1)
            bot.send_message(message.chat.id, 'Enter name of crypto', reply_markup=markup)
            bot.register_next_step_handler(message, enter_name_of_add_crypto)

        elif message.text == '💰 SELL Crypto':
            user = User.get(User.chat_id == message.chat.id)
            cryptos = Crypto.select().where(Crypto.foreign_key == user)
            if cryptos:
                data = ["You have:"]
                for crypto in cryptos:
                    data.append(f"Crypto: {crypto.name_crypto} Count: {crypto.count_crypto}")
                data.append("What crypto do you want to sell?")
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                item1 = types.KeyboardButton('⬅️ Return back')
                markup.add(item1)
                bot.send_message(message.chat.id, "\n".join(data), reply_markup=markup)
                bot.register_next_step_handler(message, enter_name_of_sell_crypto)
            else:
                create_main_menu(message, "You don't have anything to sell")

        elif message.text == '🔍 FIND Crypto':
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton('⬅️ Return back')
            markup.add(item1)
            bot.send_message(message.chat.id, 'Enter name or part of crypto', reply_markup=markup)
            bot.register_next_step_handler(message, find_crypto)

        elif message.text == '📊 STATS Crypto':
            stats_crypto(message)

        elif message.text == '🧿 SHOW Crypto':
            show_crypto(message)

        elif message.text == '⬅️ Return back':
            create_main_menu(message, "You are in main menu")

        elif message.text == '⬅️ Return to enter crypto to sell':
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton('⬅️ Return back')
            markup.add(item1)
            msg = bot.send_message(message.chat.id,
                                   "Enter the name of crypto",
                                   reply_markup=markup)
            bot.register_next_step_handler(msg, enter_name_of_sell_crypto)

        elif message.text == '⬅️ Return to enter crypto to buy':
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton('⬅️ Return back')
            markup.add(item1)
            msg = bot.send_message(message.chat.id,
                                   "Enter the name of crypto",
                                   reply_markup=markup)
            bot.register_next_step_handler(msg, enter_name_of_add_crypto)

        else:
            bot.send_message(message.chat.id,
                             "⛔️ I don't understand your command!")


bot.infinity_polling(timeout=100)
