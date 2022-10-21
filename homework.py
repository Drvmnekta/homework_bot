"""Bot for notifying about change of homework status."""

import logging
import os
import time
from http import HTTPStatus
from xmlrpc.client import Boolean

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
WEEK_TIMESTAMP = 604800
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

homework_verdicts = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.INFO,
)

logger = logging.getLogger(__name__)
log_handler = logging.StreamHandler()
logger.addHandler(log_handler)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Send message to telegram chat.

    Args:
        bot: telegram bot instance;
        message: text of message to send.
    """
    logger.info('Try to send message...')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except exceptions.SendMessageFailure:
        logger.error('Error while sending message to chat.')
    logger.info('Message sent.')


def get_api_answer(current_timestamp: int) -> dict:
    """Get API response.

    Args:
        current_timestamp: timestamp to get status for.

    Returns:
        API response in JSON format.
    """
    timestamp = current_timestamp
    request_params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=headers, params=request_params,
        )
    except exceptions.APIResponseStatusCodeException:
        logger.error('Сбой при запросе к эндпоинту')
    if response.status_code != HTTPStatus.OK:
        msg = 'Сбой при запросе к эндпоинту'
        raise exceptions.APIResponseStatusCodeException(msg)
    return response.json()


def check_response(response: dict) -> dict:
    """Check if API response is valid.

    Args:
        response: API response to check.

    Returns:
        homeworks from the valid response.
    """
    try:
        homeworks_list = response['homeworks']
    except KeyError as key_error:
        msg = f'Ошибка доступа по ключу homeworks: {key_error}'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if homeworks_list is None:
        msg = 'В ответе API нет словаря с домашками'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if not homeworks_list:
        msg = 'За последнее время нет домашек'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if not isinstance(homeworks_list, list):
        msg = 'В ответе API домашки представлены не списком'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    return homeworks_list


def parse_status(homework: dict) -> str:
    """Get homework status from API response.

    Args:
        homework: part of response with homework info.

    Returns:
        prepared message with status info.
    """
    try:
        homework_name = homework.get('homework_name')
    except KeyError as key_error:
        msg = f'Ошибка доступа по ключу homework_name: {key_error}'
        logger.error(msg)
    try:
        homework_status = homework.get('status')
    except KeyError as key_error:
        msg = f'Ошибка доступа по ключу status: {key_error}'
        logger.error(msg)

    verdict = homework_verdicts[homework_status]
    if verdict is None:
        msg = 'Неизвестный статус домашки'
        logger.error(msg)
        raise exceptions.UnknownHWStatusException(msg)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> Boolean:
    """Check if all needed environment variables are avaliable.

    Returns:
        Boolean for all env information is avaliable.
    """
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Main bot logic."""
    if not check_tokens():
        msg = 'Отсутствует необходимая переменная среды'
        logger.critical(msg)
        raise exceptions.MissingRequiredTokenException(msg)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - WEEK_TIMESTAMP)
    previous_status = None
    previous_error = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
        except exceptions.IncorrectAPIResponseException as incorrect_response:
            if str(incorrect_response) != previous_error:
                previous_error = str(incorrect_response)
                send_message(bot, incorrect_response)
            logger.error(incorrect_response)
            time.sleep(RETRY_TIME)
            continue
        try:
            homeworks = check_response(response)
            hw_status = homeworks[0].get('status')
            if hw_status == previous_status:
                logger.debug('Обновления статуса нет')
            else:
                previous_status = hw_status
                message = parse_status(homeworks[0])
                send_message(bot, message)

            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if previous_error != str(error):
                previous_error = str(error)
                send_message(bot, message)
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
