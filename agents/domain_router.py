import os
import chromadb
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_chroma = chromadb.PersistentClient(path="db/chroma")

DOMAIN_DOCS = {
    "sales": (
        "Show customer orders, order history, what a specific customer has ordered, how much they bought, "
        "their total order value, which customer ordered the most, best customers by order count. "
        "Active orders, confirmed orders, pending orders, shipped orders, delivered orders, all order statuses. "
        "Orders from UAE, orders from Saudi Arabia, orders from Egypt — filtering orders by country. "
        "Which sales rep has the most orders, sales rep performance, rep order counts. "
        "Build equipment quotes and BOMs for clients. Recommend cameras, drones, lenses, audio, lighting from "
        "AMT's brand portfolio — DJI, Sony, RED, Profoto, Sennheiser, Zeiss, Atomos. "
        "Check available stock, out of stock products, inventory availability. "
        "Top selling products, best-selling brands, average order value, sales analytics. "
        "Which customers haven't ordered recently. Find the right product for a use case or budget."
    ),
    "distribution": (
        "Track inbound shipments arriving from suppliers — not customer sales orders. "
        "Shipments from DJI, Sony, RED, Profoto, Zeiss, Sennheiser, Atomos — supplier shipment tracking. "
        "Flag delays, customs holds, and late deliveries on inbound cargo. Overdue shipments past ETA. "
        "Check supplier purchase orders for procurement. Monitor warehouse inventory reorder thresholds. "
        "Identify which supplier is behind on delivery schedule. Procurement, logistics, freight, ETA, carrier. "
        "Low stock alerts, reorder emails, inventory levels, warehouse stock counts."
    ),
    "finance": (
        "Manage invoices — which invoices are paid, unpaid, or overdue. NOT sales orders, NOT order history — invoices and payments only. "
        "Calculate VAT rates (5% standard, 15% Saudi Arabia, 14% Egypt). "
        "Show outstanding invoice balances and accounts receivable. Run aging reports on overdue invoices. "
        "Summarise total revenue from invoices and collection rate. Identify top debtors by unpaid invoices. "
        "Currency conversion for AED. Payment status, invoice due dates, overdue amounts."
    ),
    "service": (
        "Log, view, and update device repair tickets. Check warranty eligibility. Triage a technical fault. "
        "Write professional customer update emails about repair status. Create new service intake forms. "
        "Track which devices are in repair, awaiting parts, diagnosed, or ready for collection."
    ),
}


def _get_or_build_collection():
    col_name = "amt_domains_v5"
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
