"""
Document processing service for text extraction and AI analysis
"""

import asyncio
import logging
import os
import json
import re
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from asgiref.sync import sync_to_async

from chat.llm_services import LLMManager, LLMError

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for processing documents and extracting knowledge"""
    
    @classmethod
    def extract_text_from_file(cls, file_path: str, file_type: str) -> str:
        """Extract text content from various file types"""
        try:
            file_type = file_type.lower()
            
            if file_type == 'txt':
                return cls._extract_from_txt(file_path)
            elif file_type == 'md':
                return cls._extract_from_markdown(file_path)
            elif file_type == 'pdf':
                return cls._extract_from_pdf(file_path)
            elif file_type in ['doc', 'docx']:
                return cls._extract_from_docx(file_path)
            elif file_type == 'html' or file_type == 'htm':
                return cls._extract_from_html(file_path)
            elif file_type == 'json':
                return cls._extract_from_json(file_path)
            elif file_type == 'csv':
                return cls._extract_from_csv(file_path)
            elif file_type in ['xls', 'xlsx']:
                return cls._extract_from_excel(file_path)
            elif file_type == 'rtf':
                return cls._extract_from_rtf(file_path)
            else:
                logger.warning(f"Unsupported file type for text extraction: {file_type}")
                return ""
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return ""
    
    @classmethod
    def _extract_from_txt(cls, file_path: str) -> str:
        """Extract text from plain text files"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    @classmethod
    def _extract_from_markdown(cls, file_path: str) -> str:
        """Extract text from markdown files"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Remove markdown formatting but keep structure
        content = re.sub(r'#{1,6}\s+', '', content)  # Remove headers
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Remove bold
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # Remove italic
        content = re.sub(r'`(.*?)`', r'\1', content)  # Remove code
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)  # Remove links
        
        return content.strip()
    
    @classmethod
    def _extract_from_pdf(cls, file_path: str) -> str:
        """Extract text from PDF files"""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
                
        except ImportError:
            logger.warning("PyPDF2 not installed, cannot extract PDF text")
            return ""
    
    @classmethod
    def _extract_from_docx(cls, file_path: str) -> str:
        """Extract text from DOCX files"""
        try:
            from docx import Document
            
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
            
        except ImportError:
            logger.warning("python-docx not installed, cannot extract DOCX text")
            return ""
    
    @classmethod
    def _extract_from_html(cls, file_path: str) -> str:
        """Extract text from HTML files"""
        try:
            from bs4 import BeautifulSoup
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except ImportError:
            logger.warning("beautifulsoup4 not installed, cannot extract HTML text")
            return ""
    
    @classmethod
    def _extract_from_json(cls, file_path: str) -> str:
        """Extract text from JSON files"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            try:
                data = json.load(f)
                return cls._json_to_text(data)
            except json.JSONDecodeError:
                # If JSON is invalid, treat as text
                f.seek(0)
                return f.read()
    
    @classmethod
    def _json_to_text(cls, data, prefix="") -> str:
        """Convert JSON data to readable text"""
        if isinstance(data, dict):
            text = ""
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    text += f"{prefix}{key}:\n{cls._json_to_text(value, prefix + '  ')}\n"
                else:
                    text += f"{prefix}{key}: {value}\n"
            return text
        elif isinstance(data, list):
            text = ""
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    text += f"{prefix}Item {i+1}:\n{cls._json_to_text(item, prefix + '  ')}\n"
                else:
                    text += f"{prefix}{item}\n"
            return text
        else:
            return str(data)
    
    @classmethod
    def _extract_from_csv(cls, file_path: str) -> str:
        """Extract text from CSV files"""
        try:
            import pandas as pd
            
            df = pd.read_csv(file_path, encoding='utf-8', errors='ignore')
            
            # Convert DataFrame to readable text
            text = f"CSV Data with {len(df)} rows and {len(df.columns)} columns:\n\n"
            text += f"Columns: {', '.join(df.columns)}\n\n"
            
            # Add sample data (first 10 rows)
            sample = df.head(10)
            text += "Sample Data:\n"
            text += sample.to_string(index=False)
            
            return text
            
        except ImportError:
            logger.warning("pandas not installed, cannot extract CSV text")
            return ""
    
    @classmethod
    def _extract_from_excel(cls, file_path: str) -> str:
        """Extract text from Excel files"""
        try:
            import pandas as pd
            
            # Read all sheets
            excel_data = pd.read_excel(file_path, sheet_name=None, encoding='utf-8', errors='ignore')
            
            text = f"Excel file with {len(excel_data)} sheets:\n\n"
            
            for sheet_name, df in excel_data.items():
                text += f"Sheet: {sheet_name} ({len(df)} rows, {len(df.columns)} columns)\n"
                text += f"Columns: {', '.join(df.columns)}\n"
                
                # Add sample data (first 5 rows)
                sample = df.head(5)
                text += sample.to_string(index=False) + "\n\n"
            
            return text
            
        except ImportError:
            logger.warning("pandas not installed, cannot extract Excel text")
            return ""
    
    @classmethod
    def _extract_from_rtf(cls, file_path: str) -> str:
        """Extract text from RTF files"""
        try:
            from striprtf.striprtf import rtf_to_text
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                rtf_content = f.read()
            
            return rtf_to_text(rtf_content)
            
        except ImportError:
            logger.warning("striprtf not installed, cannot extract RTF text")
            return ""
    
    @classmethod
    async def generate_ai_analysis(cls, text: str, filename: str) -> Dict[str, any]:
        """Generate AI summary and keywords for document text"""
        if not text.strip():
            return {
                'summary': '',
                'keywords': [],
                'topics': [],
                'category': 'uncategorized'
            }
        
        try:
            # Truncate text if too long (keep first 4000 characters for analysis)
            analysis_text = text[:4000] + "..." if len(text) > 4000 else text
            
            analysis_prompt = f"""
Analyze the following document content and provide:
1. A concise summary (2-3 sentences)
2. Key topics and keywords
3. Document category
4. Important entities mentioned

Document filename: {filename}

Document content:
{analysis_text}

Please respond in JSON format:
{{
    "summary": "Brief summary of the document",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "topics": ["topic1", "topic2"],
    "category": "document_category",
    "entities": ["entity1", "entity2"]
}}
"""
            
            # Get AI analysis
            service = await LLMManager.get_active_service()
            
            messages = [
                {'role': 'user', 'content': analysis_prompt}
            ]
            
            response, metadata = await service.generate_response(
                messages=messages,
                max_tokens=500,
                temperature=0.1  # Lower temperature for more consistent analysis
            )
            
            # Try to parse JSON response
            try:
                analysis = json.loads(response)
                return {
                    'summary': analysis.get('summary', ''),
                    'keywords': analysis.get('keywords', []),
                    'topics': analysis.get('topics', []),
                    'category': analysis.get('category', 'uncategorized'),
                    'entities': analysis.get('entities', [])
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, extract info manually
                logger.warning(f"Failed to parse AI analysis JSON for {filename}")
                return {
                    'summary': response[:200] + "..." if len(response) > 200 else response,
                    'keywords': [],
                    'topics': [],
                    'category': 'uncategorized',
                    'entities': []
                }
            
        except LLMError as e:
            logger.error(f"LLM error during document analysis: {e}")
            return {
                'summary': f"Document content extracted from {filename}",
                'keywords': [],
                'topics': [],
                'category': 'uncategorized',
                'entities': []
            }
        except Exception as e:
            logger.error(f"Unexpected error during AI analysis: {e}")
            return {
                'summary': f"Document content extracted from {filename}",
                'keywords': [],
                'topics': [],
                'category': 'uncategorized', 
                'entities': []
            }
    
    @classmethod
    async def process_document(cls, document):
        """Process a document: extract text and generate AI analysis"""
        try:
            logger.info(f"Processing document: {document.name}")
            
            # Extract text from file
            if document.file:
                file_path = document.file.path
                text = cls.extract_text_from_file(file_path, document.file_type)
                
                if text:
                    # Generate AI analysis
                    analysis = await cls.generate_ai_analysis(text, document.original_filename)
                    
                    # Update document with extracted information
                    document.extracted_text = text
                    document.ai_summary = analysis['summary']
                    document.ai_keywords = analysis['keywords'] + analysis.get('topics', []) + analysis.get('entities', [])
                    
                    # Auto-categorize if no category set
                    if not document.category and analysis['category'] != 'uncategorized':
                        document.category = analysis['category']
                    
                    # Create search vector (simplified - could use more advanced techniques)
                    search_terms = [
                        document.name,
                        document.category or '',
                        ' '.join(document.get_tags_list()),
                        analysis['summary'],
                        ' '.join(analysis['keywords'])
                    ]
                    document.search_vector = ' '.join(filter(None, search_terms)).lower()
                    
                    await sync_to_async(document.save)(update_fields=[
                        'extracted_text', 'ai_summary', 'ai_keywords_json', 
                        'category', 'search_vector'
                    ])
                    
                    logger.info(f"Successfully processed document: {document.name}")
                    return True
                else:
                    logger.warning(f"No text extracted from document: {document.name}")
                    return False
            else:
                logger.error(f"No file attached to document: {document.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing document {document.name}: {e}")
            return False