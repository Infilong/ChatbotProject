# 🤖 Intelligent Chatbot Analysis System

A comprehensive AI-driven chatbot and customer analytics platform built with Django, React, and modern machine learning technologies. Features advanced RAG (Retrieval-Augmented Generation), LLM integration, and multilingual support.

## ✨ Key Features

### 🧠 **AI-Powered Chatbot**
- **Multi-LLM Support**: OpenAI GPT, Google Gemini, Anthropic Claude integration
- **Advanced RAG System**: Vector embeddings + BM25 hybrid search with semantic reranking
- **Document Knowledge Base**: Upload and query company documents with AI-powered responses
- **Real-time Conversations**: WebSocket-powered live chat with instant responses
- **Context-Aware Responses**: Maintains conversation history and context

### 📊 **Advanced Analytics & Insights**
- **LangExtract Integration**: Real-time conversation analysis and sentiment detection
- **Automatic Issue Detection**: AI-powered identification of customer problems and urgency levels
- **Sentiment Analysis**: Multi-language sentiment scoring with confidence metrics
- **Business Intelligence**: Extract actionable insights from customer conversations
- **Performance Metrics**: Response time tracking, satisfaction scoring, escalation analysis

### 🔍 **Document Management & Search**
- **Hybrid Search Engine**: Combines vector similarity and keyword matching (BM25)
- **Auto-Processing**: Automatic text extraction and chunking from uploaded documents
- **Duplicate Detection**: SHA-256 hash-based content deduplication
- **Multiple Formats**: Support for PDF, DOCX, TXT, MD, and more
- **Usage Analytics**: Track document effectiveness and knowledge gaps

### 🌐 **Multilingual & Admin Features**
- **Full Internationalization**: Complete Japanese translation support
- **Advanced Admin Interface**: Custom Django admin with analytics dashboards
- **User Management**: Role-based access control and user profiles
- **API Configuration**: Flexible LLM provider and model management
- **Automated Analysis**: Smart criteria-based conversation processing

## 🛠️ Technology Stack

### **Backend (Django)**
- **Framework**: Django 5.2.4 with Django REST Framework
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Real-time**: Django Channels with WebSocket support
- **AI/ML Libraries**:
  - LangExtract 1.0.3 (conversation analysis)
  - Sentence Transformers (vector embeddings)
  - FAISS-CPU (vector search)
  - Rank-BM25 (keyword search)
  - NLTK (text processing)

### **Frontend (React)**
- **Framework**: React 19.1.1 with TypeScript
- **UI Library**: Material-UI (MUI) 7.2.0 with Material Design 3
- **Theme**: Ocean Blue professional design
- **State Management**: React hooks with localStorage persistence
- **Responsive Design**: Mobile-first, cross-device compatibility

### **AI & Machine Learning**
- **LLM APIs**: OpenAI, Google Gemini, Anthropic Claude
- **Vector Search**: all-MiniLM-L6-v2 embeddings model
- **Text Analysis**: LangExtract for structured insights
- **Search Strategy**: Hybrid vector + BM25 + semantic reranking

## 🚀 Getting Started

### **Prerequisites**
- Python 3.10+ with uv package manager
- Node.js 16+ with npm
- Git for version control

### **Backend Setup**
```bash
cd backend

# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run database migrations
uv run python manage.py migrate

# Create superuser for admin access
uv run python manage.py createsuperuser

# Start development server
uv run python manage.py runserver
```

The backend will be available at `http://localhost:8000`

### **Frontend Setup**
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

The frontend will be available at `http://localhost:3000`

### **Environment Configuration**

Create a `.env` file in the backend directory:
```env
# Django Configuration
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True

# LLM API Keys
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-claude-key

# Database (optional - defaults to SQLite)
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db
```

## 📁 Project Architecture

```
ChatbotProject/
├── backend/                          # Django backend
│   ├── authentication/               # User auth and profiles
│   ├── chat/                        # Core chat functionality
│   │   ├── models.py                # Conversation & Message models
│   │   ├── llm_services.py          # LLM integration service
│   │   ├── admin.py                 # Custom admin interface
│   │   └── consumers.py             # WebSocket consumers
│   ├── documents/                   # Document management
│   │   ├── models.py                # Document models with UUID
│   │   ├── advanced_rag_service.py  # Hybrid search engine
│   │   └── knowledge_base.py        # Knowledge processing
│   ├── analytics/                   # Analytics and insights
│   │   ├── models.py                # Analytics data models
│   │   └── langextract_service.py   # AI analysis service
│   ├── locale/ja/                   # Japanese translations
│   ├── templates/                   # Django templates
│   └── requirements.txt             # Python dependencies
├── frontend/                        # React TypeScript frontend
│   ├── src/
│   │   ├── components/              # React components
│   │   │   ├── LoginPage.tsx        # Authentication interface
│   │   │   └── ChatPage.tsx         # Main chat interface
│   │   ├── theme.ts                 # Material-UI theme
│   │   └── App.tsx                  # Root component
│   └── package.json                 # Node.js dependencies
└── README.md                        # This file
```

## 🔧 Key Components

### **AI-Driven RAG Pipeline**
1. **User Query** → LLM intent analysis → Enhanced search terms
2. **Vector Search** → Semantic similarity with sentence transformers
3. **Keyword Search** → BM25 for exact term matching
4. **Hybrid Ranking** → Combined scoring with reranking
5. **Context Generation** → Document chunks + conversation history
6. **LLM Response** → Context-aware natural language generation

### **Analytics Workflow**
1. **Conversation Capture** → Real-time message processing
2. **LangExtract Analysis** → Sentiment, urgency, issue detection
3. **Insight Extraction** → Business intelligence and patterns
4. **Admin Dashboard** → Visual analytics and reporting
5. **Automated Actions** → Smart criteria-based processing

### **Security Features**
- **UUID-based URLs**: Prevents enumeration attacks
- **Content Hashing**: SHA-256 for duplicate detection
- **File Validation**: Type and size restrictions
- **Input Sanitization**: XSS and injection protection
- **Rate Limiting**: API abuse prevention

## 🌐 Internationalization

- **Primary Language**: English (default)
- **Supported Languages**: Japanese (完全サポート)
- **Admin Interface**: Fully translated with fuzzy handling
- **User Messages**: Multilingual conversation support
- **Error Messages**: Localized validation and feedback

## 📊 Admin Features

### **Analytics Dashboard**
- **Real-time Metrics**: Active users, satisfaction scores, response times
- **Issue Tracking**: Automatic categorization and urgency detection
- **Document Analytics**: Usage patterns and effectiveness scoring
- **User Insights**: Behavior analysis and engagement metrics
- **Custom Reports**: Exportable business intelligence data

### **Management Tools**
- **LLM Configuration**: Multi-provider API key management
- **Document Management**: Upload, categorize, and monitor documents
- **User Administration**: Role-based access and preferences
- **System Monitoring**: Performance metrics and error tracking
- **Automated Analysis**: Smart conversation processing rules

## 🔄 Development Status

### **Completed Features** ✅
- [x] Full-stack Django + React implementation
- [x] Multi-LLM integration (OpenAI, Gemini, Claude)
- [x] Advanced RAG with hybrid search
- [x] Real-time WebSocket chat
- [x] Japanese internationalization
- [x] Document management system
- [x] LangExtract analytics integration
- [x] Custom admin interface
- [x] Security implementation (UUID, hashing)
- [x] Vector embeddings and search


## 🔐 Security & Production

### **Security Measures**
- UUID-based resource identifiers (prevents enumeration)
- SHA-256 content hashing for file deduplication
- Input validation and sanitization
- HTTPS enforcement in production
- Rate limiting on sensitive endpoints
- Secure API key management

### **Production Deployment**
- Environment-specific configuration
- SQLite database support
- Nginx reverse proxy compatible
- Automated backup strategies



*Powered by Django, React, and cutting-edge AI technologies*