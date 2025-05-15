import os
import logging
import time
import re
from typing import List, Dict
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
import openai

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY environment variable not set.")
    raise RuntimeError("OPENAI_API_KEY not set")

# Initialize FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ChromaDB dependency
def get_chroma_collection():
    try:
        chromadb_host = os.getenv("CHROMADB_HOST", "http://13.233.244.30")
        chromadb_port = int(os.getenv("CHROMADB_PORT", "8001"))

        max_retries = 3
        for attempt in range(max_retries):
            try:
                client = chromadb.PersistentClient(path="./chroma_db")
                client.heartbeat()
                embedding_func = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=OPENAI_API_KEY,
                    model_name="text-embedding-ada-002"
                )
                collection = client.get_or_create_collection("Clothes_products", embedding_function=embedding_func)
                logger.info(f"Connected to ChromaDB at {chromadb_host}:{chromadb_port}")
                return collection
            except Exception as e:
                logger.warning(f"ChromaDB connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(10)
                else:
                    raise
    except Exception as e:
        logger.error(f"Error initializing ChromaDB: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize database")

# Pydantic model for request
class PromptRequest(BaseModel):
    prompt: str
    chat_history: List[Dict[str, str]] = []
    session_id: str | None = None

@app.post("/generate-response")
async def generate_response(request: PromptRequest, collection=Depends(get_chroma_collection)):
    try:
        logger.info(f"Processing request for session_id: {request.session_id}")

        valid_roles = {"user", "assistant", "system"}
        for msg in request.chat_history:
            if not all(key in msg for key in ["role", "content"]) or msg["role"] not in valid_roles:
                raise HTTPException(status_code=400, detail="Invalid chat_history format")

        limited_history = request.chat_history[-10:]

        try:
            results = collection.query(query_texts=[request.prompt], n_results=30)
            if not results["documents"] or not results["documents"][0]:
                logger.info("No products found for query")
                product_ids, product_names = [], []
                product_seq_ids = []
            else:
                metadatas = results["metadatas"][0]
                product_seq_ids = [str(meta.get("seq_id", "")) for meta in metadatas]
                product_names = [meta.get("name", "") for meta in metadatas]
                product_ids = product_seq_ids
                logger.info(f"Found {len(product_ids)} products")
        except Exception as e:
            logger.error(f"ChromaDB query error: {e}")
            product_ids, product_names, product_seq_ids = [], [], []

        product_string = "Available products (select up to 4 relevant ones):\n"
        for pid, name in zip(product_seq_ids, product_names):
            product_string += f"{pid}. {name}\n"

        logger.info(f"Product string sent to GPT:\n{product_string}")

        system_prompt = (
            "You are a polite and empathetic chatbot specializing in clothing and fashion advice. "
            "Your primary goal is to understand the user's preferences — such as clothing type, preferred colors, occasion, style (e.g., casual, formal, ethnic), and any fabric sensitivities — before offering product suggestions. "
            "If the user's query is vague or lacks sufficient context, ask polite follow-up questions to clarify.\n\n"

            "⚠️ When you are ready to recommend products, strictly follow this EXACT format for EACH item:\n"
            "Line 1: Here is a recommended product:\n"
            "Line 2: <Product Name>\n"
            "Line 3: Product ID: <numeric_id> (⚠️ Must be copied EXACTLY from the list below)\n\n"

            "⚠️ Important rules:\n"
            "- Recommend a maximum of 4 products.\n"
            "- Do NOT add any extra descriptions, bullet points, or formatting.\n"
            "- NEVER suggest a product without including its Product ID. If you cannot find an appropriate Product ID, do not suggest that product at all.\n"
            "- ❌ If you suggest products without a Product ID, your response will be rejected.\n\n"

            f"{product_string}"
        )

        messages = [{"role": "system", "content": system_prompt}] + limited_history + [{"role": "user", "content": request.prompt}]

        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            response_text = response.choices[0].message.content
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise HTTPException(status_code=500, detail="Error communicating with the AI model")

        matched_ids = re.findall(r'Product ID:\s*(\d{1,6})', response_text)[:4]
        logger.info(f"Extracted product IDs from GPT response: {matched_ids}")

        if not matched_ids:
            logger.info("GPT response did not include any valid Product IDs.")
            return {
                "response": response_text.strip(),
                "products": []
            }

        matched_products = []
        try:
            products_data = collection.get(ids=matched_ids)
            matched_products = products_data.get("metadatas", [])
        except Exception as e:
            logger.error(f"Error fetching product metadata: {e}")

        cleaned_response = re.sub(r'\n?Product ID:\s*\d{1,6}', '', response_text).strip()

        return {
            "response": cleaned_response,
            "products": matched_products
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
