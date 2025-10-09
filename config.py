from dotenv import load_dotenv
load_dotenv()

import os

channelID = os.getenv('channelID') 
channelLogID = os.getenv('channelLogID')
api = os.getenv('api')
calendar = os.getenv('calendar')