"""
ChromaDB + LlamaIndex semantic search over AMT's real product catalog.
Documents are embedded once and persisted to db/chroma.
LangChain StructuredTool wraps the retrieval for clean agent dispatch.
"""
import os
from dotenv import load_dotenv
load_dotenv()

import chromadb
from llama_index.core import VectorStoreIndex, Document, StorageContext, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding

# ── Real AMT catalog documents ────────────────────────────────────────────────
# Rich natural-language descriptions for accurate semantic retrieval

AMT_CATALOG = [
    # ── Cameras ──────────────────────────────────────────────────────────────
    {
        "text": "Sony FX3 Full-Frame Cinema Camera. Category: camera. Brand: Sony Professional. "
                "A compact full-frame cinema camera with dual base ISO 800/12800, 12.1MP, 4K 120fps. "
                "Ideal for documentary, corporate video, event filmmaking. Excellent low-light. "
                "Price: AED 14,900 (~USD 4,060). In-warranty service available at AMT Dubai.",
        "metadata": {"brand": "Sony", "model": "FX3", "category": "camera", "price_aed": 14900}
    },
    {
        "text": "Sony FX6 Full-Frame Cinema Camera. Category: camera. Brand: Sony Professional. "
                "Full-frame sensor with 15+ stops dynamic range, 4K 120fps, dual base ISO. "
                "Professional broadcast and high-end production camera. "
                "Price: AED 22,000 (~USD 5,990). Best for broadcast and cinematic productions.",
        "metadata": {"brand": "Sony", "model": "FX6", "category": "camera", "price_aed": 22000}
    },
    {
        "text": "Sony FX9 Full-Frame Cinema Camera. Category: camera. Brand: Sony Professional. "
                "Full-frame sensor, Fast Hybrid AF, 4K 60fps, 15+ stops dynamic range. "
                "High-end broadcast camera for news, documentary, film. "
                "Price: approx AED 38,000. Sony certified service at AMT.",
        "metadata": {"brand": "Sony", "model": "FX9", "category": "camera", "price_aed": 38000}
    },
    {
        "text": "Sony Venice 2 Large Format Cinema Camera. Category: camera. Brand: Sony Professional. "
                "8.6K large-format sensor, 15+ stops latitude, dual base ISO 800/3200. "
                "Used in major Hollywood productions. The flagship Sony cinema camera. "
                "Price: approx AED 110,000+. Authorized Sony dealer.",
        "metadata": {"brand": "Sony", "model": "Venice 2", "category": "camera", "price_aed": 110000}
    },
    {
        "text": "Sony PXW-Z280 4K Broadcast Camcorder. Category: camera. Brand: Sony Professional. "
                "3-chip 4K HDR camcorder, broadcast-grade with built-in ND filters, XAVC codec. "
                "Perfect for news, ENG, live events. Price: AED 18,500.",
        "metadata": {"brand": "Sony", "model": "PXW-Z280", "category": "camera", "price_aed": 18500}
    },
    {
        "text": "RED V-RAPTOR 8K VV Cinema Camera. Category: camera. Brand: RED Digital Cinema. "
                "8K large format, DSMC3 system, up to 120fps at 8K. "
                "The highest resolution cinema camera for major productions. "
                "Price: AED 89,000 (~USD 24,250). RED authorized distributor.",
        "metadata": {"brand": "RED", "model": "V-RAPTOR 8K", "category": "camera", "price_aed": 89000}
    },
    {
        "text": "RED Komodo 6K Cinema Camera. Category: camera. Brand: RED Digital Cinema. "
                "Compact cinema camera, 6K global shutter, REDCODE RAW. "
                "Great for solo operators, doc filmmakers, B-camera on bigger productions. "
                "Price: approx AED 18,000.",
        "metadata": {"brand": "RED", "model": "Komodo 6K", "category": "camera", "price_aed": 18000}
    },
    {
        "text": "Sony Alpha 7 IV Mirrorless Camera. Category: camera. Brand: Sony. "
                "33MP full-frame hybrid mirrorless, 4K 60fps, real-time Eye AF. "
                "Excellent for photography and video hybrid use. "
                "Price: AED 9,200 (~USD 2,510).",
        "metadata": {"brand": "Sony", "model": "Alpha 7 IV", "category": "camera", "price_aed": 9200}
    },
    {
        "text": "Hasselblad X2D 100C Medium Format Camera. Category: camera. Brand: Hasselblad. "
                "100MP CMOS medium format sensor, 16 stops dynamic range. "
                "The ultimate camera for commercial, fashion, and fine art photography. "
                "Price: approx AED 55,000. Hasselblad authorized distributor.",
        "metadata": {"brand": "Hasselblad", "model": "X2D 100C", "category": "camera", "price_aed": 55000}
    },
    {
        "text": "Blackmagic URSA Mini Pro 12K. Category: camera. Brand: Blackmagic Design. "
                "12K Super 35 sensor, BRAW RAW recording, PL/EF/B4 mounts. "
                "Great for independent filmmakers, commercials, high-end content. "
                "Price: approx AED 14,000.",
        "metadata": {"brand": "Blackmagic", "model": "URSA Mini Pro 12K", "category": "camera", "price_aed": 14000}
    },

    # ── Drones ───────────────────────────────────────────────────────────────
    {
        "text": "DJI Mavic 3 Pro Drone. Category: drone. Brand: DJI. "
                "Triple-camera drone with Hasselblad main sensor, 5.1K video, 43-min flight time. "
                "Best prosumer drone for aerial photography and filmmaking. "
                "Price: AED 7,299. DJI authorized distributor.",
        "metadata": {"brand": "DJI", "model": "Mavic 3 Pro", "category": "drone", "price_aed": 7299}
    },
    {
        "text": "DJI Inspire 3 Cinema Drone. Category: drone. Brand: DJI. "
                "Full-frame 8K cinema drone, Zenmuse X9-8K gimbal camera. "
                "Used on Hollywood productions and major commercial shoots. "
                "Price: AED 55,000. DJI authorized distributor and repair center.",
        "metadata": {"brand": "DJI", "model": "Inspire 3", "category": "drone", "price_aed": 55000}
    },
    {
        "text": "DJI Mini 4 Pro Compact Drone. Category: drone. Brand: DJI. "
                "Lightweight drone under 249g, 4K 100fps, 34-min flight time. "
                "No registration required in UAE under 250g. "
                "Price: AED 2,799. Perfect for travel and social content.",
        "metadata": {"brand": "DJI", "model": "Mini 4 Pro", "category": "drone", "price_aed": 2799}
    },
    {
        "text": "DJI Matrice 350 RTK Enterprise Drone. Category: drone. Brand: DJI. "
                "Professional enterprise drone for surveying, inspection, mapping. "
                "55-min flight time, IP55 rating, payload up to 2.7kg. "
                "Price: AED 32,000. Requires GCAA registration in UAE.",
        "metadata": {"brand": "DJI", "model": "Matrice 350 RTK", "category": "drone", "price_aed": 32000}
    },
    {
        "text": "DJI Phantom 4 Pro V2 Drone. Category: drone. Brand: DJI. "
                "20MP 1-inch sensor, 4K 60fps, 30-min flight time. "
                "Classic professional drone for real estate and aerial video. "
                "Price: approx AED 5,500.",
        "metadata": {"brand": "DJI", "model": "Phantom 4 Pro V2", "category": "drone", "price_aed": 5500}
    },
    {
        "text": "DJI Agras T50 Agricultural Drone. Category: drone. Brand: DJI. "
                "Agricultural spraying drone, 40kg payload, 16L tank. "
                "Used for crop protection and precision agriculture across MENA. "
                "Price: approx AED 55,000.",
        "metadata": {"brand": "DJI", "model": "Agras T50", "category": "drone", "price_aed": 55000}
    },

    # ── Lenses ───────────────────────────────────────────────────────────────
    {
        "text": "Zeiss Supreme Prime 35mm T1.5 Cinema Lens. Category: lens. Brand: Zeiss. "
                "Full-frame cinema prime, LPL/PL mount, Supreme coating for minimal flare. "
                "Industry-standard cinema lens for narrative filmmaking. "
                "Price: AED 28,500 (~USD 7,770). Zeiss authorized dealer.",
        "metadata": {"brand": "Zeiss", "model": "Supreme Prime 35mm T1.5", "category": "lens", "price_aed": 28500}
    },
    {
        "text": "Zeiss Supreme Prime 50mm T1.5 Cinema Lens. Category: lens. Brand: Zeiss. "
                "Full-frame cinema prime, 50mm focal length, LPL/PL mount. "
                "Perfect normal perspective for storytelling. "
                "Price: AED 28,500. Authorized Zeiss dealer.",
        "metadata": {"brand": "Zeiss", "model": "Supreme Prime 50mm T1.5", "category": "lens", "price_aed": 28500}
    },
    {
        "text": "Zeiss Supreme Prime 85mm T1.5 Cinema Lens. Category: lens. Brand: Zeiss. "
                "Full-frame portrait cinema prime, extremely shallow depth of field. "
                "Price: AED 28,500.",
        "metadata": {"brand": "Zeiss", "model": "Supreme Prime 85mm T1.5", "category": "lens", "price_aed": 28500}
    },
    {
        "text": "Sony FE 24-70mm f/2.8 GM II Zoom Lens. Category: lens. Brand: Sony. "
                "Professional E-mount zoom lens, fast aperture, lightweight. "
                "Ideal for events, news, documentary. "
                "Price: AED 8,900 (~USD 2,430).",
        "metadata": {"brand": "Sony", "model": "FE 24-70mm f/2.8 GM II", "category": "lens", "price_aed": 8900}
    },
    {
        "text": "Angenieux Optimo 28-340mm Zoom Lens. Category: lens. Brand: Angenieux. "
                "Broadcast-grade zoom, 28-340mm T3.1, used on film and broadcast. "
                "Price: approx AED 95,000. The standard zoom for high-end broadcast.",
        "metadata": {"brand": "Angenieux", "model": "Optimo 28-340mm", "category": "lens", "price_aed": 95000}
    },

    # ── Audio ─────────────────────────────────────────────────────────────────
    {
        "text": "Sennheiser MKH 416 Shotgun Microphone. Category: audio. Brand: Sennheiser. "
                "The industry-standard boom microphone for film and broadcast. "
                "Super-cardioid polar pattern, excellent rejection of off-axis noise. "
                "Price: AED 2,800 (~USD 763). Used on nearly every professional film set.",
        "metadata": {"brand": "Sennheiser", "model": "MKH 416", "category": "audio", "price_aed": 2800}
    },
    {
        "text": "Sennheiser EW-DP ENG Set Wireless Microphone. Category: audio. Brand: Sennheiser. "
                "Digital wireless microphone system, UHF, for broadcast and ENG. "
                "Bodypack transmitter with ME 2-II lavalier microphone included. "
                "Price: AED 4,600 (~USD 1,254).",
        "metadata": {"brand": "Sennheiser", "model": "EW-DP ENG Set", "category": "audio", "price_aed": 4600}
    },
    {
        "text": "Sennheiser AMBEO VR Microphone. Category: audio. Brand: Sennheiser. "
                "360-degree ambisonics microphone for VR and spatial audio production. "
                "4 matched capsules, captures full 3D soundfield. "
                "Price: AED 3,900 (~USD 1,063).",
        "metadata": {"brand": "Sennheiser", "model": "AMBEO VR Mic", "category": "audio", "price_aed": 3900}
    },
    {
        "text": "Rode NTG5 Lightweight Shotgun Microphone. Category: audio. Brand: Rode. "
                "Ultra-compact, broadcast-grade shotgun mic. "
                "Extremely lightweight for long boom pole sessions. "
                "Price: approx AED 1,600.",
        "metadata": {"brand": "Rode", "model": "NTG5", "category": "audio", "price_aed": 1600}
    },

    # ── Lighting ─────────────────────────────────────────────────────────────
    {
        "text": "Profoto B10X Plus Battery Studio Flash. Category: lighting. Brand: Profoto. "
                "500Ws TTL/HSS battery strobe, fast recycle time, built-in modeling light. "
                "The most portable high-power strobe for location shoots. "
                "Price: AED 5,500 (~USD 1,500). Profoto authorized dealer.",
        "metadata": {"brand": "Profoto", "model": "B10X Plus", "category": "lighting", "price_aed": 5500}
    },
    {
        "text": "Profoto Pro-B4 1000 Air Location Battery Kit. Category: lighting. Brand: Profoto. "
                "1000Ws battery-powered studio kit, high-speed sync capable. "
                "For professional fashion, commercial, and outdoor studio shoots. "
                "Price: AED 14,500. Profoto authorized distributor.",
        "metadata": {"brand": "Profoto", "model": "Pro-B4 1000 Air Kit", "category": "lighting", "price_aed": 14500}
    },
    {
        "text": "Aputure 600d Pro LED Light. Category: lighting. Brand: Aputure. "
                "600W daylight LED continuous light, Bowens mount, CRI/TLCI 96+. "
                "The most popular high-power LED for film and TV production. "
                "Price: approx AED 6,500.",
        "metadata": {"brand": "Aputure", "model": "600d Pro", "category": "lighting", "price_aed": 6500}
    },
    {
        "text": "Nanlite Forza 500 LED Monolight. Category: lighting. Brand: Nanlite. "
                "500W daylight LED, Bowens mount, App control, CRI 98+. "
                "Great value high-power LED for studio work. "
                "Price: approx AED 3,200.",
        "metadata": {"brand": "Nanlite", "model": "Forza 500", "category": "lighting", "price_aed": 3200}
    },
    {
        "text": "Astera Titan Tube LED. Category: lighting. Brand: Astera. "
                "RGB+W 8W tube light, wireless control, battery powered. "
                "Used on film sets for practical lighting and creative color effects. "
                "Price: approx AED 1,800 per tube.",
        "metadata": {"brand": "Astera", "model": "Titan Tube", "category": "lighting", "price_aed": 1800}
    },

    # ── Gimbals ───────────────────────────────────────────────────────────────
    {
        "text": "DJI RS 4 Pro Gimbal Stabilizer. Category: gimbal. Brand: DJI. "
                "3-axis handheld gimbal, 4.5kg payload, OLED display, vertical shooting mode. "
                "Best-in-class stabilizer for mirrorless and cinema cameras. "
                "Price: AED 1,899 (~USD 517). DJI authorized dealer.",
        "metadata": {"brand": "DJI", "model": "RS 4 Pro", "category": "gimbal", "price_aed": 1899}
    },
    {
        "text": "DJI RS 3 Mini Gimbal Stabilizer. Category: gimbal. Brand: DJI. "
                "Lightweight gimbal for mirrorless cameras, 2kg payload, foldable. "
                "Perfect for run-and-gun and travel filmmaking. "
                "Price: AED 1,099 (~USD 299).",
        "metadata": {"brand": "DJI", "model": "RS 3 Mini", "category": "gimbal", "price_aed": 1099}
    },

    # ── Recording & Monitoring ───────────────────────────────────────────────
    {
        "text": "Atomos Shogun Ultra 8K Recorder Monitor. Category: storage. Brand: Atomos. "
                "8K HDMI/SDI monitor-recorder, HDR monitoring, Apple ProRes RAW recording. "
                "Essential on-set tool for recording from cinema cameras. "
                "Price: AED 9,500 (~USD 2,590). Atomos authorized dealer.",
        "metadata": {"brand": "Atomos", "model": "Shogun Ultra", "category": "storage", "price_aed": 9500}
    },
    {
        "text": "Atomos Ninja V+ 8K Monitor Recorder. Category: storage. Brand: Atomos. "
                "Compact 5-inch HDR monitor-recorder, 8K RAW from compatible cameras. "
                "Price: approx AED 4,200.",
        "metadata": {"brand": "Atomos", "model": "Ninja V+", "category": "storage", "price_aed": 4200}
    },
    {
        "text": "Teradek Bolt 6 XT 750 Wireless Video System. Category: storage. Brand: Teradek. "
                "Zero-delay wireless video TX/RX, up to 750ft range, 4K 60fps. "
                "Industry standard on professional film and broadcast sets. "
                "Price: AED 19,500 (~USD 5,314).",
        "metadata": {"brand": "Teradek", "model": "Bolt 6 XT 750", "category": "storage", "price_aed": 19500}
    },
    {
        "text": "Sony CFexpress Type A 160GB Memory Card. Category: storage. Brand: Sony. "
                "High-speed media card for Sony FX3, FX6, FX9, Alpha cameras. "
                "Read 800MB/s, Write 700MB/s. "
                "Price: AED 1,650 (~USD 450).",
        "metadata": {"brand": "Sony", "model": "CEA-G160T CFexpress Type A", "category": "storage", "price_aed": 1650}
    },

    # ── Support & Rigging ────────────────────────────────────────────────────
    {
        "text": "Manfrotto 504 Video Head with 535 Tripod. Category: support. Brand: Manfrotto. "
                "Professional fluid video head, 12kg payload, for broadcast and cinema cameras. "
                "Price: approx AED 3,200. Manfrotto authorized dealer.",
        "metadata": {"brand": "Manfrotto", "model": "504+535", "category": "support", "price_aed": 3200}
    },
    {
        "text": "Sachtler Aktiv8 Fluid Head Tripod System. Category: support. Brand: Sachtler. "
                "8kg payload fluid head with carbon fiber legs. "
                "Broadcast standard tripod for ENG and studio work. "
                "Price: approx AED 9,500.",
        "metadata": {"brand": "Sachtler", "model": "Aktiv8", "category": "support", "price_aed": 9500}
    },
    {
        "text": "SmallRig Universal Camera Cage. Category: support. Brand: SmallRig. "
                "Modular camera cage for Sony, RED, Blackmagic cameras. "
                "Aluminum alloy, multiple 1/4-20 and ARRI locating holes. "
                "Price: approx AED 450.",
        "metadata": {"brand": "SmallRig", "model": "Universal Camera Cage", "category": "support", "price_aed": 450}
    },
]

_index = None

def _get_index():
    global _index
    if _index is not None:
        return _index

    Settings.embed_model = OpenAIEmbedding(api_key=os.getenv("OPENAI_API_KEY"))

    db_dir = os.path.join(os.path.dirname(__file__), "..", "db", "chroma")
    os.makedirs(db_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=db_dir)
    collection = client.get_or_create_collection("amt_products_v2")

    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if collection.count() < len(AMT_CATALOG):
        # Rebuild index if stale or empty
        client.delete_collection("amt_products_v2")
        collection = client.get_or_create_collection("amt_products_v2")
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        documents = [Document(text=d["text"], metadata=d["metadata"]) for d in AMT_CATALOG]
        _index = VectorStoreIndex.from_documents(documents, storage_context=storage_context, show_progress=False)
    else:
        _index = VectorStoreIndex.from_vector_store(vector_store)

    return _index


def semantic_search(query_text: str, top_k: int = 5) -> list:
    """Core retrieval — called by the LangChain tool wrapper."""
    from . import trace
    trace.log("vector_retrieve", "LlamaIndex + ChromaDB", f'Vector search: "{query_text[:60]}"')

    try:
        index = _get_index()
        retriever = index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query_text)
        return [
            {**node.metadata, "description": node.text[:200], "relevance_score": round(node.score or 0, 3)}
            for node in nodes
        ]
    except Exception as e:
        return [{"error": str(e)}]


# ── LangChain StructuredTool definition (for agent interop) ──────────────────
try:
    from langchain.tools import StructuredTool
    from pydantic import BaseModel

    class _SearchInput(BaseModel):
        query_text: str
        top_k: int = 5

    langchain_tool = StructuredTool.from_function(
        func=semantic_search,
        name="semantic_catalog_search",
        description="AI-powered semantic search over AMT's full product catalog using LlamaIndex + ChromaDB.",
        args_schema=_SearchInput,
    )
except Exception:
    langchain_tool = None


def lc_semantic_search(query_text: str, top_k: int = 5) -> list:
    """Entry point for agents — LangChain dispatch layer before LlamaIndex retrieval."""
    from . import trace
    trace.log("tool_dispatch", "LangChain", "StructuredTool → semantic_catalog_search")
    return semantic_search(query_text, top_k)
