import json
import queue
import threading
import time
from datetime import datetime

import pandas as pd
import plotly
import streamlit as st
import websocket
from streamlit.runtime.scriptrunner import add_script_run_ctx

from besser.bot.core.message import Message, MessageType
from besser.bot.platforms.payload import Payload, PayloadAction, PayloadEncoder

from src.app.parent_bot import parent_bot
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
            message = Message(t=t, content=content, is_user=False, timestamp=datetime.now())
            streamlit_session._session_state['queue'].put(message)
        streamlit_session._handle_rerun_script_request()

    user_type = {
        0: 'assistant',
        1: 'user'
    }

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

    # open_data_url = st.text_input('Enter URL')

    for message in st.session_state['history']:
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