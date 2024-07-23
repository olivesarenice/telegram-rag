import os

import api
from flask import Flask, json, jsonify, render_template, request
from loguru import logger

lg = logger.info

app = Flask(__name__)


def get_db_connection(endpoint, token, keyspace):
    return api.connect(endpoint, token, keyspace)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthcheck")
def healthcheck():
    response = {"message": f"Server is connected to: {database}"}
    return response


@app.route("/send_message", methods=["POST"])
def send_message():
    collection = conn_d.get("collection")
    # recieve message from the user
    data = request.get_json()
    lg(f"RECV: {data}")
    # ensure message is converted to json if it was recieved as str
    if isinstance(data, str):
        data = json.loads(data)

    # extract text of the message
    message_id = data.get("message_id")
    text = data.get("text")

    # # invoke beluga llm
    # llm_answer = llm(query, top_k=40, top_p=0.4, temperature=0.5)
    # response = {"message": llm_answer}
    docs = [api.prepare_doc(message_id, text)]
    lg(f"LLM parsed text")
    response = collection.insert_many(docs)
    lg(f"Insert to DB complete: {response}")
    return jsonify(response)


@app.route("/get_message", methods=["POST"])
def get_message():
    # recieve message from the user
    data = request.get_json()

    # ensure message is converted to json if it was recieved as str
    if isinstance(data, str):
        data = json.loads(data)

    lg(data)
    # extract text of the message
    message_id = data.get("message_id")
    text = data.get("text")
    docs = api.retrieve_hybrid_search(
        text=text,
        top_n=1,
        collection=conn_d["collection"],
    )
    lg(docs)
    response = api.augmented_generation(prompt=text, docs=docs)
    # return jsonify(response)
    return jsonify(response)


if __name__ == "__main__":

    database = get_db_connection(
        endpoint=os.environ["ASTRA_API_ENDPOINT"],
        token=os.environ["ASTRA_API_TOKEN"],
        keyspace="telegram_rag",
    )
    collection = database.get_collection("core_messages")

    conn_d = {}
    conn_d["collection"] = collection
    conn_d["database"] = database

    app.run()
