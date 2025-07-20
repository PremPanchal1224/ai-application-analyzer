import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import csv
import io

class AdminManager:
    """Comprehensive admin management functionality"""
    
    def __init__(self, db_path='app.db'):
        self.db_path = db_path
    
    def get_dashboard_stats(self) -> Dict:
        """Get comprehensive dashboard statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Application statistics
        cursor.execute('SELECT COUNT(*) FROM applications')
        stats['total_applications'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "pending"')
        stats['pending_applications'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "approved"')
        stats['approved_applications'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "rejected"')
        stats['rejected_applications'] = cursor.fetchone()[0]
        
        # User statistics
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "student"')
        stats['total_students'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
        stats['total_admins'] = cursor.fetchone()[0]
        
        # Recent activity (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        cursor.execute('SELECT COUNT(*) FROM applications WHERE created_at >= ?', (week_ago,))
        stats['recent_applications'] = cursor.fetchone()[0]
        
        # AI Analysis statistics
        cursor.execute('SELECT COUNT(DISTINCT application_id) FROM analysis_results WHERE analysis_type = "ai_recommendations"')
        stats['ai_analyzed'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT application_id) FROM analysis_results WHERE analysis_type = "document_verification"')
        stats['document_analyzed'] = cursor.fetchone()[0]
        
        # Average scores
        cursor.execute('SELECT AVG(confidence_score) FROM analysis_results WHERE analysis_type = "ai_recommendations"')
        avg_score = cursor.fetchone()[0]
        stats['avg_ai_score'] = round(avg_score, 1) if avg_score else 0
        
        conn.close()
        return stats
    
    def get_detailed_applications(self, status_filter=None, limit=None) -> List[Dict]:
        """Get detailed application list with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                a.id, a.full_name, a.email, a.target_university, a.course,
                a.status, a.created_at, u.username,
                ar1.confidence_score as ai_score,
                ar2.confidence_score as doc_score,
                COUNT(d.id) as document_count
            FROM applications a
            JOIN users u ON a.user_id = u.id
            LEFT JOIN analysis_results ar1 ON a.id = ar1.application_id AND ar1.analysis_type = 'ai_recommendations'
            LEFT JOIN analysis_results ar2 ON a.id = ar2.application_id AND ar2.analysis_type = 'document_verification'
            LEFT JOIN documents d ON a.id = d.application_id
        '''
        
        params = []
        if status_filter:
            query += ' WHERE a.status = ?'
            params.append(status_filter)
        
        query += ' GROUP BY a.id ORDER BY a.created_at DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        cursor.execute(query, params)
        applications = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        columns = ['id', 'full_name', 'email', 'university', 'course', 'status', 'created_at', 
                  'username', 'ai_score', 'doc_score', 'document_count']
        
        return [dict(zip(columns, app)) for app in applications]
    
    def update_application_status(self, app_id: int, status: str, admin_notes: str = None) -> bool:
        """Update application status with admin notes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update application status
            cursor.execute('''
                UPDATE applications 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (status, app_id))
            
            # Log admin action
            cursor.execute('''
                INSERT INTO admin_actions (application_id, action, notes, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (app_id, f'status_change_{status}', admin_notes))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating application status: {e}")
            return False
    
    def bulk_update_applications(self, app_ids: List[int], status: str, notes: str = None) -> Dict:
        """Bulk update multiple applications"""
        success_count = 0
        failed_count = 0
        
        for app_id in app_ids:
            if self.update_application_status(app_id, status, notes):
                success_count += 1
            else:
                failed_count += 1
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'total_processed': len(app_ids)
        }
    
    def get_user_management_data(self) -> List[Dict]:
        """Get user data for management"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                u.id, u.username, u.email, u.role, u.created_at,
                COUNT(a.id) as application_count,
                MAX(a.created_at) as last_application
            FROM users u
            LEFT JOIN applications a ON u.id = a.user_id
            GROUP BY u.id
            ORDER BY u.created_at DESC
        ''')
        
        users = cursor.fetchall()
        conn.close()
        
        columns = ['id', 'username', 'email', 'role', 'created_at', 
                  'application_count', 'last_application']
        
        return [dict(zip(columns, user)) for user in users]
    
    def generate_analytics_report(self, days=30) -> Dict:
        """Generate comprehensive analytics report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days)
        
        report = {
            'period_days': days,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Application trends
        cursor.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM applications 
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date
        ''', (start_date,))
        
        application_trend = cursor.fetchall()
        report['application_trend'] = [{'date': row[0], 'count': row[1]} for row in application_trend]
        
        # Status distribution
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM applications
            WHERE created_at >= ?
            GROUP BY status
        ''', (start_date,))
        
        status_distribution = cursor.fetchall()
        report['status_distribution'] = [{'status': row[0], 'count': row[1]} for row in status_distribution]
        
        # Top universities
        cursor.execute('''
            SELECT target_university, COUNT(*) as count
            FROM applications
            WHERE created_at >= ?
            GROUP BY target_university
            ORDER BY count DESC
            LIMIT 10
        ''', (start_date,))
        
        top_universities = cursor.fetchall()
        report['top_universities'] = [{'university': row[0], 'count': row[1]} for row in top_universities]
        
        # AI Score distribution
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN confidence_score >= 80 THEN 'Excellent (80+)'
                    WHEN confidence_score >= 60 THEN 'Good (60-79)'
                    WHEN confidence_score >= 40 THEN 'Average (40-59)'
                    ELSE 'Needs Improvement (<40)'
                END as score_range,
                COUNT(*) as count
            FROM analysis_results
            WHERE analysis_type = 'ai_recommendations' AND created_at >= ?
            GROUP BY score_range
        ''', (start_date,))
        
        score_distribution = cursor.fetchall()
        report['ai_score_distribution'] = [{'range': row[0], 'count': row[1]} for row in score_distribution]
        
        conn.close()
        return report
    
    def export_applications_csv(self, status_filter=None) -> str:
        """Export applications to CSV format"""
        applications = self.get_detailed_applications(status_filter)
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=applications[0].keys() if applications else [])
        writer.writeheader()
        writer.writerows(applications)
        
        return output.getvalue()
    
    def initialize_admin_tables(self):
        """Create additional admin-specific tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Admin actions log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                admin_user_id INTEGER,
                action TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES applications (id),
                FOREIGN KEY (admin_user_id) REFERENCES users (id)
            )
        ''')
        
        # System notifications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # System settings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()

class NotificationManager:
    """Handle system notifications"""
    
    def __init__(self, db_path='app.db'):
        self.db_path = db_path
    
    def create_notification(self, user_id: int, title: str, message: str, type: str = 'info'):
        """Create a new notification"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (?, ?, ?, ?)
        ''', (user_id, title, message, type))
        
        conn.commit()
        conn.close()
    
    def get_user_notifications(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get notifications for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, message, type, is_read, created_at
            FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        notifications = cursor.fetchall()
        conn.close()
        
        columns = ['id', 'title', 'message', 'type', 'is_read', 'created_at']
        return [dict(zip(columns, notif)) for notif in notifications]
    
    def mark_as_read(self, notification_id: int):
        """Mark notification as read"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE notifications SET is_read = TRUE WHERE id = ?', (notification_id,))
        
        conn.commit()
        conn.close()
    
    def broadcast_notification(self, title: str, message: str, role_filter: str = None):
        """Send notification to all users or specific role"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if role_filter:
            cursor.execute('SELECT id FROM users WHERE role = ?', (role_filter,))
        else:
            cursor.execute('SELECT id FROM users')
        
        user_ids = [row[0] for row in cursor.fetchall()]
        
        for user_id in user_ids:
            self.create_notification(user_id, title, message, 'system')
        
        conn.close()
        return len(user_ids)
