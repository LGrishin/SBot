"""Main"""

from datetime import datetime
from telebot import TeleBot
from requests import post
import numpy as np
import matplotlib.pyplot as plt
from config import TOKEN, WINDY_API_KEY

bot = TeleBot(TOKEN)


@bot.message_handler(commands=['start'])  # /start
def welcome(message):
    """Welcome  message"""
    bot.send_message(message.chat.id,
                     "Привет! Отправь мне свою геолокацию для получения данных о погоде! "
                     "Если хочешь узнать больше, используй /help")


@bot.message_handler(commands=['help'])  # /help
def help_inf(message):
    """Help message"""
    bot.send_message(message.chat.id,
                     "Данный бот позволяет получить информацию о погодных"
                     "условиях для твоей геолокации."
                     "Данные предоставляются в формате [время, температура, осадки, "
                     "скорость "
                     "ветра, направление ветра]. Так же прилагаются графики"
                     "динамики температуры и осадков.\n"
                     "Чтобы получить данные, просто "
                     "отправь отправь боту свою геолокацию. Информация о погоде"
                     "получена с сайта windy.com")


@bot.message_handler(content_types=['text'])  # любой текст
def lalala(message):
    """Help message 2"""
    bot.send_message(message.chat.id, "Чтобы получить данные о погоде, отправь свою геолокацию.")


def get_data_from_windy(loc):  # отправка запроса в windy.com через API
    """Get data for location"""
    data = {"lat": loc[1],
            "lon": loc[0],
            "model": "gfs",
            "parameters": ["temp", "wind", "precip"],
            # "levels": ["150h"],
            "key": WINDY_API_KEY
            }
    header = {"Content-Type": "application/json"}
    result = post("https://api.windy.com/api/point-forecast/v2", json=data, headers=header)
    return result


def data_processing(data):  # Обработка полученных данных
    """Data processing"""
    weather_values = data.json()
    # преобразование времени из ms в s
    weather_values['ts'] = [int(i / 1000) + 25200 for i in weather_values['ts']]
    # преобразование температуры из K в °C
    weather_values['temp-surface'] = [int(i - 273.15) for i in
                                      weather_values['temp-surface']]
    weather_values['wind_u-surface'] = np.array(weather_values['wind_u-surface'])
    weather_values['wind_v-surface'] = np.array(weather_values['wind_v-surface'])
    return weather_values


def answer(weather_values):
    """prepare answer"""
    wind_direction = []
    for i in range(weather_values['wind_u-surface'].size):  # Определение направления ветра
        if weather_values['wind_u-surface'][i] >= 0 and weather_values['wind_v-surface'][i] >= 0:
            wind_direction.append('ЮЗ')  # юго-западный
        elif weather_values['wind_u-surface'][i] < 0 <= weather_values['wind_v-surface'][i]:
            wind_direction.append('ЮВ')  # юго-восточный
        elif weather_values['wind_v-surface'][i] < 0 <= weather_values['wind_u-surface'][i]:
            wind_direction.append('СЗ')  # северо-западный
        elif weather_values['wind_u-surface'][i] < 0 and weather_values['wind_v-surface'][i] < 0:
            wind_direction.append('СВ')  # северо-восточный

    wind_u = np.power(weather_values['wind_u-surface'], 2)
    wind_v = np.power(weather_values['wind_v-surface'], 2)
    wind_speed = np.power(wind_v + wind_u, 1 / 2)  # вычисляем длину вектора ветра

    time = []
    for i in weather_values['ts']:
        time.append(datetime.utcfromtimestamp(i).strftime('%Y-%m-%d %H:%M:%S')[
                    11:16])  # переводим время из unix в нормальный формат

    text = 'Погода на ближайшие сутки:\n\n'
    plot_time = np.array(time[:8])
    # заготовки для построения графиков
    temp_surface = np.array(weather_values['temp-surface'][:8])
    precip_surface = np.array(weather_values['past3hprecip-surface'][:8])

    for i in range(9):  # формирование ответа
        text += time[i] + '  ' + str(weather_values['temp-surface'][i]) + '°C  ' + \
                str(float(weather_values['past3hprecip-surface'][i]))[:3] + 'mm  ' \
                + str(wind_speed[i])[:3] + 'm/s, ' + wind_direction[i] + '\n\n'

    plt.plot(plot_time, temp_surface, color='r')
    plt.savefig('temperature_dynamics.png',
                dpi=100)  # перезаписываем графики в фотки чтобы потом отправить пользователю
    plt.clf()
    plt.ylim(ymin=0)
    plt.plot(plot_time, precip_surface, color='m')
    plt.savefig('Precipitation_dynamics.png', dpi=100)
    return text


def send_image(chat_id):  # отправляем фотки пользователю
    """Send images"""
    with open('temperature_dynamics.png', 'rb') as photo_1:
        bot.send_photo(chat_id, photo=photo_1, caption="Динамика температуры")

    with open('Precipitation_dynamics.png', 'rb') as photo_2:
        bot.send_photo(chat_id, photo=photo_2, caption="Динамика осадков")


@bot.message_handler(content_types=['location'])
def location(message):
    """prepare location"""
    if message.location is not None:
        # получаем координаты из геолокации
        loc = [message.location.longitude, message.location.latitude]
        data = get_data_from_windy(loc)  # отправляем API запрос для данных координат
        weather_values = data_processing(data)  # обрабатываем данные и приводим к удобному виду
        text = answer(weather_values)  # формируем ответ пользователю
        bot.send_message(message.chat.id, text)  # отправляем сообщение с прогнозом
        send_image(message.chat.id)  # отправляем графики пользователю


bot.polling(none_stop=True)
