from telethon import TelegramClient
from datetime import datetime
from transformers import pipeline, AutoModelForTokenClassification, AutoTokenizer
from geopy.geocoders import Nominatim
import json
import asyncio
import time
import re


# *********UNFINISHED SCRIPT
# Telegram API credentials
api_id = 20139028
api_hash = 'c9146b63101289d057c8d96a9cbc345e'
channel_usernames = ['s2undergroundwire']  # Example channel usernames

# Initialize Telegram client
client = TelegramClient("session_name", api_id, api_hash)

ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", grouped_entities=True)
splitter_pipeline = pipeline("text2text-generation", model="google/flan-t5-base", max_length=512)
event_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

geolocator = Nominatim(user_agent="geo_locator")


def extract_tearline_blocks(text): # this function is tailoring the LLM to operate within the confines of the
                                    # s2underground post format. Their is a 512 token count limit for each post
                                    # and the LLMs must rather be used on individual tearline blocks so we stay
                                    # below that limit.
    pattern = r"-----BEGIN TEARLINE-----(.*?)-----END TEARLINE-----"
    tearline_blocks = re.findall(pattern, text, re.DOTALL)

    stripped_blocks = []
    for block in tearline_blocks:
        stripped_blocks.append(block.strip())

    return stripped_blocks


# s2underground has a unique post format using sub-headings or "tearlines". Each tearline corresponds to an event
# that can be classified or given an event type attribute once the feature is created from the geojson file. These
# events need to be
def split_post_by_tears(text):
    prompt = (f"Split the following Telegram post into separate event summaries based on the tearlines. "
              "Each summary must be one line and start with the most specific place name. "
              "Tearlines will have international events and homefront events. Events will begin with a general"
              "location such as this example: "
              "Florida: An active shooter was reported at Florida State University this afternoon. Initial reports "
              "indicate that two separate gunmen conducted a complex small arms (SMARMS) attack at the FSU Student Union. "
              "As of this report, 2x victims are deceased, and 4x others are wounded. Reports have varied throughout the day, "
              "however many locals suggest that one of the shooters was neutralized at the scene by police, and the "
              "second shooter was taken into custody. One of the shooters has been identified as Phoenix Eichner, "
              "the son of a local Sheriff's Deputy who used his parent's service weapons in the attack."
              "Please choose the most specific geolocation possible from each tearline example. In the case above,"
              "the most specific geolocation would be Florida State University and not Florida."
              f"\n\n{text}")

    try:
        results = splitter_pipeline(prompt)
        response = results[0].get("generated_text", "")
    except (IndexError, KeyError, TypeError):
        response = ""

    sub_events = []
    for line in response.split("\n"):
        stripped = line.strip()
        if stripped:
            sub_events.append(stripped)

    result = []
    for event in sub_events:
        result.append({"summary": event, "ac_note": ""})

    return result


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
        entity_group = entity.get("entity_group", "")
        word = entity.get("word", "")
        if "LOC" in entity_group:
            locations.add(word)
        elif "PER" in entity_group:
            people.add(word)
        elif "ORG" in entity_group:
            organizations.add(word)

    return list(locations), list(people), list(organizations)


# This function uses OSM's Nominatim geocoding service (free) to apply coordinates to LOC items in the
# s2underground posts.
def geocode_locations(locations):
    geo_data = []
    seen = {}

    for location in locations:
        if location in seen:
            geo_data.append(seen[location])
            continue

        try:
            geo_result = geolocator.geocode(location)
            time.sleep(1)  # obey Nominatim's rate limit
            if geo_result:
                geo_info = {
                    "name": location,
                    "latitude": geo_result.latitude,
                    "longitude": geo_result.longitude
                }
                seen[location] = geo_info
                geo_data.append(geo_info)
        except Exception as e:
            print(f"Geocoding failed for {location}: {e}")

    return geo_data


def classify_event(text):
    # candidate labels for map features. These should appear as attribute data under a "type"
    candidate_labels = ["diplomatic meeting", "terrorist attack", "gathering event", "military activity",
                        "natural disaster", "civil unrest", "global finance", "tragedy"]

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

    current_date = datetime.utcnow().date()
    telegram_posts = []

    async with client:
        for channel_username in channel_usernames:  #loop through channel unsernames list (right now just one)
            channel = await client.get_entity(channel_username)  #call get_entity() on the telegram client object
            async for message in client.iter_messages(channel):  #loop through the channel's messages
                if message.text and message.date.date() == current_date:    #if there is text
                    telegram_posts.append(message.text)

    return telegram_posts


async def process_posts():
    telegram_posts = await fetch_telegram_posts()

    print(f"Fetched {len(telegram_posts)} Telegram posts")

    features = []
    for post in telegram_posts:
        tearline_blocks = extract_tearline_blocks(post)

        for block in tearline_blocks:
            sub_events = split_post_by_tears(block)

            for sub_event in sub_events:
                summary = sub_event["summary"]

                locations, people, organizations = extract_entities(summary)
                geo_data = await asyncio.to_thread(geocode_locations, locations)
                event_type = classify_event(summary)

                for geo in geo_data:  # using geodata here. Each location should be a new feature

                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [geo["latitude"], geo["longitude"]]
                        },
                        "properties": {
                            "location_name": geo["name"],
                            "summary": summary,
                            "source_post": post,
                            "entities": {
                                "people": people,
                                "organizations": organizations,
                                "locations": locations
                            },
                            "event_type": event_type,
                            "source": "s2underground"
                        }
                    }
                    features.append(feature)

    geojson = {
                "type": "FeatureCollection",
                "features": features
            }

    with open("s2underground_posts.geojson", "w") as f:
        json.dump(geojson, f, indent=4)

    print("GeoJSON file created successfully!")


if __name__ == "__main__":
    asyncio.run(process_posts())
