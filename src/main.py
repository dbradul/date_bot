import re

from itertools import islice

import functools
import subprocess
from bot import bot
from enum import Enum

from utils import reverse_readline, upsert_gentlemen_by_profile_id

clients = {
    545573346: 'Olga',
    229253199: 'Dmytro',
}

LOG_NUM_RECORDS = 10


class State(Enum):
    STARTED = 'started'
    STOPPED = 'stopped'
    UNKNOWN = 'unknown'


state = State.UNKNOWN


class Commands(Enum):
    START = 'start'
    STOP = 'stop'
    RESTART = 'restart'
    # STATS = 'stats'
    LOGS = 'log'
    ADD_MEN_IDS = 'add'
    # TEST = 'test'
    # SCREENSHOT = 'screen'

    @classmethod
    def list(cls):
        return '/' + '\n/'.join(c.value for c in cls)


def is_known_user(f):
    @functools.wraps(f)
    def inner(message):
        if message.from_user.id not in clients:
            bot.send_message(message.chat.id, f"Don't know who you are. Please, contact author.")
            return
        elif clients[message.from_user.id]:
            bot.send_message(message.chat.id, f'Hi, {message.from_user.first_name}! 👋 Nice to see you back! 🙃')
            clients[message.from_user.id] = ''
        return f(message)

    return inner


@bot.message_handler(commands=[Commands.START.value])
@is_known_user
def start_message(message):
    global state
    bot.send_message(message.chat.id, f"Starting sending emails...")
    subprocess.call(['docker-compose', 'up', '-d'])
    state = State.STARTED
    bot.send_message(message.chat.id, f"Sending email has been started!")


@bot.message_handler(commands=[Commands.STOP.value])
@is_known_user
def stop_message(message):
    global state
    bot.send_message(message.chat.id, f"Stopping sending emails...")
    subprocess.call(['docker-compose', 'down', '-t', '0'])
    state = State.STOPPED
    bot.send_message(message.chat.id, f"Sending emails has been stopped!")


@bot.message_handler(commands=[Commands.RESTART.value])
@is_known_user
def restart_message(message):
    stop_message(message)
    start_message(message)


@bot.message_handler(commands=[Commands.LOGS.value])
@is_known_user
def logs_message(message):
    bot.send_message(message.chat.id, f"Collecting bot logs...")
    num_records = LOG_NUM_RECORDS
    if m := re.match('/log (\d+)', message.text):
        num_records = int(m.group(1))
    logs = [line for line in islice(reverse_readline('./docker/sender/log/logfile.log'), num_records)]
    bot.send_message(message.chat.id, '\n'.join(reversed(logs)))


@bot.message_handler(commands=[Commands.ADD_MEN_IDS.value])
@is_known_user
def add_men_ids_message(message):
    if state != State.STOPPED:
        bot.send_message(
            message.chat.id, 'Bot is already started or in unknown state! \nYou need to stop it before adding IDs.'
        )
        return

    if m := re.match('/add ([\d+ ]+)$', message.text):
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
