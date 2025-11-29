
# 📝 Tutorial Instalasi Project Finance Data Pipeline

Ini merupakan langkah-langkah mudah untuk menjalankan seluruh stack aplikasi, mulai dari scheduler data hingga dashboard visualisasi, menggunakan Docker Compose.

Prasyarat 🛠️

Pastikan komputer kamu sudah ter-install perangkat lunak berikut:

    Docker
    Docker Compose (Versi terbaru sudah terintegrasi dengan Docker)
## Installation

### Langkah 1: Clone Repository

Buka terminal kamu dan clone project ini:

    git clone https://github.com/Minkqwqw/ finance-daily-scheduler.git
    cd finance-daily-scheduler

### Langkah 2: Konfigurasi Environment Variables (.env)

Untuk menjalankan service ini dengan aman, kamu perlu membuat file konfigurasi .env.

Buat file baru bernama .env di root directory project (sejajar dengan docker-compose.yml).

Isi file tersebut dengan format berikut:

    # MinIO Config
    MINIO_ROOT_USER=your_username
    MINIO_ROOT_PASSWORD=your_password
    MINIO_ENDPOINT=minio:9000
    MINIO_BUCKET_NAME=finance-reports

    # n8n Config (Webhook yang nanti kamu buat di n8n)
    # Ganti bagian 'your-webhook-uuid' setelah setup n8n
    N8N_WEBHOOK_URL=http://n8n:5678/your_webhook_URL

    Catatan: Ganti your_username, your_password dengan nilai yang kamu inginkan.


### Langkah 3: Konfigurasi Scheduler Ofelia (ofelia.ini)

**Project ini menggunakan Ofelia untuk menjalankan cron job setiap hari jam 05:10 dan 17:00 WIB.**

***Buat file baru bernama ofelia.ini di root directory project.***

Isi file tersebut dengan contoh konfigurasi seperti ini:


    ; ofelia.ini - Configuration File
    ; Detik(*) Menit(*) Jam(*) Hari(*) Bulan(*) Minggu(*) ;

    [job-exec "finance-morning"]
    schedule = 0 30 7 * * *
    container = batch-processor
    command = python main.py

    [job-exec "finance-sore"]
    schedule = 0 0 17 * * *
    container = batch-processor
    command = python main.py

### Langkah 4: Jalankan Project dengan Docker Compose

Jalankan semua service di background:

    docker-compose up -d --build

Setelah semua container aktif, service yang akan berjalan adalah:

    MinIO (Storage)

    n8n (Workflow Engine)

    Ofelia (Cron Scheduler)

    Batch Processor (Idle container untuk dieksekusi Ofelia)

    Web UI (Streamlit Dashboard)

### Langkah 5: Akses Service 🌐
Kamu wajib akses MinIO Console terlebih dahulu untuk melakukan konfigurasi pertama kali, masukkan username dan password yang telah dibuat sebelumnya

lalu buat bucket dengan nama  `finance-reports`

 Setelah itu kamu bisa mengakses service melalui port yang sudah dikonfigurasi:

    n8n:   http://localhost:5678
    MinIO Console:	http://localhost:9001
    Streamlit Web UI:	http://localhost:8501

#### PENTING!! untuk Web UI (Streamlit) memiliki inline credential yaitu:

    "finance": "finance",
    "devops": "admin123"

Credential ini bisa diubah dengan cara mengubahnya pada `/web-ui/app.py` dan mencari line #FUNGSI LOGIN

Jika kamu melakukan perubahan pada code. Maka wajib melakukan perintah `docker-compose down` lalu `docker-compose up -d --build` kembali.

### N8N Nodes
Buat Nodes  dan  ikuti konfigurasi seperti sebagai berikut