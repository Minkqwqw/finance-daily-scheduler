import streamlit as st
import pandas as pd
import os
import requests
import random
from minio import Minio
from faker import Faker
from io import BytesIO
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="DOE8 Finance System", layout="wide", page_icon="🏦")

# --- INIT KONEKSI & ENV ---
minio_client = Minio(
    endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False
)
bucket_name = os.getenv("MINIO_BUCKET")
webhook_url = os.getenv("N8N_WEBHOOK")
fake = Faker()

# --- FUNGSI LOGIN ---
def check_login(username, password):
    users = {
        "finance": "finance",
        "devops": "admin123"
    }
    if username in users and users[username] == password:
        return True
    return False

# --- FUNGSI MANUAL TRIGGER (Logic Batch Dipindah Kesini) ---
def run_manual_job():
    try:
        # 1. Generate Data
        data = []
        for _ in range(50): # Bikin 50 data aja biar cepet
            data.append({
                "transaction_id": fake.uuid4(),
                "name": fake.name(),
                "amount": round(random.uniform(10000, 5000000), 2),
                "date": fake.date_this_month().isoformat(),
                "status": random.choice(["CLEARED", "PENDING"])
            })
        df = pd.DataFrame(data)
        
        # Timestamp
        ts_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        # 2. Gacha Error (Biar bisa demo gagal juga via tombol)
        # Kita set peluang gagal lebih kecil di tombol manual (10%) biar enak demo
        if random.randint(1, 10) == 1: 
            # --- FAIL ---
            error_msg = "MANUAL TRIGGER ERROR: Reconciliation Mismatch Detected!"
            error_filename = f"error_{ts_str}.txt"
            
            # Upload Error Log
            minio_client.put_object(
                bucket_name=bucket_name,
                object_name=error_filename,
                data=BytesIO(error_msg.encode('utf-8')),
                length=len(error_msg),
                content_type='text/plain'
            )
            
            # Webhook Failed
            requests.post(webhook_url, json={
                "status": "failed",
                "error_message": error_msg,
                "timestamp": datetime.now().isoformat()
            })
            return False, "Job Failed (Simulated)! Alert sent to PagerDuty."
            
        else:
            # --- SUCCESS ---
            filename = f"report_{ts_str}.csv"
            csv_bytes = df.to_csv(index=False).encode('utf-8')
            
            # Upload Report
            if not minio_client.bucket_exists(bucket_name=bucket_name):
                minio_client.make_bucket(bucket_name=bucket_name)

            minio_client.put_object(
                bucket_name=bucket_name,
                object_name=filename,
                data=BytesIO(csv_bytes),
                length=len(csv_bytes),
                content_type='text/csv'
            )
            
            # Webhook Success
            requests.post(webhook_url, json={
                "status": "success",
                "filename": filename,
                "download_link": f"http://localhost:9001/{bucket_name}/{filename}",
                "timestamp": datetime.now().isoformat()
            })
            return True, "Job Success! Report generated & Email sent."

    except Exception as e:
        return False, f"System Error: {str(e)}"

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None

# ==========================================
# HALAMAN LOGIN
# ==========================================
if not st.session_state['logged_in']:
    st.title("🔒 Secure Login Portal")
    col1, col2 = st.columns([1, 2])
    with col1:
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        if st.button("Login"):
            if check_login(username_input, password_input):
                st.session_state['logged_in'] = True
                if username_input == "finance":
                    st.session_state['user_role'] = "Finance Team"
                else:
                    st.session_state['user_role'] = "DevOps Team"
                st.rerun()
            else:
                st.error("Username atau Password salah!")
#    st.info("Finance: `finance`/`uang123` | DevOps: `devops`/`admin123`")

# ==========================================
# DASHBOARD
# ==========================================
else:
    with st.sidebar:
        st.write(f"User: **{st.session_state['user_role']}**")
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.title("🏦 End-of-Day Processing System")

    # --- FINANCE VIEW ---
    if st.session_state['user_role'] == "Finance Team":
        st.header("📊 Financial Reports")
        try:
            objects = minio_client.list_objects(bucket_name=bucket_name)
            # Filter cuma ambil file csv (report)
            files = [obj.object_name for obj in objects if obj.object_name.startswith("report_")]
            files.sort(reverse=True) # Terbaru paling atas
            
            if st.button("🔄 Refresh List"):
                st.rerun()
            
            if files:
                selected_file = st.selectbox("Select Report Date:", files)
                if st.button("View Report"):
                    data = minio_client.get_object(bucket_name=bucket_name, object_name=selected_file)
                    df = pd.read_csv(data)
                    st.dataframe(df)
                    st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), selected_file, 'text/csv')
            else:
                st.warning("No reports found yet.")
        except Exception as e:
            st.error(f"Connection Error: {e}")

    # --- DEVOPS VIEW ---
    elif st.session_state['user_role'] == "DevOps Team":
        st.header("🛠️ System Health & Logs")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("MinIO Storage", "Online", "Healthy")
        col2.metric("Scheduler", "Active", "Running")
        col3.metric("Workflow", "Ready", "Listening")
        
        st.subheader("Job Execution Logs")
        
        # --- TOMBOL REFRESH ---
        if st.button("🔄 Refresh Logs", type="primary"):
            st.rerun()

        # Baca Log dari MinIO
        try:
            objects = minio_client.list_objects(bucket_name=bucket_name)
            log_entries = []
            for obj in objects:
                fname = obj.object_name
                if fname.startswith("report_"):
                    status, msg = "SUCCESS", "File Generated"
                    ts = fname.replace("report_", "").replace(".csv", "")
                elif fname.startswith("error_"):
                    status, msg = "FAILED", "Error Logged"
                    ts = fname.replace("error_", "").replace(".txt", "")
                else:
                    continue
                log_entries.append({"Timestamp": ts, "Status": status, "Message": msg})
            
            if log_entries:
                df_logs = pd.read_json(pd.DataFrame(log_entries).to_json(orient='records'))
                df_logs = df_logs.sort_values(by="Timestamp", ascending=False)
                
                def color_status(val):
                    return f'background-color: {"#d4edda" if val == "SUCCESS" else "#f8d7da"}; color: black'
                
                st.dataframe(df_logs.style.applymap(color_status, subset=['Status']), use_container_width=True)
            else:
                st.info("No logs available.")
        except Exception as e:
            st.error(f"Log Error: {e}")
        
        st.markdown("---")
        st.subheader("🚨 Emergency Control")
        
        # --- TOMBOL FORCE TRIGGER YANG SUDAH BERFUNGSI ---
        if st.button("⚠️ Force Trigger Batch Job (Manual)"):
            with st.spinner("Executing Batch Process..."):
                is_success, msg = run_manual_job()
                if is_success:
                    st.success(msg)
                    st.balloons() # Efek visual sukses
                else:
                    st.error(msg)
