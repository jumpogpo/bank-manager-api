import asyncio
import random
import string
import os
import qrcode
from datetime import datetime
from pydantic import BaseModel
from pymongo import MongoClient
from fastapi import HTTPException, Request
from PIL import Image, ImageDraw, ImageFont
from pythainlp.util import thai_strftime

class AccountCreate(BaseModel):
    first_name: str
    last_name: str
    deposit_amount: int

class EditAccount(BaseModel):
    account_id: int
    first_name: str = None
    last_name: str = None
    balance: int = None

class Transaction(BaseModel):
    account_id: int
    amount: int

class TransferTransaction(BaseModel):
    account_id: int
    target_account_id: int
    amount: int

class BankManager:
    def __init__(self, thai_bank_name: str, eng_bank_name: str):
        mongodb_user = os.environ.get('MONGODB_USER', None)
        mongodb_pass = os.environ.get('MONGODB_PASS', None)
        mongodb_service_name = os.environ.get('MONGODB_SERVICE_NAME', 'localhost')
        mongodb_port = os.environ.get('MONGODB_PORT', '27017')

        if not mongodb_user or not mongodb_pass:
            auth_string = ""
        else:
            auth_string = f"{mongodb_user}:{mongodb_pass}@"
        
        self.client = MongoClient(f"mongodb://{auth_string}{mongodb_service_name}:{mongodb_port}/")
        self.db = self.client['bank']
        self.accounts_data = self.db['accounts_data']
        self.transactions_data = self.db['transactions_data']
        self.thai_bank_name = thai_bank_name
        self.eng_bank_name = eng_bank_name
        self.locks = {}

    # Create Account Method
    def create_account(self, first_name: str, last_name: str, deposit_amount: int):
        account_id = self.generate_unique_account_id(self)

        account_data = {
            "account_id": account_id,
            "first_name": first_name,
            "last_name": last_name,
            "balance": deposit_amount,
        }

        self.accounts_data.insert_one(account_data)
        del account_data["_id"]
        return account_data      
    
    # Delete Account Method
    def delete_account(self, account_id: int):
        return self.accounts_data.delete_one({"account_id": account_id}).deleted_count > 0

    # Edit Account Method
    def edit_account(self, account_id: int, first_name: str, last_name: str, balance: int):
        account_data = self.accounts_data.find_one({"account_id": account_id})

        if not account_data:
            return "Can't find this account id info"

        update_data = {}
        
        if first_name is not None:
            update_data["first_name"] = first_name
        if last_name is not None:
            update_data["last_name"] = last_name
        if balance is not None:
            update_data["balance"] = balance

        if update_data:
            result = self.accounts_data.update_one({"account_id": account_id}, {"$set": update_data})
            
            if result.modified_count > 0:
                updated_account_data = self.accounts_data.find_one({"account_id": account_id}, {"_id": 0})
                return updated_account_data

        return "No updates were provided"

    # List All Accounts Method
    def get_all_acounts(self):
        return list(self.accounts_data.find({}, {"_id": 0})) or {}

    # Get Account Info Method
    def get_account_info(self, account_id: int):
        return self.accounts_data.find_one({"account_id": account_id}, {"_id": 0})
    
    # Get Transaction Info Method
    def get_transaction_info(self, transaction_id: str):
        return self.transactions_data.find_one({"transaction_id": transaction_id}, {"_id": 0})
    
    # Get Account Transactions Info Method
    def get_account_transactions_info(self, account_id: int):
        account_data = self.accounts_data.find_one({"account_id": account_id})

        if not account_data:
            return "Can't find this account id info"
        
        query = {
            "$or": [
                {"account_id": account_id},
                {"received_account_id": account_id},
                {"deducted_account_id": account_id}
            ]
        }

        return list(self.transactions_data.find(query, {"_id": 0}))

    # Deposit Method
    async def deposit(self, account_id: int, amount: int):
        async with (await self.get_lock(account_id)):
            if amount <= 0:
                return "Amount must be more than 0"

            account_data = self.accounts_data.find_one({"account_id": account_id}, {"_id": 0})

            if not account_data:
                return "Can't find this account id info"

            transaction_id = self.generate_unique_transaction_id(self)
            time_stamp = datetime.now()

            account_data["balance"] += amount
            self.accounts_data.update_one({"account_id": account_id}, {"$set": {"balance": account_data["balance"]}})

            self.transactions_data.insert_one({
                "transaction_id": transaction_id,
                "action": "deposit",
                "account_id": account_id,
                "amount": amount,
                "timestamp": str(time_stamp),
            })

            account_data["transaction_id"] = transaction_id
            return account_data

    # Withdraw Method
    async def withdraw(self, account_id: int, amount: int):
        async with (await self.get_lock(account_id)):
            if amount <= 0:
                return "Amount must be more than 0"

            account_data = self.accounts_data.find_one({"account_id": account_id}, {"_id": 0})

            if not account_data:
                return "Can't find this account id info"
            
            if account_data["balance"] < amount:
                return "Account balance must be more than withdraw amount"

            transaction_id = self.generate_unique_transaction_id(self)
            time_stamp = datetime.now()

            account_data["balance"] -= amount
            self.accounts_data.update_one({"account_id": account_id}, {"$set": {"balance": account_data["balance"]}})

            self.transactions_data.insert_one({
                "transaction_id": transaction_id,
                "action": "withdraw",
                "account_id": account_id,
                "amount": amount,
                "timestamp": str(time_stamp),
            })

            account_data["transaction_id"] = transaction_id
            return account_data

    # Transfer Method
    async def transfer(self, account_id: int, target_account_id: int, amount: int):
        async with (await self.get_lock(account_id)), (await self.get_lock(target_account_id)):
            if amount <= 0:
                return "Amount must be more than 0"
            
            account_data = self.accounts_data.find_one({"account_id": account_id}, {"_id": 0})

            if not account_data:
                return "Can't find this account id info"

            if account_data["balance"] < amount:
                return "Account balance must be more than or equal to transfer amount"

            target_account_data = self.accounts_data.find_one({"account_id": target_account_id}, {"_id": 0})

            if not target_account_data:
                return "Can't find this target account id info"
            
            transaction_id = self.generate_unique_transaction_id(self)
            time_stamp = datetime.now()

            account_data["balance"] -= amount
            self.accounts_data.update_one({"account_id": account_id}, {"$set": {"balance": account_data["balance"]}})

            target_account_data["balance"] += amount
            self.accounts_data.update_one({"account_id": target_account_id}, {"$set": {"balance": target_account_data["balance"]}})

            self.transactions_data.insert_one({
                "transaction_id": transaction_id,
                "action": "transfer",
                "received_account_id": target_account_id,
                "deducted_account_id": account_id,
                "amount": amount,
                "timestamp": str(time_stamp),
            })

            account_data["transaction_id"] = transaction_id
            return account_data

    def generate_slip(self, transaction_id: str, request: Request):
        transaction_info = self.get_transaction_info(transaction_id)

        if transaction_info is None:
            raise HTTPException(status_code=400, detail="Can't find this transaction id info")

        if transaction_info["action"] != "transfer":
            raise HTTPException(status_code=400, detail="Can you generate a slip-only transaction transfer")

        deducted_account_id = str(transaction_info["deducted_account_id"])
        received_account_id = str(transaction_info["received_account_id"])

        deducted_account_data = self.accounts_data.find_one({"account_id": int(deducted_account_id)}, {"_id": 0})
        received_account_data = self.accounts_data.find_one({"account_id": int(received_account_id)}, {"_id": 0})

        if not deducted_account_data:
            deducted_account_name = ""
        else:
            deducted_account_name = f'{deducted_account_data.get("first_name", "")} {deducted_account_data.get("last_name", "")}'

        if not received_account_data:
            received_account_name = ""
        else:
            received_account_name = f'{received_account_data.get("first_name", "")} {received_account_data.get("last_name", "")}'

        transaction_id = transaction_info["transaction_id"]
        amount = transaction_info["amount"]
        timestamp_str = transaction_info["timestamp"]
        timestamp_text = thai_strftime(datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f"), "%d %b %y %H:%M น.")

        # Generate Slip Image
        image = Image.open("./src/images/slip_background.png")
        draw = ImageDraw.Draw(image)
        large_font = ImageFont.truetype("./src/fonts/NotoSansThai.ttf", 26)
        small_font = ImageFont.truetype("./src/fonts/NotoSansThai.ttf", 22)

        # Title
        bank_logo = Image.open("./src/images/bank_logo.png").convert('RGBA')
        bank_logo = bank_logo.resize((220, 120))
        image.paste(bank_logo, (470, 15), bank_logo)
        draw.text((55, 30), "โอนเงินสำเร็จ", fill='black', font=large_font)
        draw.text((55, 80), f"{timestamp_text}", fill='black', font=large_font)

        # Add Deducted Information
        deducted_profile_img = Image.open("./src/images/deducted_profile_image.png").convert('RGBA')
        deducted_profile_img = deducted_profile_img.resize((120, 120))
        image.paste(deducted_profile_img, (30, 180), deducted_profile_img)
        draw.text((180, 180), deducted_account_name, fill='black', font=large_font)
        draw.text((180, 230), f"ธ.{self.thai_bank_name}", fill='black', font=large_font)
        draw.text((180, 280), "xxx-x-x{}-x".format(deducted_account_id[4:8]), fill='black', font=large_font)

        # Add Received Information
        received_profile_img = Image.open("./src/images/received_profile_image.png").convert('RGBA')
        received_profile_img = received_profile_img.resize((120, 120))
        image.paste(received_profile_img, (30, 425), received_profile_img)
        draw.text((180, 420), received_account_name, fill='black', font=large_font)
        draw.text((180, 470), f"ธ.{self.thai_bank_name}", fill='black', font=large_font)
        draw.text((180, 520), "xxx-x-x{}-x".format(received_account_id[4:8]), fill='black', font=large_font)

        # Transaction ID
        draw.text((35, 615), "เลขที่รายการ:", fill='black', font=small_font)
        text_width, text_height = draw.textsize(transaction_id, small_font)
        draw.text((350 - text_width, 665), transaction_id, fill='black', font=small_font)

        # Amount
        amount_text = "{:,.2f} บาท".format(amount)
        draw.text((35, 710), "จำนวน:", fill='black', font=small_font)
        text_width, text_height = draw.textsize(amount_text, small_font)
        draw.text((350 - text_width, 760), amount_text, fill='black', font=small_font)

        # Charge
        draw.text((35, 800), "ค่าธรรมเนียม:", fill='black', font=small_font)
        text_width, text_height = draw.textsize("0.00 บาท", small_font)
        draw.text((350 - text_width, 850), "0.00 บาท", fill='black', font=small_font)

        # Scan QR Code
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1,border=1)
        qr.add_data(f"{request.base_url}transaction/{transaction_id}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((200, 200))
        image.paste(img, (418, 645))

        # Verify Text Image
        verify_text_image = Image.open("./src/images/verify_text.png").convert('RGBA')
        verify_text_image = verify_text_image.resize((213, 35))
        image.paste(verify_text_image, (410, 852), verify_text_image)
        return image

    @staticmethod
    def generate_bank_account_id():
        account_number = ''.join([str(random.randint(0, 9)) for _ in range(9)])
        checksum = sum(map(int, account_number)) % 10
        account_number += str(checksum)
        return int(account_number)
    
    @staticmethod
    def generate_unique_account_id(self):
        while True:
            account_id = self.generate_bank_account_id()
            if not self.accounts_data.find_one({"account_id": account_id}):
                return account_id
    
    @staticmethod
    def generate_transaction_id():
        transaction_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
        return transaction_id

    @staticmethod
    def generate_unique_transaction_id(self):
        while True:
            transaction_id = self.generate_transaction_id()
            if not self.transactions_data.find_one({"transaction_id": transaction_id}):
                return transaction_id

    async def get_lock(self, account_id: int):
        if account_id not in self.locks:
            self.locks[account_id] = asyncio.Lock()
        return self.locks[account_id]
