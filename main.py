import os
from fastapi import FastAPI, HTTPException
from web3 import Web3
from dotenv import load_dotenv
import openai

# -------------------- Load environment variables --------------------
if os.getenv("RAILWAY_ENVIRONMENT_ID"):
    ALCHEMY_RPC = os.environ.get("ALCHEMY_RPC")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
else:
    load_dotenv()
    ALCHEMY_RPC = os.getenv("ALCHEMY_RPC")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

if not ALCHEMY_RPC or not OPENAI_API_KEY:
    raise RuntimeError("❌ Required environment variables are missing")

# -------------------- Init Clients --------------------
web3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC))

openai.api_key = OPENAI_API_KEY
openai.base_url = OPENAI_BASE_URL
openai.headers = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "HTTP-Referer": "https://chabi-wallet-backend-production.up.railway.app",
    "X-Title": "chabi-wallet"
}

# -------------------- FastAPI App --------------------
app = FastAPI(title="Chabi Wallet API")

@app.get("/")
def home():
    return {"message": "🚀 chabi wallet ab live ha!"}

@app.get("/debug_rpc")
def debug_rpc():
    return {
        "alchemy_loaded": ALCHEMY_RPC[:45] + "...",
        "connected": web3.is_connected(),
        "openai_base": OPENAI_BASE_URL,
        "openai_key_loaded": bool(OPENAI_API_KEY)
    }

@app.get("/eth_balance")
def get_eth_balance(wallet: str):
    try:
        if not web3.is_connected():
            raise HTTPException(status_code=503, detail="Web3 not connected")

        checksum_address = web3.to_checksum_address(wallet)
        balance_wei = web3.eth.get_balance(checksum_address)
        balance_eth = web3.from_wei(balance_wei, "ether")

        return {"wallet": wallet, "eth_balance": float(balance_eth)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/explain_balance")
def explain_wallet_balance(wallet: str):
    try:
        if not OPENAI_API_KEY:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY missing")

        if not web3.is_connected():
            raise HTTPException(status_code=503, detail="Web3 not connected")

        checksum_address = web3.to_checksum_address(wallet)
        balance_wei = web3.eth.get_balance(checksum_address)
        balance_eth = web3.from_wei(balance_wei, "ether")

        prompt = (
            f"This Ethereum wallet has a balance of {balance_eth:.2f} ETH. "
            "Explain what this means in simple words. "
            "Also suggest why a wallet might hold that much ETH (whale, DAO, exchange, etc.)."
        )

        response = openai.ChatCompletion.create(
            model="mistralai/mistral-7b-instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for a Web3 wallet app."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250
        )

        explanation = response.choices[0].message.content

        return {
            "wallet": wallet,
            "balance_eth": float(balance_eth),
            "explanation": explanation.strip()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
