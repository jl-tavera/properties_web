from fastapi import FastAPI
from pydantic import BaseModel
from uuid import uuid4
from agents.utils.langchain_utils import (
    create_llm,
    create_vectorstore,
    load_metadata_field_info,
    create_retriever
)
from agents.utils.agent_utils import ApartmentSearchAgent

# constants for vector store and embedding
QDRANT_URL = "http://localhost:6333"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "apartments"
MODEL_NAME = "gpt-4o-mini"
DOCUMENT_CONTENT_DESCRIPTION = "Descripción del apartamento"

app = FastAPI()
# in-memory session store: session_id -> agent
session_store: dict[str, ApartmentSearchAgent] = {}



class AgentRequest(BaseModel):
    query: str
    session_id: int = None


class AgentResponse(BaseModel):
    response: str
    session_id: int


@app.post("/ask", response_model=AgentResponse)
def ask(payload: AgentRequest):
    # reuse or create session_id
    sid = payload.session_id
    print(f"Session ID: {sid}") 

    agent = session_store.get(sid)
    if not agent:
        llm = create_llm(MODEL_NAME)
        vectorstore = create_vectorstore(
            QDRANT_URL, EMBEDDING_MODEL, COLLECTION_NAME
        )
        metadata_info = load_metadata_field_info()
        retriever = create_retriever(
            llm, vectorstore, DOCUMENT_CONTENT_DESCRIPTION, metadata_info
        )
        agent = ApartmentSearchAgent(llm, retriever)
        session_store[sid] = agent

    reply = agent.handle_query(payload.query)

    return {"response": reply, "session_id": sid}