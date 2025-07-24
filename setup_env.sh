#!/bin/bash

echo "Setting up environment variables on fly.io..."
echo ""

# Read from .env file and set on fly.io
if [ -f ".env" ]; then
    echo "Reading environment variables from .env file..."
    
    # Set each environment variable from .env file
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        if [[ -n "$key" && ! "$key" =~ ^# ]]; then
            # Remove quotes if present
            value=$(echo "$value" | sed 's/^"//;s/"$//;s/^'\''//;s/'\''$//')
            echo "Setting $key=***"
            fly secrets set "$key=$value"
        fi
    done < .env
    
    echo ""
    echo "Environment variables set successfully!"
    echo ""
    echo "To verify, run:"
    echo "fly secrets list"
    echo ""
    echo "To deploy with the new environment variables:"
    echo "fly deploy"
else
    echo "Error: .env file not found!"
    echo "Please create a .env file with your environment variables first."
    exit 1
fi 