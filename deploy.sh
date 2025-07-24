#!/bin/bash

echo "Deploying to fly.io..."

# Check if environment variables are set
echo "Checking environment variables..."
if ! fly secrets list | grep -q "SHOPIFY_ACCESS_TOKEN"; then
    echo "Environment variables not set. Please run ./setup_env.sh first."
    echo "Or set them manually with:"
    echo "fly secrets set SHOPIFY_ACCESS_TOKEN=your_token_here"
    echo "fly secrets set EXTERNAL_API_TOKEN=your_token_here"
    exit 1
fi

# Build and deploy
fly deploy

echo "Deployment complete!"
echo ""
echo "To check the logs:"
echo "fly logs"
echo ""
echo "To check the health endpoint:"
echo "fly status"
echo "curl https://edit-price.fly.dev/health"
echo ""
echo "To trigger a manual update via webhook:"
echo "curl -X POST https://edit-price.fly.dev/webhook" 