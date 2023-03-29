import os
import sys
import logging
import time
from dotenv import load_dotenv
from http import HTTPStatus

import requests
import telegram

import exceptions

load_dotenv()


PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
handler.setFormatter(formatter)


RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS: dict[str, str] = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Функция для проверки наличия необходимых переменных окружения."""
    list_env_vars = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
    if not all(list_env_vars):
        logger.critical('Отсутствует переменная окружения')
        raise exceptions.MissingEnviromentVariable(
            'Отсутствует переменная окружения'
        )
    return True


def send_message(bot: telegram.Bot, message: str) -> None:
    """Функция для отправки сообщения в чат телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение в телеграмм успешно отправлено')
    except Exception:
        logger.error('Ошибка при отправке сообщение в чат телеграмм')
        raise exceptions.SendMessageError(
            'Ошибка при отправке сообщение в чат телеграмм'
        )


def get_api_answer(timestamp: int) -> dict:
    """Функция для отправки запроса к API ЯП."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params={
            'from_date': timestamp
        })
    except requests.exceptions.RequestException:
        raise exceptions.GetRequestError('Сбой при запросе к эндпоинту')
    if response.status_code != HTTPStatus.OK:
        raise exceptions.StatusCodeNotOK(
            f'Статус запроса не ОК! Статус запроса: {response.status_code}'
        )
    try:
        answer = response.json()
    except Exception:
        raise exceptions.JsonConvertingError('Ошибка при представлении json')
    else:
        return answer


def check_response(response: dict) -> bool:
    """Функция для проверки корректности ответа API."""
    try:
        logger.info('Проверяем ответ API: TRY')
        homeworks = response['homeworks']
        response['current_date']
    except KeyError:
        raise KeyError('Отсутствуют ожидаемые ключи в ответе API')
    if not isinstance(homeworks, list):
        raise TypeError('Значение ключа ответа API - не список')
    elif len(homeworks) > 0:
        if homeworks[0]['status'] not in HOMEWORK_VERDICTS:
            raise exceptions.NoMatchStatusHomework(
                'Неизвестный статус домашней работы в ответе API'
            )
        else:
            logger.info('Проверяем ответ API: OK')
            return True
    else:
        logger.info('Проверяем ответ API: OK (No changes)')
    return False


def parse_status(homework: dict) -> str:
    """Функция для подготовки сообщения для отправки в чат телеграмм."""
    if isinstance(homework, dict):
        for key in ['homework_name', 'status']:
            if key not in homework:
                raise KeyError(
                    f'В homework не оказалось ключа {key}'
                )
        homework_name = homework.get('homework_name')
        verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
        if not all((homework_name, verdict)):
            raise exceptions.IncorrectHomeworkStatus(
                'Пустой или недокументированный статус домашней работы'
            )
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        raise TypeError('homework не является словарем')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit(
            (
                'Программа остановлена. ',
                'Не обнаружены необходимые переменные окружения.'
            )
        )
    bot: telegram.Bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time())
    last_error = None

    while True:
        try:
            answer = get_api_answer(timestamp)
            if check_response(answer):
                send_message(bot, parse_status(answer['homeworks'][0]))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if str(error) != str(last_error):
                logger.error(message)
                last_error = error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
