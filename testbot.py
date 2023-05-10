import telebot
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
import time
import sqlite3
import os 
import schedule

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if TOKEN is None:
    raise ValueError("BOT_TOKEN environment variable is not set.")

bot = telebot.TeleBot(TOKEN)

default_source = "https://ria.ru/export/rss2/index.xml"
n_news = 5
sources = {
    "РИА": "https://ria.ru/export/rss2/index.xml",
    "Лента.ru": "https://lenta.ru/rss",
    "ТАСС": "http://tass.ru/rss/v2.xml",
}

logging.basicConfig(
    level=logging.ERROR,
    filename="news_fetch_errors.log",
    format="%(levelname)s: %(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)



def fetch_and_add_news(source=default_source):
    try:       
        conn = sqlite3.connect('news.db')
        cursor = conn.cursor()
        response = requests.get(source)
        soup = BeautifulSoup(response.text, features="xml")
        items = soup.findAll("item")[:10]
        for item in items:
            cursor.execute("INSERT INTO news (title, link) VALUES (?, ?)", (item.title.text, item.link.text))
        conn.commit()
        news = [(item.title.text, item.link.text) for item in items]
        conn.close()
        return news
    except (sqlite3.Error, requests.exceptions.RequestException) as e:
        logging.error(f"Failed to fetch news from {source}. Error: {e}")
        return []



def update_news():
    news = fetch_and_add_news(source)



def add_news(title, link):
    try:
        conn = sqlite3.connect('news.db')
        cursor = conn.cursor()
        query = "INSERT INTO news (title, link) VALUES (?, ?)"
        cursor.execute(query, (title, link))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Failed to add news to database. Error: {e}")


@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.send_message(message.chat.id, "Привет! Этот бот позволяет получать новости из различных источников. "
                                      "Для получения списка доступных источников и выбора источника используйте команду /from_source. "
                                      "Доступные команды: /from_source, /get, /update_n, /default,'/subscribe','/unsubscribe','/subscriptions'")


@bot.message_handler(commands=['from_source'])
def from_source_handler(message):
    source_kb = telebot.types.InlineKeyboardMarkup()
    for source_name in sources:
        source_button = telebot.types.InlineKeyboardButton(text=source_name, callback_data='source ' + sources[source_name])
        source_kb.add(source_button)
    bot.send_message(message.chat.id, 'Выберите источник:', reply_markup=source_kb)


@bot.callback_query_handler(func=lambda call: call.data.split()[0] == 'source')
def source_handler(call):
    source = call.data.split()[1]
    news = fetch_and_add_news(source)
    if len(news) < 1:
        response_text = "К сожалению, новостей не обнаружено."
    else:
        response_text = "Вот последние новости:"
        for n in range(min(n_news, len(news))):
            response_text = '\n'.join([response_text, f"\n{n + 1}. {news[n][0]}\n<a href='{news[n][1]}'>Источник: " + str(news[n][1]).rpartition('.ru')[0] + '.ru'+"</a>"])
    default_kb = telebot.types.InlineKeyboardMarkup()
    default_button = telebot.types.InlineKeyboardButton(text='Выбрать как источник по умолчанию', callback_data='default ' + source)
    default_kb.add(default_button)

    bot.send_message(call.message.chat.id, response_text, reply_markup=default_kb, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data.split()[0] == 'default')
def default_handler(call):
    global default_source
    default_source = call.data.split()[1]
    bot.send_message(call.message.chat.id, f'Источник по умолчанию теперь '+ str(default_source).rpartition('.ru')[0] + '.ru')


@bot.message_handler(commands=['update_n'])
def update_n_handler(message):
    bot.send_message(message.chat.id, 'Введите количество новостей (от 1 до 10):')


@bot.message_handler(func=lambda message: message.text.isdigit() and int(message.text) in range(1, 11))
def n_set_handler(message):
    global n_news
    n_news = int(message.text)
    bot.send_message(message.chat.id, f'Количество новостей, выводимых за раз, теперь равно {n_news}.')


@bot.message_handler(commands=['default'])
def default_source_handler(message):
    bot.send_message(message.chat.id, f'Источник новостей по умолчанию:' + str(default_source).rpartition('.ru')[0] + '.ru')


@bot.message_handler(commands=['get'])
def get_news_handler(message):
    news = fetch_and_add_news(default_source)
    if len(news) < 1:
        response_text = "К сожалению, новостей не обнаружено."
    else:
        response_text = "Вот последние новости:"
        for n in range(min(n_news, len(news))):
            response_text = '\n'.join([response_text, f"\n{n + 1}. {news[n][0]}\n<a href='{news[n][1]}'>Источник: " + str(news[n][1]).rpartition('.ru')[0] + '.ru'+"</a>"])
    bot.send_message(message.chat.id, response_text, parse_mode='HTML')

subscriptions = {}

@bot.message_handler(commands=['subscribe'])
def subscribe_handler(message):
    source_kb = telebot.types.InlineKeyboardMarkup()
    for source_name in sources:
        source_button = telebot.types.InlineKeyboardButton(text=source_name, callback_data='subscribe ' + source_name)
        source_kb.add(source_button)
    bot.send_message(message.chat.id, 'Выберите источник для подписки:', reply_markup=source_kb)

@bot.callback_query_handler(func=lambda call: call.data.split()[0] == 'subscribe')
def subscribe_user(call):
    source = call.data.split()[1]
    if source in sources:
        if source not in subscriptions:
            subscriptions[source] = set()
        subscriptions[source].add(call.message.chat.id)
        bot.send_message(call.message.chat.id, f"Вы успешно подписались на новости {source}, теперь каждые 5 минут вам будут приходит актуальные новости с данного источника")
        newsource = sources[source]
        while True:
            news = fetch_and_add_news(newsource)
            for source in subscriptions:
                for chat_id in subscriptions[source]:
                    if len(news) < 1:
                        response_text = "К сожалению, новостей не обнаружено."
                    else:
                        response_text = "Вот последние новости:"
                        for n in range(min(n_news, len(news))):
                            response_text = '\n'.join([response_text, f"\n{n + 1}. {news[n][0]}\n<a href='{news[n][1]}'>Источник: " + str(news[n][1]).rpartition('.ru')[0] + '.ru'+"</a>"])
                        default_kb = telebot.types.InlineKeyboardMarkup()
                        bot.send_message(call.message.chat.id, response_text, reply_markup=default_kb, parse_mode='HTML')

            time.sleep(300)

        conn = sqlite3.connect('news.db')
        cursor = conn.cursor()

        query = "INSERT INTO users (chat_id, source) VALUES (?, ?)"
        values = (call.message.chat.id, source)
        cursor.execute(query, values)
        conn.commit()

        cursor.close()
        conn.close()

@bot.message_handler(commands=['unsubscribe'])
def unsubscribe_handler(message):
    source_kb = telebot.types.InlineKeyboardMarkup()
    for source_name in subscriptions:
        if message.chat.id in subscriptions[source_name]:
            source_button = telebot.types.InlineKeyboardButton(text=source_name, callback_data='unsubscribe ' + source_name)
            source_kb.add(source_button)
    if len(subscriptions) > 0:
        bot.send_message(message.chat.id, 'Выберите источник для отписки:', reply_markup=source_kb)
    else:
        bot.send_message(message.chat.id, "У вас нет подписок для отписки.")
    
@bot.callback_query_handler(func=lambda call: call.data.split()[0] == 'unsubscribe')
def unsubscribe_user(call):
    source = call.data.split()[1]
    if source in subscriptions and call.message.chat.id in subscriptions[source]:
        subscriptions[source].remove(call.message.chat.id)
        bot.send_message(call.message.chat.id, f"Вы успешно отписались от новостей {source}.")

        conn = sqlite3.connect('news.db')
        cursor = conn.cursor()

        query = "DELETE FROM users WHERE chat_id=? AND source=?"
        values = (call.message.chat.id, source)
        cursor.execute(query, values)
        conn.commit()

        cursor.close()
        conn.close()
    else:
        bot.send_message(call.message.chat.id, f"Вы не подписаны на новости {source}.")

@bot.message_handler(commands=['subscriptions'])
def list_subscriptions(message):
    subscription_list = "Ваши подписки:\n"
    if len(subscriptions) > 0:
        for source in subscriptions:
            if message.chat.id in subscriptions[source]:
                subscription_list += f"- {source}\n"
        bot.send_message(message.chat.id, subscription_list)
    else:
        bot.send_message(message.chat.id, "У вас пока нет подписок.")



bot.polling(none_stop=True)


