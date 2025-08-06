from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Fireblocks Webhook Service", version="1.0.0")

# Pydantic model for Fireblocks webhook payload
class FireblocksWebhook(BaseModel):
    id: str
    source: Optional[dict] = None
    destination: Optional[dict] = None
    amount: Optional[str] = None
    assetId: Optional[str] = None
    createdAt: Optional[str] = None
    event: Optional[str] = None

def send_telegram_message(message: str) -> bool:
    """Send message to Telegram using bot token and chat ID from environment variables."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.error("Missing Telegram bot token or chat ID in environment variables")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        })
        
        if response.status_code == 200:
            logger.info("Telegram message sent successfully")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending Telegram message: {str(e)}")
        return False

def format_transaction_message(webhook_data: FireblocksWebhook) -> str:
    """Format the transaction data into a readable Telegram message."""
    message = f"""
�� <b>New Transaction Created</b>

📋 <b>Transaction ID:</b> <code>{webhook_data.id}</code>
💰 <b>Amount:</b> {webhook_data.amount or 'N/A'} {webhook_data.assetId or 'N/A'}
📅 <b>Created:</b> {webhook_data.createdAt or 'N/A'}

📍 <b>Source:</b> {webhook_data.source.get('id', 'N/A') if webhook_data.source else 'N/A'}
�� <b>Destination:</b> {webhook_data.destination.get('id', 'N/A') if webhook_data.destination else 'N/A'}

#Fireblocks #Transaction
"""
    return message.strip()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Fireblocks Webhook Service is running", "status": "healthy"}

@app.post("/fireblocks-webhook")
async def fireblocks_webhook(webhook_data: FireblocksWebhook):
    """Handle Fireblocks webhook POST requests."""
    try:
        logger.info(f"Received webhook for transaction: {webhook_data.id}")
        
        # Check if this is a TRANSACTION_CREATED event
        if webhook_data.event != "TRANSACTION_CREATED":
            logger.info(f"Ignoring event type: {webhook_data.event}")
            return {"message": "Event ignored", "event": webhook_data.event}
        
        # Format and send Telegram message
        message = format_transaction_message(webhook_data)
        success = send_telegram_message(message)
        
        if success:
            logger.info(f"Successfully processed webhook for transaction: {webhook_data.id}")
            return {"message": "Webhook processed successfully", "transaction_id": webhook_data.id}
        else:
            logger.error(f"Failed to send Telegram message for transaction: {webhook_data.id}")
            raise HTTPException(status_code=500, detail="Failed to send Telegram notification")
            
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "Fireblocks Webhook Service",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
