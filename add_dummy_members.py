"""
Script untuk menambah data dummy member gym
"""

from gym_models import Member
import logging

logging.basicConfig(level=logging.INFO)

def add_dummy_members():
    """Menambah data member dummy untuk testing"""
    dummy_members = [
        {
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '08123456789',
            'membership_type': 'premium'
        },
        {
            'name': 'Jane Smith', 
            'email': 'jane@example.com',
            'phone': '08234567890',
            'membership_type': 'basic'
        },
        {
            'name': 'Mike Johnson',
            'email': 'mike@example.com', 
            'phone': '08345678901',
            'membership_type': 'vip'
        },
        {
            'name': 'Sarah Wilson',
            'email': 'sarah@example.com',
            'phone': '08456789012', 
            'membership_type': 'basic'
        },
        {
            'name': 'David Brown',
            'email': 'david@example.com',
            'phone': '08567890123',
            'membership_type': 'premium'
        }
    ]
    
    print("Menambah data member dummy...")
    
    for member_data in dummy_members:
        success = Member.add_member(
            member_data['name'],
            member_data['email'], 
            member_data['phone'],
            member_data['membership_type']
        )
        
        if success:
            print(f"✓ Member {member_data['name']} berhasil ditambahkan")
        else:
            print(f"✗ Gagal menambah member {member_data['name']}")
    
    # Tampilkan semua member
    print("\nDaftar member:")
    members = Member.get_all_members() 
    for member in members:
        print(f"- {member['member_id']}: {member['name']} ({member['tier']} - {member['total_points']} poin)")

if __name__ == "__main__":
    add_dummy_members()