import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import sqlite3
from typing import List, Dict, Optional
import os
from datetime import datetime, timedelta
import threading

class EmailManager:
    """Handle email notifications and communications"""
    
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        # In production, use environment variables or config file
        self.sender_email = "your-app-email@gmail.com"
        self.sender_password = "your-app-password"  # Use app-specific password
        self.sender_name = "AI Application Analyzer"
        
    def send_email(self, recipient_email: str, subject: str, body_text: str, body_html: str = None) -> bool:
        """Send email notification"""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = recipient_email
            
            # Create text and HTML parts
            text_part = MIMEText(body_text, "plain")
            message.attach(text_part)
            
            if body_html:
                html_part = MIMEText(body_html, "html")
                message.attach(html_part)
            
            # Create secure connection and send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())
            
            return True
            
        except Exception as e:
            print(f"Email sending error: {e}")
            return False
    
    def send_application_status_email(self, user_email: str, user_name: str, 
                                    application_data: Dict, new_status: str, admin_notes: str = None) -> bool:
        """Send application status update email"""
        
        subject = f"Application Status Update - {new_status.title()}"
        
        # Text version
        text_body = f"""
Dear {user_name},

Your application status has been updated:

Application Details:
- University: {application_data.get('target_university', 'N/A')}
- Course: {application_data.get('course', 'N/A')}
- New Status: {new_status.title()}

"""
        
        if admin_notes:
            text_body += f"Admin Notes: {admin_notes}\n\n"
        
        text_body += """
You can view your complete application status by logging into your dashboard.

Best regards,
AI Application Analyzer Team
"""
        
        # HTML version
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0;">🎓 AI Application Analyzer</h1>
            <p style="margin: 10px 0 0 0;">Application Status Update</p>
        </div>
        
        <div style="background: white; padding: 30px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333;">Dear {user_name},</h2>
            
            <p>Your application status has been updated:</p>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #495057; margin-top: 0;">Application Details</h3>
                <p><strong>University:</strong> {application_data.get('target_university', 'N/A')}</p>
                <p><strong>Course:</strong> {application_data.get('course', 'N/A')}</p>
                <p><strong>New Status:</strong> 
                    <span style="background: {'#d4edda' if new_status == 'approved' else '#f8d7da' if new_status == 'rejected' else '#fff3cd'}; 
                                 color: {'#155724' if new_status == 'approved' else '#721c24' if new_status == 'rejected' else '#856404'}; 
                                 padding: 5px 10px; border-radius: 3px; font-weight: bold;">
                        {new_status.title()}
                    </span>
                </p>
            </div>
            
            {f'<div style="background: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0;"><strong>Admin Notes:</strong><br>{admin_notes}</div>' if admin_notes else ''}
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="http://localhost:5000/dashboard" 
                   style="background: #007bff; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    View Dashboard
                </a>
            </div>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            
            <p style="color: #666; font-size: 14px;">
                Best regards,<br>
                <strong>AI Application Analyzer Team</strong>
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        return self.send_email(user_email, subject, text_body, html_body)
    
    def send_welcome_email(self, user_email: str, user_name: str, username: str) -> bool:
        """Send welcome email to new users"""
        
        subject = "Welcome to AI Application Analyzer!"
        
        text_body = f"""
Dear {user_name},

Welcome to AI Application Analyzer!

Your account has been successfully created with the username: {username}

You can now:
- Submit study abroad applications
- Upload and verify your documents with AI
- Get personalized university recommendations
- Track your application progress

Login to get started: http://localhost:5000/login

Best regards,
AI Application Analyzer Team
"""
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0;">🎉 Welcome!</h1>
            <p style="margin: 10px 0 0 0;">AI Application Analyzer</p>
        </div>
        
        <div style="background: white; padding: 30px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 10px 10px;">
            <h2 style="color: #333;">Dear {user_name},</h2>
            
            <p>Welcome to <strong>AI Application Analyzer</strong>! Your account has been successfully created.</p>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Username:</strong> {username}</p>
                <p><strong>Account Type:</strong> Student</p>
            </div>
            
            <h3 style="color: #495057;">What you can do now:</h3>
            <ul style="padding-left: 20px;">
                <li>📝 Submit study abroad applications</li>
                <li>📄 Upload and verify documents with AI</li>
                <li>🏫 Get personalized university recommendations</li>
                <li>📊 Track your application progress</li>
                <li>🤖 Access AI-powered profile analysis</li>
            </ul>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="http://localhost:5000/login" 
                   style="background: #28a745; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Login to Get Started
                </a>
            </div>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            
            <p style="color: #666; font-size: 14px;">
                Best regards,<br>
                <strong>AI Application Analyzer Team</strong>
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        return self.send_email(user_email, subject, text_body, html_body)

class NotificationScheduler:
    """Schedule and manage automated notifications"""
    
    def __init__(self, db_path='app.db'):
        self.db_path = db_path
        self.email_manager = EmailManager()
    
    def send_pending_application_reminders(self):
        """Send reminders for applications pending for too long"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find applications pending for more than 7 days
        week_ago = datetime.now() - timedelta(days=7)
        
        cursor.execute('''
            SELECT a.id, a.full_name, a.email, a.target_university, a.course, a.created_at,
                   u.username
            FROM applications a
            JOIN users u ON a.user_id = u.id
            WHERE a.status = 'pending' AND a.created_at < ?
        ''', (week_ago,))
        
        pending_apps = cursor.fetchall()
        
        # Send reminder emails to students
        for app in pending_apps:
            app_id, full_name, email, university, course, created_at, username = app
            
            subject = "Application Under Review - Update"
            
            text_body = f"""
Dear {full_name},

Your application to {university} for {course} is currently under review.

Application submitted: {created_at}
Current status: Under Review

Our team is carefully reviewing your application. We'll notify you as soon as there's an update.

You can check your application status anytime in your dashboard.

Best regards,
AI Application Analyzer Team
"""
            
            self.email_manager.send_email(email, subject, text_body)
        
        conn.close()
        return len(pending_apps)
    
    def send_daily_admin_summary(self):
        """Send daily summary to administrators"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get admin emails
        cursor.execute('SELECT email, username FROM users WHERE role = "admin"')
        admins = cursor.fetchall()
        
        if not admins:
            return 0
        
        # Get today's statistics
        today = datetime.now().date()
        
        cursor.execute('SELECT COUNT(*) FROM applications WHERE DATE(created_at) = ?', (today,))
        new_applications = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "pending"')
        pending_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "approved" AND DATE(updated_at) = ?', (today,))
        approved_today = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "rejected" AND DATE(updated_at) = ?', (today,))
        rejected_today = cursor.fetchone()[0]
        
        # Send summary to each admin
        for admin_email, admin_username in admins:
            subject = f"Daily Admin Summary - {today}"
            
            text_body = f"""
Daily Summary for {today}

New Applications: {new_applications}
Pending Review: {pending_count}
Approved Today: {approved_today}
Rejected Today: {rejected_today}

Action Required:
- {pending_count} applications need review

Login to admin dashboard: http://localhost:5000/admin

Best regards,
System Notification
"""
            
            self.email_manager.send_email(admin_email, subject, text_body)
        
        conn.close()
        return len(admins)

class WhatsAppManager:
    """WhatsApp notifications using Twilio (optional)"""
    
    def __init__(self):
        # Twilio credentials (optional feature)
        self.account_sid = "your_twilio_account_sid"
        self.auth_token = "your_twilio_auth_token"
        self.whatsapp_number = "whatsapp:+1234567890"
        self.enabled = False  # Set to True if you want to use WhatsApp
    
    def send_whatsapp_notification(self, to_number: str, message: str) -> bool:
        """Send WhatsApp notification (requires Twilio setup)"""
        if not self.enabled:
            return False
            
        try:
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            
            message = client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=f'whatsapp:{to_number}'
            )
            
            return True
            
        except Exception as e:
            print(f"WhatsApp sending error: {e}")
            return False

class NotificationService:
    """Main notification service that coordinates all notification types"""
    
    def __init__(self, db_path='app.db'):
        self.db_path = db_path
        self.email_manager = EmailManager()
        self.whatsapp_manager = WhatsAppManager()
        self.scheduler = NotificationScheduler(db_path)
    
    def notify_application_status_change(self, application_id: int, new_status: str, admin_notes: str = None):
        """Send notifications when application status changes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get application and user data
        cursor.execute('''
            SELECT a.*, u.email, u.username
            FROM applications a
            JOIN users u ON a.user_id = u.id
            WHERE a.id = ?
        ''', (application_id,))
        
        result = cursor.fetchone()
        if not result:
            return False
        
        # Create application dict
        app_columns = ['id', 'user_id', 'full_name', 'email', 'phone', 'date_of_birth', 
                      'nationality', 'target_university', 'course', 'academic_level', 
                      'gpa', 'gre_score', 'toefl_score', 'ielts_score', 'work_experience', 
                      'statement_of_purpose', 'status', 'created_at', 'updated_at']
        
        app_data = dict(zip(app_columns, result[:-2]))  # Exclude email and username
        user_email = result[-2]
        username = result[-1]
        
        # Send email notification
        email_sent = self.email_manager.send_application_status_email(
            user_email, 
            app_data['full_name'],
            app_data,
            new_status,
            admin_notes
        )
        
        # Send WhatsApp notification if phone number is available
        whatsapp_sent = False
        if app_data.get('phone') and self.whatsapp_manager.enabled:
            message = f"Hi {app_data['full_name']}, your application to {app_data['target_university']} has been {new_status}. Check your email for details."
            whatsapp_sent = self.whatsapp_manager.send_whatsapp_notification(
                app_data['phone'], 
                message
            )
        
        conn.close()
        return {'email_sent': email_sent, 'whatsapp_sent': whatsapp_sent}
    
    def notify_new_registration(self, user_id: int):
        """Send welcome email to new users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT username, email FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result:
            username, email = result
            self.email_manager.send_welcome_email(email, username, username)
        
        conn.close()
    
    def run_scheduled_tasks(self):
        """Run all scheduled notification tasks"""
        results = {}
        
        # Send pending application reminders
        results['pending_reminders'] = self.scheduler.send_pending_application_reminders()
        
        # Send daily admin summary
        results['admin_summaries'] = self.scheduler.send_daily_admin_summary()
        
        return results
