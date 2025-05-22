import re
from langchain.memory import ConversationBufferMemory
from langchain.agents import Tool, initialize_agent, AgentType

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
ID_PATTERN = re.compile(r"^\d{1,4}$")          # hasta 6 dígitos; ajusta a tu rango


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

        # ─── Definición de herramientas ─────────────────────────────
        search_tool = Tool(
            name="search_apartments",
            func=self.search_apartments,
            description=("Busca uno o varios apartamentos en la base "
                         "de datos. Si el argumento es numérico se "
                         "interpretará como ID único.")
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
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            memory=self.memory,
            handle_parsing_errors=True,
            agent_kwargs={"prefix": SYSTEM_PROMPT},     # NEW
            verbose=False,
        )

    EMOJIS = {
    "price": "💰",
    "bed": "🛏️",
    "bath": "🛁",
    "area": "📐",
    "location": "📍",
    "agency": "🏢",
    "parking": "🅿️",
    "stratum": "🎖️",
    "bullet": "🌟",
    "link": "🔗",}

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
        third_line = (f"   {EMOJIS['bullet']} {fac_str}") if fac_str else ""
        fourth_line = (f"   {EMOJIS['link']} {link}") if link else ""
        divider = "\n"
        return "\n".join([first_line, second_line, third_line,fourth_line, divider])
    
    def pretty_details(self, md: dict, description: str) -> str:
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

        def fmt(val):
            if isinstance(val, list):
                return ", ".join(map(str, val))
            return str(val)

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

        location = ", ".join(md.get("location", []))
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

        if desc := md.get("page_content") or description:
            parts.append(f"\n{EMOJIS['desc']} Descripción:\n{desc.strip()}\n")

        return "\n".join(parts)

    def search_apartments(self, query: str) -> str:
        # --- Búsqueda directa por ID -----------------------------------------
        if ID_PATTERN.match(query):
            doc = self._fetch_by_id(query)
            if not doc:
                return "No encontré un apartamento con ese ID."
            self.last_results = [doc]
            md = doc.metadata
            return self._pretty_listing(md, md.get("id", query))

        # --- Búsqueda semántica normal ---------------------------------------
        docs = self.retriever.get_relevant_documents(query)
        self.last_results = docs
        if not docs:
            return "No encontré ningún apartamento."

        lines = [self._pretty_listing(doc.metadata, i)
                for i, doc in enumerate(docs, start=1)]
        lines.append("✦ Escribe el **ID** si quieres ver todos los detalles.")
        return "\n".join(lines)


    # 3. ─────────────────────────────  get_apartment_details
    def get_apartment_details(self, selection: str) -> str:
        selection = selection.strip()
        doc = self._fetch_by_id(selection)

        if doc:
            return self.pretty_details(doc.metadata, doc.page_content)

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

        return self.agent.run(q)
