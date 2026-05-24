import os
import chromadb
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_chroma = chromadb.PersistentClient(path="db/chroma")

DOMAIN_DOCS = {
    "sales": (
        "Show active customer orders, confirmed orders, pending orders from buyers, order status, order history. "
        "Build equipment quotes and BOMs for clients. Recommend cameras, drones, lenses, audio, lighting from "
        "AMT's brand portfolio — DJI, Sony, RED, Profoto, Sennheiser, Zeiss, Atomos. Check available stock to sell. "
        "Pull up what a customer has ordered before. Compare two products. "
        "Find the right product for a use case or budget. Respond to quote requests."
    ),
    "distribution": (
        "Track inbound shipments arriving from suppliers — not customer sales orders. "
        "Flag delays, customs holds, and late deliveries on inbound cargo. "
        "Check supplier purchase orders for procurement. Monitor warehouse inventory reorder thresholds. "
        "Identify which supplier is behind on delivery schedule. Procurement, logistics, freight, ETA, carrier."
    ),
    "finance": (
        "Manage invoices — which are paid, unpaid, or overdue. Calculate VAT for UAE 5%, Saudi Arabia 15%, "
        "Egypt 14%. Show outstanding customer balances and receivables. Run aging reports. "
        "Summarise total revenue and collection rate. Identify top debtors. Currency conversion for AED."
    ),
    "service": (
        "Log, view, and update device repair tickets. Check warranty eligibility. Triage a technical fault. "
        "Write professional customer update emails about repair status. Create new service intake forms. "
        "Track which devices are in repair, awaiting parts, diagnosed, or ready for collection."
    ),
}


def _get_or_build_collection():
    col_name = "amt_domains_v2"
    existing = [c.name for c in _chroma.list_collections()]
    if col_name in existing:
        return _chroma.get_collection(col_name)

    col = _chroma.create_collection(col_name, metadata={"hnsw:space": "cosine"})
    ids, docs, metas = [], [], []
    for dept, text in DOMAIN_DOCS.items():
        ids.append(dept)
        docs.append(text)
        metas.append({"department": dept})

    embeddings = client.embeddings.create(
        model="text-embedding-3-small", input=docs
    ).data
    col.add(
        ids=ids,
        documents=docs,
        metadatas=metas,
        embeddings=[e.embedding for e in embeddings],
    )
    return col


_collection = None


def classify(question: str) -> tuple[str, float]:
    global _collection
    if _collection is None:
        _collection = _get_or_build_collection()

    emb = client.embeddings.create(
        model="text-embedding-3-small", input=[question]
    ).data[0].embedding

    result = _collection.query(query_embeddings=[emb], n_results=1)
    dept = result["ids"][0][0]
    distance = result["distances"][0][0]
    confidence = round((1 - distance) * 100, 1)
    return dept, confidence
