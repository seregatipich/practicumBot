import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщение в чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logger.info('Сообщение успешно отправлено')
    except (TypeError, NameError, AttributeError, Exception) as error:
        message = f'Ошибка отправки сообщения: {error}'
        logger.error(message)


def get_api_answer(current_timestamp):
    """Делаем запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            message = 'API недоступна: status code is not OK'
            logger.error(message)
            raise Exception(message)
        return response.json()
    except (
        json.decoder.JSONDecodeError,
        requests.exceptions.RequestException,
        Exception
    ) as error:
        message = f'Ошибка обращения к API: {error}'
        logger.error(message)
        raise Exception(message)


def check_response(response):
    """Проверяем ответ API на корректность."""
    if not isinstance(response, dict):
        message = 'Недопустимый тип ответа API'
        logger.error(message)
        raise TypeError(message)
    if not isinstance(response['homeworks'], list):
        message = 'Недопустимый тип ответа API'
        logger.error(message)
        raise TypeError(message)
    try:
        return response['homeworks']
    except KeyError as error:
        message = f'Ошибка проверки ответа API: {error}'
        logger.error(message)
        raise Exception(message)


def parse_status(homework):
    """Извлекаем статус из конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        message = 'Отсутствует ключ homework_name'
        logger.error(message)
        raise KeyError(message)
    homework_status = homework.get('status')
    if homework_status is None:
        message = 'Отсутствует ключ status'
        logger.error(message)
        raise KeyError(message)
    if homework_status not in VERDICTS:
        message = 'Неизвестный статус домашней работы'
        logger.error(message)
        raise KeyError(message)
    verdict = VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность переменных окружения."""
    tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    return all(tokens)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствует переменная окружения'
        logger.critical(message)
        raise Exception(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                last_homework = homeworks[0]
                message = parse_status(last_homework)
                send_message(bot, message)
            current_timestamp = response.get('current_date')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != last_message:
                send_message(bot, message)
                logger.error(message)
                last_message = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
