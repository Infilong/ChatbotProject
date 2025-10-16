# Intelligent Chatbot Analysis System

A comprehensive AI-driven chatbot platform with advanced document management, conversation analytics, and multilingual support. Built with Django, React, and modern machine learning technologies.

## ✨ Key Features

### 🧠 **AI-Powered Chatbot System**

![Chat System Demo](Assets/chat-demo.gif)

- **Multi-LLM Support**: OpenAI GPT, Google Gemini, Anthropic Claude integration
- **Advanced RAG (Retrieval-Augmented Generation)**: Hybrid vector + BM25 search with semantic reranking
- **Real-time Chat Interface**: WebSocket-powered conversations with instant responses
- **Context-Aware Responses**: Maintains conversation history and document context
- **Document Knowledge Base**: Upload company documents for AI-powered Q&A

### 📊 **Comprehensive Analytics & Insights**

![Analytics Dashboard Demo](Assets/analytics-demo.gif)

- **LangExtract Integration**: AI-powered conversation analysis with sentiment detection
- **Automatic Issue Detection**: Smart identification of customer problems and urgency levels
- **Business Intelligence**: Extract actionable insights from customer interactions
- **Message Analytics**: Response time tracking, satisfaction scoring, escalation analysis
- **Document Usage Analytics**: Track document effectiveness and identify knowledge gaps

### 🔍 **Advanced Document Management**

![Document Management Demo](assets/document-management-demo.gif)

- **Hybrid Search Engine**: Vector embeddings (sentence-transformers) + BM25 keyword matching
- **Smart Processing**: Automatic text extraction, chunking, and content optimization
- **Duplicate Prevention**: SHA-256 hash-based content deduplication
- **File Upload Progress**: Real-time progress indicators with cancel/minimize controls
- **Multiple Formats**: PDF, DOCX, TXT, MD, JSON, CSV, XLSX, RTF, HTML support
- **Usage Analytics**: Performance tracking and document effectiveness scoring

### 🌐 **Enterprise Admin Features**
- **Multilingual Support**: Complete Japanese (日本語) internationalization
- **Advanced Django Admin**: Custom interfaces with analytics dashboards
- **Session Management**: Real-time user tracking with device and location detection
- **Security Features**: UUID-based URLs, content hashing, file validation
- **Progress Tracking**: Real-time indicators for long-running operations
- **User Management**: Role-based access control and preferences

### 🔧 **Technical Infrastructure**
- **Background Processing**: Async analysis with progress tracking and error handling
- **API Management**: Flexible LLM provider configuration and monitoring
- **Vector Search**: FAISS-powered semantic search with reranking
- **Automatic Analysis**: Smart criteria-based conversation processing
- **Error Recovery**: Robust retry mechanisms and graceful degradation

## 🛠️ Technology Stack

### **Backend (Django 5.2.4)**
```
Core Framework:
├── Django REST Framework 3.16.0     # API development
├── Django Channels 4.3.1            # WebSocket support
├── Django CORS Headers 4.7.0        # Cross-origin requests
└── Django Jazzmin 3.1.0             # Modern admin interface

AI & Machine Learning:
├── LangExtract 1.0.3                # Conversation analysis
├── Sentence Transformers 2.7.0      # Vector embeddings
├── FAISS-CPU 1.8.0                  # Vector search
├── Rank-BM25 0.2.2                  # Keyword search
├── Scikit-learn 1.5.1               # ML utilities
└── NLTK 3.9.1                       # Text processing

LLM Integrations:
├── OpenAI 1.98.0                    # GPT models
├── Google-GenerativeAI 0.8.3        # Gemini models
└── Anthropic 0.35.0                 # Claude models

Data Processing:
├── Pandas 2.3.1                     # Data analysis
├── NumPy 2.3.2                      # Numerical computing
└── RapidFuzz 3.10.0                 # Fuzzy matching
```

### **Frontend (React 19.1.1)**
```
Core Framework:
├── React 19.1.1                     # UI framework
├── TypeScript 4.9.5                 # Type safety
└── React DOM 19.1.1                 # DOM rendering

UI Components:
├── Material-UI 7.2.0                # Component library
├── MUI Icons 7.2.0                  # Icon set
├── Emotion 11.14.0                  # CSS-in-JS styling
└── Material Design 3                # Design system

Development Tools:
├── React Scripts 5.0.1              # Build toolchain
├── Testing Library 16.3.0           # Testing utilities
└── Web Vitals 2.2.4                 # Performance metrics
```

### **Database & Infrastructure**
- **Database**: SQLite (development) with PostgreSQL compatibility
- **Session Storage**: Django sessions with Redis support
- **File Storage**: Local filesystem with configurable backends
- **Real-time**: WebSocket connections via Django Channels
- **Caching**: Redis-compatible caching layer
- **Deployment**: Production-ready with environment configuration

## 🚀 Getting Started

### **Prerequisites**
- **Python 3.10+** with uv package manager
- **Node.js 16+** with npm
- **Git** for version control

### **Backend Setup**
```bash
cd backend

# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
# OPENAI_API_KEY=your-openai-key
# GEMINI_API_KEY=your-gemini-key
# ANTHROPIC_API_KEY=your-claude-key

# Run database migrations
uv run python manage.py migrate

# Create superuser for admin access
uv run python manage.py createsuperuser

# Compile translations (Japanese support)
uv run python manage.py compilemessages

# Start development server
uv run python manage.py runserver
```

**Backend available at:** `http://localhost:8000`  
**Admin Interface:** `http://localhost:8000/admin`

### **Frontend Setup**
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

**Frontend available at:** `http://localhost:3000`

### **Environment Configuration**

Create `.env` in the backend directory:
```env
# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# LLM API Keys (at least one required)
OPENAI_API_KEY=sk-your-openai-key
GEMINI_API_KEY=AIza-your-gemini-key
ANTHROPIC_API_KEY=sk-ant-your-claude-key

# Database (optional - defaults to SQLite)
DATABASE_URL=sqlite:///db.sqlite3

# Redis (optional - for production caching)
REDIS_URL=redis://localhost:6379/0
```

## 📁 Project Architecture

```
ChatbotProject/
├── backend/                          # Django Backend
│   ├── analytics/                    # Analytics & Insights
│   │   ├── models.py                # Analytics data models
│   │   ├── langextract_service.py   # AI conversation analysis
│   │   └── api_views.py             # Analytics API endpoints
│   │
│   ├── authentication/              # User Management
│   │   ├── models.py                # User profiles & preferences
│   │   ├── session_models.py        # Session tracking
│   │   ├── session_admin.py         # Session management admin
│   │   └── middleware.py            # Session & timezone detection
│   │
│   ├── chat/                        # Core Chat System
│   │   ├── models.py                # Conversations & Messages
│   │   ├── llm_services.py          # Multi-LLM integration
│   │   ├── admin.py                 # Advanced admin interface
│   │   ├── consumers.py             # WebSocket handlers
│   │   └── services/                # Business logic services
│   │
│   ├── documents/                   # Document Management
│   │   ├── models.py                # Document models with UUID
│   │   ├── advanced_rag_service.py  # Hybrid search engine
│   │   ├── knowledge_base.py        # Document processing
│   │   └── admin.py                 # Document admin with progress
│   │
│   ├── core/                        # Shared Services
│   │   ├── services/                # Business logic
│   │   │   ├── automatic_analysis_service.py
│   │   │   ├── llm_admin_service.py
│   │   │   └── message_analysis_service.py
│   │   └── exceptions/              # Custom exceptions
│   │
│   ├── templates/admin/             # Custom Admin Templates
│   │   ├── documents/change_form.html  # Upload progress modal
│   │   ├── chat/llm_chat.html       # LLM chat interface
│   │   └── analytics/               # Analytics dashboards
│   │
│   ├── locale/ja/LC_MESSAGES/       # Japanese Translations
│   ├── static/admin/                # Admin static files
│   └── requirements.txt             # Python dependencies
│
├── frontend/                        # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginPage.tsx        # Authentication
│   │   │   └── ChatPage.tsx         # Main chat interface
│   │   ├── theme.ts                 # Material-UI Ocean Blue theme
│   │   └── App.tsx                  # Root component
│   ├── public/                      # Static assets
│   └── package.json                 # Node.js dependencies
│
└── README.md                        # This documentation
```

## 🔧 Core Features & Implementation

### **AI-Driven RAG Pipeline**
```python
# Advanced hybrid search implementation
def hybrid_search(query: str) -> List[DocumentChunk]:
    # 1. LLM intent analysis - enhance query terms
    enhanced_query = llm_service.analyze_intent(query)
    
    # 2. Vector similarity search (sentence-transformers)
    vector_results = faiss_index.search(enhanced_query)
    
    # 3. BM25 keyword matching
    bm25_results = bm25_index.search(enhanced_query)
    
    # 4. Hybrid scoring and reranking
    combined_results = rerank_results(vector_results, bm25_results)
    
    return combined_results
```

### **Real-time Analytics Processing**
```python
# LangExtract conversation analysis
def analyze_conversation(messages: List[Message]) -> AnalysisResult:
    # Extract sentiment, urgency, issues, customer intent
    analysis = langextract_service.analyze(messages)
    
    # Store structured insights
    analytics_summary = AnalyticsSummary.objects.create(
        conversation=conversation,
        sentiment=analysis.sentiment,
        satisfaction_level=analysis.satisfaction,
        issues_detected=analysis.issues,
        urgency_indicators=analysis.urgency
    )
    
    return analysis
```

### **Progressive File Upload System**
```javascript
// Real-time upload progress with controls
const uploadWithProgress = (file, onProgress, onCancel) => {
    const xhr = new XMLHttpRequest();
    
    xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
            const percentage = (e.loaded / e.total) * 100;
            const speed = calculateSpeed(e.loaded, startTime);
            onProgress({ percentage, speed, remaining: estimateTime(e) });
        }
    });
    
    return xhr; // Cancelable upload
};
```

### **Multilingual Admin Interface**
- **Complete Japanese Translation**: All admin interfaces, error messages, and UI elements
- **Professional Localization**: Context-aware translations with proper Japanese business terminology
- **Fuzzy Translation Handling**: Graceful fallback for partially translated content
- **Admin Menu Consistency**: Language-independent ordering using technical identifiers

### **Session Management & Analytics**
- **Real-time User Tracking**: Active sessions with device detection and timezone handling
- **Customer vs Admin Sessions**: Separate tracking for frontend users and admin users
- **Session Analytics**: Login patterns, device usage, geographic distribution
- **Automatic Cleanup**: Expired session management with configurable timeouts

## 🔐 Security & Production Features

### **Security Implementation**
- **UUID-based URLs**: Prevents enumeration attacks (`/documents/a4c9d8e2-...` instead of `/documents/1/`)
- **Content-based Deduplication**: SHA-256 hashing prevents duplicate uploads
- **File Validation**: Type, size, and content verification
- **Input Sanitization**: XSS and injection protection
- **Rate Limiting**: API abuse prevention
- **Secure Headers**: CSRF, CORS, and security middleware

### **Production Readiness**
- **Environment Configuration**: Separate dev/staging/production settings
- **Database Flexibility**: SQLite (dev) to PostgreSQL (production) migration path
- **Static File Handling**: Optimized for CDN deployment
- **Error Monitoring**: Comprehensive logging and error tracking
- **Performance Optimization**: Database query optimization and caching strategies

## 🌐 Internationalization (i18n)

### **Supported Languages**
- **English** (en): Primary language, complete coverage
- **Japanese** (ja): Full translation including admin interface, error messages, and business terminology

### **Translation Features**
- **Admin Interface**: Complete Japanese localization of Django admin
- **User Messages**: Multilingual conversation support
- **Error Handling**: Localized validation and error messages
- **Business Terms**: Industry-appropriate translations for technical terminology
- **Fuzzy Handling**: Graceful fallback for partial translations

### **Adding New Languages**
```bash
# Create translation files
uv run python manage.py makemessages -l es  # Spanish example

# Edit translations in locale/es/LC_MESSAGES/django.po

# Compile translations
uv run python manage.py compilemessages
```

## 📊 Analytics & Business Intelligence

### **Conversation Analytics**
- **Sentiment Analysis**: Real-time emotional tone detection
- **Issue Classification**: Automatic categorization of customer problems
- **Urgency Detection**: Priority scoring based on conversation content
- **Satisfaction Tracking**: Multi-level satisfaction scoring (1-10 scale)
- **Resolution Monitoring**: Track problem-to-solution patterns

### **Document Intelligence**
- **Usage Analytics**: Track which documents are most/least effective
- **Knowledge Gap Detection**: Identify missing information from user queries
- **Search Performance**: Monitor search quality and result relevance
- **Content Optimization**: Recommendations for document improvements

### **System Performance**
- **Response Time Tracking**: Monitor LLM and system response times
- **User Engagement**: Session duration, interaction patterns
- **Error Monitoring**: Track and categorize system errors
- **Capacity Planning**: Usage trends and resource utilization

## 🚦 Development Status

### **Completed Features** ✅
- [x] **Full-stack Implementation**: Django backend + React frontend
- [x] **Multi-LLM Integration**: OpenAI, Gemini, Claude support
- [x] **Advanced RAG System**: Vector + BM25 hybrid search with reranking
- [x] **Real-time Chat**: WebSocket-powered conversations
- [x] **Japanese Internationalization**: Complete admin and UI translation
- [x] **Document Management**: Upload, processing, and search with progress indicators
- [x] **Analytics Integration**: LangExtract-powered conversation analysis
- [x] **Security Implementation**: UUID URLs, content hashing, file validation
- [x] **Session Management**: Real-time user tracking with device detection
- [x] **Admin Interface**: Custom Django admin with analytics dashboards
- [x] **Background Processing**: Async analysis with progress tracking
- [x] **Vector Search**: Sentence transformers with FAISS indexing
- [x] **File Upload Progress**: Real-time indicators with cancel/minimize controls
- [x] **Message Analytics**: Response time and satisfaction tracking

### **Architecture Highlights**
- **Modern AI Stack**: Leverages latest LLM APIs and embedding models
- **Scalable Design**: Microservice-ready architecture with clear separation of concerns
- **Enterprise Ready**: Security, multilingual support, and admin tools built-in
- **Developer Friendly**: Comprehensive documentation and modular design
- **Production Tested**: Robust error handling and performance optimization

## 🔄 API Documentation

### **REST Endpoints**
```
Authentication:
POST /api/auth/login/          # User authentication
POST /api/auth/logout/         # Session termination

Chat:
GET  /api/chat/conversations/  # List conversations
POST /api/chat/send/          # Send message
GET  /api/chat/history/       # Conversation history

Documents:
POST /api/documents/upload/   # File upload with progress
GET  /api/documents/search/   # Hybrid search
GET  /api/documents/         # List documents

Analytics:
GET  /api/analytics/summary/  # Analytics dashboard data
POST /api/analytics/analyze/ # Trigger conversation analysis
```

### **WebSocket Connections**
```javascript
// Real-time chat connection
const chatSocket = new WebSocket('ws://localhost:8000/ws/chat/');

// Message handling
chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    // Handle real-time message updates
};
```

## 🤝 Contributing

### **Development Setup**
1. **Fork the repository** and clone locally
2. **Set up backend**: Follow backend setup instructions
3. **Set up frontend**: Follow frontend setup instructions
4. **Create feature branch**: `git checkout -b feature/your-feature`
5. **Test thoroughly**: Run all test suites
6. **Submit pull request**: With detailed description

### **Code Standards**
- **Backend**: Follow Django best practices and PEP 8
- **Frontend**: TypeScript strict mode, Material-UI guidelines
- **Testing**: Maintain test coverage above 80%
- **Documentation**: Update README and inline docs
- **Internationalization**: Add translations for new user-facing strings

---

**Powered by Django 5.2.4, React 19.1.1, and cutting-edge AI technologies**

*Built for enterprise-scale intelligent conversation analysis and document management*