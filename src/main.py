import re

from itertools import islice

import functools
import subprocess
from bot import bot
from enum import Enum

from utils import reverse_readline

clients = {
    545573346: 'Olga',
    229253199: 'Dmytro',
}

LOG_NUM_RECORDS = 10


class Commands(Enum):
    START = 'start'
    STOP = 'stop'
    RESTART = 'restart'
    # STATS = 'stats'
    LOGS = 'log'
    # ADD_MEN_IDS = 'add'
    SCREENSHOT = 'screen'

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
    bot.send_message(message.chat.id, f"Starting sending emails...")
    subprocess.call(['docker-compose', 'up', '-d'])
    bot.send_message(message.chat.id, f"Sending email has been started!")


@bot.message_handler(commands=[Commands.STOP.value])
@is_known_user
def stop_message(message):
    bot.send_message(message.chat.id, f"Stopping sending emails...")
    subprocess.call(['docker-compose', 'down', '-t', '0'])
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


@bot.message_handler(commands=[Commands.SCREENSHOT.value])
@is_known_user
def screen_message(message):
    bot.send_message(message.chat.id, 'ec2-13-59-181-29.us-east-2.compute.amazonaws.com:9222')


@bot.message_handler(content_types=['text', 'url'])
def send_text(message):
    bot.send_message(
        message.chat.id,
        f'Sorry! Did not get your request :(\n\nPlease, select one of the available commands:\n{Commands.list()}',
    )


if __name__ == "__main__":
    bot.polling()
