"""
Test script untuk debug masalah total jam kerja
"""
from database import get_db_manager
from models import Employee, Attendance
from datetime import datetime, date, time

print("=== DEBUG TOTAL JAM KERJA ===")

# 1. Cek data absensi terbaru
db = get_db_manager()
recent_attendance = db.execute_query("""
    SELECT a.*, e.name, e.bagian 
    FROM attendance a 
    JOIN employees e ON a.employee_id = e.id 
    ORDER BY a.created_at DESC 
    LIMIT 3
""")

if recent_attendance:
    print(f"\n📊 Data absensi terbaru:")
    for att in recent_attendance:
        print(f"- {att['name']} ({att['bagian']}):")
        print(f"  Tanggal: {att['tanggal']}")
        print(f"  Jam Masuk: {att['jam_masuk']}")
        print(f"  Jam Pulang: {att['jam_pulang']}")
        print(f"  Total Jam Kerja: {att['total_jam_kerja']} (type: {type(att['total_jam_kerja'])})")
        print()
else:
    print("❌ Tidak ada data absensi")

# 2. Test manual calculation
print("🧮 Test manual calculation:")
test_masuk = time(8, 0, 0)
test_pulang = time(17, 30, 0)
calculated = Attendance.calculate_work_hours(test_masuk, test_pulang)
print(f"Test: {test_masuk} to {test_pulang} = {calculated} (type: {type(calculated)})")

# 3. Test extract_attendance function
print("\n📋 Test extract_attendance:")
try:
    from app import extract_attendance
    names, bagian, tanggal, times, l = extract_attendance()
    print(f"Hasil extract: {l} records")
    if l > 0:
        for i in range(min(3, l)):  # Show first 3
            print(f"- {names[i]} ({bagian[i]}) on {tanggal[i]}")
            print(f"  Times: Masuk={times[i][0]}, Pulang={times[i][1]}, Total={times[i][2]}")
except Exception as e:
    print(f"❌ Error in extract_attendance: {e}")

print("\n=== DIAGNOSIS ===")
print("Kemungkinan masalah:")
print("1. total_jam_kerja di database NULL atau tidak terhitung")
print("2. Format data tidak sesuai dengan yang diharapkan di frontend")
print("3. Logic update tidak memicu perhitungan total jam kerja")