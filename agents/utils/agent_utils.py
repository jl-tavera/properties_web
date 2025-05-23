import re
import json
from langchain.memory import ConversationBufferMemory
from langchain.agents import Tool, initialize_agent, AgentType
from qdrant_client.models import Filter, FieldCondition, MatchText

# 1. ────────────────────────────  System Prompt mejorado
SYSTEM_PROMPT = """
Eres un asistente experto en ayudar a usuarios a encontrar apartamentos
en la base Qdrant.    
Reglas clave:
• Cuando el usuario pida “buscar” o describa un apartamento, usa la tool
  `search_apartments`.  
• Devuelve la lista numerada incluyendo **ID** y un resumen (link, precio,
  habitaciones).  
  ↳ Termina siempre con:  
    “✦ Escribe el ID si quieres ver todos los detalles de un apartamento.”
• Si el usuario escribe solo un número o un ID, llama a
  `get_apartment_details` y muestra TODOS sus metadatos, cada uno en una
  línea «clave: valor».  
• Nunca inventes datos; si no hay resultados, di cortésmente que no
  encontraste coincidencias.
"""
ID_PATTERN = re.compile(r"^\d{1,4}$")         


class ApartmentSearchAgent:
    def __init__(self, llm, retriever, *, qdrant_client=None,
                 collection_name=None):
        """
        Parameters
        ----------
        llm : BaseLanguageModel
        retriever : VectorStoreRetriever (de Qdrant o análogo)
        qdrant_client, collection_name : opcionales, solo si quieres
            hacer lookup directo por ID, en lugar de depender de
            `self.last_results`.
        """
        self.memory = ConversationBufferMemory(return_messages=True)
        self.last_results = []
        self.retriever = retriever
        self.qdrant = qdrant_client          # NEW
        self.collection_name = collection_name
        self.map_info = None

        # ─── Definición de herramientas ─────────────────────────────
        search_tool = Tool(
            name="search_apartments",
            func=self.search_apartments,
            description=(
                "Usa esta herramienta cuando el usuario quiera buscar apartamentos. "
                "Puede describir características como número de habitaciones, barrio, ciudad, etc. "
                "La herramienta devuelve un mensaje simple con la cantidad de resultados encontrados. "
                "NO formatea ni muestra los apartamentos directamente — los resultados son gestionados por la interfaz del usuario. "
                "Después de usar esta herramienta, simplemente espera a que el usuario pida más detalles."
            )
        )

        detail_tool = Tool(
            name="get_apartment_details",
            func=self.get_apartment_details,
            description="Devuelve todos los metadatos de un apartamento."
        )

        # ─── Inicialización del agente con prompt custom ────────────
        self.agent = initialize_agent(
            tools=[search_tool, detail_tool],
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS ,
            memory=self.memory,
            handle_parsing_errors=False,
            agent_kwargs={"prefix": SYSTEM_PROMPT},     # NEW
            verbose=False,
        )

    EMOJIS = {
            "id": "🆔",
            "price": "💰",
            "bed": "🛏️",
            "bath": "🛁",
            "area": "📐",
            "location": "📍",
            "agency": "🏢",
            "parking": "🅿️",
            "stratum": "🎖️",
            "floor": "🏙️",
            "age": "⏳",
            "facilities": "🛠️",
            "places": "🗺️",
            "upload": "📅",
            "link": "🔗",
            "transport": "🚍",
            "desc": "📝",
        }
    

    def _format_price(self, value: int) -> str:
        try:
            value = int(float(value))
            return f"${value:,.0f}".replace(",", " ")  # thin-space as thousands sep.
        except Exception:
            return str(value)

    def _pretty_listing(self, md: dict[str, any], idx: int) -> str:
        """Devuelve un string bonito para un resultado."""
        idx = md.get("id", idx)
        price = self._format_price(md.get("price", "?"))
        beds = md.get("bedrooms", "?")
        baths = md.get("bathrooms", "?")
        area = md.get("area", "?")
        loc_parts = md.get("location", [])
        location = ", ".join(loc_parts[:2]) if loc_parts else "Sin ubicación"
        agency = md.get("agency", "—")
        parking = md.get("parking_lots", 0)
        stratum = md.get("stratum", "?")
        link = md.get("link", "")
        # Tomamos máximo 3 facilities para no saturar la línea.
        facilities = md.get("facilities") or []
        fac_str = " · ".join(facilities[:3])
        EMOJIS = self.EMOJIS
        first_line = (f"{idx}️⃣ {EMOJIS['price']} {price} | "
                    f"{EMOJIS['bed']} {beds} | "
                    f"{EMOJIS['bath']} {baths} | "
                    f"{EMOJIS['area']} {area} m²")
        second_line = (f"   {EMOJIS['location']} {location} · "
                    f"{EMOJIS['agency']} {agency} · "
                    f"{EMOJIS['parking']} {parking} · "
                    f"{EMOJIS['stratum']} {stratum}")
        third_line = (f"   {EMOJIS['facilities']} {fac_str}") if fac_str else ""
        fourth_line = (f"   {EMOJIS['link']} {link}") if link else ""
        divider = "\n"
        return "\n".join([first_line, second_line, third_line,fourth_line, divider])
    
    def _pretty_details(self, md: dict) -> str:

        def fmt(val):
            if isinstance(val, list):
                return ", ".join(map(str, val))
            return str(val)

        EMOJIS = self.EMOJIS
        parts = []

        parts.append(f"{EMOJIS['id']}  {md.get('id', '?')}\n")
        if link := md.get("link"):
            parts.append(f"{EMOJIS['link']} {link} \n")

        price = f"${int(md['price']):,}".replace(",", " ") if 'price' in md else "?"
        parts.append(
            f"{EMOJIS['price']} {price} | "
            f"{EMOJIS['bed']} {md.get('bedrooms', '?')} | "
            f"{EMOJIS['bath']} {md.get('bathrooms', '?')} | "
            f"{EMOJIS['area']} {md.get('area', '?')} m² \n"
        )

        location = (md.get("location", "Ubicaci'on Desconocida") )
        parts.append(
            f"{EMOJIS['location']} {location} | "
            f"{EMOJIS['agency']} {md.get('agency', '—')} \n "
            f"{EMOJIS['parking']} {md.get('parking_lots', 0)} | "
            f"{EMOJIS['stratum']} Estrato {md.get('stratum', '?')}"
        )

        piso = md.get("floor", "?")
        min_age = md.get("construction_age_min", "?")
        max_age = md.get("construction_age_max", "?")
        parts.append(
            f"{EMOJIS['floor']} Piso: {piso} | "
            f"{EMOJIS['age']} Antigüedad: {min_age}-{max_age} años"
        )

        if fecha := md.get("upload_date"):
            parts.append(f"{EMOJIS['upload']} Publicado: {fecha} \n")

        facs = md.get("facilities", [])
        if facs:
            parts.append(f"{EMOJIS['facilities']} Comodidades: {', '.join(facs)} \n")

        places = md.get("places", [])
        if places:
            parts.append(f"{EMOJIS['places']} Lugares cercanos: {', '.join(places[:5])}… \n")

        transport = md.get("transportation", [])
        if transport:
            parts.append(f"{EMOJIS['transport']} Transporte: {', '.join(transport)}\n")

        if desc := md.get("description") :
            parts.append(f"\n{EMOJIS['desc']} Descripción:\n{desc.strip()}\n")

        return "\n".join(parts)


    def search_apartments(self, query: str) -> str:
        # --- Búsqueda directa por ID -----------------------------------------
        if ID_PATTERN.match(query):
            doc = self._fetch_by_id(query)
            if not doc:
                return "No encontré un apartamento con ese ID."
            self.last_results = [doc]
            return self._pretty_listing(doc.metadata, doc.metadata.get("id", query))


        # --- Si no hay resultados, pero se usó filtro, intentar sin filtro ----
    
        docs = self.retriever.get_relevant_documents(query)

        if not docs:
            return "No encontré ningún apartamento."

        # --- Guardar y mostrar resultados --------------------------------------
        self.last_results = docs
        self.map_info = [doc.metadata for doc in docs]
    
        #listings = [self._pretty_listing(doc.metadata, i) for i, doc in enumerate(docs, start=1)]
        listings = f"Se encontraron {len(docs)} apartamentos."

        return (
        f"Se encontraron {len(docs)} apartamentos relevantes. "
        "Los resultados están disponibles. "
        "✦ Escribe el ID si quieres ver los detalles de alguno."
    )



    # 3. ─────────────────────────────  get_apartment_details
    def get_apartment_details(self, selection: str) -> str:
        selection = selection.strip()
        doc = self._fetch_by_id(selection)
        self.map_info = []
        if doc:
            return self._pretty_details(doc.metadata)

        return "No encontré un apartamento con ese ID."

    # Utilidad para buscar por ID directo en Qdrant o en caché
    # --------------------------------------------------------
    def _fetch_by_id(self, point_id: str):
        # Si tenemos cliente Qdrant, intenta recuperación directa
        if self.qdrant and self.collection_name:
            try:
                hits = self.qdrant.retrieve(
                    collection_name=self.collection_name,
                    ids=[int(point_id)]
                )
                if hits:
                    return hits[0]
            except Exception:
                pass  # si no es un int válido o hay error, sigue con el fallback

        # Fallback: buscar en `last_results`
        for doc in self.last_results:
            if str(doc.metadata.get("id")) == str(point_id):
                return doc

        return None

    # Exponer la interfaz pública
    def handle_query(self, query: str) -> str:
        q = query.strip()

        if ID_PATTERN.match(q):
            return self.get_apartment_details(q)
        
        if q.lower() == "comparar":
            if not self.map_info:
                return "No hay resultados para comparar."
            else:
                return "comparar"

        return self.agent.run(q)
