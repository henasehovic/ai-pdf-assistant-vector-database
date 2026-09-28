import sqlite3
import hashlib
import re
from datetime import datetime
from typing import Dict, Any, Optional

DATABASE_FILE = "users.db"

def init_database():
    """Initialize the users database"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            surname TEXT NOT NULL,
            telephone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username: str) -> bool:
    """Validate username format"""
    if len(username) < 3 or len(username) > 20:
        return False
    pattern = r'^[a-zA-Z0-9_]+$'
    return re.match(pattern, username) is not None

def validate_password(password: str) -> bool:
    """Validate password strength"""
    if len(password) < 6:
        return False
    return True

def validate_telephone(telephone: str) -> bool:
    """Validate telephone number format"""
    if not telephone:
        return True  # Telephone is optional
    pattern = r'^[\+]?[1-9][\d]{0,15}$'
    return re.match(pattern, telephone.replace(" ", "").replace("-", "")) is not None

def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user in the database"""
    # Extract user data
    username = user_data.get('username', '').strip()
    email = user_data.get('email', '').strip().lower()
    password = user_data.get('password', '')
    name = user_data.get('name', '').strip()
    surname = user_data.get('surname', '').strip()
    telephone = user_data.get('telephone', '').strip() if user_data.get('telephone') else None
    
    # Validation
    if not all([username, email, password, name, surname]):
        raise ValueError("All required fields must be provided")
    
    if not validate_username(username):
        raise ValueError("Username must be 3-20 characters long and contain only letters, numbers, and underscores")
    
    if not validate_email(email):
        raise ValueError("Invalid email format")
    
    if not validate_password(password):
        raise ValueError("Password must be at least 6 characters long")
    
    if len(name) < 2 or len(name) > 50:
        raise ValueError("Name must be between 2 and 50 characters")
    
    if len(surname) < 2 or len(surname) > 50:
        raise ValueError("Surname must be between 2 and 50 characters")
    
    if telephone and not validate_telephone(telephone):
        raise ValueError("Invalid telephone number format")
    
    # Initialize database if it doesn't exist
    init_database()
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            raise ValueError("Username already exists")
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            raise ValueError("Email already exists")
        
        # Hash password
        password_hash = hash_password(password)
        
        # Insert new user
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, name, surname, telephone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, name, surname, telephone))
        
        user_id = cursor.lastrowid
        
        # Get the created user
        cursor.execute('''
            SELECT id, username, email, name, surname, telephone, created_at
            FROM users WHERE id = ?
        ''', (user_id,))
        
        user_row = cursor.fetchone()
        
        conn.commit()
        
        return {
            "id": user_row[0],
            "username": user_row[1],
            "email": user_row[2],
            "name": user_row[3],
            "surname": user_row[4],
            "telephone": user_row[5],
            "created_at": user_row[6]
        }
        
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            raise ValueError("Username already exists")
        elif "email" in str(e):
            raise ValueError("Email already exists")
        else:
            raise ValueError("Database integrity error")
    
    finally:
        conn.close()

def verify_user(username: str, password: str) -> Dict[str, Any]:
    """Verify user credentials and return user data"""
    if not username or not password:
        raise ValueError("Username and password are required")
    
    # Initialize database if it doesn't exist
    init_database()
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        # Hash the provided password
        password_hash = hash_password(password)
        
        # Find user with matching username and password
        cursor.execute('''
            SELECT id, username, email, name, surname, telephone, created_at
            FROM users WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))
        
        user_row = cursor.fetchone()
        
        if not user_row:
            raise ValueError("Invalid username or password")
        
        return {
            "id": user_row[0],
            "username": user_row[1],
            "email": user_row[2],
            "name": user_row[3],
            "surname": user_row[4],
            "telephone": user_row[5],
            "created_at": user_row[6]
        }
        
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    init_database()
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, username, email, name, surname, telephone, created_at
            FROM users WHERE id = ?
        ''', (user_id,))
        
        user_row = cursor.fetchone()
        
        if not user_row:
            return None
        
        return {
            "id": user_row[0],
            "username": user_row[1],
            "email": user_row[2],
            "name": user_row[3],
            "surname": user_row[4],
            "telephone": user_row[5],
            "created_at": user_row[6]
        }
        
    finally:
        conn.close()

def get_all_users() -> list:
    """Get all users (for admin purposes)"""
    init_database()
    
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, username, email, name, surname, telephone, created_at
            FROM users ORDER BY created_at DESC
        ''')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "name": row[3],
                "surname": row[4],
                "telephone": row[5],
                "created_at": row[6]
            })
        
        return users
        
    finally:
        conn.close()

# Initialize database when module is imported
if __name__ == "__main__":
    init_database()
    print("Database setup complete")