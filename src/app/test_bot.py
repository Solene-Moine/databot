# You may need to add your working directory to the Python path. To do so, uncomment the following lines of code
# import sys
# sys.path.append("/Path/to/directory/bot-framework") # Replace with your directory path

import logging
import requests
import json

from besser.bot.core.bot import Bot
from besser.bot.core.session import Session
from besser.bot.nlp.intent_classifier.intent_classifier_prediction import IntentClassifierPrediction
from besser.bot.nlp.intent_classifier.intent_classifier_configuration import LLMIntentClassifierConfiguration
from besser.bot.nlp.llm.llm_openai_api import LLMOpenAI
from besser.bot.platforms.websocket import WEBSOCKET_PORT

logging.basicConfig(level=logging.INFO, format='{levelname} - {asctime}: {message}', style='{')

bot = Bot('llm_bot')
bot.load_properties('config.ini')
websocket_platform = bot.use_websocket_platform(use_ui=False)

# Create the LLM
gpt = LLMOpenAI(
    bot=bot,
    name='gpt-4o-mini',
    parameters={},
    num_previous_messages=10
)

ic_config = LLMIntentClassifierConfiguration(
    llm_name='gpt-4o-mini',
    parameters={},
    use_intent_descriptions=True,
    use_training_sentences=False,
    use_entity_descriptions=True,
    use_entity_synonyms=False
)
bot.set_default_ic_config(ic_config)

############################################################################################################################################

# OTHER FUNCTIONS

def updateTags(): #get all the existing tags from datalux
    url = "https://data.public.lu/api/1/datasets/?format=csv"
    tags = set()
    while(url):
        response = requests.get(url).json()
        for dataset in response['data']:
            tags.update(dataset['tags'])
        url = response['next_page']
    with open("src/app/datasets_tags.json", "w") as file:
        dict_tags = {"tags": list(tags)}
        json.dump(dict_tags, file, indent=4)

# STATES BODIES' DEFINITION + TRANSITIONS

greetings_state = bot.new_state('greetings_state', initial=True)
smalltalk_state = bot.new_state('smalltalk_state')
databaseRequest_state = bot.new_state('databaseRequest_state')
answer_state = bot.new_state('answer_state')

# ENTITIES

word_entity = bot.new_entity(
    name='word_entity',
    description='a string of letters with meaning. This entity does not include nonsensical string of letters',
)

# INTENTS

hello_intent = bot.new_intent(
    name='hello_intent',
    description='The user greets you'
)

databaseRequest_intent = bot.new_intent(
    name = 'databaseRequest_intent',
    description = 'The user asks for a dataset about a specific topic',
    training_sentences = [
    'What database talks about TOPIC',
    'Can you give me a TOPIC dataset',
    'I would like to see datas on TOPIC',
])
databaseRequest_intent.parameter('topic1', 'TOPIC', word_entity)

smalltalk_intent = bot.new_intent(
    name='smalltalk_intent',
    description='The user is trying to talk about random things that are not related to datasets creation, which are out of your purpose. The questions can be extremely varied.',
    training_sentences = ['how are you doing?',
     'do you want to chat?'
     'what is your favorite color?'
     'give me a cooking recipe'
     'help me solve this math problem'
     'is Italy a democraty'
])


# STATES BODIES' DEFINITION + TRANSITIONS

def global_fallback_body(session: Session):
    answer = gpt.predict(f"You are being used within an intent-based chatbot. The chatbot triggered the fallback mechanism because no intent was recognized from the user input. Generate a message similar to 'Sorry, I don't know the answer', based on the user message: {session.message}")
    session.reply(answer)


bot.set_global_fallback_body(global_fallback_body)


def greetings_body(session: Session):
    answer = gpt.predict(f"You are a helpful assistant. Start the conversation with a short (2-15 words) greetings message. Make it original.")
    updateTags()
    session.reply(answer)


greetings_state.set_body(greetings_body)
# Here, we could create a state for each intent, but we keep it simple
greetings_state.when_intent_matched_go_to(hello_intent, greetings_state)
greetings_state.when_intent_matched_go_to(smalltalk_intent, smalltalk_state)
greetings_state.when_intent_matched_go_to(databaseRequest_intent, databaseRequest_state)


def answer_body(session: Session):
    answer = gpt.predict(session.message)
    session.reply(answer)


answer_state.set_body(answer_body)
answer_state.go_to(greetings_state)

def smalltalk_body(session: Session):
    answer = gpt.predict(f"You are being used within an intent-based chatbot. Your goal is to help the user browse data websites to find relevant datasets for their needs. This answer is generated because the user attempted to make small talk or to ask a question that has nothing to do with the aim of the chatbot. Generate a message similar to 'That seems very interesting, but my purpose is to help you find datasets relevant to your needs, not this.', based on the user message: {session.message}")
    session.reply(answer)

smalltalk_state.set_body(smalltalk_body)
smalltalk_state.go_to(greetings_state)

def databaseRequest_body(session: Session):
    predicted_intent: IntentClassifierPrediction = session.predicted_intent
    topic = predicted_intent.get_parameter('topic1')
    if topic.value is None:
        session.reply("Sorry, it seems this tag isn't actually a word.")
    else:
        url = "https://data.public.lu/api/1/datasets/?tag=" + str(topic.value) + "&format=csv"
        response = requests.get(url).json()
        if not response['data']:
            session.reply(f"Sorry, no datasets were found for the tag '{topic.value}'.")
            return
        else :
            session.reply(f"I found {len(response['data'])} results mentionning {topic.value}.")
            for dataset in response['data']:
                for resource in dataset['resources']:
                    if resource['format'] == "csv":
                        session.reply(f"{resource['url']}")
            

databaseRequest_state.set_body(databaseRequest_body)
databaseRequest_state.go_to(greetings_state)