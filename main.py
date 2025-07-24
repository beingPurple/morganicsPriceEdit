import requests
import json
import time
from flask import Flask, request, jsonify
import threading
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "713c29.myshopify.com")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2023-10")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

EXTERNAL_API_URL = os.getenv("EXTERNAL_API_URL", "https://api.jdsapp.com/get-product-details-by-skus")
EXTERNAL_API_TOKEN = os.getenv("EXTERNAL_API_TOKEN")

SKU_FILE = "sku.txt"
FORMULA_FILE = "formula.txt"
UNDER5_FORMULA_FILE = "under5.txt"
LOG_FILE = "price_updates.log"

# Configure logging
def setup_logging():
    """Setup logging to both file and console"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create a timestamp for the log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/price_updates_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()  # This will output to console
        ]
    )
    
    # Also log to a general log file for easy access
    general_log_handler = logging.FileHandler(LOG_FILE)
    general_log_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    general_log_handler.setFormatter(formatter)
    
    # Get the root logger and add the general log handler
    root_logger = logging.getLogger()
    root_logger.addHandler(general_log_handler)
    
    logging.info(f"Logging initialized. Log file: {log_filename}")
    return log_filename

app = Flask(__name__)

# --- FUNCTIONS ---
def clean_sku_for_external_api(sku):
    """Clean SKU by removing hyphen and any letters preceding it"""
    if '-' in sku:
        # Split by hyphen and take the last part
        parts = sku.split('-')
        return parts[-1]
    return sku

def get_all_shopify_skus():
    """Fetch all product variants with SKUs from Shopify"""
    try:
        logging.info("Fetching all products from Shopify...")
        url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
            "Content-Type": "application/json"
        }
        
        # GraphQL query to get all products with their variants and SKUs
        query = {
            "query": """
            query getProducts($cursor: String) {
              products(first: 250, after: $cursor) {
                pageInfo {
                  hasNextPage
                  endCursor
                }
                edges {
                  node {
                    id
                    title
                    variants(first: 250) {
                      edges {
                        node {
                          id
                          sku
                          price
                        }
                      }
                    }
                  }
                }
              }
            }
            """
        }
        
        all_skus = []
        cursor = None
        
        while True:
            if cursor:
                query["variables"] = {"cursor": cursor}
            else:
                query["variables"] = {}
            
            resp = requests.post(url, headers=headers, json=query)
            resp.raise_for_status()
            data = resp.json()
            
            products = data.get("data", {}).get("products", {})
            edges = products.get("edges", [])
            
            for product_edge in edges:
                product = product_edge["node"]
                variants = product["variants"]["edges"]
                
                for variant_edge in variants:
                    variant = variant_edge["node"]
                    sku = variant.get("sku")
                    if sku and sku.strip():  # Only include variants with non-empty SKUs
                        all_skus.append(sku)
            
            # Check if there are more pages
            page_info = products.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
        
        logging.info(f"Found {len(all_skus)} SKUs from Shopify products")
        return all_skus
        
    except Exception as e:
        logging.error(f"ERROR fetching SKUs from Shopify: {e}")
        import traceback
        logging.error(traceback.format_exc())
        raise

def read_skus(filename):
    try:
        with open(filename, 'r') as f:
            skus = [line.strip() for line in f if line.strip()]
        logging.info(f"Successfully read {len(skus)} SKUs from {filename}")
        return skus
    except Exception as e:
        logging.error(f"ERROR reading SKUs from {filename}: {e}")
        raise

def get_external_prices(skus):
    # Clean SKUs for external API
    cleaned_skus = [clean_sku_for_external_api(sku) for sku in skus]
    logging.info(f"Original SKUs: {skus}")
    logging.info(f"Cleaned SKUs for external API: {cleaned_skus}")
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "token": EXTERNAL_API_TOKEN,
        "skus": cleaned_skus
    }
    resp = requests.post(EXTERNAL_API_URL, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    
    # Create mapping from cleaned SKU back to original SKU
    sku_mapping = {clean_sku_for_external_api(sku): sku for sku in skus}
    
    # Map by original SKU for easy lookup
    result = {}
    for item in data:
        cleaned_sku = item["sku"]
        original_sku = sku_mapping.get(cleaned_sku)
        if original_sku:
            result[original_sku] = item
        else:
            logging.warning(f"No mapping found for cleaned SKU {cleaned_sku}")
    
    return result

def find_shopify_variant_by_sku(sku):
    # Shopify does not have a direct SKU search, so we use the GraphQL API for efficiency
    url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    query = {
        "query": f"""
        query {{
          productVariants(first: 1, query: \"sku:{sku}\") {{
            edges {{
              node {{
                id
                sku
                price
                product {{
                  id
                  title
                }}
              }}
            }}
          }}
        }}
        """
    }
    resp = requests.post(url, headers=headers, json=query)
    resp.raise_for_status()
    data = resp.json()
    logging.debug(f"Shopify variant search response for SKU {sku}: {json.dumps(data, indent=2)}")
    edges = data.get("data", {}).get("productVariants", {}).get("edges", [])
    if not edges:
        return None
    return edges[0]["node"]

def update_shopify_variant_price(product_id, variant_id, new_price):
    url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants {
          id
          price
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    variables = {
        "productId": product_id,
        "variants": [
            {
                "id": variant_id,
                "price": str(new_price)
            }
        ]
    }
    payload = {
        "query": mutation,
        "variables": variables
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    response_json = resp.json()
    logging.debug(f"Shopify price update response for variant {variant_id}: {json.dumps(response_json, indent=2)}")
    return response_json

def read_formula(filename):
    try:
        with open(filename, 'r') as f:
            formula = f.read().strip()
        logging.info(f"Successfully read formula from {filename}: {formula}")
        return formula
    except Exception as e:
        logging.error(f"ERROR reading formula from {filename}: {e}")
        raise

def read_under5_formula(filename):
    try:
        with open(filename, 'r') as f:
            formula = f.read().strip()
        logging.info(f"Successfully read under5 formula from {filename}: {formula}")
        return formula
    except Exception as e:
        logging.error(f"ERROR reading under5 formula from {filename}: {e}")
        return None

def calculate_price(formula, x, under5_formula=None):
    # x is the price from the external API
    # WARNING: eval can be dangerous if the formula file is not trusted!
    import math
    
    # If under5_formula is provided and price is under $5, use that formula
    if under5_formula and x < 5:
        logging.info(f"Price {x} is under $5, using under5 formula: {under5_formula}")
        return eval(under5_formula, {"x": x, "math": math, "__builtins__": {}})
    else:
        logging.info(f"Price {x} is $5 or above, using regular formula: {formula}")
        return eval(formula, {"x": x, "math": math, "__builtins__": {}})

def run_update():
    try:
        logging.info("=== Starting price update process ===")
        skus = get_all_shopify_skus()
        logging.info(f"Loaded {len(skus)} SKUs from Shopify")
        
        if not skus:
            logging.warning("No SKUs found in Shopify products. Skipping update.")
            return
        
        logging.info("Querying external API for prices...")
        external_prices = get_external_prices(skus)
        logging.info(f"Received prices for {len(external_prices)} SKUs from external API.")

        formula = read_formula(FORMULA_FILE)
        logging.info(f"Using formula: {formula}")

        # Read under5 formula if it exists
        under5_formula = read_under5_formula(UNDER5_FORMULA_FILE)
        if under5_formula:
            logging.info(f"Using under5 formula: {under5_formula}")
        else:
            logging.info("No under5 formula found, will use regular formula for all prices")

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for sku in skus:
            logging.info(f"Processing SKU: {sku}")
            cleaned_sku = clean_sku_for_external_api(sku)
            if cleaned_sku != sku:
                logging.info(f"  Using cleaned SKU for external API: {cleaned_sku}")
            
            price_info = external_prices.get(sku)
            if not price_info:
                logging.warning(f"  No price info found for SKU {sku} (cleaned: {cleaned_sku}) in external API response.")
                skipped_count += 1
                continue
            external_price = price_info.get("lessThanCasePrice")
            if external_price is None:
                logging.warning(f"  No lessThanCasePrice for SKU {sku}.")
                skipped_count += 1
                continue
            try:
                new_price = calculate_price(formula, external_price, under5_formula)
            except Exception as e:
                logging.error(f"  Error evaluating formula for SKU {sku}: {e}")
                error_count += 1
                continue
            variant = find_shopify_variant_by_sku(sku)
            if not variant:
                logging.warning(f"  No Shopify variant found for SKU {sku}.")
                skipped_count += 1
                continue
            logging.debug(f"  Variant details: {json.dumps(variant, indent=2)}")
            variant_id = variant["id"]
            product_id = variant["product"]["id"]
            old_price = variant["price"]
            logging.info(f"  Shopify variant ID: {variant_id}")
            logging.info(f"  Shopify product ID: {product_id}")
            logging.info(f"  Old price: {old_price} | New price: {new_price}")
            if str(old_price) == str(new_price):
                logging.info("  Price is already up to date.")
                skipped_count += 1
                continue
            result = update_shopify_variant_price(product_id, variant_id, new_price)
            errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
            graphql_errors = result.get("errors", [])
            if graphql_errors:
                logging.error(f"  GraphQL error updating price: {graphql_errors}")
                error_count += 1
            elif errors:
                logging.error(f"  User error updating price: {errors}")
                error_count += 1
            else:
                logging.info("  Price updated successfully.")
                updated_count += 1
            # Be nice to Shopify API
            time.sleep(0.5)
        
        logging.info("=== Price update process completed ===")
        logging.info(f"Summary: {updated_count} updated, {skipped_count} skipped, {error_count} errors")
        
    except Exception as e:
        logging.error(f"ERROR in run_update: {e}")
        import traceback
        logging.error(traceback.format_exc())

@app.route('/webhook', methods=['POST'])
def webhook():
    logging.info("Webhook received, running update...")
    threading.Thread(target=run_update).start()
    return jsonify({"status": "update triggered"}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "files": {
            "formula_file_exists": os.path.exists(FORMULA_FILE)
        },
        "config": {
            "shopify_store": SHOPIFY_STORE,
            "external_api_url": EXTERNAL_API_URL
        }
    }), 200

@app.route('/update-sku/<sku>', methods=['POST'])
def update_specific_sku(sku):
    """Update price for a specific SKU"""
    try:
        logging.info(f"Manual update requested for SKU: {sku}")
        cleaned_sku = clean_sku_for_external_api(sku)
        logging.info(f"Using cleaned SKU for external API: {cleaned_sku}")
        
        # Get external price
        external_prices = get_external_prices([sku])
        if not external_prices.get(sku):
            return jsonify({"error": f"No price info found for SKU {sku} (cleaned: {cleaned_sku})"}), 404
        
        price_info = external_prices[sku]
        external_price = price_info.get("lessThanCasePrice")
        if external_price is None:
            return jsonify({"error": f"No lessThanCasePrice for SKU {sku}"}), 404
        
        # Calculate new price
        formula = read_formula(FORMULA_FILE)
        under5_formula = read_under5_formula(UNDER5_FORMULA_FILE)
        new_price = calculate_price(formula, external_price, under5_formula)
        
        # Find and update Shopify variant
        variant = find_shopify_variant_by_sku(sku)
        if not variant:
            return jsonify({"error": f"No Shopify variant found for SKU {sku}"}), 404
        
        variant_id = variant["id"]
        product_id = variant["product"]["id"]
        old_price = variant["price"]
        
        if str(old_price) == str(new_price):
            return jsonify({
                "message": "Price already up to date",
                "sku": sku,
                "cleaned_sku": cleaned_sku,
                "price": new_price
            }), 200
        
        result = update_shopify_variant_price(product_id, variant_id, new_price)
        errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
        graphql_errors = result.get("errors", [])
        
        if graphql_errors or errors:
            error_msg = graphql_errors or errors
            return jsonify({"error": f"Failed to update price: {error_msg}"}), 500
        
        return jsonify({
            "message": "Price updated successfully",
            "sku": sku,
            "cleaned_sku": cleaned_sku,
            "old_price": old_price,
            "new_price": new_price
        }), 200
        
    except Exception as e:
        logging.error(f"ERROR updating specific SKU {sku}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/logs', methods=['GET'])
def view_logs():
    """View recent logs for debugging"""
    try:
        # Read the general log file
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                # Get the last 100 lines
                lines = f.readlines()
                recent_logs = lines[-100:] if len(lines) > 100 else lines
                return jsonify({
                    "log_file": LOG_FILE,
                    "recent_logs": recent_logs,
                    "total_lines": len(lines)
                }), 200
        else:
            return jsonify({"error": "Log file not found"}), 404
    except Exception as e:
        logging.error(f"Error reading logs: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Initialize logging
    log_filename = setup_logging()
    
    logging.info("Starting Shopify price update service...")
    logging.info(f"Environment: PORT={os.environ.get('PORT', '8080')}")
    logging.info(f"Working directory: {os.getcwd()}")
    logging.info(f"Files in directory: {os.listdir('.')}")
    
    # Start the update logic in a background thread on startup
    logging.info("Starting initial price update...")
    threading.Thread(target=run_update).start()
    
    # Start Flask server to listen for webhooks
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Starting Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port) 