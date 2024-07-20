import ast
import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import loguru
import pandas as pd
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI

### VECTORIZATIONS ###


# Initialize OpenAI and LangChain embeddings
def initialize_embeddings() -> Any:
    embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    return embedder


def exponential_backoff(
    attempt: int,
    max_attempts: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> Any:
    if attempt < max_attempts:
        # Calculate delay with exponential growth and add random jitter
        delay = min(max_delay, base_delay * 2**attempt) + random.uniform(0, 1)
        time.sleep(delay)
        return True  # Indicate that we should retry
    return False  # Max attempts reached, do not retry


# Function to vectorize text using OpenAIEmbeddings
def vectorize_text(
    text: Any,
    embedder: Any,
    max_characters=10_000,
) -> Any:
    # logger.debug(type(text))
    if text is None or pd.Series([text]).isna().any():
        logger.debug("Text is None, , returning NULL embeddings")
        return None
    if len(text) > max_characters:
        logger.warning(
            f"Text of length {len(text)} chars is too long, will not attempt tokenization for: {text[0:50]}...{text[-50:]}"
        )
        return None
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            vector = embedder.embed_query(text)

            if vector:
                return vector
            # Wait before retrying
            if not exponential_backoff(attempt, max_attempts):
                break  # Exceeded max attempts, give up
        except Exception as e:
            logger.error(f"An error occurred: {e}")

            # Wait before retrying
            if not exponential_backoff(attempt, max_attempts):
                break  # Exceeded max attempts, give up
    return None


def vectorize_wrapper(args: Any) -> Any:
    return vectorize_text(*args)


# Function to perform vectorization on the dataframe
def perform_vectorization(df: Any, columns_to_vectorize: Optional[dict]) -> Any:
    if columns_to_vectorize:
        embedder = initialize_embeddings()
        with ThreadPoolExecutor() as executor:
            for column, vectorized_column in columns_to_vectorize.items():
                df[vectorized_column] = list(
                    executor.map(vectorize_wrapper, [(x, embedder) for x in df[column]])
                )
                # logger.debug(df[vectorized_column])
                # logger.debug(column)
    return df


### LLM CALL-RESPONSE ###


def call_openai_response(system_prompt, user_prompt):
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response

    except Exception as e:
        logger.warning(f"An unexpected error occurred during API call: {e}")
        return None
