import re
from telethon import TelegramClient
from datetime import datetime
from transformers import pipeline, AutoModelForTokenClassification, AutoTokenizer
from geopy.geocoders import Nominatim
import json

# *********UNFINISHED SCRIPT
# Telegram API credentials
api_id = 20139028
api_hash = 'c9146b63101289d057c8d96a9cbc345e'
channel_usernames = ['s2undergroundwire']  # Example channel usernames

# Initialize Telegram client
client = TelegramClient("session_name", api_id, api_hash)

# Load the NER model and tokenizer
model_name = "dbmdz/bert-large-cased-finetuned-conll03-english"
model = AutoModelForTokenClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, framework="pt")

event_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

geolocator = Nominatim(user_agent="geo_locator")

def extract_entities(text):
    #This function extracts data (locations, people, and miscellaneuos org items) from S2Underground Telegram posts.
    entities = ner_pipeline(text)

    #create sets to hold post items
    locations = set()
    people = set()
    organizations = set()

    #for loop to tag information contained within s2underground Telegram Posts. Formatting locations, persons, organizations.
    # might add more later on
    for entity in entities:
        if "LOC" in entity["entity"]:
            locations.add(entity["word"])
        elif "PER" in entity["entity"]:
            people.add(entity["word"])
        elif "ORG" in entity["entity"]:
            organizations.add(entity["word"])

    return list(locations), list(people), list(organizations)

# This function uses OSM's Nominatim geocoding service (free) to apply coordinates to LOC items in the
# s2underground posts.
def geocode_locations(locations):
    geo_data = [] # list to contain the geodata

    for location in locations:
        try:
            geo_result = geolocator.geocode(location)
            if geo_result:
                geo_data.append({
                    "name": location,
                    "latitude": geo_result.latitude,
                    "longitude": geo_result.longitude
                })
        except Exception as e:
            print(f"Geocoding failed for {location}: {e}")

    return geo_data

def classify_event(text):
    # candidate labels for map features. These should appear as attribute data under a "type"
    candidate_labels = ["diplomatic meeting", "terrorist attack", "gathering event", "military activity",
                        "natural disaster", "civil unrest", "global finance"]

    # using the event_classifier llm from HuggingFace. Parsing text and applying the appropriate label to each feature.
    result = event_classifier(text, candidate_labels)

    # this is a sort of confidence score similar to the one used in the PUG script. If the llm has a high confidence
    # the feature meets the requirement of one of the candidate_labels, it gives it that label. Otherwise, the label
    # "unkown" is given as the feature type.
    if result["scores"][0] > 0.5:
        return result["labels"][0]
    else:
        return "unknown"


async def fetch_telegram_posts():

    current_date = datetime.now()
    telegram_posts = []

    # Regular expression to match the date format
    date_pattern = r"//The Wire//(\d{4}Z)\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})//"

    async with client:
        for channel_username in channel_usernames:  #loop through channel unsernames list (right now just one)
            channel = await client.get_entity(channel_username)  #call get_entity() on the telegram client object
            async for message in client.iter_messages(channel):  #loop through the channel's messages
                if message.text is not None:    #if there is text

                    match = re.search(date_pattern, message.text) #use the date_pattern regex to check the message's date
                    if match:
                        post_date_str = match.group(1)  # Extract matched date string
                        try:
                            # Parse the extracted date
                            post_date = datetime.strptime(post_date_str, "%H%MZ %B %d, %Y")

                            # Compare with today's date
                            if post_date.date() == current_date.date():
                                telegram_posts.append(message.text)
                        except ValueError:
                            # Skip if date parsing fails
                            continue

    return telegram_posts


async def process_posts():
    telegram_posts = await fetch_telegram_posts()

    features = []
    for post in telegram_posts:

        locations, people, organizations = extract_entities(post)
        geo_data = geocode_locations(locations)
        event_type = classify_event(post)

        for geo in geo_data:

            feature = {"type": "Feature",
                             "geometry": {
                                 "type": "Point",
                                 "coordinates": [geo["longitude"], geo["latitude"]]
                             },
                            "properties": {
                                "location_name": geo["name"],
                                "post_text": post,
                                "source": "s2underground",
                                "event_type": event_type
                            }
                        }
            features.append(feature)

    geojson = {
                "type": "FeatureCollection",
                "features": features
            }

    with open("s2underground_posts.geojson", "w") as f:
        json.dump(geojson, f, indent=4)

    print("Structured GeoJSON file created successfully!")
