import os
import time
import random
import pandas as pd
import requests
from faker import Faker
from minio import Minio
from io import BytesIO
from datetime import datetime

# Init
fake = Faker()
minio_client = Minio(
    endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
bucket_name = os.getenv("MINIO_BUCKET")
webhook_url = os.getenv("N8N_WEBHOOK")

def generate_data():
    """Membuat 100 data transaksi palsu"""
    data = []
    for _ in range(100):
        data.append({
            "transaction_id": fake.uuid4(),
            "name": fake.name(),
            "amount": round(random.uniform(10000, 5000000), 2),
            "date": fake.date_this_month().isoformat(),
            "status": random.choice(["CLEARED", "PENDING"])
        })
    return pd.DataFrame(data)

def run_batch():
    print("Starting End-of-Day Batch Process...")
    
    # 1. Generate Data
    df = generate_data()
    filename = f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
    
    # 2. Simulasi Chaos
    gacha = random.randint(1, 10)
    
    ts_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    if gacha <= 2: # --- SKENARIO ERROR ---
        error_msg = "CRITICAL: Data Reconciliation Failed. Total Debit != Total Credit."
        print(f"❌ Batch FAILED: {error_msg}")
        
        # [NEW] Upload File Error ke MinIO (Biar kedetek di Dashboard)
        error_content = error_msg.encode('utf-8')
        error_filename = f"error_{ts_str}.txt"
        
        try:
            minio_client.put_object(
                bucket_name=bucket_name,
                object_name=error_filename,
                data=BytesIO(error_content),
                length=len(error_content),
                content_type='text/plain'
            )
        except Exception as e:
            print(f"Gagal upload log error: {e}")

        # Kirim Webhook Error ke n8n
        payload = {
            "status": "failed",
            "error_message": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        try:
            requests.post(webhook_url, json=payload)
        except Exception as e:
            print(f"Failed to send webhook: {e}")
            
    else: # --- SKENARIO SUKSES ---
        print("✅ Batch SUCCESS. Uploading to MinIO...")
        
        filename = f"report_{ts_str}.csv" # Pake timestamp yang sama
        
        # Convert DF ke CSV Buffer
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        csv_buffer = BytesIO(csv_bytes)
        
        # Upload ke MinIO (Versi Fix)
        found = minio_client.bucket_exists(bucket_name=bucket_name)
        if not found:
            minio_client.make_bucket(bucket_name=bucket_name)
            
        minio_client.put_object(
            bucket_name=bucket_name,
            object_name=filename,
            data=csv_buffer,
            length=len(csv_bytes),
            content_type='text/csv'
        )

        # Kirim Webhook Sukses ke n8n
        payload = {
            "status": "success",
            "filename": filename,
            "download_link": f"http://localhost:9000/{bucket_name}/{filename}", # Link internal
            "row_count": len(df),
            "timestamp": datetime.now().isoformat()
        }
        try:
            requests.post(webhook_url, json=payload)
        except Exception as e:
            print(f"Failed to send webhook: {e}")

if __name__ == "__main__":
    run_batch()
