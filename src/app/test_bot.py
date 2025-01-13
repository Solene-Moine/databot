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

global user_knows_about_tags
user_knows_about_tags = False

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

# STATES

greetings_state = bot.new_state('greetings_state', initial=True)
help_state = bot.new_state('help_state')
transition_state = bot.new_state('transition_state')
smalltalk_state = bot.new_state('smalltalk_state')
databaseRequest_state = bot.new_state('databaseRequest_state')
updateTags_state = bot.new_state('updateTags_state')
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

help_intent = bot.new_intent(
    name='help_intent',
    description='The user is asking for help concerning your functionnalities.',
    training_sentences = [
     'what can you do ?',
     'help',
     'can you help me',
     'how do I get a specific dataset ?',
     'how do I ask you for a dataset ?',
     'what can I ask for',
     'where are your data coming from'
])

databaseRequest_intent = bot.new_intent(
    name = 'databaseRequest_intent',
    description = 'The user asks for a dataset about a specific topic',
    training_sentences = [
    'What database talks about TOPIC',
    'Can you give me a TOPIC dataset',
    'I would like to see datas on TOPIC',
    'data on TOPIC',
])
databaseRequest_intent.parameter('topic1', 'TOPIC', word_entity)

smalltalk_intent = bot.new_intent(
    name='smalltalk_intent',
    description='The user is trying to talk about random things that are not related to datasets creation, which are out of your purpose. The questions can be extremely varied.',
    training_sentences = ['how are you doing?',
     'do you want to chat?',
     'what is your favorite color?',
     'give me a cooking recipe',
     'help me solve this math problem',
     'is Italy a democraty',
])

updateTags_intent = bot.new_intent(
    name='updateTags_intent',
    description='The user is asking you to update the list of available tags because they think it might be out of date.',
    training_sentences = ['Can you update the tags?',
     'Update the tags.',
     'Keep your list of available tags up to date.',
     'Get the new tags.',
     'You should update your tags.'
])


# STATES BODIES' DEFINITION + TRANSITIONS

def global_fallback_body(session: Session):
    answer = gpt.predict(f"You are being used within an intent-based chatbot. The chatbot triggered the fallback mechanism because no intent was recognized from the user input. Generate a message similar to 'Sorry, I don't know the answer', based on the user message: {session.message}")
    session.reply(answer)


bot.set_global_fallback_body(global_fallback_body)


def greetings_body(session: Session):
    answer = gpt.predict(f"You are being used within an intent-based chatbot. Your goal is to help the user browse data websites to find relevant datasets for their needs. Start the conversation with a short (5-20 words) greetings message asking the user what they need.")
    session.reply(answer)


greetings_state.set_body(greetings_body)
greetings_state.when_intent_matched_go_to(hello_intent, greetings_state)
greetings_state.when_intent_matched_go_to(smalltalk_intent, smalltalk_state)
greetings_state.when_intent_matched_go_to(databaseRequest_intent, databaseRequest_state)
greetings_state.when_intent_matched_go_to(updateTags_intent, updateTags_state)

def help_body(session: Session):
    answer = gpt.predict(
        f"You are being used within an intent-based chatbot. The user is asking for help concerning your functionnalities. Give an answer based on the user message : {session.message}, and using the following informations :"
        f"You are an helpful assistant chatbot, that has access to the datasets of the luxembourgish open data platform (data.public.lu). You can provide the user with a dataset suited to their needs if they give you keywords on what they are looking for."
        f"You can then generate another chatbot trained on the dataset the user chose, and who will be able to answer any question concerning this specific dataset."
        )
    session.reply(answer)


help_state.set_body(help_body)
help_state.set_global(help_intent)
help_state.go_to(transition_state)

def transition_body(session: Session):
    session.reply("Do you need anything else ?")


transition_state.set_body(transition_body)
transition_state.when_intent_matched_go_to(smalltalk_intent, smalltalk_state)
transition_state.when_intent_matched_go_to(databaseRequest_intent, databaseRequest_state)
transition_state.when_intent_matched_go_to(updateTags_intent, updateTags_state)

def smalltalk_body(session: Session):
    answer = gpt.predict(f"You are being used within an intent-based chatbot. Your goal is to help the user browse data websites to find relevant datasets for their needs. This answer is generated because the user attempted to make small talk or to ask a question that has nothing to do with the aim of the chatbot. Generate a message similar to 'That seems very interesting, but my purpose is to help you find datasets relevant to your needs, not this.', based on the user message: {session.message}")
    session.reply(answer)

smalltalk_state.set_body(smalltalk_body)
smalltalk_state.go_to(transition_state)

def databaseRequest_body(session: Session):
    global user_knows_about_tags
    predicted_intent: IntentClassifierPrediction = session.predicted_intent
    topic = predicted_intent.get_parameter('topic1')
    if topic.value is None:
        session.reply("Sorry, it seems this tag doesn't mean anything.")
    else:
        url = "https://data.public.lu/api/1/datasets/?tag=" + str(topic.value) + "&format=csv"
        response = requests.get(url).json()
        if not response['data']:
            with open("src/app/datasets_tags.json", 'r') as file:
                available_tags = json.load(file)
            tags_set = set(available_tags["tags"])
            tags_str = ", ".join(str(tag) for tag in tags_set)
            if user_knows_about_tags == False:
                answer = gpt.predict(
                    f"You are being used within an intent-based chatbot. The user asked you to provide a dataset with this specific tag '{topic.value}' but you found none. "
                    f"Here is the list of the only available tags: {tags_str}. Give them a possible synonym to their first demand if one is in the list."
                    f"Tell them that they can ask you to update your tag list if they think it is not up to date."
                    )
                user_knows_about_tags = True
            else:
                answer = gpt.predict(
                    f"You are being used within an intent-based chatbot. The user asked you to provide a dataset with this specific tag '{topic.value}' but you found none. "
                    f"Here is the list of the only available tags: {tags_str}. Give them a possible synonym to their first demand if one is in the list."
                    )
            session.reply(answer)
            return
        else :


            session.reply(f"I found {len(response['data'])} result(s) mentioning {topic.value}:")
            all_datasets_info = []
            for dataset in response['data']:
                for resource in dataset['resources']:
                    if resource['format'] == "csv":
                        useful_info_dict = {
                            "dataset_title": resource["title"],
                            "dataset_date": resource["created_at"],
                            "dataset_description": resource["description"],
                            "dataset_url": resource["url"]
                        }
                        all_datasets_info.append(useful_info_dict)
                        break
            all_datasets_info_json = json.dumps(all_datasets_info, indent=4)
            session.reply(all_datasets_info_json)
            
databaseRequest_state.set_body(databaseRequest_body)
databaseRequest_state.go_to(transition_state)

def updateTags_body(session: Session):
    session.reply(f"I am updating my tag list. Please wait, it might take a while. I will tell you when I am done.")
    updateTags()
    session.reply(f"The update is over!")


updateTags_state.set_body(updateTags_body)
updateTags_state.go_to(transition_state)