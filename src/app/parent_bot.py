# You may need to add your working directory to the Python path. To do so, uncomment the following lines of code
# import sys
# sys.path.append("/Path/to/directory/bot-framework") # Replace with your directory path

import logging
import requests
import json

from besser.bot.core.bot import Bot
from besser.bot.core.session import Session
from besser.bot.platforms.websocket import WEBSOCKET_PORT
from besser.bot.nlp.intent_classifier.intent_classifier_prediction import IntentClassifierPrediction

from besser.bot.library.entity.base_entities import any_entity

#from besser.bot.nlp.llm.llm_openai_api import LLMOpenAI
#from besser.bot.nlp.intent_classifier.intent_classifier_configuration import LLMIntentClassifierConfiguration

# Configure the logging module
logging.basicConfig(level=logging.INFO, format='{levelname} - {asctime}: {message}', style='{')

# Create the parent_bot
parent_bot = Bot('parent_bot')
parent_bot.set_property(WEBSOCKET_PORT, 8764)
websocket_platform = parent_bot.use_websocket_platform(use_ui=False)

# STATES

initial_state = parent_bot.new_state('initial_parent_botstate', initial=True)
name_state = parent_bot.new_state('name_state')
id_state = parent_bot.new_state('id_state')
update_state = parent_bot.new_state('update_state')

# ENTITIES
with open("src/app/datasets_id_names.txt", "r") as file:
    name_id_dict = json.load(file)
id_entries = {key: [] for key in name_id_dict.keys()}

id_entity = parent_bot.new_entity(
    name='id_entity',
    description='The ID of a dataset, a long string containing numbers and a few alphabetical characters',
    entries=id_entries
)

name_entity = parent_bot.new_entity(
    name='name_entity',
    description='The name of a dataset, a string of alphabetical characters',
    entries={
    'name1': [],
    'name2': [],
    }
)

# INTENTS

id_intent = parent_bot.new_intent('id_intent', [
    'What is the dataset of id ID?',
    'id dataset ID',
    'dataset id ID',
])
id_intent.parameter('id1', 'ID', id_entity)

name_intent = parent_bot.new_intent('name_intent', [
    'What dataset is called NAME?',
    'name dataset NAME',
    'dataset name NAME',
])
name_intent.parameter('name1', 'NAME', name_entity)

update_intent = parent_bot.new_intent('update_intent', [
    'update',
])

# OTHER FUNCTIONS

def updateDatabase():
    dict = {} #dictionary to link name and id of every dataset
    url = "https://data.public.lu/api/1/datasets/"
    while(url):
        response = requests.get(url).json()
        for dataset in response['data']:
            dict[dataset['id']] = dataset['title'] #the ids are unique so they are the keys
        url = response['next_page']
    with open("src/app/datasets_id_names.txt", "w") as file:
        json.dump(dict, file, indent=4)


# STATES BODIES' DEFINITION + TRANSITIONS

def confused_body(session: Session):
    session.reply("I feel like you are not making any sense.")


def initial_body(session: Session):
    session.reply("Hello! Give me a dataset ID or name and I will retrieve it!")

initial_state.set_body(initial_body)
initial_state.when_intent_matched_go_to(id_intent, id_state)
initial_state.when_intent_matched_go_to(name_intent, name_state)
initial_state.when_intent_matched_go_to(update_intent, update_state)
initial_state.set_fallback_body(confused_body)


def name_body(session: Session):
    session.reply('I cannot give you any information about this yet. But my next update surely will fix this !')

name_state.set_body(name_body)
name_state.go_to(initial_state)


def id_body(session: Session):
    predicted_intent: IntentClassifierPrediction = session.predicted_intent
    id = predicted_intent.get_parameter('id1')
    if id.value is None:
        session.reply("Sorry, it seems this id does not exist. If you think this is a mistake you can ask me to update my database.")
    else:
        url = "https://data.public.lu/api/1/datasets/" + str(id.value) + "/"
        response = requests.get(url).json()
        print(json.dumps(response,indent=4))
        format = ""
        for resource in response['resources']:
                if resource['format'] == "csv":
                    format = resource['format']
                    break
        if format == "csv":
            session.reply(f"It seems the {id.value} dataset has a csv.")
        else:
            session.reply(f"It seems the {id.value} dataset does not have any csv.")

id_state.set_body(id_body)
id_state.go_to(initial_state)

def update_body(session: Session):
    session.reply('I will start updating my database and tell you when I am done. Please wait, it will take a little while.')
    updateDatabase()
    session.reply('The update is done !')

update_state.set_body(update_body)
update_state.go_to(initial_state)