import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import cv2
import numpy as np
import spacy
import re
import os
from typing import Dict, List, Tuple, Optional

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Please install the spaCy English model: python -m spacy download en_core_web_sm")
    nlp = None

class DocumentProcessor:
    def __init__(self, tesseract_path=None):
        """Initialize document processor with optional Tesseract path"""
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Common patterns for data extraction
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'[\+]?[1-9]?[0-9]{7,15}',
            'gpa': r'(?:GPA|CGPA|Grade Point Average)[:\s]*([0-9]+\.?[0-9]*)',
            'gre_score': r'(?:GRE|Graduate Record Examination)[:\s]*([0-9]{3})',
            'toefl_score': r'(?:TOEFL|Test of English)[:\s]*([0-9]{2,3})',
            'ielts_score': r'(?:IELTS|International English)[:\s]*([0-9]\.?[0-9]?)',
            'date': r'\b(?:[0-3]?[0-9][/-][0-1]?[0-9][/-](?:[0-9]{2})?[0-9]{2})\b'
        }

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF using PyMuPDF"""
        try:
            doc = fitz.open(file_path)
            text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text()
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return ""

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR accuracy"""
        try:
            # Read image
            img = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.medianBlur(gray, 3)
            
            # Apply thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            return thresh
            
        except Exception as e:
            print(f"Error preprocessing image: {str(e)}")
            return None

    def extract_text_from_image(self, file_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            # Preprocess image
            processed_img = self.preprocess_image(file_path)
            
            if processed_img is not None:
                # Apply OCR
                text = pytesseract.image_to_string(processed_img, config='--psm 6')
                return text.strip()
            else:
                # Fallback to direct OCR
                text = pytesseract.image_to_string(Image.open(file_path))
                return text.strip()
                
        except Exception as e:
            print(f"Error extracting text from image: {str(e)}")
            return ""

    def extract_text_from_document(self, file_path: str, mime_type: str) -> str:
        """Main function to extract text from any supported document"""
        text = ""
        
        if mime_type and 'pdf' in mime_type.lower():
            text = self.extract_text_from_pdf(file_path)
        elif mime_type and any(img_type in mime_type.lower() for img_type in ['image', 'jpeg', 'png', 'jpg']):
            text = self.extract_text_from_image(file_path)
        else:
            # Try to determine by file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.pdf':
                text = self.extract_text_from_pdf(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                text = self.extract_text_from_image(file_path)
        
        return text

    def extract_structured_data(self, text: str) -> Dict[str, any]:
        """Extract structured data from text using patterns and NLP"""
        extracted_data = {}
        
        # Extract using regex patterns
        for field, pattern in self.patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if field in ['gpa', 'ielts_score']:
                    extracted_data[field] = float(matches[0]) if matches[0] else None
                elif field in ['gre_score', 'toefl_score']:
                    extracted_data[field] = int(matches[0]) if matches[0] else None
                else:
                    extracted_data[field] = matches[0]
        
        # Extract names using spaCy NER
        if nlp:
            doc = nlp(text[:1000])  # Process first 1000 chars for performance
            names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
            if names:
                extracted_data['names'] = names[:3]  # Top 3 names
        
        return extracted_data

    def compare_with_form_data(self, extracted_data: Dict, form_data: Dict) -> Dict[str, any]:
        """Compare extracted document data with form submission data"""
        comparison_results = {
            'matches': {},
            'discrepancies': {},
            'missing_in_document': {},
            'confidence_score': 0.0
        }
        
        total_fields = 0
        matched_fields = 0
        
        # Compare specific fields
        comparable_fields = ['email', 'gpa', 'gre_score', 'toefl_score', 'ielts_score']
        
        for field in comparable_fields:
            if field in form_data and form_data[field]:
                total_fields += 1
                
                if field in extracted_data:
                    form_value = form_data[field]
                    extracted_value = extracted_data[field]
                    
                    # Handle different comparison types
                    if field == 'email':
                        if str(form_value).lower() == str(extracted_value).lower():
                            comparison_results['matches'][field] = {
                                'form': form_value,
                                'document': extracted_value,
                                'status': 'exact_match'
                            }
                            matched_fields += 1
                        else:
                            comparison_results['discrepancies'][field] = {
                                'form': form_value,
                                'document': extracted_value,
                                'issue': 'email_mismatch'
                            }
                    
                    elif field in ['gpa', 'gre_score', 'toefl_score', 'ielts_score']:
                        # Allow small tolerance for numeric values
                        tolerance = 0.1 if field in ['gpa', 'ielts_score'] else 5
                        
                        if abs(float(form_value) - float(extracted_value)) <= tolerance:
                            comparison_results['matches'][field] = {
                                'form': form_value,
                                'document': extracted_value,
                                'status': 'within_tolerance'
                            }
                            matched_fields += 1
                        else:
                            comparison_results['discrepancies'][field] = {
                                'form': form_value,
                                'document': extracted_value,
                                'issue': 'score_mismatch'
                            }
                else:
                    comparison_results['missing_in_document'][field] = form_data[field]
        
        # Calculate confidence score
        if total_fields > 0:
            comparison_results['confidence_score'] = (matched_fields / total_fields) * 100
        
        # Name comparison (fuzzy matching)
        if 'names' in extracted_data and 'full_name' in form_data:
            form_name = form_data['full_name'].lower()
            document_names = [name.lower() for name in extracted_data['names']]
            
            name_found = any(
                any(part in doc_name or doc_name in part 
                    for doc_name in document_names)
                for part in form_name.split()
            )
            
            if name_found:
                comparison_results['matches']['name_verification'] = {
                    'form': form_data['full_name'],
                    'document': extracted_data['names'],
                    'status': 'name_found'
                }
            else:
                comparison_results['discrepancies']['name_verification'] = {
                    'form': form_data['full_name'],
                    'document': extracted_data['names'],
                    'issue': 'name_not_found'
                }
        
        return comparison_results

class DocumentAnalyzer:
    """Main analyzer class that orchestrates document processing"""
    
    def __init__(self, tesseract_path=None):
        self.processor = DocumentProcessor(tesseract_path)
    
    def analyze_application_documents(self, application_id: int, documents: List[Dict], form_data: Dict) -> Dict:
        """Analyze all documents for an application"""
        analysis_results = {
            'application_id': application_id,
            'documents_analyzed': [],
            'overall_verification': {},
            'individual_analyses': {},
            'summary': {
                'total_documents': len(documents),
                'successfully_processed': 0,
                'overall_confidence': 0.0,
                'red_flags': [],
                'recommendations': []
            }
        }
        
        all_extracted_data = {}
        
        # Process each document
        for doc in documents:
            doc_analysis = self._analyze_single_document(doc, form_data)
            analysis_results['individual_analyses'][doc['document_type']] = doc_analysis
            
            if doc_analysis['extraction_success']:
                analysis_results['summary']['successfully_processed'] += 1
                # Merge extracted data
                all_extracted_data.update(doc_analysis['extracted_data'])
        
        # Perform overall verification
        if all_extracted_data:
            overall_comparison = self.processor.compare_with_form_data(all_extracted_data, form_data)
            analysis_results['overall_verification'] = overall_comparison
            analysis_results['summary']['overall_confidence'] = overall_comparison['confidence_score']
            
            # Generate red flags and recommendations
            analysis_results['summary']['red_flags'] = self._identify_red_flags(overall_comparison)
            analysis_results['summary']['recommendations'] = self._generate_recommendations(overall_comparison, form_data)
        
        return analysis_results
    
    def _analyze_single_document(self, document: Dict, form_data: Dict) -> Dict:
        """Analyze a single document"""
        result = {
            'document_type': document['document_type'],
            'filename': document['original_filename'],
            'extraction_success': False,
            'extracted_text': '',
            'extracted_data': {},
            'verification_results': {}
        }
        
        try:
            # Extract text
            text = self.processor.extract_text_from_document(
                document['file_path'], 
                document['mime_type']
            )
            
            result['extracted_text'] = text[:500]  # Store first 500 chars for preview
            
            if text:
                result['extraction_success'] = True
                
                # Extract structured data
                extracted_data = self.processor.extract_structured_data(text)
                result['extracted_data'] = extracted_data
                
                # Compare with form data
                comparison = self.processor.compare_with_form_data(extracted_data, form_data)
                result['verification_results'] = comparison
                
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def _identify_red_flags(self, comparison: Dict) -> List[str]:
        """Identify potential issues that need attention"""
        red_flags = []
        
        if comparison['discrepancies']:
            for field, details in comparison['discrepancies'].items():
                if field == 'email':
                    red_flags.append(f"Email mismatch: Form has '{details['form']}' but document shows '{details['document']}'")
                elif 'score' in field:
                    red_flags.append(f"{field.upper()} score discrepancy: Form shows {details['form']} vs Document shows {details['document']}")
                elif 'name' in field:
                    red_flags.append("Student name not clearly found in uploaded documents")
        
        if comparison['confidence_score'] < 50:
            red_flags.append("Low verification confidence - manual review recommended")
            
        return red_flags
    
    def _generate_recommendations(self, comparison: Dict, form_data: Dict) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if comparison['confidence_score'] >= 80:
            recommendations.append("✅ Documents appear to match form data well")
        elif comparison['confidence_score'] >= 60:
            recommendations.append("⚠️ Some discrepancies found - review recommended")
        else:
            recommendations.append("❌ Multiple discrepancies found - detailed review required")
        
        if comparison['missing_in_document']:
            missing_fields = list(comparison['missing_in_document'].keys())
            recommendations.append(f"Request clearer documents for: {', '.join(missing_fields)}")
        
        if not comparison['matches'] and not comparison['discrepancies']:
            recommendations.append("Unable to extract verifiable data - may need manual document review")
            
        return recommendations
