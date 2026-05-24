import json
import logging
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm
import uuid

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Config
DATA_PATH = Path("comprehensive_plant_data_pipeline/02_cleaned_data/organized_cleaned_data_20260410_113316.json")
EMBED_MODEL = "BAAI/bge-base-en-v1.5"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "plant_collection"
BATCH_SIZE = 32

def main():
    log.info("Loading cleaned data...")
    if not DATA_PATH.exists():
        log.error(f"File not found: {DATA_PATH}")
        return
        
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    log.info(f"Loaded {len(data)} items. Initializing text splitter...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    log.info("Chunking text...")
    chunks = []
    
    # data is a dict with 'by_platform', 'by_plant_type', etc.
    # we just need to iterate over all items in 'by_platform'
    all_items = []
    if "by_platform" in data:
        for platform_items in data["by_platform"].values():
            all_items.extend(platform_items)
            
    log.info(f"Found {len(all_items)} raw items to chunk.")
    
    for item in tqdm(all_items):
        content = item.get("text", "")
        if not content:
            continue
            
        splits = splitter.split_text(content)
        for i, split in enumerate(splits):
            chunks.append({
                "text": split,
                "plant_name": item.get("plant_name", ""),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source_platform": item.get("source_platform", ""),
                "chunk_index": i
            })
            
    log.info(f"Generated {len(chunks)} chunks.")
    
    log.info(f"Loading embedding model {EMBED_MODEL}...")
    model = SentenceTransformer(EMBED_MODEL)
    
    log.info(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    log.info(f"Recreating collection '{COLLECTION_NAME}' (dimension=768)...")
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    
    log.info("Embedding and uploading in batches...")
    for i in tqdm(range(0, len(chunks), BATCH_SIZE)):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [item["text"] for item in batch]
        
        # Embed
        embeddings = model.encode(texts)
        
        # Upload
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=emb.tolist(),
                payload={
                    "content": item["text"], # For compatibility with rag_benchmark
                    "plant_name": item["plant_name"],
                    "title": item["title"],
                    "url": item["url"],
                    "source_platform": item["source_platform"],
                    "chunk_index": item["chunk_index"]
                }
            )
            for emb, item in zip(embeddings, batch)
        ]
        
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        
    log.info("Database rebuild complete!")

if __name__ == "__main__":
    main()
