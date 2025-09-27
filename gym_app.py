import cv2
import os
import csv
import pickle
from flask import Flask, request, render_template, jsonify
from datetime import date, datetime, timedelta
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
import pandas as pd
import joblib
import shutil
from scipy.spatial.distance import euclidean

# Import database modules
from database import get_db_manager
from gym_models import Member, MemberVisit, PointsHistory, GymStatistics
from config import get_app_config
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load app configuration
app_config = get_app_config()
app.secret_key = app_config['secret_key']

# Initialize database
db_manager = get_db_manager()
if not db_manager.initialize_database():
    logger.error("Gagal inisialisasi database!")

nimgs = 10
selected_camera_id = 0  # Akan dipilih lewat dropdown

# Tanggal hari ini
current_date = date.today()
tanggal_hari_ini = current_date.strftime("%A, %d %B %Y")

# Inisialisasi folder & face detector
face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
os.makedirs('static/faces', exist_ok=True)

def timedelta_to_time_str(td):
    """Konversi timedelta ke string waktu HH:MM"""
    if td is None:
        return '-'
    if isinstance(td, timedelta):
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    return str(td)

# Register template filter
app.jinja_env.filters['timedelta_to_time'] = timedelta_to_time_str

def serialize_visit_for_json(visit):
    """Konversi visit data untuk JSON serialization"""
    if not visit:
        return None
    
    # Copy visit data and convert objects that are not JSON serializable
    serialized = {}
    
    for key, value in visit.items():
        if isinstance(value, timedelta):
            # Convert timedelta to time string
            serialized[key] = timedelta_to_time_str(value)
        elif isinstance(value, date) and not isinstance(value, datetime):
            # Convert date to string
            serialized[key] = value.strftime('%Y-%m-%d')
        elif isinstance(value, datetime):
            # Convert datetime to string
            serialized[key] = value.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # Keep other values as is
            serialized[key] = value
    
    return serialized

def total_members():
    """Menghitung total member terdaftar dari database"""
    try:
        members = Member.get_all_members()
        return len(members) if members else 0
    except Exception as e:
        logger.error(f"Error getting total registered members: {e}")
        # Fallback ke folder jika database error
        try:
            return len(os.listdir('static/faces'))
        except:
            return 0

def extract_faces(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_points = face_detector.detectMultiScale(gray, 1.2, 5, minSize=(20, 20))
        return face_points
    except:
        return []

def identify_face(facearray):
    try:
        if not os.path.exists('static/face_recognition_model.pkl'):
            logger.warning("Model face recognition tidak ditemukan")
            return ['TIDAK_TERDAFTAR']
        
        # Load model dalam format dictionary baru
        with open('static/face_recognition_model.pkl', 'rb') as f:
            model_data = pickle.load(f)
        
        model_type = model_data.get('model_type', 'multi_class')
        
        if model_type == 'template_matching':
            # Handle template matching untuk single member
            from scipy.spatial.distance import euclidean
            
            avg_template = model_data['avg_template']
            threshold = model_data['threshold']
            member_name = model_data['member_name']
            
            # Hitung distance ke template rata-rata
            # facearray sudah dalam format flatten, tapi pastikan ukuran sesuai
            face_flat = facearray.flatten()
            
            logger.debug(f"Face recognition debug:")
            logger.debug(f"  Input shape: {facearray.shape}")
            logger.debug(f"  Face flat shape: {face_flat.shape}")
            logger.debug(f"  Template shape: {avg_template.shape}")
            logger.debug(f"  Threshold: {threshold:.2f}")
            
            # Jika ukuran tidak cocok, reshape ke (50,50) = 2500
            if len(face_flat) != len(avg_template):
                logger.debug(f"  Shape mismatch, fixing...")
                # Asumsi input adalah hasil cv2.resize yang belum di-flatten dengan benar
                # Reshape ke bentuk yang sesuai (2500,)
                if len(face_flat) == 7500:  # Kemungkinan 3 channel BGR
                    # Convert ke grayscale atau ambil channel pertama saja
                    face_reshaped = face_flat.reshape(50, 50, 3)
                    face_gray = face_reshaped[:, :, 0]  # Ambil channel pertama
                    face_flat = face_gray.flatten()
                    logger.debug(f"  Fixed BGR to grayscale: {face_flat.shape}")
                else:
                    # Resize to match template size
                    target_size = int(np.sqrt(len(avg_template)))  # Should be 50
                    face_flat = face_flat[:target_size*target_size]
                    logger.debug(f"  Resized to match template: {face_flat.shape}")
            
            distance = euclidean(face_flat, avg_template)
            logger.debug(f"  Distance: {distance:.2f}")
            
            if distance <= threshold:
                predicted_member = member_name
                logger.debug(f"  MATCH! Recognized as: {member_name}")
            else:
                predicted_member = 'TIDAK_TERDAFTAR'
                logger.debug(f"  NO MATCH. Distance {distance:.2f} > threshold {threshold:.2f}")
                
        elif model_type == 'single_class':
            # Handle OneClassSVM untuk single member
            model = model_data['model']
            scaler = model_data['scaler']
            member_name = model_data['member_name']
            
            # Normalisasi input
            facearray_scaled = scaler.transform(facearray)
            
            # Prediksi - OneClassSVM return 1 untuk inlier, -1 untuk outlier
            prediction = model.predict(facearray_scaled)
            
            if prediction[0] == 1:
                predicted_member = member_name
            else:
                predicted_member = 'TIDAK_TERDAFTAR'
                
        else:
            # Handle multi-class SVM (format lama)
            model = model_data['model']
            label_encoder = model_data['label_encoder']
            prediction_encoded = model.predict(facearray)
            prediction_names = label_encoder.inverse_transform(prediction_encoded)
            predicted_member = prediction_names[0]
        
        # Validasi apakah prediksi member masih ada di database
        if predicted_member and predicted_member != 'TIDAK_TERDAFTAR':
            # Cek apakah member masih terdaftar di database
            member = Member.get_member_by_name(predicted_member)
            if not member or member['status'] != 'active':
                logger.warning(f"Member {predicted_member} tidak ditemukan atau tidak aktif")
                return ['TIDAK_TERDAFTAR']
        
        return [predicted_member]
    except Exception as e:
        logger.error(f"Error in identify_face: {e}")
        return ['TIDAK_TERDAFTAR']

def train_model():
    """Train face recognition model"""
    try:
        faces = []
        labels = []
        userlist = os.listdir('static/faces')
        
        if not userlist:
            logger.warning("Tidak ada data training")
            return False
        
        for user in userlist:
            user_path = f'static/faces/{user}'
            if not os.path.isdir(user_path):
                continue
                
            for imgname in os.listdir(user_path):
                if imgname.endswith(('.jpg', '.jpeg', '.png')):
                    img_path = os.path.join(user_path, imgname)
                    img = cv2.imread(img_path)
                    if img is not None:
                        resized_face = cv2.resize(img, (50, 50))
                        faces.append(resized_face.flatten())
                        labels.append(user)
        
        if len(faces) == 0:
            logger.error("Tidak ada wajah yang valid untuk training")
            return False
        
        faces = np.array(faces)
        knn = KNeighborsClassifier(n_neighbors=5)
        knn.fit(faces, labels)
        
        joblib.dump(knn, 'static/face_recognition_model.pkl')
        logger.info(f"Model berhasil dilatih dengan {len(faces)} gambar dari {len(set(labels))} member")
        return True
        
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return False

@app.route('/')
@app.route('/gym')
def home():
    """Halaman utama gym membership system"""
    try:
        # Get today's statistics
        today_stats = GymStatistics.get_daily_summary()
        
        # Get member statistics  
        member_stats = GymStatistics.get_member_statistics()
        
        # Get today's visits
        today_visits = MemberVisit.get_daily_visits()
        
        # Get all members
        members = Member.get_all_members()
        total_registered = len(members) if members else 0
        
        return render_template(
            'gym_home.html',
            today_stats=today_stats,
            member_stats=member_stats,
            today_visits=today_visits,
            members=members,
            total_members=total_registered,
            active_members=len([v for v in today_visits if not v.get('check_out_time')])
        )
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        return render_template('gym_home.html', 
                             total_members=0,
                             today_stats={'total_visits': 0, 'unique_members': 0, 'total_points_earned': 0, 'average_duration': 0},
                             member_stats={'tier_distribution': {}, 'total_members': 0, 'active_today': 0},
                             today_visits=[],
                             members=[],
                             active_members=0)

@app.route('/start', methods=['POST'])
def start():
    """Start face recognition"""
    global selected_camera_id
    try:
        data = request.get_json()
        selected_camera_id = int(data.get('camera_id', 0))
        logger.info(f"Camera ID diset ke: {selected_camera_id}")
        return jsonify({'status': 'success', 'message': f'Camera {selected_camera_id} siap digunakan'})
    except Exception as e:
        logger.error(f"Error setting camera: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/gym_checkin')
def gym_checkin_camera():
    """Buka kamera GUI untuk check-in member"""
    return run_gym_camera('checkin')

@app.route('/gym_checkout')  
def gym_checkout_camera():
    """Buka kamera GUI untuk check-out member"""
    return run_gym_camera('checkout')

def run_gym_camera(mode='checkin'):
    """Fungsi untuk menjalankan kamera face recognition untuk gym check-in/out"""
    print(f"[DEBUG] Mulai {mode} dengan kamera ID: {selected_camera_id}")
    
    cap = cv2.VideoCapture(selected_camera_id)
    if not cap.isOpened():
        return render_template('gym_home.html', message="❌ Kamera tidak tersedia")

    recognition_success = False
    success_member = ""
    loading_counter = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        faces = extract_faces(frame)
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            face = cv2.resize(frame[y:y+h, x:x+w], (50, 50))
            member_name = identify_face(face.reshape(1, -1))[0]
            
            # Cek jika member tidak terdaftar
            if member_name == 'TIDAK_TERDAFTAR':
                # Tampilkan pesan error untuk member tidak terdaftar
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)  # Red rectangle
                cv2.putText(frame, 'MEMBER TIDAK TERDAFTAR!', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, 'WAJAH TIDAK DIKENALI', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.putText(frame, 'Hubungi admin untuk mendaftar', (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(frame, 'Tekan ESC untuk keluar', (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            else:
                # Tampilkan recognition result untuk member terdaftar
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f'{member_name} - {mode.upper()} DETECTED', (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                # Loading animation setelah face terdeteksi
                if not recognition_success:
                    loading_counter += 1
                    loading_text = "MEMPROSES" + "." * (loading_counter % 4)
                    cv2.putText(frame, loading_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    
                    # Setelah 30 frames (sekitar 1 detik), proses check-in/out
                    if loading_counter >= 30:
                        success = process_gym_visit(member_name, mode)
                        if success:
                            recognition_success = True
                            success_member = member_name
                            loading_counter = 0
                            print(f"[SUCCESS] {mode.capitalize()} recorded for {member_name}")
                        else:
                            # Reset jika gagal
                            loading_counter = 0
                            print(f"[ERROR] Failed to record {mode} for {member_name}")
        else:
            loading_counter = 0  # Reset loading jika tidak ada wajah
        
        # Tampilkan status loading atau success
        if recognition_success:
            # Tampilkan pesan sukses
            cv2.putText(frame, f'{mode.upper()} BERHASIL!', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f'Member: {success_member}', (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, 'Kamera akan ditutup dalam 3 detik...', (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            loading_counter += 1
            if loading_counter >= 90:  # 3 detik (30 fps x 3)
                break
        else:
            # Tampilkan status model dan instruksi
            model_exists = os.path.exists('static/face_recognition_model.pkl')
            if not model_exists:
                cv2.putText(frame, 'STATUS: TIDAK ADA MEMBER TERDAFTAR', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(frame, f'{mode.upper()}: Semua wajah akan ditolak', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            else:
                cv2.putText(frame, f'GYM {mode.upper()} - Posisikan wajah di kamera', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, 'Tekan ESC untuk keluar', (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow(f"Gym {mode.capitalize()}", frame)
        if cv2.waitKey(1) == 27:  # ESC key
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Return dengan hasil
    try:
        # Get data untuk template
        today_stats = GymStatistics.get_daily_summary()
        today_visits = MemberVisit.get_daily_visits()
        members = Member.get_all_members()
        member_stats = GymStatistics.get_member_statistics()
        
        if recognition_success:
            message = f"✅ {mode.capitalize()} berhasil untuk member {success_member}!"
            return render_template('gym_home.html', 
                                 message=message,
                                 today_stats=today_stats,
                                 today_visits=today_visits,
                                 members=members,
                                 member_stats=member_stats)
        else:
            return render_template('gym_home.html',
                                 today_stats=today_stats,
                                 today_visits=today_visits,
                                 members=members,
                                 member_stats=member_stats)
    except Exception as e:
        logger.error(f"Error returning template: {e}")
        return render_template('gym_home.html', 
                             message="Error loading data",
                             today_stats={},
                             today_visits=[],
                             members=[],
                             member_stats={})

def process_gym_visit(member_name, mode):
    """Proses check-in atau check-out member"""
    try:
        member = Member.get_member_by_name(member_name)
        if not member:
            logger.error(f"Member {member_name} tidak ditemukan")
            return False
        
        if mode == 'checkin':
            success, message = MemberVisit.check_in(member['member_id'])
        else:  # checkout
            success, message = MemberVisit.check_out(member['member_id'])
        
        if success:
            logger.info(f"Member {member_name} {mode} berhasil: {message}")
            return True
        else:
            logger.error(f"Member {member_name} {mode} gagal: {message}")
            return False
            
    except Exception as e:
        logger.error(f"Error processing {mode} for {member_name}: {e}")
        return False

@app.route('/gym_checkin_api', methods=['POST'])
def gym_checkin_api():
    """API Check-in member ke gym menggunakan face recognition"""
    try:
        cap = cv2.VideoCapture(selected_camera_id)
        if not cap.isOpened():
            return jsonify({'status': 'error', 'message': 'Kamera tidak dapat diakses'})
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return jsonify({'status': 'error', 'message': 'Gagal mengambil gambar'})
        
        # Deteksi wajah
        faces = extract_faces(frame)
        
        if len(faces) == 0:
            return jsonify({'status': 'error', 'message': 'Wajah tidak terdeteksi'})
        
        # Ambil wajah pertama yang terdeteksi
        (x, y, w, h) = faces[0]
        cropped_face = frame[y:y+h, x:x+w]
        resized_face = cv2.resize(cropped_face, (50, 50)).flatten().reshape(1, -1)
        
        # Identifikasi member
        prediction = identify_face(resized_face)
        member_name = prediction[0] if prediction else 'TIDAK_TERDAFTAR'
        
        if member_name == 'TIDAK_TERDAFTAR':
            return jsonify({'status': 'error', 'message': 'Member tidak terdaftar'})
        
        # Proses check-in
        member = Member.get_member_by_name(member_name)
        if not member:
            return jsonify({'status': 'error', 'message': 'Data member tidak ditemukan'})
        
        success, message = MemberVisit.check_in(member['member_id'])
        
        if success:
            # Get updated member info for response
            updated_member = Member.get_member_by_id(member['member_id'])
            return jsonify({
                'status': 'success',
                'message': message,
                'member': {
                    'name': updated_member['name'],
                    'member_id': updated_member['member_id'],
                    'tier': updated_member['tier'],
                    'total_points': updated_member['total_points']
                }
            })
        else:
            return jsonify({'status': 'error', 'message': message})
            
    except Exception as e:
        logger.error(f"Error in gym_checkin: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/gym_checkout_api', methods=['POST'])
def gym_checkout_api():
    """API Check-out member dari gym menggunakan face recognition"""
    try:
        cap = cv2.VideoCapture(selected_camera_id)
        if not cap.isOpened():
            return jsonify({'status': 'error', 'message': 'Kamera tidak dapat diakses'})
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return jsonify({'status': 'error', 'message': 'Gagal mengambil gambar'})
        
        # Deteksi wajah
        faces = extract_faces(frame)
        
        if len(faces) == 0:
            return jsonify({'status': 'error', 'message': 'Wajah tidak terdeteksi'})
        
        # Ambil wajah pertama yang terdeteksi
        (x, y, w, h) = faces[0]
        cropped_face = frame[y:y+h, x:x+w]
        resized_face = cv2.resize(cropped_face, (50, 50)).flatten().reshape(1, -1)
        
        # Identifikasi member
        prediction = identify_face(resized_face)
        member_name = prediction[0] if prediction else 'TIDAK_TERDAFTAR'
        
        if member_name == 'TIDAK_TERDAFTAR':
            return jsonify({'status': 'error', 'message': 'Member tidak terdaftar'})
        
        # Proses check-out
        member = Member.get_member_by_name(member_name)
        if not member:
            return jsonify({'status': 'error', 'message': 'Data member tidak ditemukan'})
        
        success, message = MemberVisit.check_out(member['member_id'])
        
        if success:
            # Get updated member info for response
            updated_member = Member.get_member_by_id(member['member_id'])
            return jsonify({
                'status': 'success',
                'message': message,
                'member': {
                    'name': updated_member['name'],
                    'member_id': updated_member['member_id'],
                    'tier': updated_member['tier'],
                    'total_points': updated_member['total_points']
                }
            })
        else:
            return jsonify({'status': 'error', 'message': message})
            
    except Exception as e:
        logger.error(f"Error in gym_checkout: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/get_cameras')
def get_cameras():
    """Mendapatkan daftar kamera yang tersedia"""
    try:
        available_cameras = []
        for i in range(5):  # Check camera 0-4
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append({
                    'id': i,
                    'name': f'Camera {i}'
                })
                cap.release()
        
        if not available_cameras:
            available_cameras = [{'id': 0, 'name': 'Default Camera'}]
        
        return jsonify(available_cameras)
    except Exception as e:
        logger.error(f"Error getting cameras: {e}")
        return jsonify([{'id': 0, 'name': 'Default Camera'}])

@app.route('/get_gym_data')
def get_gym_data():
    """API untuk mendapatkan data gym real-time"""
    try:
        # Get today's statistics
        today_stats = GymStatistics.get_daily_summary()
        
        # Get today's visits
        today_visits = MemberVisit.get_daily_visits()
        
        # Count active members (checked in but not out)
        active_members = len([v for v in today_visits if not v.get('check_out_time')])
        
        # Serialize visits for JSON
        serialized_visits = [serialize_visit_for_json(visit) for visit in today_visits[:10]]
        
        return jsonify({
            'status': 'success',
            'data': {
                'today_visits': today_stats.get('total_visits', 0),
                'unique_members': today_stats.get('unique_members', 0),
                'active_members': active_members,
                'total_points_earned': today_stats.get('total_points_earned', 0),
                'average_duration': today_stats.get('average_duration', 0),
                'recent_visits': serialized_visits  # 10 kunjungan terbaru - sudah diserialisasi
            }
        })
    except Exception as e:
        logger.error(f"Error getting gym data: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/member_profile/<member_id>')
def member_profile(member_id):
    """Halaman profil member"""
    try:
        member = Member.get_member_by_id(member_id)
        if not member:
            return render_template('error.html', message='Member tidak ditemukan')
        
        # Get member visits
        visits = MemberVisit.get_member_visits(member_id, limit=20)
        
        # Get points history
        points_history = PointsHistory.get_member_history(member_id, limit=20)
        
        return render_template('member_profile.html',
                             member=member,
                             visits=visits,
                             points_history=points_history)
    except Exception as e:
        logger.error(f"Error in member profile: {e}")
        return render_template('error.html', message=str(e))

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    """Menambah member baru"""
    if request.method == 'GET':
        return render_template('add_member.html')
    
    try:
        name = request.form['name']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        membership_type = request.form.get('membership_type', 'basic')
        
        if not name:
            return jsonify({'status': 'error', 'message': 'Nama member harus diisi'})
        
        # Check if member already exists
        existing_member = Member.get_member_by_name(name)
        if existing_member:
            return jsonify({'status': 'error', 'message': 'Member dengan nama ini sudah terdaftar'})
        
        # Add member to database
        success = Member.add_member(name, email, phone, membership_type)
        
        if success:
            return jsonify({'status': 'success', 'message': f'Member {name} berhasil ditambahkan'})
        else:
            return jsonify({'status': 'error', 'message': 'Gagal menambahkan member'})
            
    except Exception as e:
        logger.error(f"Error adding member: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/take_images', methods=['POST'])
def take_images():
    """Mengambil foto untuk training face recognition"""
    try:
        member_name = request.form['member_name']
        
        if not member_name:
            return jsonify({'status': 'error', 'message': 'Nama member harus diisi'})
        
        # Check if member exists
        member = Member.get_member_by_name(member_name)
        if not member:
            return jsonify({'status': 'error', 'message': 'Member tidak ditemukan'})
        
        # Create directory for member photos
        member_dir = f'static/faces/{member_name}'
        os.makedirs(member_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(selected_camera_id)
        if not cap.isOpened():
            return jsonify({'status': 'error', 'message': 'Kamera tidak dapat diakses'})
        
        i = 0
        while i < nimgs:
            ret, frame = cap.read()
            if not ret:
                break
            
            faces = extract_faces(frame)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 255), 1)
                cv2.rectangle(frame, (x, y), (x+w, y-40), (50, 50, 255), -1)
                cv2.putText(frame, f'{member_name}', (x, y-15), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 50, 255), 1)
                
                # Save cropped face
                face_img = frame[y:y+h, x:x+w]
                cv2.imwrite(f'{member_dir}/{member_name}_{i}.jpg', face_img)
                i += 1
                
                if i >= nimgs:
                    break
            
            # Show progress (optional - for debugging)
            cv2.putText(frame, f'Foto ke-{i}/{nimgs}', (30, 30), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 20), 2)
            
        cap.release()
        cv2.destroyAllWindows()
        
        if i < nimgs:
            return jsonify({'status': 'warning', 'message': f'Hanya berhasil mengambil {i} foto dari {nimgs} yang dibutuhkan'})
        
        return jsonify({'status': 'success', 'message': f'Berhasil mengambil {i} foto untuk {member_name}'})
        
    except Exception as e:
        logger.error(f"Error taking images: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/train_faces', methods=['POST'])
def train_faces():
    """Train face recognition model"""
    try:
        success = train_model()
        
        if success:
            return jsonify({'status': 'success', 'message': 'Model face recognition berhasil dilatih'})
        else:
            return jsonify({'status': 'error', 'message': 'Gagal melatih model'})
            
    except Exception as e:
        logger.error(f"Error training faces: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/members')
def members():
    """Halaman daftar member"""
    try:
        all_members = Member.get_all_members()
        return render_template('members_list.html', members=all_members)
    except Exception as e:
        logger.error(f"Error getting members: {e}")
        return render_template('members_list.html', members=[])

@app.route('/statistics')
def statistics():
    """Halaman statistik gym"""
    try:
        # Get daily statistics for last 30 days
        stats_data = []
        for i in range(30):
            stat_date = date.today() - timedelta(days=i)
            daily_stats = GymStatistics.get_daily_summary(stat_date)
            daily_stats['date'] = stat_date.strftime('%Y-%m-%d')
            stats_data.append(daily_stats)
        
        # Get member statistics
        member_stats = Member.get_member_stats()
        
        return render_template('statistics.html', 
                             stats_data=stats_data,
                             member_stats=member_stats)
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return render_template('statistics.html', 
                             stats_data=[],
                             member_stats={})

if __name__ == '__main__':
    print("🏋️ Starting Gym Membership System...")
    print("🌐 Server running at: http://localhost:5000")
    print("📷 Make sure camera is connected for face recognition")
    print("🔑 Access the gym dashboard at: http://localhost:5000/gym")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)