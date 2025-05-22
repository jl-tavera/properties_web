import json
import os
from typing import List

from langchain.chains.query_constructor.base import AttributeInfo
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain.retrievers.self_query.qdrant import QdrantTranslator
from langchain_openai import ChatOpenAI
from qdrant_client import QdrantClient


def create_llm(model_name: str):

    return ChatOpenAI(temperature=0, 
                      model=model_name)

def create_vectorstore(url: str, 
                       model_name:str, 
                       collection_name: str):

    client = QdrantClient(
        url=url
    )
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    vectorstore = Qdrant(client=client, 
                         collection_name=collection_name, 
                         embeddings=embeddings)
    return vectorstore


def load_metadata_field_info() -> List[AttributeInfo]:
    """
    Load a list of AttributeInfo from the metadata_fields.json file
    located in the agents/ directory (one level up from this utils module).

    :return: List of AttributeInfo instances
    """
    # 1. Determine directory of this file (agents/utils/)
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Build path to agents/metadata_fields.json
    json_path = os.path.abspath(
        os.path.join(current_dir, "..", "metadata.json")
    )

    # 3. Load and parse JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 4. Convert each entry into an AttributeInfo
    field_info: List[AttributeInfo] = []
    for entry in data:
        field_info.append(
            AttributeInfo(
                name=entry["name"],
                description=entry["description"],
                type=entry["type"],
            )
        )

    return field_info

def create_retriever(llm,
                            vectorstore,
                            document_content_description, 
                            metadata_field_info,):

    translator = QdrantTranslator(metadata_key="metadata")
    retriever = SelfQueryRetriever.from_llm(
        llm=llm,
        vectorstore=vectorstore,
        document_contents=document_content_description,
        metadata_field_info=metadata_field_info,
        structured_query_translator=translator,
        search_kwargs={"k": 10}, 
    )
    
    return retriever

