# You may need to add your working directory to the Python path. To do so, uncomment the following lines of code
# import sys
# sys.path.append("/Path/to/directory/bot-framework") # Replace with your directory path

import logging
import requests
import re
from requests.exceptions import RequestException
import json
import operator

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

# ADDITIONNAL FUNCTIONS / VARIABLES

global user_knows_about_tags_update
user_knows_about_tags_update = False
global user_has_been_greeted
user_has_been_greeted = False

def updateTags(): #get all the existing tags
    with open("src/app/open_data_portal_API.json", 'r') as file:
        website_dict = json.load(file)
    tags = set()

    for root_url in website_dict["udata_root"]: #works for any website using uData API. Only need to update open_data_portal_API.json to give the html root
        url = root_url + "api/1/datasets/?format=csv"
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

    """for root_url in website_dict["ckan_root"]:""" #eventually support could be added for open data website using the ckan API


def get_datasets_info_with_tag_from_platform(opendata_url, tag, datasets_info):
    url = opendata_url + "api/1/datasets/" + "/?tag=" + tag + "&format=csv"
    response = {}
    try:
        response = requests.get(url).json()
    except:
        print(f"Error: Unvalid API request {url}.")
    if not len(response) == 0 and response['data']:
        for dataset in response['data']:
            for resource in dataset['resources']:
                if resource['format'] == "csv":
                    try: #check that the csv url is valid before considering the dataset as useful
                        response = requests.head(resource["url"], timeout=5)
                    except requests.RequestException as e:
                        print(f"Error checking URL {resource['url']}, ignoring file")
                        continue #no need to stay in this loop iteration if the csv url is not valid
                    if response.status_code == 200:
                        title_prompt = (
                            f"Generate a very short descriptive title for a dataset, based on the following information from the dataset:\n"
                            f"{resource['title']}\n"
                            f"{dataset['acronym']}\n"
                            f"{resource['description']}\n"
                            f"{dataset['description']}\n"
                            f"No bullet points or sub-titles, only a short title."
                        )
                        description_prompt = (
                            f"Generate a short description for a dataset, using the following context:\n"
                            f"title : {resource['title']}\n"
                            f"other title : {dataset['acronym']}\n"
                            f"date : {resource['created_at']}\n"
                            f"frequency : {dataset['frequency']}\n"
                            f"description : {resource['description']}\n"
                            f"other description : {dataset['description']}\n"
                            f"No bullet points or titles, only a short 50-70 words description. You must only talk concisely about the content of the dataset."
                        )
                        dataset_title = gpt.predict(title_prompt).strip()
                        dataset_description = gpt.predict(description_prompt).strip()
                        useful_info_dict = {
                            "dataset_source": opendata_url,
                            "dataset_title": dataset_title if dataset_title else resource["title"],
                            "dataset_date": resource["created_at"],
                            "dataset_description": dataset_description if dataset_description else resource["description"],
                            "dataset_organization": dataset.get("organization", {}) and dataset["organization"].get("acronym", "Unknown"),  #There isn't always an organization
                            "dataset_url": resource["url"]
                        }
                        datasets_info.append(useful_info_dict)
                        break



# STATES

neutral_state = parent_bot.new_state('neutral_state', initial=True)
help_state = parent_bot.new_state('help_state')
databaseRequest_state = parent_bot.new_state('databaseRequest_state')
updateTags_state = parent_bot.new_state('updateTags_state')
giveMoreDetails_state = parent_bot.new_state('giveMoreDetails_state')

# ENTITIES

word_entity = parent_bot.new_entity(
    name='word_entity',
    description='a string of letters with meaning. This entity does not include nonsensical string of letters',
)

# INTENTS

negative_intent = parent_bot.new_intent(
    name='negative_intent',
    description='The user answer with the negative',
    training_sentences = [
        'no',
        'nope',
        'absolutely not',
        'no way',
        'I do not want to',
        'I will not',
        'I do not need it',
        'I do not need you',
    ]
)

help_intent = parent_bot.new_intent(
    name='help_intent',
    description='The user is asking for help concerning your functionnalities.',
    training_sentences = [
    'what can you do ?',
    'help',
    'can you help me',
    'help',
    'how do I get a specific dataset ?',
    'how do I ask you for a dataset ?',
    'help',
    'help.',
    'What kind of data can you provide ?',
    'please help',
    'help.',
    'What kind of dataset can you fetch',
    'help',
    'What can I ask for',
    'help!',
    'What is your purpose',
    'help?',
    'Where are your data coming from',
    'help me!',
    'tell me about your functionnalities',
    "give me your sources",
    "Can I get some assistance?",
    'help',
    "I need help.",
    "Help me out here.",
    "What do you offer?",
    'help',
    'help...',
    'help!',
    "How do I use you?",
    "Explain your features.",
    "What can I ask you?",
    'help me please',
    "Show me how to get a dataset.",
    'just help me',
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



def neutral_body(session: Session):
    global user_has_been_greeted
    if (not user_has_been_greeted):
        answer = gpt.predict(f"You are being used within an intent-based chatbot. Your goal is to help the user browse data websites to find relevant datasets for their needs. Start the conversation with a short (5-20 words) greetings message asking the user what they need.")
        session.reply(answer)
        user_has_been_greeted = True
    else:
        session.reply("What else can I do for you ?")

neutral_state.set_body(neutral_body)
neutral_state.when_intent_matched_go_to(databaseRequest_intent, databaseRequest_state)
neutral_state.when_intent_matched_go_to(updateTags_intent, updateTags_state)



def help_body(session: Session):
    answer = gpt.predict(
        f"You are being used within an intent-based chatbot. The user is asking for help concerning your functionnalities. Give an answer based on the user message : {session.message}, and using the following informations :"
        f"You are an helpful assistant chatbot, that has access to the datasets of several open data platform. You can provide the user with a dataset suited to their needs if they give you keywords on what they are looking for."
        f"You can then generate another chatbot trained on the dataset the user chose, and who will be able to answer any question concerning this specific dataset."
        )
    session.reply(answer)

help_state.set_body(help_body)
help_state.set_global(help_intent)



def databaseRequest_body(session: Session):
    session.reply("Let me check the database... 🔄")
    global user_knows_about_tags_update
    session.set('need_more_detail_on_request', False)
    predicted_intent: IntentClassifierPrediction = session.predicted_intent
    topic = predicted_intent.get_parameter('topic1')
    if topic.value is None:
        session.reply("Sorry, I didn't catch the tag you were looking for")
    else:
        with open("src/app/datasets_tags.json", 'r') as file:
                available_tags = json.load(file)
        if str(topic.value) not in available_tags["tags"] :
            tags_set = set(available_tags["tags"])
            tags_str = ", ".join(str(tag) for tag in tags_set)
            if user_knows_about_tags_update == False:
                answer = gpt.predict(
                    f"You are being used within an intent-based chatbot. The user asked you to provide a dataset with this specific tag '{topic.value}' but you found none. "
                    f"Here is the list of the only available tags: {tags_str}. Give them possible synonyms or other spellings to their first demand if some are in the list. They HAVE to be on the list."
                    f"Tell them that they can ask you to update your tag list if they think it is not up to date."
                    )
                user_knows_about_tags_update = True
            else:
                answer = gpt.predict(
                    f"You are being used within an intent-based chatbot. The user asked you to provide a dataset with this specific tag '{topic.value}' but you found none."
                    f"Here is the list of the only available tags: {tags_str}. Give them possible synonyms or other spellings to their first demand if some are in the list. They HAVE to be on the list."
                    )
            session.reply(answer)
            return
        else : #the API request is only made if the bots know that there will be at least one dataset returned
            with open("src/app/open_data_portal_API.json", 'r') as file:
                website_dict = json.load(file)
            all_datasets_info = []
            session.reply("There are a few relevant datasets, please hang on a little while ! 🙏")
            for root_url in website_dict["udata_root"]:
                get_datasets_info_with_tag_from_platform(root_url, str(topic.value), all_datasets_info)
            if not all_datasets_info: #not a single dataset was found, even though the tag is in the list of available datasets. Perhaps it is no longer available
                session.reply(f"I didn't find a single dataset for the tag {topic.value}, even though there should be one. You might want to ask me to update my tag list.")
                return
            else :
                session.set('all_datasets_info', all_datasets_info)
                dataset_number = len(all_datasets_info)
                if dataset_number <= 10:
                    session.reply(f"I found {dataset_number} result(s) mentioning {topic.value}:")
                    all_datasets_info_json = json.dumps(all_datasets_info, indent=4)
                    session.reply(all_datasets_info_json)
                else : 
                    session.set('need_more_detail_on_request', True)
                    session.set('all_datasets_info', all_datasets_info)
                    session.reply(f"I found quite a lot of datasets mentioning {topic.value}. Can you give me more details on what you are looking for ?")
 
databaseRequest_state.set_body(databaseRequest_body)
databaseRequest_state.when_variable_matches_operation_go_to('need_more_detail_on_request', operator.eq, False, neutral_state)
#If we do need more detail, we will wait for the users answer
databaseRequest_state.when_intent_matched_go_to(databaseRequest_intent, giveMoreDetails_state)
databaseRequest_state.when_variable_matches_operation_go_to('need_more_detail_on_request', operator.eq, True, giveMoreDetails_state)  


def giveMoreDetails_body(session: Session):
    all_datasets_info = session.get('all_datasets_info')
    session.reply("Here are the 10 dataset I found most suited to your needs :")
    answer = gpt.predict(
         f"You are being used within an intent-based chatbot. The user is asking for a dataset fitting this description: {session.message}."
         f"Here are all the dataset you have available : {all_datasets_info}."
         f"Select 10 datasets that are the closest to the user's needs. Be very mindful of the keywords they gave you."
         f"Give them back in order of relevance using this format :"
         f"number : dataset_url"
         f"Do not write anything else, and it is crucial to respect the format."
         f"Warning : the dataset_url is NOT the dataset_source !!!"
         )
    # Regex pattern to capture URLs after 'number :' 
    url_pattern = r'[:]\s*(https?://[^\s]+)'

    # Find all URLs in the response
    urls_to_keep = re.findall(url_pattern, answer)

    # Filter all_datasets_info based on extracted URLs
    all_datasets_info = [dataset for dataset in all_datasets_info if dataset["dataset_url"] in urls_to_keep]
    all_datasets_info_json = json.dumps(all_datasets_info, indent=4)
    session.reply(all_datasets_info_json)

giveMoreDetails_state.set_body(giveMoreDetails_body)
giveMoreDetails_state.go_to(neutral_state)


def updateTags_body(session: Session):
    session.reply(f"I am updating my tag list. Please wait, it might take a while. I will tell you when I am done.")
    updateTags()
    session.reply(f"The update is over!")

updateTags_state.set_body(updateTags_body)
updateTags_state.go_to(neutral_state)