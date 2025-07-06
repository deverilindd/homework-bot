import logging
import os
import requests
import time

from dotenv import load_dotenv
from telebot import TeleBot


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 10 * 60
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
    filename='bot.log',
    filemode='w',

)


class WrongCodeError(Exception):
    """Вернулся код, отличный от 200."""

    ...


def check_tokens():
    """Проверяет наличие переменных окружения."""
    if not all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        logging.critical('Отсутствует переменная окружения')
        return False
    else:
        return True


def send_message(bot, message):
    """Отправляет сообщение."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(
            f'Пользователю:{TELEGRAM_CHAT_ID} отправлено сообщение:"{message}"'
        )
    except Exception as e:
        logging.error(f'Ошибка при отправке сообщения {e}')
        raise


def get_api_answer(timestamp):
    """Делает запрос к API Практикума."""
    try:
        params = {'from_date': timestamp}
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params,
        )
        if response.status_code != 200:
            raise WrongCodeError

    except requests.RequestException:
        error_text = f'API вернул код {response.status_code}. URL: {ENDPOINT}'
        logging.error(error_text)
        raise requests.RequestException(error_text)
    except ValueError:
        error_text = 'Не удалось преобразовать ответ от API'
        logging.error(error_text)
        raise

    return response.json()


def check_response(response):
    """Проверка ответа от API."""
    yandex_homework_keys = (
        'homeworks',
        'current_date',
    )
    if not isinstance(response, dict):
        error_text = 'Ответ API не является словарем'
        logging.error(error_text)
        raise TypeError(error_text)
    for key in yandex_homework_keys:
        if key not in response:
            error_text = f'Ключ "{key}" отсутствует в ответе API'
            logging.error(error_text)
            raise KeyError(error_text)
    if not isinstance(response.get('homeworks'), list):
        error_text = 'Значение по ключу "homeworks" не является списком'
        logging.error(error_text)
        raise TypeError(error_text)


def parse_status(homework):
    """Поиск изменения статуса домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logging.error(
            f'Ключ {homework_name} отсутсвует'
        )
        raise
    try:
        homework_status = homework['status']
        verdict = HOMEWORK_VERDICTS[homework_status]
    except KeyError:
        logging.error(
            f'{homework_status} - невалидный статус'
        )
        raise KeyError

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_statuses = {}

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get('homeworks')
            if not homeworks:
                logging.debug('Статусы не изменились')
            else:
                for homework in homeworks:
                    homework_name = homework['homework_name']
                    now_status_message = parse_status(homework)
                    if last_statuses.get(homework_name) != now_status_message:
                        try:
                            send_message(bot, now_status_message)
                        except Exception as error:
                            logging.error(
                                f'Ошибка при отправке сообщения: {error}')
                        last_statuses[homework_name] = now_status_message
            timestamp = int(response.get('current_date', timestamp))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
