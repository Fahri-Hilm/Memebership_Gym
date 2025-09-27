"""
Database Schema untuk Gym Membership System
Merubah dari sistem absensi karyawan ke membership gym
"""
from database import get_db_manager
import logging

logger = logging.getLogger(__name__)

def create_gym_membership_schema():
    """
    Create new database schema for gym membership system
    """
    db = get_db_manager()
    
    try:
        # 1. Members table (replacing employees)
        members_sql = """
        CREATE TABLE IF NOT EXISTS members (
            id INT AUTO_INCREMENT PRIMARY KEY,
            member_id VARCHAR(20) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE,
            phone VARCHAR(20),
            membership_type ENUM('basic', 'premium', 'vip') DEFAULT 'basic',
            tier ENUM('bronze', 'silver', 'gold', 'platinum') DEFAULT 'bronze',
            total_points INT DEFAULT 0,
            join_date DATE NOT NULL,
            last_visit DATE,
            status ENUM('active', 'inactive', 'suspended') DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        
        # 2. Member visits table (replacing attendance)
        visits_sql = """
        CREATE TABLE IF NOT EXISTS member_visits (
            id INT AUTO_INCREMENT PRIMARY KEY,
            member_id INT NOT NULL,
            visit_date DATE NOT NULL,
            check_in_time TIME,
            check_out_time TIME,
            duration_minutes INT,
            points_earned INT DEFAULT 0,
            visit_type ENUM('gym', 'class', 'personal_training') DEFAULT 'gym',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
            UNIQUE KEY unique_member_date (member_id, visit_date)
        )
        """
        
        # 3. Membership tiers configuration
        tiers_sql = """
        CREATE TABLE IF NOT EXISTS membership_tiers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tier_name ENUM('bronze', 'silver', 'gold', 'platinum') UNIQUE NOT NULL,
            min_points INT NOT NULL,
            points_per_visit INT DEFAULT 10,
            bonus_multiplier DECIMAL(3,2) DEFAULT 1.00,
            benefits JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # 4. Points history table
        points_history_sql = """
        CREATE TABLE IF NOT EXISTS points_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            member_id INT NOT NULL,
            points_change INT NOT NULL,
            reason VARCHAR(255),
            reference_id INT,
            reference_type ENUM('visit', 'bonus', 'penalty', 'manual') DEFAULT 'visit',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
        """
        
        # 5. Gym statistics table
        gym_stats_sql = """
        CREATE TABLE IF NOT EXISTS gym_statistics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stat_date DATE NOT NULL UNIQUE,
            total_visits INT DEFAULT 0,
            unique_members INT DEFAULT 0,
            new_members INT DEFAULT 0,
            total_revenue DECIMAL(10,2) DEFAULT 0.00,
            peak_hour VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # Execute all table creations
        tables = [
            ("members", members_sql),
            ("member_visits", visits_sql), 
            ("membership_tiers", tiers_sql),
            ("points_history", points_history_sql),
            ("gym_statistics", gym_stats_sql)
        ]
        
        for table_name, sql in tables:
            db.execute_query(sql)
            print(f"✅ Table '{table_name}' created successfully")
        
        # Insert default tier configurations
        insert_default_tiers(db)
        
        print("🎉 Gym membership database schema created successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error creating gym membership schema: {e}")
        return False

def insert_default_tiers(db):
    """Insert default membership tier configurations"""
    tiers_data = [
        ('bronze', 0, 10, 1.00, '{"discounts": {"gym": 0, "classes": 0}, "free_sessions": 0, "guest_passes": 0}'),
        ('silver', 500, 15, 1.25, '{"discounts": {"gym": 5, "classes": 10}, "free_sessions": 1, "guest_passes": 1}'),
        ('gold', 1500, 20, 1.50, '{"discounts": {"gym": 10, "classes": 15}, "free_sessions": 2, "guest_passes": 2}'),
        ('platinum', 3000, 30, 2.00, '{"discounts": {"gym": 20, "classes": 25}, "free_sessions": 5, "guest_passes": 5}')
    ]
    
    for tier_name, min_points, points_per_visit, multiplier, benefits in tiers_data:
        try:
            db.execute_query("""
                INSERT IGNORE INTO membership_tiers 
                (tier_name, min_points, points_per_visit, bonus_multiplier, benefits) 
                VALUES (%s, %s, %s, %s, %s)
            """, (tier_name, min_points, points_per_visit, multiplier, benefits))
            print(f"✅ Tier '{tier_name}' configured: {min_points}+ points, {points_per_visit} pts/visit")
        except Exception as e:
            print(f"❌ Error inserting tier {tier_name}: {e}")

if __name__ == "__main__":
    print("🏋️ Creating Gym Membership Database Schema...")
    success = create_gym_membership_schema()
    if success:
        print("🎯 Database ready for gym membership system!")
    else:
        print("❌ Failed to create database schema")