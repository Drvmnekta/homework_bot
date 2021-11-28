import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

# from logging.handlers import RotatingFileHandler


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.INFO,
    # filename='main.log',
    # filemode='w'
)

logger = logging.getLogger(__name__)
# handler = RotatingFileHandler('main.log', maxBytes=50000000, backupCount=2)
handler = logging.StreamHandler()
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение в чат отправлено')
    except Exception:
        logger.error('Сбой при отправке сообщения в чат')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту."""
    timestamp = current_timestamp or int(time.time())
    # timestamp = 0
    params = {'from_date': timestamp}

    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        msg = 'Сбой при запросе к эндпоинту'
        logger.error(msg)
        raise Exception(msg)
    response = response.json()
    return response


def check_response(response):
    """Проверяет ответ API на корректность."""
    homeworks_dict = response['homeworks']
    if homeworks_dict is None:
        msg = 'В ответе API нет словаря с домашками'
        logger.error(msg)
        raise Exception(msg)
    if homeworks_dict == []:
        msg = 'За последнее время нет домашек'
        logger.error(msg)
        raise Exception(msg)
    if not isinstance(homeworks_dict, list):
        msg = 'В ответе API домашки представлены не списком'
        logger.error(msg)
        raise Exception(msg)
    return homeworks_dict


def parse_status(homework):
    """Извлекает из информации о домашке ее статус."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    # ...

    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        msg = 'Неизвестный статус домашки'
        logger.error(msg)
        verdict = 'Неизвестный статус'
        raise Exception(msg)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN]):
        return True
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        msg = 'Отсутствует необходимая переменная среды'
        logger.critical(msg)
        raise Exception(msg)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    previous_response = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            check_response(response)
            if response != previous_response:
                message = parse_status(response.get('homeworks')[0])
                send_message(bot, message)
            else:
                logger.debug('Обновления статуса нет')

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        # else:
        #    ...


if __name__ == '__main__':
    main()
