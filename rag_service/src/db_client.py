import datetime
import os

import llm_helper
from astrapy import DataAPIClient
from astrapy.constants import VectorMetric
from astrapy.exceptions import CollectionAlreadyExistsException, InsertManyException
from astrapy.ids import UUID, uuid8
from astrapy.info import CollectionVectorServiceOptions
from dotenv import load_dotenv
from loguru import logger

load_dotenv("../.env")

lg = logger.info


def infer_domain(text):
    if text.startswith("#"):
        return text.split(" ")[1:]
    else:
        tag_list = ["dev-ideas", "lessons", "data-engineering", "life"]
        tags_str = "','".join(tag_list)

        system_prompt = f"""
        I have a piece of text and a list of tags. Please infer the tag that best matches the text. Return the tag as a string. If you are unable to infer the tag, return "untagged". Do not return anything else.
        """

        user_prompt = f"""\
        tags: ['{tags_str}']
        text: {text}
        """

        response = llm_helper.call_openai_response(system_prompt, user_prompt)
        return response.choices[0].message.content


def summarise_content(text):
    system_prompt = f"""
    You are to return a summary of the given text in less than 120 characters. Do not include references and links.
    """

    user_prompt = f"""
    text: {text}
    """

    response = llm_helper.call_openai_response(system_prompt, user_prompt)
    return response.choices[0].message.content


def infer_title(text):
    system_prompt = f"""
    You are to return a title that best describes the text. Use less than 20 characters.
    """

    user_prompt = f"""
    text: {text}
    """

    response = llm_helper.call_openai_response(system_prompt, user_prompt)
    return response.choices[0].message.content


def clean_content(text):
    system_prompt = f"""
    You are to clean up the given text, including proper formatting and rephrasing, so that it is easy to understand. Use language that a B2 English proficiency speaker would use. Add hyperlinks where appropriate. Return the text in Markdown format.
    """

    user_prompt = f"""
    text: {text}
    """

    response = llm_helper.call_openai_response(system_prompt, user_prompt)
    return response.choices[0].message.content


def preprocess_content(text):
    if text is None:
        text = ""

    return text.strip()


def prepare_doc(message_id, raw_content):

    # Initial content only contains raw_content
    doc = {
        "_id": uuid8(),
        "message_id": message_id,
        "update_ts": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "domain": None,
        "cleaned_title": None,
        "cleaned_summary": None,
        "cleaned_content": None,
        "cleaned_concat": None,
        "raw_content": raw_content,
        "$vector": None,
    }
    # Call LLM OpenAI to produce cleaned fields

    text = preprocess_content(raw_content)

    domain = infer_domain(text)
    title = infer_title(text)
    summary = summarise_content(text)
    content = clean_content(text)
    concat = " | ".join([title, summary, content])
    embedding = llm_helper.vectorize_text(concat, llm_helper.initialize_embeddings())

    cleaned_data = {}
    cleaned_data["domain"] = domain
    cleaned_data["cleaned_title"] = title
    cleaned_data["cleaned_summary"] = summary
    cleaned_data["cleaned_content"] = content
    cleaned_data["cleaned_concat"] = concat
    cleaned_data["$vector"] = embedding
    doc.update(cleaned_data)
    return doc


def retrieve_hybrid_search(filter_d, text, top_n):
    """_summary_

    Args:
        filter_d (dict): {"domain":"ideas"} | {"$and": [{"name": "John"}, {"price": {"$lt": 100}}]}
        text (str): _description_
        top_n (int): _description_

    Returns:
        _type_: _description_
    """

    embedding = llm_helper.vectorize_text(text, llm_helper.initialize_embeddings())

    results_ite = collection.find(
        filter_d,
        sort={"$vector": embedding},
        limit=top_n,
    )

    # query = results_ite.get_sort_vector()
    return [doc for doc in results_ite]


if __name__ == "__main__":

    import json
    import random

    # Initialize the client and get a "Database" object
    client = DataAPIClient(os.environ["ASTRA_API_TOKEN"])
    database = client.get_database(
        os.environ["ASTRA_API_ENDPOINT"], namespace="telegram_rag"
    )

    lg(f"* Database: {database.info().name}")

    try:
        collection = database.create_collection(
            "core_messages",
            dimension=1536,
            metric=VectorMetric.DOT_PRODUCT,  # Or just 'cosine'.
            check_exists=True,  # Optional
        )
    except CollectionAlreadyExistsException:
        lg("Collection already exists.")

    collection = database.get_collection("core_messages")

    # with open("data/test_messages.json", "r") as file:
    #     data = json.load(file)
    # random_item = random.choice(data)

    # message_id = random_item["object_id"]
    # text = random_item["message"]
    # docs = [prepare_doc(message_id, text)]
    # lg(docs)
    # response = collection.insert_many(docs)
    # lg(response)

    text = "startup ideas"

    lg(retrieve_hybrid_search(filter_d={}, text=text, top_n=1))
