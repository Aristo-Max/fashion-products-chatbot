import json
import chromadb
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load OpenAI API key from environment variable
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("Error: OPENAI_API_KEY environment variable not set.")
    exit(1)

# Load products from Fashion_Dataset.json file
try:
    with open('Fashion_Dataset.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, dict):
            products = data.get("Sheet1", [])
            logger.info("Loaded products from key 'Sheet1' in JSON.")
        elif isinstance(data, list):
            products = data
            logger.info("Loaded products as a list from JSON.")
        else:
            logger.error("Unexpected JSON format in Fashion_Dataset.json.")
            exit(1)
except FileNotFoundError:
    logger.error("Error: 'Fashion_Dataset.json' file not found.")
    exit(1)
except json.JSONDecodeError:
    logger.error("Error: 'Fashion_Dataset.json' contains invalid JSON.")
    exit(1)

# Format each product into a searchable string
def format_product(product):
    brand = product.get("brand", "")
    name = product.get("name", "") or product.get("Title", "")
    price = product.get("price", "") or product.get("Price", "")
    description = product.get("description", "")
    image = product.get("image", "")
    color = product.get("color", "")

    formatted = (
        f"Product: {name}. URL: {brand}. brand: {price}. "
        f"description: {description}. Image: {image}. color: {color}."
    )
    if not name:
        logger.warning(f"Product {product} has no valid name.")
    return formatted.strip()

# Flatten and sanitize metadata
def sanitize_metadata(data, parent_key='', sep='_'):
    sanitized = {}

    if not isinstance(data, dict):
        return {}

    for k, v in data.items():
        key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            sanitized.update(sanitize_metadata(v, key, sep))
        elif isinstance(v, list):
            sanitized[key] = ", ".join(str(item) for item in v if item is not None)
        elif v is None:
            sanitized[key] = ""
        elif isinstance(v, (str, int, float, bool)):
            sanitized[key] = v
        else:
            sanitized[key] = str(v)

    return sanitized

# Initialize OpenAI embedding function
try:
    embedding_func = embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-ada-002"
    )
except Exception as e:
    logger.error(f"Error initializing OpenAI embedding function: {e}")
    exit(1)

# Initialize ChromaDB client
hostname = os.getenv("CHROMADB_HOST", "http://13.233.244.30")
port = int(os.getenv("CHROMADB_PORT", "80"))

if hostname.startswith("http://"):
    hostname = hostname[7:]
elif hostname.startswith("https://"):
    hostname = hostname[8:]

# Retry connection to handle startup delays
max_retries = 5
for attempt in range(max_retries):
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        client.heartbeat()
        logger.info(f"Successfully connected to ChromaDB at {hostname}:{port}")
        break
    except Exception as e:
        logger.warning(f"ChromaDB connection attempt {attempt + 1} failed: {e}")
        if attempt < max_retries - 1:
            time.sleep(5)
        else:
            logger.error("Failed to connect to ChromaDB after retries.")
            exit(1)

# Create a new collection
collection_name = "Clothes_products"
try:
    existing_collections = client.list_collections()
    if any(col.name == collection_name for col in existing_collections):
        client.delete_collection(collection_name)
        logger.info(f"Deleted existing collection: {collection_name}")

    collection = client.create_collection(collection_name, embedding_function=embedding_func)
    logger.info(f"Created new collection: {collection_name}")

except Exception as e:
    logger.error(f"Error managing collection {collection_name}: {e}")
    exit(1)

# Add products to the collection in batches
batch_size = 100
documents = []
metadatas = []
ids = []

try:
    for i, product in enumerate(products):
        try:
            seq_id = i + 1  # Numeric ID starting from 1
            doc = format_product(product)

            sanitized_metadata = sanitize_metadata(product)
            sanitized_metadata["seq_id"] = seq_id

            documents.append(doc)
            metadatas.append(sanitized_metadata)
            ids.append(str(seq_id))

            if len(documents) >= batch_size:
                collection.add(documents=documents, metadatas=metadatas, ids=ids)
                logger.info(f"Added batch of {len(documents)} products")
                documents, metadatas, ids = [], [], []

        except Exception as e:
            logger.error(f"Error processing product {i}: {e}")
            continue

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        logger.info(f"Added final batch of {len(documents)} products")

    logger.info("Products successfully added to ChromaDB!")

except Exception as e:
    logger.error(f"Error adding products to ChromaDB: {e}")
    exit(1)

# List all collections
collections = client.list_collections()
logger.info("Available collections:")
for collection in collections:
    logger.info(collection.name)
