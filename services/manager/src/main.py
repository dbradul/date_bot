import time
import functools
import logging
import re
import subprocess
from enum import Enum
from itertools import islice

from bot import bot

import config
from utils import reverse_readline, upsert_gentlemen_by_profile_id

_logger =  logging.getLogger('manager')
_logger.addHandler(logging.StreamHandler())

_allowed_users = {
    545573346: 'User1',
    229253199: 'User2',
}

LOG_NUM_RECORDS = 10
LOG_FILE = '/app/log/logfile.log'

class State(Enum):
    STARTED = 'started'
    STOPPED = 'stopped'
    UNKNOWN = 'unknown'


state = State.UNKNOWN


class Commands(Enum):
    # START = 'start'
    STOP = 'stop'
    RESTART = 'restart'
    # STATS = 'stats'
    LOGS = 'log'
    ADD_MEN_IDS = 'add'
    SET_RESUME_FROM_ID = 'set_resume_from_id'
    # TEST = 'test'
    # SCREENSHOT = 'screen'

    @classmethod
    def list(cls):
        return '/' + '\n/'.join(c.value for c in cls)


def is_authorized(f):
    @functools.wraps(f)
    def inner(message):
        if message.from_user.id not in _allowed_users:
            bot.send_message(message.chat.id, f"Don't know who you are. Please, contact author.")
            return
        elif _allowed_users[message.from_user.id]:
            bot.send_message(message.chat.id, f'Hi, {message.from_user.first_name}! 👋 Nice to see you back! 🙃')
            _allowed_users[message.from_user.id] = ''
        return f(message)

    return inner


# @bot.message_handler(commands=[Commands.START.value])
# @is_authorized
def start_message(message):
    global state
    bot.send_message(message.chat.id, f"Starting sending emails...")
    # subprocess.call(['docker-compose', 'up', '-d'])
    subprocess.call(['docker', 'start', 'date_bot_browser_1'])
    subprocess.call(['docker', 'start', 'date_bot_sender_1'])
    state = State.STARTED
    bot.send_message(message.chat.id, f"Sending email has been started!")


@bot.message_handler(commands=[Commands.STOP.value])
@is_authorized
def stop_message(message):
    global state
    bot.send_message(message.chat.id, f"Stopping sending emails...")
    # subprocess.call(['docker-compose', 'down', '-t', '0'])
    subprocess.call(['docker', 'stop', 'date_bot_sender_1', '-t', '0'])
    subprocess.call(['docker', 'stop', 'date_bot_browser_1', '-t', '0'])
    state = State.STOPPED
    bot.send_message(message.chat.id, f"Sending emails has been stopped!")


@bot.message_handler(commands=[Commands.RESTART.value])
# @bot.message_handler(commands=[Commands.START.value])
@is_authorized
def restart_message(message):
    stop_message(message)
    start_message(message)


@bot.message_handler(commands=[Commands.LOGS.value])
@is_authorized
def logs_message(message):
    bot.send_message(message.chat.id, f"Collecting bot logs...")
    num_records = LOG_NUM_RECORDS
    if m := re.match(f'/{Commands.LOGS.value} (\d+)', message.text):
        num_records = int(m.group(1))
    logs = [line for line in islice(reverse_readline(LOG_FILE), num_records)]
    bot.send_message(message.chat.id, '\n'.join(reversed(logs)))


@bot.message_handler(commands=[Commands.ADD_MEN_IDS.value])
@is_authorized
def add_men_ids_message(message):
    if state != State.STOPPED:
        bot.send_message(
            message.chat.id, 'Bot is already started or in unknown state! \nYou need to stop it before adding IDs.'
        )
        return

    if m := re.match(f'/{Commands.ADD_MEN_IDS.value} ([\d+ ]+)$', message.text):
        profile_id = None
        try:
            bot.send_message(message.chat.id, f"Adding men ids...")
            for profile_id in m.group(1).split():
                upsert_gentlemen_by_profile_id(int(profile_id))
            bot.send_message(message.chat.id, 'IDs have been successfully added/updated!')
        except Exception as e:
            if profile_id:
                bot.send_message(message.chat.id, f'ERROR: Something went wrong while adding ID {profile_id}: {e}')
            else:
                bot.send_message(message.chat.id, f'ERROR: Something went wrong while adding IDs: {e}')
    else:
        bot.send_message(
            chat_id=message.chat.id,
            text='Wrong format!\n Expected: integers delimited by space. \nExample: `/add 123 456 789`',
            parse_mode="Markdown",
        )

@bot.message_handler(commands=[Commands.SET_RESUME_FROM_ID.value])
@is_authorized
def set_resume_from_id(message):

    if m := re.match(f'/{Commands.SET_RESUME_FROM_ID.value} (\d+)$', message.text):
        resume_from_id = None
        try:
            bot.send_message(message.chat.id, f"Setting resume ID...")
            resume_from_id = int(m.group(1))
            config.set('RESUME_FROM_ID', resume_from_id)
            # for profile_id in m.group(1).split():
            #     upsert_gentlemen_by_profile_id(int(profile_id))
            bot.send_message(message.chat.id, 'Resume ID has been successfully set!')
        except Exception as e:
            bot.send_message(message.chat.id, f'ERROR: Something went wrong while setting resume ID {resume_from_id}: {e}')
    else:
        bot.send_message(
            chat_id=message.chat.id,
            text=f'Wrong format!\n Expected: integer. \nExample: `/{Commands.SET_RESUME_FROM_ID.value} 12345`',
            parse_mode="Markdown",
        )


# @bot.message_handler(commands=[Commands.SCREENSHOT.value])
# @is_known_user
# def screen_message(message):
#     bot.send_message(message.chat.id, '13.59.181.29:9222')


@bot.message_handler(content_types=['text', 'url'])
def send_text(message):
    bot.send_message(
        message.chat.id,
        f'Sorry! Did not get your request :(\n\nPlease, select one of the available commands:\n{Commands.list()}',
    )


if __name__ == "__main__":
    bot.polling()
    # while True:
    #     print('Sleeping...')
    #     _logger.info('Sleeping...')
    #     time.sleep(2)
    #     # command = input('Please, enter command: ')
    #     # match command:
    #     #     case 'start':
    #     #         _logger.info('start_message')
    #     #         start_message('')
    #     #     case 'stop':
    #     #         _logger.info('stop_message')
    #     #         stop_message('')
