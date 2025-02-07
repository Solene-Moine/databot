import json
import queue
import random
import threading
import time
import chardet
import requests
from datetime import datetime

import pandas as pd
import plotly
import streamlit as st
import websocket
from streamlit.runtime.scriptrunner import add_script_run_ctx

from besser.bot.core.message import Message, MessageType
from besser.bot.platforms.payload import Payload, PayloadAction, PayloadEncoder

from src.app.parent_bot import parent_bot
from src.app.app import get_app
from src.app.project import Project
from src.app.content import Content
from src.utils.session_state_keys import AI_ICON, CKAN, COUNT_CSVS, COUNT_DATASETS, EDITED_PACKAGES_DF, IMPORT, \
    IMPORT_OPEN_DATA_PORTAL, METADATA, OPEN_DATA_SOURCES, SELECTED_PROJECT, SELECT_ALL_CHECKBOXES, TITLE, UDATA, \
    UPLOAD_DATA
from src.utils.session_monitoring import get_streamlit_session


@st.cache_resource
def run_parent_bot():
    parent_bot.run(sleep=False)

def open_data():
    run_parent_bot()

    st.header('Open Data Exploration')
    # User input component. Must be declared before history writing
    user_input = st.chat_input("What is up?")

    def is_json(string):
        try:
            json.loads(string)
            return True
        except json.JSONDecodeError:
            return False
        
    def display_expanders(message):
        for expander_entry in message.content.expanders: 
            file_url = expander_entry["dataset_url"] 
            response = requests.head(file_url) #check that the csv link is valid
            if response.status_code == 200:
                with st.expander(expander_entry["dataset_title"], False): 
                    st.write(f"Source platform: {expander_entry['dataset_source']}")
                    st.write(f"Title: {expander_entry['dataset_title']}")
                    st.write(f"Creation Date: {expander_entry['dataset_date']}")
                    st.write(f"Organization: {expander_entry['dataset_organization']}")
                    st.write(f"Description: {expander_entry['dataset_description']}")
                    st.write(f"CSV URL: {file_url}")
                    delimiter = st.text_input(label='Delimiter', value=',', key=f'delimiter_{file_url}_{random.randint(1, 10000)}')
                    project_name = st.text_input(label='Project Name', value=expander_entry["dataset_title"], key=f'name_{expander_entry["dataset_url"]}_{random.randint(1, 10000)}')
                    st.write("Preview (using your chosen delimiter):")
                    csv_encoding = chardet.detect(requests.get(file_url).content)['encoding']
                    dataset_preview = pd.read_csv(file_url, sep=delimiter, encoding=csv_encoding, nrows=2)
                    st.dataframe(dataset_preview)
                    if st.button(f"Generate bot", key=f'button_{file_url}'):
                        app = get_app()
                        if project_name in [project.name for project in app.projects]:
                            st.error(f"The project name '{project_name}' already exists. Please choose another one")
                        else:
                            project = Project(app, project_name, pd.read_csv(file_url, delimiter=delimiter, encoding=csv_encoding))
                            st.session_state[SELECTED_PROJECT] = project
                            st.info(
                                f'The project **{project.name}** has been created! Go to **Admin** to train a 🤖 bot upon it.')

    def on_message(ws, payload_str):
        #https://github.com/streamlit/streamlit/issues/2838
        """This function is run on every message the bot sends"""
        streamlit_session = get_streamlit_session()
        payload: Payload = Payload.decode(payload_str)
        content = None
        if payload.action == PayloadAction.BOT_REPLY_STR.value:
            content = payload.message
            t = MessageType.STR
        elif payload.action == PayloadAction.BOT_REPLY_DF.value:
            content = pd.read_json(payload.message)
            t = MessageType.DATAFRAME
        elif payload.action == PayloadAction.BOT_REPLY_PLOTLY.value:
            content = plotly.io.from_json(payload.message)
            t = MessageType.PLOTLY
        elif payload.action == PayloadAction.BOT_REPLY_OPTIONS.value:
            t = MessageType.OPTIONS
            d = json.loads(payload.message)
            content = []
            for button in d.values():
                content.append(button)

        if content is not None:
            if t == MessageType.STR and is_json(content):


                main_content = content
                content = Content(main_content=main_content)
                useful_info_list = json.loads(main_content)
                for useful_info_dict in useful_info_list:
                    expander_entry = {
                        "dataset_source": useful_info_dict["dataset_source"],
                        "dataset_title": useful_info_dict["dataset_title"],
                        "dataset_date": useful_info_dict["dataset_date"],
                        "dataset_organization": useful_info_dict["dataset_organization"],
                        "dataset_description": useful_info_dict["dataset_description"],
                        "dataset_url": useful_info_dict["dataset_url"]
                    }
                    content.expanders.append(expander_entry)

            message = Message(t=t, content=content, is_user=False, timestamp=datetime.now())
            streamlit_session._session_state['queue'].put(message)
            
            
        streamlit_session._handle_rerun_script_request()

    user_type = {
        0: 'assistant',
        1: 'user'
    }

    # Initialize session state
    if 'history' not in st.session_state:
        st.session_state['history'] = []

    if 'queue' not in st.session_state:
        st.session_state['queue'] = queue.Queue()

    if 'websocket_parent' not in st.session_state:
        host = 'localhost'
        port = '8764'
        ws = websocket.WebSocketApp(f"ws://{host}:{port}/",
                                    on_message=on_message)
        websocket_thread = threading.Thread(target=ws.run_forever)
        add_script_run_ctx(websocket_thread)
        websocket_thread.start()
        st.session_state['websocket_parent'] = ws

    ws = st.session_state['websocket_parent']


    # Display chat messages
    for message in st.session_state['history']:
        with st.chat_message(user_type[message.is_user]):  
            if isinstance(message.content, Content): #the content is of type Content only if the message has an expander
                display_expanders(message)
            else:
                st.write(message.content)
                            
        
    while not st.session_state['queue'].empty():
        with st.chat_message("assistant"):
            message = st.session_state['queue'].get()
            if message.type == MessageType.OPTIONS:
                st.session_state['buttons'] = message.content
            elif message.type == MessageType.STR :
                st.session_state['history'].append(message)
                with st.spinner(''):
                    time.sleep(1)
                if not isinstance(message.content, Content):
                    st.write(message.content)
                else:
                    display_expanders(message)

    if 'buttons' in st.session_state:
        buttons = st.session_state['buttons']
        cols = st.columns(1)
        for i, option in enumerate(buttons):
            if cols[0].button(option):
                with st.chat_message("user"):
                    st.write(option)
                message = Message(t=MessageType.STR, content=option, is_user=True, timestamp=datetime.now())
                st.session_state.history.append(message)
                payload = Payload(action=PayloadAction.USER_MESSAGE,
                                  message=option)
                ws.send(json.dumps(payload, cls=PayloadEncoder))
                del st.session_state['buttons']
                break

    if user_input:
        if 'buttons' in st.session_state:
            del st.session_state['buttons']
        with st.chat_message("user"):
            st.write(user_input)
        message = Message(t=MessageType.STR, content=user_input, is_user=True, timestamp=datetime.now())
        st.session_state.history.append(message)
        payload = Payload(action=PayloadAction.USER_MESSAGE,
                          message=user_input)
        try:
            ws.send(json.dumps(payload, cls=PayloadEncoder))
        except Exception as e:
            st.error('Your message could not be sent. The connection is already closed')