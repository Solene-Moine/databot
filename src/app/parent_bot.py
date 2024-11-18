# You may need to add your working directory to the Python path. To do so, uncomment the following lines of code
# import sys
# sys.path.append("/Path/to/directory/bot-framework") # Replace with your directory path

import logging

from besser.bot.core.bot import Bot
from besser.bot.core.session import Session
from besser.bot.platforms.websocket import WEBSOCKET_PORT

# Configure the logging module
logging.basicConfig(level=logging.INFO, format='{levelname} - {asctime}: {message}', style='{')

# Create the parent_bot
parent_bot = Bot('parent_bot')
parent_bot.set_property(WEBSOCKET_PORT, 8764)
websocket_platform = parent_bot.use_websocket_platform(use_ui=False)

# STATES

initial_state = parent_bot.new_state('initial_state', initial=True)
hello_state = parent_bot.new_state('hello_state')
good_state = parent_bot.new_state('good_state')
bad_state = parent_bot.new_state('bad_state')

# INTENTS

hello_intent = parent_bot.new_intent('hello_intent', [
    'hello',
    'hi',
])

good_intent = parent_bot.new_intent('good_intent', [
    'good',
    'fine',
])

bad_intent = parent_bot.new_intent('bad_intent', [
    'bad',
    'awful',
])


# STATES BODIES' DEFINITION + TRANSITIONS


initial_state.when_intent_matched_go_to(hello_intent, hello_state)


def hello_body(session: Session):
    session.reply('Hi! How are you?')


hello_state.set_body(hello_body)
hello_state.when_intent_matched_go_to(good_intent, good_state)
hello_state.when_intent_matched_go_to(bad_intent, bad_state)


def good_body(session: Session):
    session.reply('I am glad to hear that!')


good_state.set_body(good_body)
good_state.go_to(initial_state)


def bad_body(session: Session):
    session.reply('I am sorry to hear that...')


bad_state.set_body(bad_body)
bad_state.go_to(initial_state)