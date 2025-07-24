from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    # Optionally, you can inspect request.json for SKUs or other info
    print("Received webhook:", request.json)
    # Trigger your update script (non-blocking)
    subprocess.Popen(['python3', '/update_shopify_prices.py'])
    return '', 204  # Respond with no content

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)