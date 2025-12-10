from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime

def generate_sanction_pdf(customer_name, amount, emi, filename='sanction_letter.pdf'):
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(100, 750, "Tata Capital Personal Loan Sanction Letter")
    c.drawString(100, 730, f"Customer: {customer_name}")
    c.drawString(100, 710, f"Amount: Rs. {amount:,}")
    c.drawString(100, 690, f"EMI: Rs. {emi:,}")
    c.drawString(100, 670, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    c.save()
    return filename


7. utils/blockchain_log.py
Python


from web3 import Web3
import os

def log_approval(tx_data):
    # Simulate local testnet for demo (no real setup needed)
    try:
        w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
        if w3.is_connected():
            tx_hash = w3.eth.send_transaction({
                'from': w3.eth.accounts[0],
                'data': tx_data.encode(),
                'gas': 21000
            }).hex()
            return tx_hash
    except:
        pass
    # Fallback simulation
    return '0x' + os.urandom(32).hex()[:64]
