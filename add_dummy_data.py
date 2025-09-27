"""
Script untuk menambahkan data karyawan dummy untuk testing
"""
from database import get_db_manager
from models import Employee

# Data karyawan dummy
dummy_employees = [
    ("Ahmad", "karyawan"),
    ("Siti", "staff"),
    ("Budi", "karyawan"),
    ("Maya", "staff"),
    ("Rudi", "karyawan")
]

print("=== MENAMBAH DATA KARYAWAN DUMMY ===")

db = get_db_manager()

for name, bagian in dummy_employees:
    try:
        success = Employee.add_employee(name, bagian)
        if success:
            print(f"✅ Berhasil menambah: {name} ({bagian})")
        else:
            print(f"❌ Gagal menambah: {name} ({bagian})")
    except Exception as e:
        print(f"❌ Error adding {name}: {e}")

print(f"\n=== VERIFIKASI ===")
employees = Employee.get_all_employees()
print(f"Total karyawan di database: {len(employees) if employees else 0}")

if employees:
    print("Karyawan terdaftar:")
    for emp in employees:
        print(f"  - {emp['name']} ({emp['bagian']})")

print(f"\n✅ Data dummy berhasil ditambahkan!")
print("Sekarang Anda bisa:")
print("1. Test absensi dengan data kosong (akan muncul 'TIDAK TERDAFTAR')")
print("2. Tambah foto wajah untuk karyawan dummy")
print("3. Test absensi dengan karyawan terdaftar")