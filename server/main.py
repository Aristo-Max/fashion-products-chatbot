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

        # Validate chat_history format
        valid_roles = {"user", "assistant", "system"}
        for msg in request.chat_history:
            if not all(key in msg for key in ["role", "content"]) or msg["role"] not in valid_roles:
                raise HTTPException(status_code=400, detail="Invalid chat_history format")

        # Limit chat history to last 10 messages
        max_history_length = 10
        limited_history = request.chat_history[-max_history_length:]

        # Query ChromaDB for relevant products
        try:
            results = collection.query(
                query_texts=[request.prompt],
                n_results=5
            )
            if not results["documents"] or not results["documents"][0]:
                logger.info("No products found for query")
                product_ids = []
                product_names = []
            else:
                product_ids = results["ids"][0]
                product_names = [metadata.get("name", "") for metadata in results["metadatas"][0]]
                logger.info(f"Found {len(product_ids)} products")
        except Exception as e:
            logger.error(f"ChromaDB query error: {e}")
            product_ids = []
            product_names = []

        # Prepare product string to send to GPT (only use product names)
        product_string = "Available products (suggest only when appropriate):\n"
        for pid, name in zip(product_ids, product_names):
            product_string += f"{pid}. {name}\n"

        messages = [
            {
                "role": "system",
                "content": (
                "You are a polite and empathetic chatbot specializing in CLOTHING and fashion advice."
                # "⚠️ When a user says more, show me more, any other?, or similar phrases asking for additional options, continue suggesting **up to 4 more products** that match the **SAME COLOR and STYLE** previously discussed." 
                "Your primary goal is to understand the user's preferences — such as clothing type, preferred colors, occasion, style (e.g., casual, formal, ethnic), and any fabric sensitivities — before offering product suggestions. "
                "If the user's query is vague or lacks sufficient context, ask polite follow-up questions to clarify. "
                "You may also recommend products that are relevant based on their description, brand, or color, even if the user doesn't explicitly mention them. "
                "You can only suggest products for women. If someone asks for men's or kids' products, politely respond that YOU CAN ONLY RECOMMED WOMEN'S clothing. "
                "You MUST only recommend products that are present in the provided data. Do not recommend any product outside the provided data under any circumstances. "
                "Do not give any extra information unless the user explicitly asks for it.\n\n"
                "DO NOT provide any other COLORS OR STYLES  product unless the user explicitly asks for them. "
                "YOU MUST PROVIDE CORRECT COLOR and BRAND and STYLE of the product. which user is asking for.\n\n"

                "⚠️ When you are ready to recommend products, strictly follow this EXACT format for EACH item:\n"
                "You are a helpful, friendly, and accurate fashion assistant. Your job is to suggest up to 4 women's fashion products based ONLY on the data provided.\n\n"

                "✅ Response Format:\n"
                "- Start with a polite line like: 'Thank you for your query!' or 'I'm here to help you!'\n"
                "- Then say: 'Here are some options for [item]:'\n"
                "- If only one product is returned, list it without a number.\n"
                "- List up to 4 products as: \"<number>. <Product Name>.\" Product ID: <numeric_id>(one per line).\n"
                "- Do not repeat the intro for each product.\n"
                "- Do not mention images; the frontend will display them from metadata.\n\n"

               

                "⚠️ Important rules:\n"
                "- Recommend a maximum of 4 products.\n"
                "- ❌ If you cannot find a matching Product ID from the list, do NOT suggest that product.\n"
                "- ❌ Do not guess or invent Product IDs.\n"

                "- Do NOT add any extra descriptions, bullet points, or formatting.\n"
                "- NEVER suggest a product without including its Product ID. If you cannot find an appropriate Product ID, do not suggest that product at all.\n"
                "- ❌ If you suggest products without a Product ID, your response will be rejected.\n"
                "- ❌ Do NOT suggest any product that is not present in the provided data.\n"
                "- ❌ Do NOT suggest any product for men or kids. Only recommend products for women.\n"
                "- ❌ Do NOT provide any extra information unless the user asks for it explicitly.\n\n"

                f"{product_string}"
                )
            }
        ] + limited_history + [{"role": "user", "content": request.prompt}]

        # Generate response with OpenAI
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

       # Extract Product IDs in format: Product ID: 123
        matched_ids = re.findall(r'Product ID:\s*(\d{1,6})', response_text)
        logger.info(f"Extracted product IDs from GPT response: {matched_ids}")

        # Fetch product metadata from ChromaDB
        matched_products = []
        if matched_ids:
            try:
                products_data = collection.get(ids=[str(pid) for pid in matched_ids])
                for metadata in products_data.get("metadatas", []):
                    matched_products.append(metadata)
            except Exception as e:
                logger.error(f"Failed to fetch matched products from ChromaDB: {e}")

        # Remove product IDs from GPT response before sending to frontend
        cleaned_response = re.sub(r'\n?Product ID:\s*\d{1,6}', '', response_text).strip()
        cleaned_response = re.sub(r'\n?\s*Product ID:.*', '', response_text)

        # Return GPT response and relevant product metadata
        return {
            "response": cleaned_response,
            "products": matched_products
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")