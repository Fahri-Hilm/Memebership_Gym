"""
Gym Membership Models
Models untuk sistem membership gym dengan poin dan tier system
"""

from database import get_db_manager
from datetime import datetime, date, time, timedelta
import logging
import random
import string

logger = logging.getLogger(__name__)

class Member:
    """Model untuk gym member"""
    
    @staticmethod
    def add_member(name, email=None, phone=None, membership_type='basic'):
        """Menambah member baru"""
        try:
            db = get_db_manager()
            
            # Generate unique member ID
            member_id = Member.generate_member_id()
            
            # Set join date
            join_date = date.today()
            
            result = db.execute_query("""
                INSERT INTO members 
                (member_id, name, email, phone, membership_type, join_date, total_points, tier)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 'bronze')
            """, (member_id, name, email, phone, membership_type, join_date))
            
            if result > 0:
                logger.info(f"Member {name} berhasil ditambahkan dengan ID: {member_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Gagal menambah member: {e}")
            return False
    
    @staticmethod
    def generate_member_id():
        """Generate unique member ID"""
        try:
            db = get_db_manager()
            
            while True:
                # Format: GYM + 4 digit random
                member_id = "GYM" + "".join(random.choices(string.digits, k=4))
                
                # Check if ID already exists
                existing = db.execute_query(
                    "SELECT id FROM members WHERE member_id = %s", 
                    (member_id,)
                )
                
                if not existing:
                    return member_id
                    
        except Exception as e:
            logger.error(f"Error generating member ID: {e}")
            return f"GYM{random.randint(1000, 9999)}"
    
    @staticmethod
    def get_member_by_id(member_id):
        """Mendapatkan member berdasarkan member_id"""
        try:
            db = get_db_manager()
            result = db.execute_query(
                "SELECT * FROM members WHERE member_id = %s", 
                (member_id,)
            )
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting member: {e}")
            return None
    
    @staticmethod
    def get_member_by_name(name):
        """Mendapatkan member berdasarkan nama"""
        try:
            db = get_db_manager()
            result = db.execute_query(
                "SELECT * FROM members WHERE name = %s", 
                (name,)
            )
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting member by name: {e}")
            return None
    
    @staticmethod
    def get_all_members():
        """Mendapatkan semua member"""
        try:
            db = get_db_manager()
            return db.execute_query("""
                SELECT m.*, mt.tier_name, mt.points_per_visit, mt.benefits
                FROM members m
                LEFT JOIN membership_tiers mt ON m.tier = mt.tier_name
                ORDER BY m.total_points DESC, m.join_date DESC
            """)
        except Exception as e:
            logger.error(f"Error getting all members: {e}")
            return []
    
    @staticmethod
    def update_member_points(member_id, points_to_add):
        """Update poin member dan tier"""
        try:
            db = get_db_manager()
            
            # Get current member data
            member = Member.get_member_by_id(member_id)
            if not member:
                return False
            
            new_total_points = member['total_points'] + points_to_add
            
            # Determine new tier based on points
            new_tier = Member.calculate_tier(new_total_points)
            
            # Update member
            result = db.execute_query("""
                UPDATE members 
                SET total_points = %s, tier = %s, last_visit = %s
                WHERE member_id = %s
            """, (new_total_points, new_tier, date.today(), member_id))
            
            if result > 0:
                # Log point transaction
                PointsHistory.add_transaction(
                    member['id'], 
                    'earned', 
                    points_to_add, 
                    f"Visit points earned"
                )
                
                logger.info(f"Member {member_id} points updated: +{points_to_add} points, tier: {new_tier}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating member points: {e}")
            return False
    
    @staticmethod
    def calculate_tier(total_points):
        """Menentukan tier berdasarkan total poin"""
        if total_points >= 3000:
            return 'platinum'
        elif total_points >= 1500:
            return 'gold'
        elif total_points >= 500:
            return 'silver'
        else:
            return 'bronze'
    
    @staticmethod
    def get_member_stats():
        """Mendapatkan statistik member"""
        try:
            db = get_db_manager()
            
            # Total members
            total_members = db.execute_query("SELECT COUNT(*) as count FROM members WHERE status = 'active'")
            total_count = total_members[0]['count'] if total_members else 0
            
            # Members by tier
            tier_stats = db.execute_query("""
                SELECT tier, COUNT(*) as count 
                FROM members 
                WHERE status = 'active'
                GROUP BY tier
            """)
            
            # Recent members (last 30 days)
            recent_members = db.execute_query("""
                SELECT COUNT(*) as count 
                FROM members 
                WHERE join_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """)
            recent_count = recent_members[0]['count'] if recent_members else 0
            
            return {
                'total_members': total_count,
                'tier_distribution': tier_stats or [],
                'new_members_30_days': recent_count
            }
            
        except Exception as e:
            logger.error(f"Error getting member stats: {e}")
            return {
                'total_members': 0,
                'tier_distribution': [],
                'new_members_30_days': 0
            }

class MemberVisit:
    """Model untuk kunjungan member ke gym"""
    
    @staticmethod
    def check_in(member_identifier):
        """Member check-in ke gym - member_identifier bisa berupa member_id atau name"""
        try:
            db = get_db_manager()
            
            # Try to get member by member_id first, then by name
            member = Member.get_member_by_id(member_identifier)
            if not member:
                member = Member.get_member_by_name(member_identifier)
            
            if not member or member['status'] != 'active':
                return False, "Member tidak ditemukan atau tidak aktif"
            
            today = date.today()
            current_time = datetime.now().time()
            
            # Check if already checked in today using database ID
            existing_visit = db.execute_query("""
                SELECT * FROM member_visits 
                WHERE member_id = %s AND visit_date = %s AND check_out_time IS NULL
            """, (member['id'], today))
            
            if existing_visit:
                return False, "Member sudah check-in hari ini"
            
            # Create new visit record using database ID
            result = db.execute_query("""
                INSERT INTO member_visits 
                (member_id, visit_date, check_in_time)
                VALUES (%s, %s, %s)
            """, (member['id'], today, current_time))
            
            if result > 0:
                logger.info(f"Member {member['name']} (ID: {member['member_id']}) checked in at {current_time}")
                return True, f"Check-in berhasil! Selamat datang {member['name']}"
            
            return False, "Gagal mencatat check-in"
            
        except Exception as e:
            logger.error(f"Error during check-in: {e}")
            return False, str(e)
    
    @staticmethod
    def check_out(member_identifier):
        """Member check-out dari gym - member_identifier bisa berupa member_id atau name"""
        try:
            db = get_db_manager()
            
            # Try to get member by member_id first, then by name
            member = Member.get_member_by_id(member_identifier)
            if not member:
                member = Member.get_member_by_name(member_identifier)
                
            if not member:
                return False, "Member tidak ditemukan"
            
            today = date.today()
            current_time = datetime.now().time()
            
            # Find active visit (checked in but not checked out)
            active_visit = db.execute_query("""
                SELECT * FROM member_visits 
                WHERE member_id = %s AND visit_date = %s AND check_out_time IS NULL
                ORDER BY check_in_time DESC LIMIT 1
            """, (member['id'], today))
            
            if not active_visit:
                return False, "Tidak ada check-in aktif hari ini"
            
            visit = active_visit[0]
            
            # Calculate duration
            check_in_time = visit['check_in_time']
            
            # Ensure check_in_time is a time object
            if isinstance(check_in_time, datetime):
                check_in_time = check_in_time.time()
            elif isinstance(check_in_time, timedelta):
                # Convert timedelta to time (assuming it's hours from midnight)
                total_seconds = int(check_in_time.total_seconds())
                hours = (total_seconds // 3600) % 24
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                check_in_time = time(hours, minutes, seconds)
            
            # Convert time to datetime for calculation
            today_datetime = datetime.combine(today, check_in_time)
            checkout_datetime = datetime.combine(today, current_time)
            
            # Handle case where checkout is next day
            if checkout_datetime <= today_datetime:
                checkout_datetime += timedelta(days=1)
            
            duration = checkout_datetime - today_datetime
            duration_minutes = int(duration.total_seconds() / 60)
            
            # Calculate points based on tier and duration
            tier_info = db.execute_query(
                "SELECT points_per_visit FROM membership_tiers WHERE tier_name = %s", 
                (member['tier'],)
            )
            base_points = tier_info[0]['points_per_visit'] if tier_info else 10
            
            # Bonus points for longer sessions
            bonus_points = 0
            if duration_minutes >= 60:  # 1+ hours
                bonus_points += 5
            if duration_minutes >= 120:  # 2+ hours
                bonus_points += 10
            
            total_points = base_points + bonus_points
            
            # Update visit record
            result = db.execute_query("""
                UPDATE member_visits 
                SET check_out_time = %s, duration_minutes = %s, points_earned = %s
                WHERE id = %s
            """, (current_time, duration_minutes, total_points, visit['id']))
            
            if result > 0:
                # Update member total points
                Member.update_member_points(member['member_id'], total_points)
                
                logger.info(f"Member {member['name']} (ID: {member['member_id']}) checked out. Duration: {duration_minutes}min, Points: {total_points}")
                
                return True, f"Check-out berhasil! Durasi: {duration_minutes} menit, Poin: +{total_points}"
            
            return False, "Gagal mencatat check-out"
            
        except Exception as e:
            logger.error(f"Error during check-out: {e}")
            return False, str(e)
    
    @staticmethod
    def get_member_visits(member_id, limit=10):
        """Mendapatkan riwayat kunjungan member"""
        try:
            db = get_db_manager()
            member = Member.get_member_by_id(member_id)
            if not member:
                return []
            
            return db.execute_query("""
                SELECT * FROM member_visits 
                WHERE member_id = %s 
                ORDER BY visit_date DESC, check_in_time DESC 
                LIMIT %s
            """, (member['id'], limit))
            
        except Exception as e:
            logger.error(f"Error getting member visits: {e}")
            return []
    
    @staticmethod
    def get_daily_visits(visit_date=None):
        """Mendapatkan kunjungan harian"""
        try:
            db = get_db_manager()
            if not visit_date:
                visit_date = date.today()
            
            return db.execute_query("""
                SELECT mv.*, m.member_id, m.name, m.tier
                FROM member_visits mv
                JOIN members m ON mv.member_id = m.id
                WHERE mv.visit_date = %s
                ORDER BY mv.check_in_time DESC
            """, (visit_date,))
            
        except Exception as e:
            logger.error(f"Error getting daily visits: {e}")
            return []

class PointsHistory:
    """Model untuk riwayat poin member"""
    
    @staticmethod
    def add_transaction(member_db_id, transaction_type, points, description):
        """Menambah transaksi poin"""
        try:
            db = get_db_manager()
            
            result = db.execute_query("""
                INSERT INTO points_history 
                (member_id, transaction_type, points, description)
                VALUES (%s, %s, %s, %s)
            """, (member_db_id, transaction_type, points, description))
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Error adding points transaction: {e}")
            return False
    
    @staticmethod
    def get_member_history(member_id, limit=20):
        """Mendapatkan riwayat poin member"""
        try:
            db = get_db_manager()
            member = Member.get_member_by_id(member_id)
            if not member:
                return []
            
            return db.execute_query("""
                SELECT * FROM points_history 
                WHERE member_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (member['id'], limit))
            
        except Exception as e:
            logger.error(f"Error getting points history: {e}")
            return []

class GymStatistics:
    """Model untuk statistik gym"""
    
    @staticmethod
    def get_daily_summary(summary_date=None):
        """Mendapatkan ringkasan harian"""
        try:
            db = get_db_manager()
            if not summary_date:
                summary_date = date.today()
            
            # Always calculate real-time stats from visits data (don't cache)
            visits = MemberVisit.get_daily_visits(summary_date)
            total_visits = len(visits)
            total_points_earned = sum(visit.get('points_earned', 0) for visit in visits)
            
            # Get unique members who visited - use member_id for uniqueness
            unique_member_ids = set()
            for visit in visits:
                if isinstance(visit, dict) and 'member_id' in visit:
                    unique_member_ids.add(visit['member_id'])
            
            unique_members = len(unique_member_ids)
            
            # Calculate average duration
            completed_visits = [v for v in visits if v.get('duration_minutes') and v.get('duration_minutes') > 0]
            avg_duration = sum(v['duration_minutes'] for v in completed_visits) / len(completed_visits) if completed_visits else 0
            
            stats_data = {
                'total_visits': total_visits,
                'unique_members': unique_members,
                'total_points_earned': total_points_earned,
                'average_duration': int(avg_duration)
            }
            
            # Update or insert gym_statistics for record keeping (optional)
            try:
                existing = db.execute_query("""
                    SELECT id FROM gym_statistics WHERE stat_date = %s
                """, (summary_date,))
                
                if existing:
                    # Update existing record
                    db.execute_query("""
                        UPDATE gym_statistics 
                        SET total_visits = %s, unique_members = %s, total_revenue = %s
                        WHERE stat_date = %s
                    """, (total_visits, unique_members, total_points_earned, summary_date))
                else:
                    # Insert new record
                    db.execute_query("""
                        INSERT INTO gym_statistics 
                        (stat_date, total_visits, unique_members, new_members, total_revenue)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (summary_date, total_visits, unique_members, 0, total_points_earned))
            except:
                # Ignore database update errors, we have the calculated stats
                pass
            
            return stats_data
            
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return {
                'total_visits': 0,
                'unique_members': 0,
                'total_points_earned': 0,
                'average_duration': 0
            }
    
    @staticmethod
    def get_member_statistics():
        """Mendapatkan statistik member"""
        try:
            db = get_db_manager()
            
            # Get tier distribution
            tier_stats = db.execute_query("""
                SELECT tier, COUNT(*) as count 
                FROM members 
                WHERE status = 'active'
                GROUP BY tier
            """)
            
            # Convert to list of objects for template
            tier_distribution = []
            for stat in tier_stats:
                tier_distribution.append({
                    'tier': stat['tier'],
                    'count': stat['count']
                })
                
            # Get total members
            total_members = db.execute_query("""
                SELECT COUNT(*) as total FROM members WHERE status = 'active'
            """)
            
            total_count = total_members[0]['total'] if total_members else 0
            
            # Get active members today
            today_visitors = db.execute_query("""
                SELECT COUNT(DISTINCT member_id) as active_today
                FROM member_visits 
                WHERE DATE(check_in_time) = CURDATE()
            """)
            
            active_today = today_visitors[0]['active_today'] if today_visitors else 0
            
            return {
                'tier_distribution': tier_distribution,
                'total_members': total_count,
                'active_today': active_today
            }
            
        except Exception as e:
            logger.error(f"Error getting member statistics: {e}")
            return {
                'tier_distribution': [
                    {'tier': 'bronze', 'count': 0},
                    {'tier': 'silver', 'count': 0},
                    {'tier': 'gold', 'count': 0},
                    {'tier': 'platinum', 'count': 0}
                ],
                'total_members': 0,
                'active_today': 0
            }