from telethon import TelegramClient
import re
import json
from datetime import datetime
#from transformers import pipeline, AutoModelForTokenClassification, AutoTokenizer



api_id = 20139028
api_hash = 'c9146b63101289d057c8d96a9cbc345e'
channel_usernames = ['militarysummary']  # Example channel usernames

# Initialize Telegram client
client = TelegramClient('session_name', api_id, api_hash)

# later on I plan to implement a language model to parse and posts and create geojson features
#model_name = "dbmdz/bert-large-cased-finetuned-conll03-english"

# Load model and tokenizer explicitly
#model = AutoModelForTokenClassification.from_pretrained(model_name)
#tokenizer = AutoTokenizer.from_pretrained(model_name)

# Initialize pipeline with the loaded model and tokenizer
#ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, framework="pt")
"""
telegram_posts = [
    "Ukraine conducted long-range missile strikes in Bryansk.",
    "FPV drone strike reported near the southern border.",
    "Farmer protests in London draw tens of thousands."
]

for post in telegram_posts:
    print("Post: {}".format(post))
    entities = ner_pipeline(post)
    for entity in entities:
        print(" - Entity: {}, Label: {}".format(entity['word'], entity['entity']))
"""

# The functions below all follow a similar pattern. They use a regex to to find patterns matches geospatial data
# and associated attribute data. In the case below, text input patterns matching those of coordinates in decimal
# degrees are searched for. The Military summary post formatting on Telegram follows this pattern.
def extract_coordinates(text):
    pattern = r'(-?\d{1,3}\.\d+),\s*(-?\d{1,3}\.\d+)'
    matches = re.findall(pattern, text)
    coordinates = []
    for match in matches:
        lat_str = match[0]
        lon_str = match[1]
        lat = float(lat_str)
        lon = float(lon_str)
        coordinates.append((lat, lon))

    return coordinates


def extract_place(text):
    place_pattern = r'Place:\s*(.*)'
    match = re.search(place_pattern, text)
    if match:
        result = match.group(1)
        result = result.strip()
    else:
        result = None

    return result


def extract_date(text):
    date_pattern = r'Date:\s*~?(\d{2}\.\d{2}\.\d{4})'
    match = re.search(date_pattern, text)
    if match:
        date_text = match.group(1).strip()
        return datetime.strptime(date_text, "%d.%m.%Y").strftime("%d.%m.%Y")
    return None


def extract_squad(text):
    squad_pattern = r'Squad:\s*([^\n\r]*)'
    match = re.search(squad_pattern, text)
    if match:
        squad_text = match.group(1).strip()
        return squad_text
    else:
        return None


def extract_description(text):
    description_pattern = r'Description:\s*([^\n\r]*)'
    match = re.search(description_pattern, text)
    if match:
        description_text = match.group(1).strip()
        return description_text
    else:
        return None


def extract_id(text):
    id_pattern = r'id:\s*(\d+)'
    match = re.search(id_pattern, text)
    if match:
        id_text = match.group(1)
        id_text = id_text.strip()
        return id_text
    else:
        return None


def extract_source(text):
    source_pattern = r'source:\s*(.*)'
    match = re.search(source_pattern, text)
    if match:
        source_text = match.group(1)
        source_text = source_text.strip()
        return source_text
    else:
        return None

# the MilitarySummary Telegram channel is unique in its format.
async def fetch_and_process_messages():
    geojson_features = [] #declare a list to hold geojson features.
    current_date_str = datetime.now().strftime("%d.%m.%Y") #store the current date in current_date_str for matching later

    async with client:
        for channel_username in channel_usernames:  # originally this was intended to work through multiple Telegram channels
            channel = await client.get_entity(channel_username)

            async for message in client.iter_messages(channel):
                if message.text:
                    message_date = extract_date(message.text) # Check if the message date is today's date
                    if message_date and message_date == current_date_str: # if message date exists and is the same as the current date
                        coordinates = extract_coordinates(message.text) # Extract coordinates directly from message text
                        for lat, lon in coordinates:
                            # Extract other attribute information first and then build the geojson structure
                            place = extract_place(message.text)
                            squad = extract_squad(message.text)
                            description = extract_description(message.text)
                            message_id = extract_id(message.text)
                            source = extract_source(message.text)

                            geojson_features.append({
                                "type": "Feature",
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": [lat, lon]
                                },
                                "properties": {
                                    "place": place or "",  # Allow empty values hence ""
                                    "date": message_date or "",
                                    "coordinates": f"{lat},{lon}",
                                    "squad": squad or "",
                                    "description": description or "",
                                    "id": message_id or "",
                                    "source": source or ""
                                }
                            })

    geojson_data = {"type": "FeatureCollection", "features": geojson_features} # declare the geojson data
    with open("locations.geojson", "w") as file:
        json.dump(geojson_data, file, indent=2)  # Write it into a new file.

# Run the client
with client:
    client.loop.run_until_complete(fetch_and_process_messages())
