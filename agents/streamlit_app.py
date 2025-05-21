import os
from dotenv import load_dotenv
import streamlit as st
from openai import OpenAI
from qdrant_client import QdrantClient
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain.chains.query_constructor.base import AttributeInfo
from langchain.retrievers.self_query.qdrant import QdrantTranslator
from langchain.retrievers.self_query.base import SelfQueryRetriever
from langchain.memory import ConversationBufferMemory
from langchain.agents import Tool, initialize_agent, AgentType

# --------------------
# Carga de entorno y configuración
# --------------------
# Carga variables desde .env
load_dotenv()
# Obtener OpenAI API key: primero intenta secrets.toml, luego .env
api_key = None
try:
    api_key = st.secrets.get("OPENAI_API_KEY")
except Exception:
    pass
if not api_key:
    api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key no encontrada. Define OPENAI_API_KEY en secrets.toml o .env.")
client = OpenAI(api_key=api_key)

# Configuración de Qdrant: URL y API key opcionales
QDRANT_URL = os.getenv("QDRANT_URL", "localhost")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# --------------------
# Inicialización del cliente Qdrant
# --------------------
@st.cache_resource
def init_qdrant_client():
    # Conexión local si URL es localhost
    if QDRANT_URL in ("localhost", "127.0.0.1"):
        return QdrantClient(host="localhost", port=6333)
    # Conexión cloud
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# --------------------
# Inicialización del Retriever
# --------------------
@st.cache_resource
def init_retriever():
    client_qdrant = init_qdrant_client()
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    vectorstore = Qdrant(
        client=client_qdrant,
        collection_name="apartments",
        embeddings=embeddings,
    )
    metadata_field_info = [
        AttributeInfo("bedrooms",      "Número de habitaciones",                type="integer"),
        # ... resto de AttributeInfo ...
    ]
    document_content_description = (
        "Breve descripción del apartamento enfocándose en iluminación, vista y acabados."
    )
    translator = QdrantTranslator(metadata_key="metadata")
    retriever = SelfQueryRetriever.from_llm(
        llm=client,
        vectorstore=vectorstore,
        document_contents=document_content_description,
        metadata_field_info=metadata_field_info,
        structured_query_translator=translator,
        search_kwargs={"k": 10},
        enable_limit=True,
        use_original_query=False
    )
    return retriever

# --------------------
# Inicialización del Agente
# --------------------
@st.cache_resource
def init_agent(retriever):
    # Estado para resultados previos
    if 'last_results' not in st.session_state:
        st.session_state['last_results'] = []
    def search_apartments(query: str) -> str:
        docs = retriever.get_relevant_documents(query)
        st.session_state['last_results'] = docs
        if not docs:
            return "No encontré ningún apartamento para esa consulta."
        lines = []
        for i, doc in enumerate(docs, start=1):
            md = doc.metadata
            lines.append(
                f"{i}. {md.get('agency')} — {md.get('bedrooms')} hab., {md.get('bathrooms')} baños, precio: {md.get('price')}"
            )
        return "\n".join(lines)
    def get_apartment_details(selection: str) -> str:
        docs = st.session_state.get('last_results', [])
        if not docs:
            return "Primero realiza una búsqueda para guardar resultados."
        try:
            idx = int(selection.strip()) - 1
        except ValueError:
            return "Por favor indica un número válido."
        if idx < 0 or idx >= len(docs):
            return f"Sólo hay {len(docs)} resultados; elige entre 1 y {len(docs)}."
        md = docs[idx].metadata
        return "Detalles del apartamento seleccionado:\n" + "\n".join(f"{k}: {v}" for k, v in md.items())
    search_tool = Tool(
        name="search_apartments",
        func=search_apartments,
        description="Busca apartamentos y devuelve un listado numerado."
    )
    detail_tool = Tool(
        name="get_apartment_details",
        func=get_apartment_details,
        description="Devuelve metadatos completos de un apartamento por número."
    )
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    agent = initialize_agent(
        tools=[search_tool, detail_tool],
        llm=client,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        memory=memory,
        verbose=False
    )
    return agent

# --------------------
# Streamlit UI
# --------------------
def main():
    st.title("ChatGPT-like clone con Apartamentos")
    st.write("Usa el chat para buscar y consultar apartamentos.")
    # Inicialización
    if 'agent' not in st.session_state:
        # No pasar client_q a init_retriever
        retriever = init_retriever()
        st.session_state['agent'] = init_agent(retriever)
        st.session_state['messages'] = []
    st.title("ChatGPT-like clone con Apartamentos")
    st.write("Usa el chat para buscar y consultar apartamentos.")
    # Inicialización
    if 'agent' not in st.session_state:
        client_q = init_qdrant_client()
        retriever = init_retriever(client_q)
        st.session_state['agent'] = init_agent(retriever)
        st.session_state['messages'] = []
    # Mostrar mensajes existentes
    for msg in st.session_state['messages']:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])
    # Input de chat
    if prompt := st.chat_input("¿En qué puedo ayudarte?"):
        st.session_state['messages'].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        response = st.session_state['agent'].run(prompt)
        with st.chat_message("assistant"): st.markdown(response)
        st.session_state['messages'].append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
