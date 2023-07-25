import os
import logging
import time
import sys

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='homework.log'
)

PRACTICUM_TOKEN = os.getenv('USER_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Токены должны быть."""
    if PRACTICUM_TOKEN is None:
        logging.critical('Отсутствует обязательная переменная окружения: '
                         '"PRACTICUM_TOKEN". Программа '
                         'принудительно остановлена.')
        raise Exception('Отсутсвует "PRACTICUM_TOKEN"')
    elif TELEGRAM_TOKEN is None:
        logging.critical('Отсутствует обязательная переменная окружения: '
                         '"TELEGRAM_TOKEN". Программа '
                         'принудительно остановлена.')
        raise Exception('Отсутсвует "TELEGRAM_TOKEN"')
    elif TELEGRAM_CHAT_ID is None:
        logging.critical('Отсутствует обязательная переменная окружения: '
                         '"TELEGRAM_CHAT_ID". Программа '
                         'принудительно остановлена.')
        raise Exception('Отсутсвует "TELEGRAM_CHAT_ID"')


def send_message(bot, message):
    """Отправка непустого сообщения. Пустое логируется."""
    try:
        logging.debug(f'Попытка отправить сообщение "{message}"')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение "{message}"')
    except Exception as error:
        logging.error(f'Не удалось отправить сообщение. {error}')


def get_api_answer(timestamp):
    """Проверка ответа от сервера."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )
    except Exception as error:
        logging.error(f'Сбой в работе программы: Эндпоинт {ENDPOINT} '
                      f'недоступен. Код ответа API: {error}')
        raise Exception(f'Сбой в работе программы: Эндпоинт {ENDPOINT} '
                        f'недоступен. Код ответа API: {error}')
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f'Код ответа API: {response.status_code}')
        raise Exception(f'Код ответа API: {response.status_code}')


def check_response(response):
    """Проверка валидности данных."""
    if type(response) != dict:
        logging.error('Ответ от сервера ожидается в виде dict, '
                      f'а получен {type(response)}')
        raise TypeError('Ответ от сервера ожидается в виде dict, '
                        f'а получен {type(response)}')
    if 'homeworks' not in response:
        logging.error('Сбой в работе программы: Полученные от сервера '
                      'данные не соответствуют ожидаемым.')
        raise Exception('Сбой в работе программы: Полученные от сервера '
                        'данные не соответствуют ожидаемым.')
    if 'current_date' not in response:
        logging.error('Сбой в работе программы: Полученные от сервера '
                      'данные не соответствуют ожидаемым.')
        raise Exception('Сбой в работе программы: Полученные от сервера '
                        'данные не соответствуют ожидаемым.')
    homeworks = response.get('homeworks')
    if type(homeworks) != list:
        logging.error('В ключе "homeworks" содержится не list')
        raise TypeError('В ключе "homeworks" содержится не list')
    if not homeworks:
        logging.debug('Ничего нового')
        return
    else:
        return homeworks[0]


def parse_status(homework):
    """Создание текста сообщения."""
    if 'homework_name' not in homework:
        logging.error('Отсутсвует ключ "homework_name"')
        raise Exception('Отсутсвует ключ "homework_name"')
    if 'status' not in homework:
        logging.error('Отсутсвует ключ "status"')
        raise Exception('Отсутсвует ключ "status"')
    if homework['status'] not in HOMEWORK_VERDICTS:
        logging.error('Неизвестный статус проверки домашней работы '
                      f'{homework["status"]}')
        raise Exception('Неизвестный статус проверки домашней работы '
                        f'{homework["status"]}')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except Exception:
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
