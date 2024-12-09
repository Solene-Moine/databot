import json
import queue
import threading
import time
from datetime import datetime

import pandas as pd
import plotly
import re
import streamlit as st
import websocket
from streamlit.runtime.scriptrunner import add_script_run_ctx

from besser.bot.core.message import Message, MessageType
from besser.bot.platforms.payload import Payload, PayloadAction, PayloadEncoder

from src.app.parent_bot import parent_bot
from src.app.app import get_app
from src.app.project import Project
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

    def on_message(ws, payload_str):
        #https://github.com/streamlit/streamlit/issues/2838
        """This function is run on every message the bot sends"""
        dataset_creation = False
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
            # Check if content is a URL and create an expander entry
            if t == MessageType.STR and re.match(r'^(https?|ftp)://[^\s/$.?#].[^\s]*$', content):
                streamlit_session.session_state["expanders"] = [] #reset the previous datasets when the user ask for a new one
                expander_entry = {"dataset_title": f"Expander", "url": content}
                streamlit_session._session_state["expanders"].append(expander_entry)
            else:
                message = Message(t=t, content=content, is_user=False, timestamp=datetime.now())
                streamlit_session._session_state['queue'].put(message)
            
            
                
        streamlit_session._handle_rerun_script_request()

    user_type = {
        0: 'assistant',
        1: 'user'
    }

    # Initialize session state
    if "expanders" not in st.session_state:
        st.session_state["expanders"] = []

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

    col1, col2 = st.columns([6, 3], gap = "large")  # Adjust columns to control layout

# Sidebar for expanders
    if st.session_state["expanders"]:
        with st.container():  # Display expanders in a container on the right
            with col2:  # Right column
                st.write("### Data Exploration")
                for expander in st.session_state["expanders"]:
                    with st.expander(expander["dataset_title"], expanded=True):
                        st.write(f"URL: {expander['url']}")
                        delimiter = st.text_input(label='Delimiter', value=',', key=f'input_{expander["url"]}')
                        if st.button(f"Generate bot", key=f'button_{expander["url"]}'):
                            app = get_app()
                            file_url = expander["url"]
                            if file_url is None:
                                st.error('Please introduce a CSV URL')
                            else:
                                project_name = expander["dataset_title"]
                                if project_name in [project.name for project in app.projects]:
                                    st.error(f"The project name '{project_name}' already exists. Please choose another one")
                                else:
                                    project = Project(app, project_name, pd.read_csv(file_url, delimiter=delimiter))
                                    st.session_state[SELECTED_PROJECT] = project
                                    st.info(
                                        f'The project **{project.name}** has been created! Go to **Admin** to train a 🤖 bot upon it.')

    # Display chat messages
    for message in st.session_state['history']:
        if st.session_state["expanders"]:
            with col1:
                with st.chat_message(user_type[message.is_user]):
                    st.write(message.content)
        else:
            with st.chat_message(user_type[message.is_user]):
                st.write(message.content)
        
    while not st.session_state['queue'].empty():
        with st.chat_message("assistant"):
            message = st.session_state['queue'].get()
            if message.type == MessageType.OPTIONS:
                st.session_state['buttons'] = message.content
            elif message.type == MessageType.STR:
                st.session_state['history'].append(message)
                with st.spinner(''):
                    time.sleep(1)
                st.write(message.content)

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