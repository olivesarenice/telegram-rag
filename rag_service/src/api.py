import datetime
import os
import re

import boto3
import llm_helper
import markdown
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
        return text.split(" ")[0][1:]
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
    Return a summary of the given text in less than 120 characters. Start with <This document describes ...>
    """

    user_prompt = f"""
    text: {text}
    """

    response = llm_helper.call_openai_response(system_prompt, user_prompt)
    return response.choices[0].message.content


def infer_title(text):
    system_prompt = f"""
    Return a title that best describes the text. Use less than 20 characters. If you are unable to infer a title, return 'Untitled'
    """

    user_prompt = f"""
    text: {text}
    """

    response = llm_helper.call_openai_response(system_prompt, user_prompt)
    return response.choices[0].message.content


def clean_content(text):
    system_prompt = f"""
    You are to clean up the given text, including proper formatting so that it is easy to understand. Do not rephrase a sentence if the language is already concise and clear. Use concise language that a B2 English proficiency speaker would use. Return the text in Markdown format. Add hyperlinks where appropriate.
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


def retrieve_hybrid_search(text, top_n, collection):
    """_summary_

    Args:
        filter_d (dict): {"domain":"ideas"} | {"$and": [{"name": "John"}, {"price": {"$lt": 100}}]}
        text (str): _description_
        top_n (int): _description_

    Returns:
        _type_: _description_
    """
    embedding = llm_helper.vectorize_text(text, llm_helper.initialize_embeddings())

    domain = infer_domain(text)
    if domain == "":
        filter_d = {}
    else:
        filter_d = {"domain": domain}

    lg(filter_d)
    results_ite = collection.find(
        filter_d,
        sort={"$vector": embedding},
        limit=top_n,
    )

    # query = results_ite.get_sort_vector()
    return [doc for doc in results_ite]


def repack_docs_to_str_list(docs, keep_keys, sep="---"):
    repack_ls = []
    for doc in docs:
        doc_str = ""
        for key in keep_keys:
            if key == "update_ts":
                doc_str += f"*{key.upper()}* : {doc.get(key)}\n"
            else:
                doc_str += f"*{key.upper()}* :\n{doc.get(key)}\n"
        repack_ls.append(doc_str)
    return repack_ls


# Helper
def upload_to_s3(file_path, object_name, bucket_name=os.environ["PUBLIC_S3_NAME"]):

    if os.environ["RUN_ENV"] == "LOCAL":
        aws_profile = "developer_crc_PermissionSet"
        session = boto3.Session(profile_name=aws_profile)
    else:
        session = boto3.Session()

    try:

        s3_client = session.client("s3")
        s3_client.upload_file(file_path, bucket_name, object_name)
        print(f"Successfully uploaded {file_path} to s3://{bucket_name}/{object_name}")
    except Exception as e:
        print(f"Error uploading {file_path} to S3: {e}")


def create_html_file(doc):
    # Convert cleaned_content from markdown to HTML
    html_content = markdown.markdown(doc["cleaned_content"])

    # Construct the HTML content
    html = f"""
    <html>
    <head>
        <title>{doc['cleaned_title']}</title>
    </head>
    <body>
        <div>
            {doc['update_ts']}
        </div>
        <div>
            {html_content}
        </div>
        <hr />
        <div>
            <pre>{doc['raw_content']}</pre>
        </div>
    </body>
    </html>
    """
    current_ts = datetime.datetime.now().strftime("%H%M%S")
    # Create file name
    sanitise_title = re.sub(r"[^a-zA-Z0-9 ]", "", doc["cleaned_title"]).lower()
    object_name = f"{sanitise_title.replace(' ', '_')}_{current_ts}.html"

    # Save HTML content to file
    with open("tmp.html", "w", encoding="utf-8") as file:
        file.write(html)

    return object_name


def upload_to_s3_workflow(docs):
    links = []
    for doc in docs:
        # Create HTML file
        object_name = create_html_file(doc)

        # Upload the file to S3
        upload_to_s3("tmp.html", object_name)
        link = f"https://{os.environ['PUBLIC_S3_NAME']}.s3.amazonaws.com/{object_name}"
        links.append(link)
        # Clean up the local file
        os.remove("tmp.html")
    return links


def augmented_generation(prompt, docs):

    repacked_docs = repack_docs_to_str_list(
        docs,
        keep_keys=[
            "update_ts",
            "message_id",
            "cleaned_title",
        ],
    )
    docs_str = "\n---\n".join(repacked_docs)
    system_prompt = f"""
    You are a laidback, helpful daemon living in database. But never mention your role.
    Use the CONTEXT to answer the QUESTION. Try to use all context blocks to answer, only if the context is relevant to the QUESTION. Context blocks are separated by --- and are ordered by importance.
    
    If you don't have enough info to answer, just reply "I don't have enough context to answer - here are the closest documents I found", don't make anything up.
    Communicate only within CONTEXT.
    Answer in the same language as the QUESTION. Use language that a B2 English proficiency speaker would use. Format your response in Telegram Markdown V2 format.
    """

    user_prompt = """
    CONTEXT: 
    {docs_str}
    
    QUESTION: 
    {prompt}
    """.format(
        docs_str=docs_str, prompt=prompt
    )

    lg(docs_str)

    # Generate the llm reply
    response = llm_helper.call_openai_response(system_prompt, user_prompt)
    response_text = response.choices[0].message.content
    lg(response_text)

    response_text

    # Generate the links to HTML of the docs.
    links = upload_to_s3_workflow(docs)
    links_str = "\n".join([f"{i+1}. {link}" for i, link in enumerate(links)])
    # Append the links as references
    response_text_reference = response_text + "\n\nREFERENCES:\n" + links_str
    lg(response_text_reference)
    return response_text_reference  # string


def connect(endpoint, token, keyspace):
    client = DataAPIClient(token)
    database = client.get_database(endpoint, namespace=keyspace)
    lg(f"* Database: {database.info().name}")
    return database


def liveness_check(collection):

    try:
        n_docs = collection.estimated_document_count()
        lg(f"Liveness check - found {n_docs} documents.")
        return True
    except:
        lg(f"Failed liveness check.")
        return False


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

    lg(retrieve_hybrid_search(filter_d={}, text=text, top_n=3))
