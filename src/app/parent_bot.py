# You may need to add your working directory to the Python path. To do so, uncomment the following lines of code
# import sys
# sys.path.append("/Path/to/directory/bot-framework") # Replace with your directory path

import logging
import requests
from requests.exceptions import RequestException
import json

from besser.bot.core.bot import Bot
from besser.bot.core.session import Session
from besser.bot.nlp.intent_classifier.intent_classifier_prediction import IntentClassifierPrediction
from besser.bot.nlp.intent_classifier.intent_classifier_configuration import LLMIntentClassifierConfiguration
from besser.bot.nlp.llm.llm_openai_api import LLMOpenAI
from besser.bot.platforms.websocket import WEBSOCKET_PORT

logging.basicConfig(level=logging.INFO, format='{levelname} - {asctime}: {message}', style='{')

parent_bot = Bot('llm_bot')
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
    parameters={},
    use_intent_descriptions=True,
    use_training_sentences=False,
    use_entity_descriptions=True,
    use_entity_synonyms=False
)
parent_bot.set_default_ic_config(ic_config)

############################################################################################################################################

# OTHER FUNCTIONS

global user_knows_about_tags_update
user_knows_about_tags_update = False

def updateTags(): #get all the existing tags
    with open("src/app/open_data_portal_API.json", 'r') as file:
        website_dict = json.load(file)
    tags = set()

    for root_url in website_dict["udata_root"]: #works for any website using uData API. Only need to update open_data_portal_API.json to give the html root
        url = root_url + "?format=csv"
        while(url):
            try:
                response = requests.get(url).json()
                for dataset in response['data']:
                    tags.update(dataset['tags'])
                url = response['next_page']
            except RequestException as e:
                print(f"Error: Unable to load URL {url}. Exception: {e}")
                break
    with open("src/app/datasets_tags.json", "w") as file:
        dict_tags = {"tags": list(tags)}
        json.dump(dict_tags, file, indent=4)

    """for root_url in website_dict["ckan_root"]:
        url = root_url + "tag_list"
        updateTagsPortal(url)"""



# STATES

greetings_state = parent_bot.new_state('greetings_state', initial=True)
help_state = parent_bot.new_state('help_state')
transition_state = parent_bot.new_state('transition_state')
smalltalk_state = parent_bot.new_state('smalltalk_state')
databaseRequest_state = parent_bot.new_state('databaseRequest_state')
updateTags_state = parent_bot.new_state('updateTags_state')
answer_state = parent_bot.new_state('answer_state')

# ENTITIES

word_entity = parent_bot.new_entity(
    name='word_entity',
    description='a string of letters with meaning. This entity does not include nonsensical string of letters',
)

# INTENTS

hello_intent = parent_bot.new_intent(
    name='hello_intent',
    description='The user greets you'
)

help_intent = parent_bot.new_intent(
    name='help_intent',
    description='The user is asking for help concerning your functionnalities.',
    training_sentences = [
    'what can you do ?',
    'help',
    'can you help me',
    'how do I get a specific dataset ?',
    'how do I ask you for a dataset ?',
    'What kind of data can you provide ?',
    'What kind of dataset can you fetch',
    'What can I ask for',
    'What is your purpose',
    'Where are your data coming from',
    'tell me about your functionnalities',
    "give me your sources",
    "Can I get some assistance?",
    "I need help.",
    "Help me out here.",
    "What do you offer?",
    "How do I use you?",
    "Explain your features.",
    "What can I ask you?",
    "Show me how to get a dataset.",
])

databaseRequest_intent = parent_bot.new_intent(
    name = 'databaseRequest_intent',
    description = 'The user asks for a dataset about a specific topic',
    training_sentences = [
    'What database talks about TOPIC',
    'Can you give me a TOPIC dataset',
    'I would like to see datas on TOPIC',
    'data on TOPIC',
    "Can you find a dataset about TOPIC?",
    "I need data on TOPIC.",
    "Do you have datasets about TOPIC?",
    "Show me the latest TOPIC data.",
    "Get me datasets related to TOPIC.",
    "Find me information about TOPIC.",
    "I want to see datasets on TOPIC.",
    "Give me TOPIC data.",
    "do you have any info about TOPIC?",
    "Can you pull up data for TOPIC?",
    "Search for datasets about TOPIC.",
    ])
databaseRequest_intent.parameter('topic1', 'TOPIC', word_entity)

smalltalk_intent = parent_bot.new_intent(
    name='smalltalk_intent',
    description='The user is trying to talk about random things that are not related to datasets creation, which are out of your purpose. The questions can be extremely varied.',
    training_sentences = ['how are you doing?',
    'do you want to chat?',
    'what is your favorite color?',
    'give me a cooking recipe',
    'help me solve this math problem',
    'is Italy a democraty',
    "How are you today?",
    "Do you like coffee?",
    "What's your favorite book?",
    "What's the weather like?",
    "Do you play video games?",
    "Can you tell me a joke?",
    "Tell me something interesting.",
    "What do you think of the latest movie?",
    "Where would you like to travel?",
])

updateTags_intent = parent_bot.new_intent(
    name='updateTags_intent',
    description='The user is asking you to update the list of available tags because they think it might be out of date.',
    training_sentences = ['Can you update the tags?',
    'Update the tags.',
    'Keep your list of available tags up to date.',
    'Get the new tags.',
    'You should update your tags.',
    "Can you refresh the tags list?",
    "Please update your tags.",
    "Are the tags up-to-date?",
    "I think the tags need updating.",
    "Can you get the latest tags?",
    "Do you have the newest tags?",
    "Please sync the tags.",
    "Can you update the dataset tags?",
    "Get the most recent tags.",
    "Please update the available tags list.",
])


# STATES BODIES' DEFINITION + TRANSITIONS

def global_fallback_body(session: Session):
    answer = gpt.predict(f"You are being used within an intent-based bot. The chatbot triggered the fallback mechanism because no intent was recognized from the user input. Generate a message similar to 'Sorry, I don't know the answer', based on the user message: {session.message}")
    session.reply(answer)


parent_bot.set_global_fallback_body(global_fallback_body)


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
    global user_knows_about_tags_update
    predicted_intent: IntentClassifierPrediction = session.predicted_intent
    topic = predicted_intent.get_parameter('topic1')
    if topic.value is None:
        session.reply("Sorry, I didn't catch the tag you were looking for")
    else:
        #url = "https://data.public.lu/api/1/datasets/?tag=" + str(topic.value) + "&format=csv" #lux
        #https://www.data.gouv.fr/api/1/datasets/?tag=economy&format=csv #fr
        #https://dados.gov.pt/api/1/datasets/?tag=local #portuguese

        #ckan
        #url = https://catalog.data.gov/api/3/action/package_search?q=tags:mobility&fq=res_format:CSV #for specific tag and specific format in resources #us gov, no tag list
        #https://www.donneesquebec.ca/recherche/api/action/tag_list #tag list works!!! #données quebec
        #https://opendata.nhsbsa.net/api/3/action/tag_list #données NHS "The NHS Business Services Authority (NHSBSA) is an executive non-departmental public body of the Department of Health and Social Care which provides a number of support services to the National Health Service in England and Wales."
        #https://ckan.opendata.swiss/api/3/action/tag_list #données suisse
        #https://data.cnra.ca.gov/api/3/action/tag_list #california natural ressources agency
        #https://open.canada.ca/data/en/api/3/action/package_list #canado gov, no tag list
        #https://opendata-ajuntament.barcelona.cat/data/api/3/action/tag_list #barcelona
        #https://catalog.sarawak.gov.my/api/3/action/tag_list #sarawak partie de la malaisie
        #https://open.africa/api/3/action/tag_list
        #https://data.gov.au/api/3/action/tag_list #australia
        #https://data.gov.ie/api/3/action/tag_list #ireland
        #https://data.boston.gov/api/3/action/tag_list #boston (us city)
        #https://www.data.qld.gov.au/api/3/action/tag_list #queensland (australie)
        #https://data.illinois.gov/api/3/action/tag_list #state of US
        #https://dati.gov.it/opendata/api/3/action/tag_list #italy
        with open("src/app/datasets_tags.json", 'r') as file:
                available_tags = json.load(file)
        if str(topic.value) not in available_tags["tags"] :
            tags_set = set(available_tags["tags"])
            tags_str = ", ".join(str(tag) for tag in tags_set)
            if user_knows_about_tags_update == False:
                answer = gpt.predict(
                    f"You are being used within an intent-based chatbot. The user asked you to provide a dataset with this specific tag '{topic.value}' but you found none. "
                    f"Here is the list of the only available tags: {tags_str}. Give them a possible synonym to their first demand if one is in the list. You can give several tags, but they have to be on the list."
                    f"Tell them that they can ask you to update your tag list if they think it is not up to date."
                    )
                user_knows_about_tags_update = True
            else:
                answer = gpt.predict(
                    f"You are being used within an intent-based chatbot. The user asked you to provide a dataset with this specific tag '{topic.value}' but you found none."
                    f"Here is the list of the only available tags: {tags_str}. Give them a possible synonym to their first demand if one is in the list. You can give several tags, but they have to be on the list."
                    )
            session.reply(answer)
            return
        else : #the API request is only made if the bots know that there will be at least one dataset returned
            print("hell no")
            with open("src/app/open_data_portal_API.json", 'r') as file:
                website_dict = json.load(file)
            all_datasets_info = []
            for root_url in website_dict["udata_root"]:
                url = root_url + "/?tag=" + str(topic.value) + "&format=csv"
                response = requests.get(url).json()
                if response['data']:
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
            if not all_datasets_info: #not a single dataset was found, even though the tag is in the list of available datasets
                session.reply(f"I didn't find a single dataset for the tag {topic.value}, even though there should be one. You might want to ask me to update my tag list.")
                return
            else :
                session.reply(f"I found {len(all_datasets_info)} result(s) mentioning {topic.value}:")
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