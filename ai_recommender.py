import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import spacy
import re
from typing import Dict, List, Tuple, Optional
import json
import logging

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None

class ProfileAnalyzer:
    """Analyze student profiles and extract insights"""
    
    def __init__(self):
        self.academic_levels = {
            'undergraduate': 1,
            'masters': 2,
            'phd': 3
        }
        
        self.test_score_weights = {
            'gre_score': 0.3,
            'toefl_score': 0.25,
            'ielts_score': 0.25,
            'gpa': 0.2
        }

    def calculate_academic_strength(self, profile: Dict) -> Dict[str, float]:
        """Calculate academic strength metrics"""
        scores = {}
        
        # GPA scoring (out of 4.0)
        if profile.get('gpa'):
            gpa = float(profile['gpa'])
            scores['gpa_strength'] = min(gpa / 4.0, 1.0) * 100
        
        # GRE scoring (260-340 scale)
        if profile.get('gre_score'):
            gre = int(profile['gre_score'])
            # Normalize GRE score (300+ is good, 320+ is excellent)
            if gre >= 320:
                scores['gre_strength'] = 90 + (gre - 320) * 0.5
            elif gre >= 300:
                scores['gre_strength'] = 60 + (gre - 300) * 1.5
            else:
                scores['gre_strength'] = max(0, gre - 260) * 1.5
        
        # TOEFL scoring (0-120 scale)
        if profile.get('toefl_score'):
            toefl = int(profile['toefl_score'])
            # 100+ is excellent, 80+ is good
            if toefl >= 100:
                scores['toefl_strength'] = 80 + (toefl - 100) * 1.0
            elif toefl >= 80:
                scores['toefl_strength'] = 60 + (toefl - 80) * 1.0
            else:
                scores['toefl_strength'] = toefl * 0.75
        
        # IELTS scoring (0-9 scale)
        if profile.get('ielts_score'):
            ielts = float(profile['ielts_score'])
            # 7+ is excellent, 6+ is good
            scores['ielts_strength'] = min(ielts / 9.0, 1.0) * 100
        
        return scores

    def analyze_statement_of_purpose(self, sop_text: str) -> Dict[str, any]:
        """Analyze Statement of Purpose using NLP"""
        analysis = {
            'word_count': 0,
            'readability_score': 0,
            'key_themes': [],
            'sentiment_score': 0,
            'structure_score': 0,
            'recommendations': []
        }
        
        if not sop_text or not nlp:
            return analysis
        
        # Basic metrics
        words = sop_text.split()
        analysis['word_count'] = len(words)
        
        # Process with spaCy
        doc = nlp(sop_text[:2000])  # Limit for performance
        
        # Extract key themes using named entities and noun phrases
        themes = set()
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PRODUCT', 'EVENT', 'WORK_OF_ART']:
                themes.add(ent.text.lower())
        
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) <= 3:  # Keep short phrases
                themes.add(chunk.text.lower())
        
        analysis['key_themes'] = list(themes)[:10]  # Top 10 themes
        
        # Structure analysis
        paragraphs = sop_text.split('\n\n')
        analysis['structure_score'] = min(len(paragraphs) * 20, 100)  # More paragraphs = better structure
        
        # Word count recommendations
        if analysis['word_count'] < 300:
            analysis['recommendations'].append("SoP is too short. Aim for 500-800 words.")
        elif analysis['word_count'] > 1000:
            analysis['recommendations'].append("SoP is too long. Consider condensing to 500-800 words.")
        else:
            analysis['recommendations'].append("SoP length is appropriate.")
        
        # Theme diversity
        if len(themes) < 5:
            analysis['recommendations'].append("Consider adding more diverse themes and experiences.")
        
        return analysis

    def calculate_profile_completeness(self, profile: Dict) -> Dict[str, any]:
        """Calculate how complete the profile is"""
        required_fields = [
            'full_name', 'email', 'target_university', 'course', 
            'academic_level', 'statement_of_purpose'
        ]
        
        optional_fields = [
            'gpa', 'gre_score', 'toefl_score', 'ielts_score', 
            'work_experience', 'phone', 'nationality'
        ]
        
        required_score = sum(1 for field in required_fields if profile.get(field)) / len(required_fields) * 100
        optional_score = sum(1 for field in optional_fields if profile.get(field)) / len(optional_fields) * 100
        
        overall_score = (required_score * 0.7) + (optional_score * 0.3)
        
        missing_required = [field for field in required_fields if not profile.get(field)]
        missing_optional = [field for field in optional_fields if not profile.get(field)]
        
        return {
            'overall_completeness': overall_score,
            'required_completeness': required_score,
            'optional_completeness': optional_score,
            'missing_required': missing_required,
            'missing_optional': missing_optional
        }

class UniversityMatcher:
    """Match students with suitable universities"""
    
    def __init__(self):
        # Sample university database (in production, this would be a real database)
        self.universities = [
            {
                'name': 'Stanford University',
                'country': 'USA',
                'ranking': 95,
                'min_gpa': 3.7,
                'min_gre': 320,
                'min_toefl': 100,
                'programs': ['Computer Science', 'Engineering', 'Business', 'Medicine'],
                'acceptance_rate': 4.3,
                'tuition': 55000
            },
            {
                'name': 'MIT',
                'country': 'USA',
                'ranking': 98,
                'min_gpa': 3.8,
                'min_gre': 325,
                'min_toefl': 100,
                'programs': ['Computer Science', 'Engineering', 'Physics', 'Mathematics'],
                'acceptance_rate': 6.7,
                'tuition': 53450
            },
            {
                'name': 'University of Toronto',
                'country': 'Canada',
                'ranking': 85,
                'min_gpa': 3.5,
                'min_gre': 310,
                'min_toefl': 93,
                'programs': ['Computer Science', 'Engineering', 'Medicine', 'Business'],
                'acceptance_rate': 43.0,
                'tuition': 45000
            },
            {
                'name': 'University of Melbourne',
                'country': 'Australia',
                'ranking': 80,
                'min_gpa': 3.2,
                'min_gre': 305,
                'min_toefl': 79,
                'programs': ['Computer Science', 'Engineering', 'Business', 'Arts'],
                'acceptance_rate': 70.0,
                'tuition': 35000
            },
            {
                'name': 'Carnegie Mellon University',
                'country': 'USA',
                'ranking': 88,
                'min_gpa': 3.6,
                'min_gre': 315,
                'min_toefl': 95,
                'programs': ['Computer Science', 'Engineering', 'Business', 'Design'],
                'acceptance_rate': 17.0,
                'tuition': 52000
            }
        ]

    def find_matching_universities(self, profile: Dict, limit: int = 5) -> List[Dict]:
        """Find universities that match student profile"""
        matches = []
        
        student_gpa = float(profile.get('gpa', 0))
        student_gre = int(profile.get('gre_score', 0))
        student_toefl = int(profile.get('toefl_score', 0))
        target_program = profile.get('course', '').lower()
        
        for uni in self.universities:
            match_score = 0
            reasons = []
            
            # GPA match
            if student_gpa >= uni['min_gpa']:
                match_score += 25
                reasons.append(f"GPA ({student_gpa}) meets requirement ({uni['min_gpa']})")
            elif student_gpa >= uni['min_gpa'] - 0.3:
                match_score += 15
                reasons.append(f"GPA ({student_gpa}) close to requirement ({uni['min_gpa']})")
            
            # GRE match
            if student_gre >= uni['min_gre']:
                match_score += 25
                reasons.append(f"GRE ({student_gre}) meets requirement ({uni['min_gre']})")
            elif student_gre >= uni['min_gre'] - 15:
                match_score += 15
                reasons.append(f"GRE ({student_gre}) close to requirement ({uni['min_gre']})")
            
            # TOEFL match
            if student_toefl >= uni['min_toefl']:
                match_score += 25
                reasons.append(f"TOEFL ({student_toefl}) meets requirement ({uni['min_toefl']})")
            elif student_toefl >= uni['min_toefl'] - 10:
                match_score += 15
                reasons.append(f"TOEFL ({student_toefl}) close to requirement ({uni['min_toefl']})")
            
            # Program match
            program_match = any(target_program in prog.lower() for prog in uni['programs'])
            if program_match:
                match_score += 25
                reasons.append(f"Offers {target_program} program")
            
            if match_score > 40:  # Minimum threshold
                matches.append({
                    'university': uni,
                    'match_score': match_score,
                    'match_reasons': reasons,
                    'category': self._categorize_match(match_score, uni['acceptance_rate'])
                })
        
        # Sort by match score and return top matches
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        return matches[:limit]

    def _categorize_match(self, score: int, acceptance_rate: float) -> str:
        """Categorize university matches"""
        if score >= 80:
            return 'reach' if acceptance_rate < 20 else 'match'
        elif score >= 60:
            return 'match'
        else:
            return 'safety'

class RecommendationEngine:
    """Main recommendation engine that combines all analyzers"""
    
    def __init__(self):
        self.profile_analyzer = ProfileAnalyzer()
        self.university_matcher = UniversityMatcher()

    def generate_comprehensive_analysis(self, profile: Dict, documents_analysis: Dict = None) -> Dict:
        """Generate comprehensive AI analysis and recommendations"""
        
        analysis = {
            'profile_strength': {},
            'academic_metrics': {},
            'sop_analysis': {},
            'completeness': {},
            'university_recommendations': [],
            'improvement_suggestions': [],
            'overall_assessment': {}
        }
        
        # Analyze academic strength
        analysis['academic_metrics'] = self.profile_analyzer.calculate_academic_strength(profile)
        
        # Analyze Statement of Purpose
        if profile.get('statement_of_purpose'):
            analysis['sop_analysis'] = self.profile_analyzer.analyze_statement_of_purpose(
                profile['statement_of_purpose']
            )
        
        # Calculate profile completeness
        analysis['completeness'] = self.profile_analyzer.calculate_profile_completeness(profile)
        
        # Find matching universities
        analysis['university_recommendations'] = self.university_matcher.find_matching_universities(profile)
        
        # Generate improvement suggestions
        analysis['improvement_suggestions'] = self._generate_improvement_suggestions(
            analysis, profile, documents_analysis
        )
        
        # Calculate overall assessment
        analysis['overall_assessment'] = self._calculate_overall_assessment(analysis)
        
        return analysis

    def _generate_improvement_suggestions(self, analysis: Dict, profile: Dict, docs_analysis: Dict) -> List[str]:
        """Generate personalized improvement suggestions"""
        suggestions = []
        
        # Academic improvements
        academic = analysis['academic_metrics']
        
        if 'gpa_strength' in academic and academic['gpa_strength'] < 70:
            suggestions.append("Consider taking additional courses to improve your GPA if possible")
        
        if 'gre_strength' in academic and academic['gre_strength'] < 70:
            suggestions.append("Consider retaking the GRE exam to improve your score")
        
        if not profile.get('gre_score') and not profile.get('gmat_score'):
            suggestions.append("Consider taking the GRE or GMAT to strengthen your application")
        
        # Language proficiency
        has_english_test = profile.get('toefl_score') or profile.get('ielts_score')
        if not has_english_test:
            suggestions.append("Take TOEFL or IELTS exam to demonstrate English proficiency")
        
        # Profile completeness
        completeness = analysis['completeness']
        if completeness['required_completeness'] < 100:
            missing = ', '.join(completeness['missing_required'])
            suggestions.append(f"Complete required fields: {missing}")
        
        # Statement of Purpose
        sop = analysis.get('sop_analysis', {})
        if sop.get('recommendations'):
            suggestions.extend(sop['recommendations'])
        
        # Work experience
        if not profile.get('work_experience'):
            suggestions.append("Add relevant work experience or internships to strengthen your profile")
        
        # Document verification issues
        if docs_analysis and docs_analysis.get('summary', {}).get('red_flags'):
            suggestions.append("Address document verification issues found in uploaded files")
        
        return suggestions

    def _calculate_overall_assessment(self, analysis: Dict) -> Dict:
        """Calculate overall profile assessment"""
        
        # Calculate component scores
        academic_score = np.mean(list(analysis['academic_metrics'].values())) if analysis['academic_metrics'] else 0
        completeness_score = analysis['completeness']['overall_completeness']
        sop_score = 70  # Default if no SoP analysis
        
        if analysis['sop_analysis'].get('word_count'):
            wc = analysis['sop_analysis']['word_count']
            if 500 <= wc <= 800:
                sop_score = 80
            elif 300 <= wc <= 1000:
                sop_score = 70
            else:
                sop_score = 60
        
        # Weighted overall score
        overall_score = (academic_score * 0.4) + (completeness_score * 0.3) + (sop_score * 0.3)
        
        # Determine profile strength category
        if overall_score >= 85:
            strength = "Excellent"
            message = "Your profile is very strong. You're competitive for top universities!"
        elif overall_score >= 70:
            strength = "Good"
            message = "Your profile is solid. Consider some improvements for better chances."
        elif overall_score >= 55:
            strength = "Average"
            message = "Your profile needs strengthening in several areas."
        else:
            strength = "Needs Improvement"
            message = "Significant improvements needed before applying."
        
        return {
            'overall_score': round(overall_score, 1),
            'strength_category': strength,
            'assessment_message': message,
            'component_scores': {
                'academic': round(academic_score, 1),
                'completeness': round(completeness_score, 1),
                'sop': round(sop_score, 1)
            }
        }

class AIInsightGenerator:
    """Generate AI-powered insights and predictions"""
    
    def __init__(self):
        self.recommendation_engine = RecommendationEngine()
    
    def generate_application_insights(self, application_data: Dict, documents_analysis: Dict = None) -> Dict:
        """Generate comprehensive insights for an application"""
        
        # Run comprehensive analysis
        ai_analysis = self.recommendation_engine.generate_comprehensive_analysis(
            application_data, documents_analysis
        )
        
        # Add prediction insights
        ai_analysis['predictions'] = self._generate_predictions(application_data, ai_analysis)
        
        # Add competitive analysis
        ai_analysis['competitive_analysis'] = self._generate_competitive_analysis(ai_analysis)
        
        return ai_analysis
    
    def _generate_predictions(self, profile: Dict, analysis: Dict) -> Dict:
        """Generate admission predictions"""
        
        overall_score = analysis['overall_assessment']['overall_score']
        
        # Simple prediction model based on profile strength
        if overall_score >= 85:
            admission_chance = "High (70-85%)"
            top_tier_chance = "Good (40-60%)"
        elif overall_score >= 70:
            admission_chance = "Good (55-75%)"
            top_tier_chance = "Moderate (20-40%)"
        elif overall_score >= 55:
            admission_chance = "Moderate (35-55%)"
            top_tier_chance = "Low (5-20%)"
        else:
            admission_chance = "Low (15-35%)"
            top_tier_chance = "Very Low (<10%)"
        
        return {
            'overall_admission_chance': admission_chance,
            'top_tier_admission_chance': top_tier_chance,
            'confidence_level': 'Medium',  # Could be improved with more data
            'key_factors': [
                f"Profile strength: {analysis['overall_assessment']['strength_category']}",
                f"Academic performance: {analysis['overall_assessment']['component_scores']['academic']}/100",
                f"Profile completeness: {analysis['overall_assessment']['component_scores']['completeness']}/100"
            ]
        }
    
    def _generate_competitive_analysis(self, analysis: Dict) -> Dict:
        """Generate competitive analysis against typical applicants"""
        
        overall_score = analysis['overall_assessment']['overall_score']
        
        if overall_score >= 80:
            competitive_position = "Top 15%"
            benchmark = "Above average compared to successful applicants"
        elif overall_score >= 65:
            competitive_position = "Top 35%"
            benchmark = "Average compared to successful applicants"
        elif overall_score >= 50:
            competitive_position = "Top 60%"
            benchmark = "Below average - needs improvement"
        else:
            competitive_position = "Bottom 40%"
            benchmark = "Significantly below average"
        
        return {
            'competitive_position': competitive_position,
            'benchmark_comparison': benchmark,
            'areas_of_strength': self._identify_strengths(analysis),
            'areas_for_improvement': self._identify_weaknesses(analysis)
        }
    
    def _identify_strengths(self, analysis: Dict) -> List[str]:
        """Identify profile strengths"""
        strengths = []
        
        academic = analysis['academic_metrics']
        for metric, score in academic.items():
            if score >= 80:
                metric_name = metric.replace('_strength', '').replace('_', ' ').title()
                strengths.append(f"Strong {metric_name}")
        
        if analysis['completeness']['overall_completeness'] >= 90:
            strengths.append("Complete profile")
        
        if analysis.get('sop_analysis', {}).get('word_count', 0) >= 500:
            strengths.append("Well-developed Statement of Purpose")
        
        return strengths or ["Profile needs development"]
    
    def _identify_weaknesses(self, analysis: Dict) -> List[str]:
        """Identify areas for improvement"""
        weaknesses = []
        
        academic = analysis['academic_metrics']
        for metric, score in academic.items():
            if score < 60:
                metric_name = metric.replace('_strength', '').replace('_', ' ').title()
                weaknesses.append(f"Improve {metric_name}")
        
        if analysis['completeness']['overall_completeness'] < 80:
            weaknesses.append("Incomplete profile information")
        
        if len(analysis.get('improvement_suggestions', [])) > 0:
            weaknesses.extend(analysis['improvement_suggestions'][:3])  # Top 3 suggestions
        
        return weaknesses or ["Continue strengthening overall profile"]
