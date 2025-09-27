"""
Script untuk recalculate semua total jam kerja yang NULL
"""
from database import get_db_manager
from models import Attendance

print("=== RECALCULATE TOTAL JAM KERJA ===")

db = get_db_manager()

# Cari records yang punya jam masuk dan pulang tapi total_jam_kerja NULL
null_total_records = db.execute_query("""
    SELECT * FROM attendance 
    WHERE jam_masuk IS NOT NULL 
    AND jam_pulang IS NOT NULL 
    AND total_jam_kerja IS NULL
""")

if null_total_records:
    print(f"🔧 Ditemukan {len(null_total_records)} records yang perlu diperbaiki:")
    
    for record in null_total_records:
        print(f"- ID {record['id']}: {record['jam_masuk']} to {record['jam_pulang']}")
        
        # Hitung total jam kerja
        total_jam = Attendance.calculate_work_hours(record['jam_masuk'], record['jam_pulang'])
        
        if total_jam:
            # Update database
            result = db.execute_query(
                "UPDATE attendance SET total_jam_kerja = %s WHERE id = %s", 
                (total_jam, record['id'])
            )
            if result > 0:
                print(f"  ✅ Updated: {total_jam}")
            else:
                print(f"  ❌ Failed to update")
        else:
            print(f"  ❌ Failed to calculate")
    
    print(f"\n🎉 Recalculation selesai!")
else:
    print("✅ Tidak ada records yang perlu diperbaiki")

# Verify hasil
print("\n=== VERIFICATION ===")
all_attendance = db.execute_query("""
    SELECT a.*, e.name, e.bagian 
    FROM attendance a 
    JOIN employees e ON a.employee_id = e.id 
    ORDER BY a.tanggal DESC, a.created_at DESC
""")

if all_attendance:
    for att in all_attendance:
        print(f"- {att['name']} ({att['bagian']}): {att['jam_masuk']} to {att['jam_pulang']} = {att['total_jam_kerja']}")
else:
    print("❌ Tidak ada data attendance")