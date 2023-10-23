import uvicorn
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from bank_manager import BankManager, AccountCreate, Transaction, TransferTransaction, EditAccount
from io import BytesIO

port = int(os.getenv('PORT', 8000))

tags_metadata = [
    {"name": "Accounts", "description": "About accounts API"},
    {"name": "Informations", "description": "All information API"},
    {"name": "Transactions", "description": "All transactions API"},
]

app = FastAPI(
    title="Bank Account Manager API",
    version="1.0",
    description="This is Bank Account Manager API",
    docs_url="/",
    swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"},
    openapi_tags=tags_metadata,
)

bank = BankManager("เคพัง", "KPang")

@app.get("/accounts", tags=["Accounts"])
def get_all_accounts():
    return bank.get_all_acounts()

@app.post("/account", tags=["Accounts"])
def create_account(data: AccountCreate):
    return bank.create_account(data.first_name, data.last_name, data.deposit_amount)

@app.post("/account/edit", tags=["Accounts"])
def edit_account(data: EditAccount):
    edit_status = bank.edit_account(data.account_id, data.first_name, data.last_name, data.balance)
    if type(edit_status) is str:
        raise HTTPException(status_code=400, detail=edit_status)
    return edit_status

@app.delete("/delete/{account_id}", tags=["Accounts"])
def delete_account(account_id: int):
    delete_status = bank.delete_account(account_id)
    if not delete_status:
        raise HTTPException(status_code=400, detail="Can't find this account id")
    return JSONResponse(content={"message": "Delete account successful"})

@app.get("/info/{account_id}", tags=["Informations"])
def get_account_info(account_id: int):
    get_account_info_status = bank.get_account_info(account_id)
    if get_account_info_status is None:
        raise HTTPException(status_code=400, detail="Can't find this account id info")
    return get_account_info_status

@app.get("/transaction/{transaction_id}", tags=["Informations"])
def get_transaction_info(transaction_id: str):
    get_transaction_info_status = bank.get_transaction_info(transaction_id)
    if get_transaction_info_status is None:
        raise HTTPException(status_code=400, detail="Can't find this transaction id info")
    return get_transaction_info_status

@app.get("/account/transaction/{account_id}", tags=["Informations"])
def get_account_transactions_info(account_id: int):
    get_account_transactions_info_status = bank.get_account_transactions_info(account_id)
    if type(get_account_transactions_info_status) is str:
        raise HTTPException(status_code=400, detail=get_account_transactions_info_status)
    return get_account_transactions_info_status

@app.get("/slip/{transaction_id}", tags=["Informations"])
async def generate_transaction_slip(transaction_id: str, request: Request):
    image = bank.generate_slip(transaction_id, request)
    img_buffer = BytesIO()
    image.save(img_buffer, format="JPEG")
    img_buffer.seek(0)

    return StreamingResponse(
        img_buffer,
        media_type="image/jpeg",
        headers={'Content-Disposition': f'inline; filename="{transaction_id}.jpg"'}
    )

@app.post("/deposit", tags=["Transactions"])
async def deposit(data: Transaction):
    deposit_status = await bank.deposit(data.account_id, data.amount)
    if type(deposit_status) is str:
        raise HTTPException(status_code=400, detail=deposit_status)
    return deposit_status

@app.post("/withdraw", tags=["Transactions"])
async def withdraw(data: Transaction):
    withdraw_status = await bank.withdraw(data.account_id, data.amount)
    if type(withdraw_status) is str:
        raise HTTPException(status_code=400, detail=withdraw_status)
    return withdraw_status

@app.post("/transfer", tags=["Transactions"])
async def transfer(data: TransferTransaction):
    transfer_status = await bank.transfer(data.account_id, data.target_account_id, data.amount)
    if type(transfer_status) is str:
        raise HTTPException(status_code=400, detail=transfer_status)
    return transfer_status

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=port)