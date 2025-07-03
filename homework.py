import logging
import os
import requests
import time

from dotenv import load_dotenv
from telebot import TeleBot, types


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] : %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S',

)


def check_tokens():
    """Проверяет наличие переменных окружения"""
    env_vars = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    is_vars_valid = True
    for var in env_vars.keys():
        if env_vars[var] is None:
            logging.critical(f'{var} - отсутсвует')
            is_vars_valid = False
    return is_vars_valid


def send_message(bot, message):
    """Отправляет сообщение"""
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    )


def get_api_answer(timestamp):
    """Делает запрос в API"""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        try:
            answer = response.json()
        except ValueError:
            error_text = 'Не удалось преобразовать овтет от API'
            logging.error(error_text)
            raise ValueError(error_text)
        error_text = None
        if response.status_code == 401:
            error_text = f'Ошибка API: {answer["message"]}'
        elif response.status_code == 400:
            error_text = f'Ошибка API: {answer["error"]["error"]}'
        elif response.status_code != 200:
            error_text = f'Ошибка API: статус {response.status_code}'
        if error_text:
            logging.error(error_text)
            raise requests.exceptions.HTTPError(error_text)
    except Exception as e:
        logging.error(f'Ошибка API: при обращении {e}')
        raise
    return answer


def check_response(response):
    """Проверка ответа от API"""
    yandex_homework_keys = (
        'homeworks',
        'current_date',
    )
    for key in yandex_homework_keys:
        if key not in response:
            logging.error(f'Ошибка ответа API: {key} отсутсвует')
            return False
    return True


def parse_status(homework):
    """Поиск изменения статуса домашней работы"""
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""

    if not check_tokens():
        exit(1)

    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = '123211'
    # timestamp = int(time.time())
    send_message(bot, 'ЗАПУЗЫРИЛОСЬ')
    while True:
        time.sleep(5)
        try:

            response = get_api_answer(timestamp)
            # logging.debug(response)
            if check_response:
                for homework in response['homeworks']:
                    send_message(bot, parse_status(homework))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        ...


if __name__ == '__main__':
    main()
