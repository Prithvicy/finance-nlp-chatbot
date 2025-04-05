import os
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from pymongo import MongoClient
from dotenv import load_dotenv

print("Starting embedding script...")
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
QDRANT_HOST = "qdrant"
QDRANT_PORT = 6333

print(f"Connecting to MongoDB at {MONGO_URI}")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["finance_chatbot"]
news_collection = db["news"]

print("Connecting to Qdrant")
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

print("Loading sentence transformer model")
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_and_store():
    print("Fetching news articles from MongoDB")
    news_articles = list(news_collection.find())
    if not news_articles:
        print("No news articles to embed.")
        return

    print(f"Found {len(news_articles)} articles")
    valid_articles = []
    for article in news_articles:
        if "title" not in article or "summary" not in article:
            print(f"Skipping invalid article: {article}")
            continue
        valid_articles.append(article)

    if not valid_articles:
        print("No valid articles with title and summary to embed.")
        return

    print(f"Processing {len(valid_articles)} valid articles")
    texts = [f"{article['title']} {article['summary']}" for article in valid_articles]
    print("Embedding texts")
    embeddings = model.encode(texts, show_progress_bar=True)

    # Use integer IDs starting from 1
    points = [
        {
            "id": idx + 1,  # Simple integer ID (1, 2, 3, ...)
            "vector": embedding.tolist(),
            "payload": {
                "mongo_id": str(article["_id"]),  # Store original ObjectId for reference
                "title": article["title"],
                "summary": article["summary"],
                "link": article.get("link", ""),
                "source": article.get("source", "")
            }
        }
        for idx, (article, embedding) in enumerate(zip(valid_articles, embeddings))
    ]

    # Check if collection exists and create if not
    collections = qdrant_client.get_collections()
    collection_names = [col.name for col in collections.collections]
    if "news" not in collection_names:
        print("Creating Qdrant collection")
        qdrant_client.recreate_collection(
            collection_name="news",
            vectors_config={"size": model.get_sentence_embedding_dimension(), "distance": "Cosine"}
        )

    print("Storing embeddings in Qdrant")
    qdrant_client.upsert(collection_name="news", points=points)
    print(f"Stored {len(points)} embeddings in Qdrant.")

if __name__ == "__main__":
    embed_and_store()