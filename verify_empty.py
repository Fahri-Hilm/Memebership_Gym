from database import get_db_manager
import os

db = get_db_manager()

# Check database
employees = db.execute_query('SELECT COUNT(*) as count FROM employees')[0]['count']
print(f"Total karyawan di database: {employees}")

# Check model
model_exists = os.path.exists('static/face_recognition_model.pkl')
print(f"Model face recognition exists: {model_exists}")

# Check faces folder
faces_count = 0
if os.path.exists('static/faces'):
    faces_count = len([f for f in os.listdir('static/faces') if os.path.isdir(os.path.join('static/faces', f))])
print(f"Folder faces count: {faces_count}")

print("\n=== STATUS ===")
if employees == 0 and not model_exists and faces_count == 0:
    print("✅ Sistem bersih - siap untuk test 'tidak terdaftar'")
else:
    print("❌ Masih ada data tersisa")