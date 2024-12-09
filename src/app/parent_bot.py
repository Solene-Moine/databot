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
from besser.bot.nlp.intent_classifier.intent_classifier_configuration import LLMIntentClassifierConfiguration

from besser.bot.nlp.llm.llm_openai_api import LLMOpenAI

#from besser.bot.nlp.llm.llm_openai_api import LLMOpenAI
#from besser.bot.nlp.intent_classifier.intent_classifier_configuration import LLMIntentClassifierConfiguration

# Configure the logging module
logging.basicConfig(level=logging.INFO, format='{levelname} - {asctime}: {message}', style='{')

# Create the parent_bot
parent_bot = Bot('parent_bot')
parent_bot.load_properties('config.ini')
websocket_platform = parent_bot.use_websocket_platform(use_ui=False)

# Create the LLM
gpt = LLMOpenAI(
    bot=parent_bot,
    name='gpt-4o-mini',
    parameters={},
    num_previous_messages=10
)

ic_config = LLMIntentClassifierConfiguration(
    llm_name='gpt-4o-mini',
    parameters={
        "seed": None,
        "top_p": 1,
        "temperature": 1,
    },
    use_intent_descriptions=True,
    use_training_sentences=True,
    use_entity_descriptions=True,
    use_entity_synonyms=False
)

parent_bot.set_default_ic_config(ic_config)

# STATES
###################################################################################################

initial_state = parent_bot.new_state('initial_parent_botstate', initial=True)
smalltalk_state = parent_bot.new_state('smalltalk_state')
confused_state = parent_bot.new_state('confused_state')
name_state = parent_bot.new_state('name_state')
id_state = parent_bot.new_state('id_state')
update_state = parent_bot.new_state('update_state')
#######################################################################################################

# ENTITIES
#########################################################################################################
with open("src/app/datasets_id_names.json", "r") as file:
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
############################################################################################################

# INTENTS
#############################################################################################################
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

smalltalk_intent = parent_bot.new_intent(
    name='smalltalk_intent',
    description='The user is trying to talk about random things that are not related to datasets creation, which are out of your purpose. The questions can be extremely varied.',
    training_sentences = ['how are you doing?',
     'do you want to chat?'
     'what is your favorite color?'
     'give me a cooking recipe'
     'help me solve this math problem'
     'is Italy a democraty'
])
############################################################################################################

# OTHER FUNCTIONS

def updateDatabase():
    dict = {} #dictionary to link name and id of every dataset
    url = "https://data.public.lu/api/1/datasets/"
    while(url):
        response = requests.get(url).json()
        for dataset in response['data']:
            dict[dataset['id']] = dataset['title'] #the ids are unique so they are the keys
        url = response['next_page']
    with open("src/app/datasets_id_names.json", "w") as file:
        json.dump(dict, file, indent=4)


# STATES BODIES' DEFINITION + TRANSITIONS

def confused_body(session: Session):
    answer = gpt.predict(f"You are being used within an intent-based chatbot. Your goal is to help the user browse data websites to find relevant datasets for their needs. You are generating a fallback answer because the intent of the user was not identified. Generate a message similar to 'I am sorry, I did not quite catch what you were trying to ask here. Can you rephrase it ?', based on the user message: {session.message}")
    session.reply(answer)

def smalltalk_body(session: Session):
    answer = gpt.predict(f"You are being used within an intent-based chatbot. Your goal is to help the user browse data websites to find relevant datasets for their needs. This answer is generated because the user attempted to make small talk or to ask a question that has nothing to do with the aim of the chatbot. Generate a message similar to 'That seems very interesting, but my purpose is to help you find datasets relevant to your needs, not this.', based on the user message: {session.message}")
    session.reply(answer)

smalltalk_state.set_global(smalltalk_intent)
smalltalk_state.when_intent_matched_go_to(id_intent, id_state)

def initial_body(session: Session):
    session.reply("Hello! Give me a dataset ID or name and I will retrieve it!")

initial_state.set_body(initial_body)
initial_state.when_intent_matched_go_to(id_intent, id_state)
initial_state.when_intent_matched_go_to(name_intent, name_state)
initial_state.when_intent_matched_go_to(update_intent, update_state)
parent_bot.set_global_fallback_body(confused_body)


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
        format = ""
        for resource in response['resources']:
                if resource['format'] == "csv":
                    format = resource['format']
                    break
        if format == "csv":
            session.reply(f"It seems the {id.value} dataset has a csv. I will generate infos on the right side of the screen.")
            session.reply(f"{resource['url']}")
        else:
            session.reply(f"It seems the {id.value} dataset does not have any csv.")

id_state.set_body(id_body)
id_state.set_global(id_state)
id_state.go_to(initial_state)

def update_body(session: Session):
    session.reply('I will start updating my database and tell you when I am done. Please wait, it will take a little while.')
    updateDatabase()
    session.reply('The update is done !')

update_state.set_body(update_body)
update_state.set_global(update_state)
update_state.go_to(initial_state)