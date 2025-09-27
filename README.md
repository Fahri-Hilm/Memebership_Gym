# 🏋️‍♂️ SISTEM MEMBERSHIP GYM FACE RECOGNITION

Sistem manajemen membership gym berbasis teknologi **Face Recognition** menggunakan **Python Flask** dan **MySQL Database** dengan **PyMySQL**. Sistem ini dapat mendeteksi wajah member secara otomatis untuk mencatat absensi gym dan mengelola membership.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8.0-red.svg)

## 🌟 **Fitur Utama**

### 🎯 **Face Recognition**
- ✅ Deteksi wajah real-time menggunakan OpenCV
- ✅ Machine Learning dengan K-Nearest Neighbors (KNN)
- ✅ Training model otomatis dari foto member
- ✅ Akurasi tinggi untuk identifikasi member gym

### 📊 **Database MySQL**
- ✅ **Database**: `gym_membership_db`
- ✅ **PyMySQL** untuk koneksi database
- ✅ **3 Tabel**: members, attendance, activity_log
- ✅ **Foreign Key Constraints** untuk data integrity
- ✅ **Auto-increment** dan **timestamps**

### 📱 **Web Interface**
- ✅ Interface yang user-friendly untuk gym
- ✅ Dashboard dengan statistik member real-time
- ✅ Form untuk menambah member baru
- ✅ Tampilan data kehadiran gym mingguan
- ✅ Multi-camera support untuk area gym

### 🏃‍♂️ **Sistem Kehadiran Gym**
- ✅ **Check-in** dan **Check-out** gym
- ✅ **Perhitungan durasi workout** otomatis
- ✅ **Log aktivitas** member lengkap
- ✅ **Data statistik** mingguan dan harian
- ✅ **Status membership** dan validasi

## 🏗️ **Struktur Database**

### � **Tabel `members`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- name (VARCHAR(100), NOT NULL)
- membership_type (VARCHAR(50), NOT NULL)
- phone (VARCHAR(15))
- email (VARCHAR(100))
- join_date (DATE, NOT NULL)
- expiry_date (DATE, NOT NULL)
- status (ENUM: 'active', 'inactive', 'expired')
- created_at, updated_at (TIMESTAMP)
```

### 📅 **Tabel `attendance`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- member_id (INT, FOREIGN KEY)
- tanggal (DATE, NOT NULL)
- jam_masuk, jam_keluar, total_durasi (TIME)
- status (ENUM: 'hadir', 'tidak_hadir')
- workout_type (VARCHAR(100))
- created_at, updated_at (TIMESTAMP)
```

### 📝 **Tabel `activity_log`**
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- member_id (INT, FOREIGN KEY)
- activity_type (ENUM: 'checkin', 'checkout', 'add_member', 'face_recognition')
- description (TEXT)
- created_at (TIMESTAMP)
```

## 🚀 **Instalasi & Setup**

### 1️⃣ **Clone Repository**
```bash
git clone https://github.com/Fahri-Hilm/Memebership_Gym.git
cd Memebership_Gym
```

### 2️⃣ **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3️⃣ **Setup Database MySQL**
**Untuk Laragon:**
- Start MySQL service di Laragon
- Default: User `root`, Password kosong
- Port: `3306`

**Untuk XAMPP/MySQL lainnya:**
- Sesuaikan konfigurasi di `config.py`

### 4️⃣ **Inisialisasi Database**
```bash
python init_database.py
```

### 5️⃣ **Jalankan Aplikasi**
```bash
python app.py
```

**Sistem Lama (Employee):** http://127.0.0.1:5001  
**Sistem Gym (Member):** http://127.0.0.1:5002

> **Note:** Gunakan `gym_app.py` untuk menjalankan sistem gym yang terbaru

## 📁 **Struktur Project**

```
Memebership_Gym/
├── 🐍 app.py                 # Aplikasi Flask utama (sistem lama)
├── 🏋️‍♂️ gym_app.py              # Aplikasi Flask gym utama (sistem baru)
├── ⚙️ config.py              # Konfigurasi database & aplikasi
├── 🗄️ database.py           # Database manager PyMySQL
├── 📊 models.py              # Model data lama (Employee, Attendance, ActivityLog)
├── 🏃‍♂️ gym_models.py          # Model data gym (Member, Attendance, ActivityLog)
├── 🔧 init_database.py       # Script inisialisasi database
├── 🧪 test_database.py       # Script testing database
├── 🗑️ clear_database.py      # Script untuk mengosongkan database
├── 📋 requirements.txt       # Dependencies Python
├── 🤖 haarcascade_frontalface_default.xml # Face detection model
├── 📁 static/
│   ├── 🤖 face_recognition_model.pkl     # Trained ML model
│   └── 📸 faces/                         # Foto training member gym
├── 📁 templates/
│   ├── 🌐 home.html                      # Template web interface lama
│   ├── 🏋️‍♂️ gym_home.html               # Template gym home
│   ├── ➕ add_member.html               # Form tambah member
│   ├── � members_list.html             # Daftar member
│   └── 📊 statistics.html               # Statistik gym
├── �📁 Attendance/
│   └── 📄 *.csv                          # File backup attendance
└── 📖 README.md                          # Dokumentasi ini
```

## 🎮 **Cara Penggunaan**

### 👤 **Menambah Member Baru**
1. Klik **"Tambah Member Baru"**
2. Isi **Nama**, **Tipe Membership**, **Phone**, **Email**
3. **Hadap kamera** untuk mengambil 10 foto training
4. System akan **training model** otomatis
5. Member siap untuk check-in/out

### 🏃‍♂️ **Check-in Gym**
1. Klik **"Check-in"**
2. **Hadap kamera** sampai wajah terdeteksi
3. System **otomatis mencatat** jam masuk gym
4. Pilih **jenis workout** (opsional)

### �‍♂️ **Check-out Gym**
1. Klik **"Check-out"**
2. **Hadap kamera** sampai wajah terdeteksi  
3. System **otomatis menghitung** durasi workout
4. Data tersimpan untuk statistik

### 📊 **Fitur Khusus Gym**

#### 🏋️‍♂️ **Tipe Membership**
- **Basic** - Akses gym standar
- **Premium** - Akses gym + kelas fitness
- **VIP** - Akses penuh + personal trainer

#### 📈 **Statistik & Analytics**
- ✅ Total member aktif
- ✅ Rata-rata durasi workout
- ✅ Member terpopuler (paling sering datang)
- ✅ Grafik kehadiran harian/mingguan
- ✅ Status membership (aktif/expired)

#### 🔔 **Notifikasi Otomatis**
- ⚠️ Member yang akan expired
- 📧 Reminder perpanjangan membership
- 🎉 Selamat datang member baru

## 🛠️ **Konfigurasi**

### 📝 **Edit `config.py`**
```python
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',  # Sesuaikan dengan setup MySQL Anda
    'database': 'gym_membership_db',
    'charset': 'utf8mb4'
}
```

## 🔧 **Troubleshooting**

### ❌ **Database Connection Error**
```bash
# Pastikan MySQL running
# Cek konfigurasi di config.py
# Test koneksi:
python test_database.py
```

### 🗑️ **Reset Database**
```bash
# Kosongkan semua data:
python clear_database.py

# Inisialisasi ulang:
python init_database.py
```

### 📷 **Kamera Tidak Terdeteksi**
- Pastikan webcam terpasang
- Coba ganti ID kamera di dropdown
- Restart aplikasi

## 🎯 **Teknologi yang Digunakan**

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Backend programming |
| **Flask** | 2.3.3 | Web framework |
| **PyMySQL** | 1.1.2 | MySQL database connector |
| **OpenCV** | 4.8.0 | Computer vision & face detection |
| **scikit-learn** | 1.3.0 | Machine learning (KNN) |
| **NumPy** | 1.24.3 | Numerical computing |
| **Pandas** | 2.0.3 | Data manipulation |
| **MySQL** | 8.0+ | Database management |

## 🚀 **Fitur Mendatang**

- 📊 **Dashboard Analytics** dengan grafik workout
- 📱 **Mobile App** (Android/iOS) untuk member
- 📧 **Email Notifications** untuk membership expiry
- 📄 **Export Reports** (PDF/Excel) untuk statistik gym
- � **Multi-branch Support** untuk chain gym
- 🔐 **User Authentication & Authorization** untuk staff
- 🎨 **Custom Themes** dan branding gym
- 💳 **Payment Integration** untuk perpanjangan membership
- 📅 **Class Booking System** untuk kelas fitness
- 🏆 **Achievement System** dan rewards untuk member

## 📞 **Support**

Jika Anda mengalami masalah:
1. 📖 Baca dokumentasi ini dengan teliti
2. 🧪 Jalankan `python test_database.py` untuk diagnosis
3. 🗑️ Reset database dengan `python clear_database.py`
4. 📱 Hubungi developer untuk support lanjutan

## 📄 **Lisensi**

MIT License - Bebas digunakan untuk keperluan komersial dan non-komersial.

---

**🎉 Sistem Membership Gym Face Recognition - Solusi Manajemen Gym Modern untuk Era Digital!**

*Dibuat dengan ❤️ menggunakan Python, Flask, dan MySQL untuk kemudahan manajemen gym*