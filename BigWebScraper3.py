from langchain_google_community import GoogleSearchAPIWrapper
from langchain_community.document_loaders import AsyncHtmlLoader
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM
from sentence_transformers import SentenceTransformer, util
import torch
#import requests
import json
#from huggingface_hub import login
import asyncio
import bs4
import os
import time
from geopy.geocoders import Nominatim

os.environ["GOOGLE_CSE_ID"] = "--------------"
os.environ["GOOGLE_API_KEY"] = "--------------"

#NEL_MODEL = "impresso-project/nel-mgenre-multilingual"

#nel_tokenizer = AutoTokenizer.from_pretrained(NEL_MODEL)
#nel_model = AutoModelForSeq2SeqLM.from_pretrained(NEL_MODEL)

sentence_similarity_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
tg_pipeline = pipeline("text-generation", "tiiuae/Falcon3-3B-Instruct", tokenizer="tiiuae/Falcon3-3B-Instruct")
ner_pipeline = pipeline("ner", "Jean-Baptiste/roberta-large-ner-english", tokenizer="Jean-Baptiste/roberta-large-ner-english", aggregation_strategy="simple")
classifier_pipeline = pipeline("zero-shot-classification", "facebook/bart-large-mnli")
auto_tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

geolocator = Nominatim(user_agent="conflict-monitoring-app-01", timeout=3)

# STEP 1) function defined to use CSE to search Google for news articles. In this case articles related to global conflicts
def search_google_with_query():
    #target_url = "https://www.bbc.com/news/articles/cvg9r4q99g4o"
    search = GoogleSearchAPIWrapper()
    query = f"inurl:cvg9r4q99g4o site:bbc.com"

    query_results = search.results(query, num_results=1)
    links = []
    for result in query_results:
        # title = result.get('title')
        link = result.get('link')
        # snippet = result.get('snippet')
        if link:
            links.append(link)
    return links

# STEP 2) function to split articles into chunks of text.
def chunk_text(soup, max_tokens=150, stride=10, min_length=20):
    paragraphs = soup.find_all("p")

    texts = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) >= min_length:
            texts.append(text)

    full_text = " ".join(texts)

    tokens = auto_tokenizer.encode(full_text, add_special_tokens=False)
    chunks = []
    for i in range(0, len(tokens), max_tokens - stride):
        chunk = tokens[i:i + max_tokens]
        chunk_paragraph = auto_tokenizer.decode(chunk)
        chunks.append(chunk_paragraph.strip())

        print("\n" + "=" * 80)
        print(f"Chunk {len(chunks)} ({len(chunk_paragraph.split())} words):")
        print(chunk_paragraph[:1000])  # print first 1000 chars for readability
        print("=" * 80 + "\n")

    return chunks

#STEP 3) must tag locs, per, and org for context and output control in text-generation step. These will be
        # items to include in the text-generation summary.
def analyze_chunk_with_ner(chunk):
    loc_list = []
    per_list = []
    org_list = []

    entities = ner_pipeline(chunk)

    for entity in entities:
        if 'entity_group' in entity:
            if entity['entity_group'] == 'LOC':
                loc_list.append(entity['word'])
            elif entity['entity_group'] == 'PER':
                per_list.append(entity['word'])
            elif entity['entity_group'] == 'ORG':
                org_list.append(entity['word'])

    locs, pers, orgs = set(loc_list), set(per_list), set(org_list)

    print("\nExtracted Named Entities:")
    print(f"  Locations: {', '.join(locs) if locs else 'None'}")
    print(f"  People: {', '.join(pers) if pers else 'None'}")
    print(f"  Organizations: {', '.join(orgs) if orgs else 'None'}")

    return locs, pers, orgs

#STEP 4) function using the tg_pipeline to write an event summary for each chunk of text
def summarize_chunk(chunk, ner_entities):
    locs, pers, orgs = ner_entities

    if locs:
        loc_str = ", ".join(locs)
    else:
        loc_str = "None"

    if pers:
        person_str = ", ".join(pers)
    else:
        person_str = "None"

    if orgs:
        org_str = ", ".join(orgs)
    else:
        org_str = "None"

    ner_context = f"""
    Named Entities Detected:
    - Locations: {loc_str}
    - People: {person_str}
    - Organizations: {org_str}
    """
    prompt = f"""
    You are a military intelligence analyst.
    Write one concise factual sentence summarizing the event described and specific location(s) WHERE the event occured.

    You MUST explicitly reference all of the detected named location entities for the event described in the excerpt.
    Only include entities present in the named entities.
    Do NOT add new people, places, or organizations.
    Do NOT speculate or mention dates.
    No assistant role tags (just output the sentence).
    
    Named Entities:
    {ner_context}

    Excerpt:
    {chunk}

    Summary (include relevant named entities):
    """.strip()

    response = tg_pipeline(prompt, max_new_tokens=75, return_full_text=False)
    return response[0]["generated_text"].strip()

#STEP 4)
#def classifiy_event_from_chunk(chunks):

def filter_duplicate_summaries(summaries, threshold=0.35):

    if not summaries:
        return []

    embeddings = sentence_similarity_model.encode(summaries, convert_to_tensor=True, normalize_embeddings=True)
    unique_summaries = [summaries[0]]
    unique_embeddings = [embeddings[0]]

    for i in range(1, len(summaries)):
        stacked_unique = torch.stack(unique_embeddings)
        scores = util.cos_sim(embeddings[i], stacked_unique)
        max_sim = float(scores.max())

        if max_sim < threshold:
            unique_summaries.append(summaries[i])
            unique_embeddings.append(embeddings[i])
        else:
            print(f"Skipping similar summary.")

    print("\n===== UNIQUE SUMMARIES =====")
    for i, summary in enumerate(unique_summaries, 1):
        print(f"\n[{i}] {summary}")

    return unique_summaries

def generate_the_where(unique_summaries, ner_locs_per_summary):
    results = {}

    for summary in unique_summaries:
        locs = ner_locs_per_summary.get(summary, [])
        loc_str = ", ".join(locs) if locs else "None"

        prompt = f"""
        You are an intelligence analyst.
        Extract ONLY the specific geographic location(s) where the event described in the summary took place.

        Only choose from this list of NER-detected locations:
        [{loc_str}]

        Respond with a VALID Python list of strings.
        No explanations, no extra words, no labels.

        Summary: {summary}

        Return format example: ["Kyiv", "Donetsk"]
        """
        response = tg_pipeline(prompt, max_new_tokens=30, return_full_text=False)

        # extract generated text safely
        generated_text = response[0].get("generated_text", "") if response else ""

        try:
            extracted_locs = eval(generated_text)
            if not isinstance(extracted_locs, list):
                extracted_locs = []
        except:
            extracted_locs = []

        results[summary] = extracted_locs

    return results

"""def link_loc_with_nel(locations, context_sentence, max_length=75):

    linked_entities = []
    for location in locations:
        if location not in context_sentence:
            continue
        marked_text = context_sentence.replace(location, f"[START] {location} [END]", 1)

        nel_inputs = nel_tokenizer(marked_text, )"""

def geocode_place(place_name, max_retries=3):
    for attempt in range(max_retries):
        try:
            time.sleep(1)
            loc = geolocator.geocode(place_name, exactly_one=True)
            if loc:
                return [loc.latitude, loc.longitude]
        except Exception as e:
            print(f"Geocoding error for {place_name} (attempt {attempt + 1}): {e}")
            time.sleep(1.5)

    return None

def build_geojson_from_summaries(summary_to_locations):
    features = []

    for summary, locs in summary_to_locations.items():
        for loc in locs:
            coords = geocode_place(loc)
            if coords:
                lat, lon = coords
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "properties": {
                        "summary": summary,
                        "location": loc,
                        "source": "https://www.bbc.com/news/articles/c1m8nmx75evo"
                    }
                }
                features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }

def classify_summary(summary):
    event_labels = [
        "diplomatic meeting", "terrorist attack", "military activity",
        "natural disaster", "civil unrest", "global finance", "tragedy", "trade"
    ]

    result = classifier_pipeline(summary, event_labels)
    top_label = result["labels"][0]
    confidence = float(result["scores"][0])

    print(f"\nSummary classified as: {top_label} ({confidence:.2f})")
    return {"top_label": top_label, "confidence": confidence}

async def access_and_analyze_urls_with_loader(urls):
    loader = AsyncHtmlLoader(urls)
    html_documents = await loader.aload()

    all_summary_locations = {}

    for document in html_documents:
        source = document.metadata.get('source')
        print(f"\n Source: {source}\n")
        soup = bs4.BeautifulSoup(document.page_content, "html.parser")
        tokenized_chunks = chunk_text(soup)

        all_summaries = []
        ner_locs_per_summary = {}  # map each summary to its LOCs

        for i, chunk in enumerate(tokenized_chunks[:-1]):  # skip last chunk
            ner_entities = analyze_chunk_with_ner(chunk)
            locs, pers, orgs = ner_entities

            print(f"\n--- Analyzing chunk {i + 1}/{len(tokenized_chunks)} ---")
            summary_text = summarize_chunk(chunk, ner_entities)
            print(f"\n📝 Summary:\n{summary_text}")

            all_summaries.append(summary_text)
            ner_locs_per_summary[summary_text] = list(locs)

        filtered_summaries = filter_duplicate_summaries(all_summaries, threshold=0.35)
        summary_locations = generate_the_where(filtered_summaries, ner_locs_per_summary)

        for summary_text, locs in summary_locations.items():
            print("\nExtracted Locations:")
            print(locs)
            classification = classify_summary(summary_text)
            print(f"Classification tag results: {classification}")

        all_summary_locations.update(summary_locations)

    geojson = build_geojson_from_summaries(all_summary_locations)

    with open("article_events.geojson", "w") as f:
        json.dump(geojson, f, indent=4)

    print(f"Saved geojson file.")

if __name__ == "__main__":
    urls = search_google_with_query()
    if urls:
        asyncio.run(access_and_analyze_urls_with_loader(urls))
    else:
        print("No URLs found for the query.")
