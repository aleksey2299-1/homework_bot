import os
import logging
import time
import sys
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('USER_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}


def check_tokens():
    """Токены должны быть."""
    if not all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        message = ('Отсутствует обязательная переменная окружения. '
                   'Программа принудительно остановлена.')
        logging.critical(message)
        raise Exception(message)


def send_message(bot, message):
    """Отправка непустого сообщения. Пустое логируется."""
    logging.debug(f'Попытка отправить сообщение "{message}"')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(f'Не удалось отправить сообщение. {error}')
    else:
        logging.debug(f'Бот отправил сообщение "{message}"')


def get_api_answer(timestamp):
    """Проверка ответа от сервера."""
    logging.debug(f'Попытка отправить запрос к {ENDPOINT}')
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )
    except telegram.error.TelegramError as error:
        raise telegram.error.TelegramError('Ошибка со стороный приложения. '
                                           f'{error}')
    except Exception as error:
        raise Exception(f'Страница {response.url} '
                        f'недоступна. Код ответа API: {error}')
    else:
        logging.debug(f'Запрос к {ENDPOINT} успешно отправлен')
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        raise Exception(f'Код ответа API: {response.status_code}')


def check_response(response):
    """Проверка валидности данных."""
    if not isinstance(response, dict):
        raise TypeError('Ответ от сервера ожидается в виде dict, '
                        f'а получен {type(response)}')
    if 'homeworks' not in response:
        raise Exception('Полученные от сервера '
                        'данные не соответствуют ожидаемым.')
    if 'current_date' not in response:
        raise Exception('Полученные от сервера '
                        'данные не соответствуют ожидаемым.')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('В ключе "homeworks" содержится не list')
    if not homeworks:
        logging.debug('Ничего нового')
        return
    else:
        return homeworks[0]


def parse_status(homework):
    """Создание текста сообщения."""
    if 'homework_name' not in homework:
        raise Exception('Отсутсвует ключ "homework_name"')
    if 'status' not in homework:
        raise Exception('Отсутсвует ключ "status"')
    if homework['status'] not in HOMEWORK_VERDICTS:
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
    duplicate_check = 'для проверки неповторяемости сообщения'

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                if duplicate_check != message:
                    send_message(bot, message)
                    duplicate_check = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if duplicate_check != message:
                send_message(bot, message)
                duplicate_check = message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
        filename='homework.log',
    )
    main()
