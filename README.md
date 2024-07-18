# telegram-rag
Telegram Bot that uses LLM to write, store, and retrieve your sporadic thoughts.

# Project Plan

Motivation:

Having gone through many note taking apps, I find myself defaulting to the 'Saved Messages' function in Telegram. It's accessible, quick, and most importantly **everything** is stored in a single location, allowing me to do efficient keyword searches. This is important when I inevitably forget the background of the people I'm about to meet at a conference, or when I want to know what I was learning about last week on the train.

My user journey:

1. Something triggers me to write down notes - a YT video, meeting someone, an interesting article, etc.
2. I hurriedly type notes in my Saved Messages - notes that are full of typos, run-on sentences, and no context other than a few http links.
3. Occasionally, I review my Saved Messages to see if there are any items for me to act on, or formally write about in my journal.
4. Weeks later, I search through those messages to find information about a specific person I met. And then I search up their name on LinkedIn to familiarise myself.

Is there a way to make this entire process more consolidated and 'smarter'?

Requirements:

1. A service that handles the message content sent to Telegram servers when I do either a `/save` or `/ask` command to the bot in Telegram app, and then forwards that request to another service to handle the retrieval portion.
   
2. A service that, depending on whether it sent a request at a `/save` or `/ask` endpoint, will run the necessary LLM embedding, retrieval, and reply generation with the accompanying text `{content}`.

Approach:

This is basically a Telegram Bot service on the front-end combined with a RAG pipeline on the backend. With this design, the RAG pipeline can be extended to plug-in any contextual data store that I want, as long as the data store is updated. 

The messages sent to the bot will be treated as the primary data store, and the contextual data stores could be my own file system, LinkedIn connection details, etc.

The bot serves as the semantic router which will determine which data stores to search on, based on the #domain that is specified in the quote. 

Let's call this application **Second Thought**

Architecture:

![alt text](image.png)

In terms of resource provision, I chose the lowest cost options possible. While it would have been better to keep the vector database within the AWS ecosystem, the options were all too expensive.

Datastax provides a generous free tier and serves our purpose more than sufficiently.

We will host the services as Flask apps inside docker containers on an EC2 instance. Assuming 25% utilisation, a t4g.small instance will cost < $2 per month, which is a great price. 

All other services like EventBridge and Lambda are forever free.