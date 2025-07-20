# 🎓 AI Application Analyzer

An intelligent web application that helps students analyze and improve their study abroad applications using AI-powered document processing, OCR technology, and personalized recommendations.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)
![AI](https://img.shields.io/badge/AI-Powered-purple.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🌟 Features

### **For Students:**
- 📝 **Application Management** - Create, edit, and track study abroad applications
- 📄 **Document Upload** - Upload transcripts, test scores, SOPs, and other documents
- 🔍 **AI Document Analysis** - OCR-powered text extraction and verification
- 🤖 **AI Recommendations** - Personalized university suggestions and profile analysis
- 📊 **Progress Tracking** - Real-time application status and insights
- 📧 **Notifications** - Email alerts for status updates and reminders

### **For Administrators:**
- 👨‍💼 **Enhanced Dashboard** - Comprehensive application management interface
- 📈 **Analytics & Reports** - Detailed insights and export capabilities
- 👥 **User Management** - Complete user administration system
- 📢 **Bulk Notifications** - Mass communication tools
- ⚡ **Quick Actions** - One-click approve/reject functionality
- 📊 **Data Export** - CSV export for external analysis

### **AI-Powered Intelligence:**
- 🔍 **OCR Processing** - Extract text from PDFs and images using Tesseract
- 🎯 **Document Verification** - Compare form data with uploaded documents
- 🏫 **University Matching** - AI-powered university recommendations
- 📝 **Statement Analysis** - NLP-based Statement of Purpose evaluation
- 🎨 **Profile Assessment** - Comprehensive academic strength analysis

## 🛠️ Technology Stack

- **Backend:** Python 3.8+, Flask 2.3.3
- **Database:** SQLite (production-ready for small to medium scale)
- **AI/ML:** scikit-learn, spaCy, sentence-transformers
- **OCR:** Tesseract, PyMuPDF, OpenCV
- **Frontend:** HTML5, Bootstrap 5, JavaScript
- **Authentication:** Flask-Login
- **File Processing:** Werkzeug, Pillow
- **Email:** SMTP integration with HTML templates

Complete Setup Commands 

# 1. Clone the repository
git clone https://github.com/PremPanchal1224/ai-application-analyzer.git

# 2. Navigate to project directory
cd ai-application-analyzer

# 3. Create virtual environment
python -m venv venv

# 4. Activate virtual environment (Windows)
venv\Scripts\activate

# 5. Install Python dependencies
pip install -r requirements.txt

# 6. Download spaCy language model
python -m spacy download en_core_web_sm

# 7. Run the application
python app.py


**Windows:**
1. Download from [GitHub Tesseract Releases](https://github.com/UB-Mannheim/tesseract/wiki)
2. Install to default location (`C:\Program Files\Tesseract-OCR\`)
3. Add to system PATH or the application will auto-detect


