# Shopify Price Update Service

This service automatically updates Shopify product prices based on external API data.

## Features

- **Automatic SKU Discovery**: Fetches all product SKUs from your Shopify store automatically
- **SKU Cleaning**: Automatically removes hyphens and preceding letters from SKUs before querying the external API
- **Comprehensive Logging**: Detailed logs saved to files for audit trails and debugging
- Runs price updates on deployment
- Responds to webhook triggers for real-time updates
- Uses configurable pricing formula
- Supports bulk updates for all products

## Logging

The service provides comprehensive logging for audit trails and debugging:

- **Console Output**: Real-time logs displayed in the console
- **Timestamped Log Files**: Individual log files for each run (`logs/price_updates_YYYYMMDD_HHMMSS.log`)
- **General Log File**: Continuous log file (`price_updates.log`) for easy access
- **Log Levels**: INFO, WARNING, ERROR, and DEBUG levels for different types of messages

### Log Files Location
- `logs/` directory contains timestamped log files
- `price_updates.log` contains the most recent logs
- Logs include all API calls, price updates, errors, and summaries

## Deployment

### Quick Deploy
```bash
./deploy.sh
```

### Manual Deploy
```bash
fly deploy
```

### Setting up Environment Variables on fly.io

1. **Using the setup script** (recommended):
   ```bash
   ./setup_env.sh
   ```

2. **Manual setup**:
   ```bash
   fly secrets set SHOPIFY_ACCESS_TOKEN=your_token_here
   fly secrets set EXTERNAL_API_TOKEN=your_token_here
   fly secrets set SHOPIFY_STORE=your-store.myshopify.com
   ```

3. **Verify environment variables**:
   ```bash
   fly secrets list
   ```

**Important**: Environment variables are stored securely on fly.io and are not included in your code repository.

## Configuration

The service uses environment variables for configuration. Create a `.env` file in the root directory with the following variables:

### Required Environment Variables

- `SHOPIFY_ACCESS_TOKEN` - Your Shopify admin API access token
- `EXTERNAL_API_TOKEN` - Your external API token for price data

### Optional Environment Variables

- `SHOPIFY_STORE` - Your Shopify store domain (default: 713c29.myshopify.com)
- `SHOPIFY_API_VERSION` - Shopify API version (default: 2023-10)
- `EXTERNAL_API_URL` - External API URL (default: https://api.jdsapp.com/get-product-details-by-skus)

### Example .env file
```
SHOPIFY_STORE=your-store.myshopify.com
SHOPIFY_API_VERSION=2023-10
SHOPIFY_ACCESS_TOKEN=shpat_your_access_token_here
EXTERNAL_API_URL=https://api.jdsapp.com/get-product-details-by-skus
EXTERNAL_API_TOKEN=your_external_api_token_here
```

The service also uses the following files:
- `formula.txt` - Pricing formula (use 'x' as variable for external price)

**Note**: No SKU file needed! The app automatically discovers all SKUs from your Shopify store.

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /webhook` - Trigger price update for all products
- `POST /update-sku/<sku>` - Update price for a specific SKU
- `GET /logs` - View recent logs for debugging

## Troubleshooting

### Check if the app is running
```bash
fly status
```

### View logs
```bash
fly logs
```

### View application logs
```bash
curl https://edit-price.fly.dev/logs
```

### Test health endpoint
```bash
curl https://edit-price.fly.dev/health
```

### Trigger manual update for all products
```bash
curl -X POST https://edit-price.fly.dev/webhook
```

### Update a specific SKU
```bash
curl -X POST https://edit-price.fly.dev/update-sku/YOUR_SKU_HERE
```

### Common Issues

1. **App not starting**: Check logs with `fly logs`
2. **No products found**: Ensure your Shopify products have SKUs assigned
3. **Port issues**: The app runs on port 8080 (configured in fly.toml)
4. **API errors**: Check Shopify and external API credentials

## Development

To run locally:
```bash
python main.py
```

The app will:
1. Start a Flask server on port 8080
2. Fetch all SKUs from your Shopify store
3. Run an initial price update in the background
4. Listen for webhook requests

## How It Works

1. **SKU Discovery**: Uses Shopify GraphQL API to fetch all products and their variants
2. **SKU Cleaning**: Automatically removes hyphens and preceding letters from SKUs before querying the external API (e.g., "ZPB-LTM814" becomes "LTM814")
3. **Price Fetching**: Queries external API for current prices using cleaned SKUs
4. **Price Calculation**: Applies your formula to calculate new prices
5. **Bulk Updates**: Updates all matching products in Shopify
6. **Summary Reporting**: Provides detailed logs of what was updated, skipped, or failed

## SKU Cleaning

The service automatically cleans SKUs before sending them to the external API:
- **Input**: `ZPB-LTM814` (Shopify SKU)
- **Output**: `LTM814` (sent to external API)
- **Logic**: Removes everything before and including the hyphen

This allows you to use different SKU formats in Shopify while maintaining compatibility with your external pricing API. 