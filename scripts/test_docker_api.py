import asyncio
from app.db.session import AsyncSessionLocal
from app.tools.customer_tool import create_customer
import urllib.request
import json

async def run_test():
    async with AsyncSessionLocal() as db:
        cust = await create_customer(db, name="Docker Test Customer", phone="9998887776")
        customer_id = cust["customer_id"]
        print(f"Created customer: {customer_id}")

    # Now test POST /ledger
    url = "http://localhost:8000/ledger"
    payload = {
        "customer_id": customer_id,
        "transaction_type": "credit_given",
        "amount": 750.0,
        "item_description": "Kirana items",
        "source": "text",
        "confidence": 1.0
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        print(f"Transaction created: {res_data}")

    # Now test GET /customer/{customer_id}/balance
    with urllib.request.urlopen(f"http://localhost:8000/customer/{customer_id}/balance") as resp:
        bal_data = json.loads(resp.read().decode("utf-8"))
        print(f"Live balance: {bal_data}")

    # Now test GET /reports/daily
    with urllib.request.urlopen("http://localhost:8000/reports/daily") as resp:
        daily_data = json.loads(resp.read().decode("utf-8"))
        print(f"Daily report: {daily_data}")

    # Now test GET /reports/outstanding
    with urllib.request.urlopen("http://localhost:8000/reports/outstanding") as resp:
        out_data = json.loads(resp.read().decode("utf-8"))
        print(f"Outstanding report: {out_data}")

if __name__ == "__main__":
    asyncio.run(run_test())
