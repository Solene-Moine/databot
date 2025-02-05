# DataBot and ParentBot: Reliable data exploration through chatbots

This platform is used to create bots whose job is to find relevant datasets and to answer questions about a specific data source. It allows the automatic
generation of a chat/voice bot swarm to attend all the data sources in an **Open Data Portal**.

The highlights of DataBot are:

- 💻 **Import data** through a friendly UI.
  - 💾 Upload your dataset directly to the platform, or...
  - 🌐 Automatically load all the data sources from an Open Data Portal through its API (see ParentBot).
- 🔎 A **data schema** is automatically inferred from the data source, and can be **enhanced** 💪 to improve the bot knowledge about 
  the data (e.g., synonyms or translations). This can be done either manually or using ✨AI.
- 🤖 **Automatically generate a chatbot for each data source**. These chatbots are powered by the [**BESSER Bot Framework**](https://github.com/BESSER-PEARL/bot-framework).
  They recognize the user intent and generate the appropriate answer. So, no hallucinations at all.
- Generation of tabular📅 and graphical📈 answers.
- 🎙️ Interact with the chatbots either writing or speaking: **voice recognition integrated**.
- ✨ For those questions the bot fails to identify, AI can be used to generate the best possible answer.
- ✨ For the AI components (data schema enhancement and answer generation), we use the OpenAI API.

![DataBot Playground Screenshot](docs/source/img/playground_screenshot.png)

But how you might be asking yourself, "how can you find the perfect dataset for my needs ?"
Look no further than **ParentBot** ! Its features include:

- I worked really hard on it

- How to use it?
 - What's the answer when you don't have results?
 - What's the answer when you have results? What can you do next?
 - Describe how to add new URLs to look for datasets

insert pretty screenshot here

## Requirements

- Python 3.11
- Recommended: Create a virtual environment (e.g. [venv](https://docs.python.org/3/library/venv.html), [conda](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html))

For example with venv, after installing Python 3.11 on your machine, you can create a new virtual environment: 

```bash
python3.11 -m venv ChatbotVirtualEnv
```

To activate the environment:
```bash
source ChatbotVirtualEnv/bin/activate
```

To deactivate the virtual environment: 
```bash
deactivate ChatbotVirtualEnv 
```

To permanently delete the environment: 
```bash
rm -rf ChatbotVirtualEnv (depuis le parent directory)
```

## Installation

```bash
git clone https://github.com/BESSER-PEARL/databot
cd databot
pip install -r requirements.txt
touch config.ini
```

## Configuration

For the parent_bot to work, you will need an OpenAI API Key.
In your config.ini, paste the following text, and replace "**YOUR-OPENAI-API-KEY**" with your actual key. 

```bash
[websocket_platform]
websocket.host = localhost
websocket.port = 8764
streamlit.host = localhost
streamlit.port = 5000

[telegram_platform]
telegram.token = YOUR-BOT-TOKEN

[nlp]
nlp.language = en
nlp.region = US
nlp.timezone = Europe/Madrid
nlp.pre_processing = True
nlp.intent_threshold = 0.4
nlp.openai.api_key = YOUR-OPENAI-API-KEY
nlp.hf.api_key = YOUR-API-KEY
nlp.replicate.api_key = YOUR-API-KEY

[db]
db.monitoring = False
db.monitoring.dialect = postgresql
db.monitoring.host = localhost
db.monitoring.port = 5432
db.monitoring.database = DB-NAME
db.monitoring.username = DB-USERNAME
db.monitoring.password = DB-PASSWORD
```

## Launching

To launch the platform in your browser, simply run this command from the databot directory.
```bash
streamlit run main.py
```

## License

This project is licensed under the [MIT](https://mit-license.org/) license

Copyright © 2023 Luxembourg Institute of Science and Technology. All rights reserved.
