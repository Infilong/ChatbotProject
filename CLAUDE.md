# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Multilingual GUI Support

**BEFORE WRITING ANY NEW CODE, ALWAYS CONSIDER MULTILINGUAL SUPPORT:**

🌍 **All user interface components MUST support multiple languages from the start**
- Use Django's `gettext_lazy as _` for all user-facing text
- Frontend components should use i18n libraries (React i18next recommended)
- Never hardcode English text in user interfaces
- All admin interfaces must use custom display methods with translated labels
- Database models should have verbose_name with translations
- Form labels, error messages, and help text must be translatable

**Translation Implementation Requirements:**
- Backend: Use `from django.utils.translation import gettext_lazy as _` 
- Frontend: Implement React i18next for component translations
- Admin interfaces: Create custom display methods with `short_description = _('Translation')`
- All user-facing strings wrapped with `_('Text')`
- Maintain Japanese translations in `backend/locale/ja/LC_MESSAGES/django.po`

## Common Development Tasks

### Frontend Development
Navigate to the `frontend/` directory for all React TypeScript development:

```bash
cd frontend
npm install
npm start      # Development server at http://localhost:3000
npm test       # Run tests in watch mode
npm run build  # Production build
```

### Backend Development
Navigate to the `backend/` directory for Django development with uv python:

```bash
cd backend
uv venv                    # Create virtual environment
uv pip install -r requirements.txt  # Install dependencies
uv run python manage.py runserver   # Start Django server at http://localhost:8000
uv run python manage.py migrate     # Run database migrations
uv run python manage.py test        # Run backend tests
```

### Project Architecture

**Frontend Structure (React + TypeScript)**
- **Main App**: `frontend/src/App.tsx` - Root component handling authentication state and routing
- **Authentication**: Session management via localStorage with `chatSession` key
- **Components**: 
  - `LoginPage.tsx` - Authentication interface with demo credentials (admin/password)
  - `ChatPage.tsx` - Main chat interface with message handling, file uploads, emoji picker, and feedback system
- **Theme**: Material UI theme in `frontend/src/theme.ts` with Ocean Blue color scheme (#006A6B primary, #0288D1 secondary)
- **State Management**: React useState with localStorage persistence for messages and session data

**Backend Structure**
- Django REST API with PostgreSQL database (architecture planned)
- LangExtract integration for conversation analysis
- WebSocket support via Django Channels for real-time communication
- Backend directory ready for implementation

**Message System**
- Messages stored in localStorage under `chatMessages` key
- Message interface includes: id, text, sender, timestamp, optional feedback, optional file attachment
- Simulated bot responses for demo purposes

**Styling & Design**
- Material Design 3 principles
- Ocean Blue theme (#0288D1, #1565C0)
- Responsive design optimized for mobile and desktop
- Clean, flat design with subtle shadows and rounded corners

## Project Vision: Intelligent Chatbot Analysis System

**Background**: Building an intelligent system for DataPro Solutions to automate customer interactions while extracting strategic insights from conversation data.

**Core Objectives**:
1. **Intelligent Chatbot** with natural conversation capabilities and learning functions
2. **Customer Insight Analysis System** for real-time issue extraction and sentiment analysis

**Planned Tech Stack**:
- **Frontend**: React + TypeScript (current implementation)
- **Backend**: Django REST API with uv python environment
- **Database**: PostgreSQL with Django ORM
- **Communication**: Django REST Framework + Django Channels (WebSockets)
- **LLM APIs**: OpenAI, Gemini, Claude for conversation analysis and insights
- **Data Analysis**: Google LangExtract for structured conversation insights

**Development Phases**:

**Phase 1: Frontend Foundation** ✅
- React TypeScript setup with Material UI
- Authentication and chat interface
- Message handling with file attachments and feedback

**Phase 2: Backend & API Integration** (Next)
- Django REST API setup with uv python environment
- PostgreSQL database with Django models for users, conversations, messages
- Django REST Framework for standard API endpoints
- Django Channels for WebSocket real-time communication
- OpenAI/Gemini/Claude API integration for intelligent responses
- Google LangExtract integration for conversation analysis

**Phase 3: Intelligent Analysis**
- Real-time conversation analysis using LangExtract
- Sentiment analysis and urgency detection with precise source grounding
- Issue categorization and customer need extraction
- Learning from conversation patterns and user feedback
- Satisfaction level scoring with contextual references

**Phase 4: Admin Analytics & Document Management**
- Django Admin dashboard with Twitter-style analytics and visualizations
- Document management system for knowledge base
- Business intelligence reporting with LangExtract insights
- Proactive solution recommendations based on conversation patterns

## Development Notes

**Current State (Phase 1)**
- Demo authentication accepts any username/password combination
- Session persists in localStorage until logout
- Logout clears all related localStorage data (session, messages, feedback counts)
- Simulated bot responses for demo purposes

**Message Features**
- Real-time message display with timestamps
- File attachment support (.jpg, .png, .pdf, .docx, etc.)
- Emoji picker with predefined emoji set
- Thumbs up/down feedback system for bot messages
- Auto-scroll to latest messages

**Planned Integration Points**
- Django backend with user authentication and session management
- LLM API integration (OpenAI, Gemini, Claude) for intelligent responses
- LangExtract conversation analysis pipeline for structured insight extraction
- WebSocket support for real-time communication
- Analytics dashboard for customer insights and business intelligence

## LangExtract Integration for User Data Analysis

**Key Capabilities for Admin Analytics:**

1. **Conversation Intelligence**
   - Extract structured insights from unstructured chat conversations
   - Sentiment analysis with precise source grounding (maps to exact conversation locations)
   - Issue categorization and urgency detection
   - Customer satisfaction indicators with contextual references

2. **Administrative Dashboard Features**
   - User intent classification across conversation history
   - Problem pattern recognition and trending
   - Satisfaction level scoring (1-10 scale) with drill-down capabilities
   - Pain point identification with exact conversation highlights

3. **Data Extraction Schema**
   ```python
   conversation_analysis = {
       "sentiment": "positive/negative/neutral",
       "satisfaction_level": "1-10 scale",
       "issues_raised": ["categorized problems"],
       "urgency_indicators": ["urgent phrases with source"],
       "resolution_status": "resolved/pending/escalated",
       "customer_intent": "support/inquiry/complaint",
       "key_insights": ["actionable business intelligence"]
   }
   ```

**Implementation Strategy:**
- Use LangExtract's precise source grounding for admin verification
- Generate interactive HTML visualizations of conversation analysis
- Support multiple LLM models (Gemini, OpenAI) for cross-validation
- Process long conversation histories through parallel processing
- Enable multiple extraction passes for higher insight recall

**Requirements:**
- Python 3.10+ with uv environment
- API keys for cloud LLM models (Gemini/OpenAI)
- PostgreSQL database setup
- Integration with Django models for conversation storage

## Database & Communication Architecture

### PostgreSQL Database
- JSON/JSONB support for LangExtract analysis results and message metadata
- Full-text search capabilities for conversation history and admin filtering
- Scalable design for large conversation datasets
- Advanced Django field types (ArrayField, JSONField)

### Frontend-Backend Communication
**Django REST Framework (DRF):**
- RESTful APIs for authentication, user management, conversation history
- Analytics data retrieval for admin dashboard
- Standard CRUD operations

**Django Channels + WebSockets:**
- Real-time chat communication
- Live message delivery without polling
- Real-time analytics updates for admin dashboard
- Scalable concurrent session handling

**Frontend Integration:**
- Axios for REST API calls
- WebSocket API for real-time features
- React Query for API state management and caching

## Environment Variables & Configuration

### Backend Environment Variables (.env)
- `DATABASE_URL`: PostgreSQL connection string
- `DJANGO_SECRET_KEY`: Django application secret key
- `OPENAI_API_KEY`: OpenAI API key for LLM integration
- `GEMINI_API_KEY`: Google Gemini API key
- `CLAUDE_API_KEY`: Anthropic Claude API key
- `DEBUG`: Django debug mode (True/False)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `CORS_ALLOWED_ORIGINS`: Frontend URL for CORS

### Frontend Environment Variables (.env)
- `REACT_APP_API_URL`: Backend API base URL
- `REACT_APP_WS_URL`: WebSocket server URL

## Security & Authentication

### Authentication Strategy
- JWT tokens for API authentication
- Session management via Django sessions
- Secure HttpOnly cookies for token storage
- Token refresh mechanism for extended sessions

### Security Configuration
- CORS setup for frontend-backend communication
- Rate limiting on API endpoints (especially LLM calls)
- Input validation and sanitization
- File upload security (type validation, size limits)
- HTTPS enforcement in production

### Data Protection
- Conversation data encryption at rest
- Secure API key management
- User data privacy compliance
- Audit logging for admin actions

## Testing Strategy

### Backend Testing
- Unit tests for Django models and serializers
- API endpoint testing with Django REST framework
- LangExtract integration testing with mock responses
- WebSocket connection testing
- Database performance testing

### Frontend Testing
- React component unit tests with Jest and React Testing Library
- Integration tests for chat functionality
- End-to-end testing with Cypress
- WebSocket connection testing
- Mobile responsiveness testing

### API Testing
- Automated API testing with Postman/Newman
- Load testing for concurrent users
- LLM API integration testing with rate limiting
- Error handling and edge case testing

## Deployment & Production

### Development Environment
- Docker Compose for local development
- PostgreSQL container for database
- Redis container for Django Channels (WebSocket scaling)
- Hot reloading for both frontend and backend

### Production Considerations
- Docker containerization for backend and frontend
- Nginx reverse proxy for static files and load balancing
- PostgreSQL with connection pooling
- Redis for WebSocket scaling and caching
- Environment-specific configuration management
- Automated backup strategy for conversation data
- Monitoring and logging setup (Django logging, frontend error tracking)

### Scaling Strategy
- Horizontal scaling for Django backend
- CDN for static assets
- Database read replicas for analytics queries
- Message queue for background LangExtract processing
- Load balancer for WebSocket connections

## Django Admin Analytics & Document Management

### Analytics Dashboard (Twitter-Style Visualizations)

**Key Metrics & Graphs:**
- Daily/Weekly/Monthly chat volume trends (line charts)
- User satisfaction score trends with sentiment color coding (area charts)
- Response time analytics and performance metrics (bar charts)
- Peak usage hours and user activity heatmaps
- Bot vs human escalation rates (pie charts)

**LangExtract-Powered Insights:**
- Issue categories trending over time (stacked bar charts)
- Sentiment distribution analysis (multi-line charts)
- Customer intent classification breakdown (donut charts)
- Problem resolution rate tracking (progress indicators)
- User engagement scoring (gauge charts)
- Real-time conversation analytics feed

**Document Analytics:**
- Most referenced documents performance (horizontal bar charts)
- Document effectiveness scoring based on user satisfaction
- Knowledge gap detection from unanswered questions
- User question topic analysis and trending
- Document usage patterns and optimization suggestions

### Document Management System

**Knowledge Base Features:**
- Upload and categorize company documents (PDFs, Word docs, etc.)
- Auto-extract text content for AI search and retrieval
- Document versioning and approval workflow
- Enable/disable documents for AI responses
- Track document usage and effectiveness metrics

**AI Integration:**
- Document search integration with LLM responses
- Context-aware answers based on company knowledge base
- Automatic identification of documentation gaps from user questions
- Continuous improvement suggestions based on LangExtract analysis

**Admin Interface Enhancements:**
- Custom Django admin pages for analytics visualization
- Interactive charts using Chart.js or Plotly integration
- Export functionality for business reporting
- Real-time dashboard updates via WebSocket connections
- Mobile-responsive admin interface for on-the-go monitoring

**Required Packages:**
- django-admin-charts for embedding interactive graphs
- django-plotly-dash for advanced data visualizations
- django-admin-interface for modern UI themes
- django-import-export for data export capabilities

## Django Admin Translation Strategy

**Critical: All admin interfaces must be fully translatable**

**Problem:** Django admin displays field names (not verbose_name) as column headers when model fields are used directly in `list_display`.

**Solution:** Always use custom display methods with Japanese `short_description` labels:

```python
# ❌ Wrong - displays English field names
list_display = ['name', 'category', 'created_at', 'is_active']

# ✅ Correct - uses custom display methods with translations
list_display = ['name_display', 'category_display', 'created_at_display', 'is_active_display']

def name_display(self, obj):
    return obj.name
name_display.short_description = _('Name')
name_display.admin_order_field = 'name'

def is_active_display(self, obj):
    return obj.is_active
is_active_display.short_description = _('Is Active')
is_active_display.admin_order_field = 'is_active'
is_active_display.boolean = True  # For boolean fields
```

**Translation Workflow:**
1. Create custom display methods for all `list_display` fields
2. Add `short_description = _('Japanese Translation')` to each method
3. Maintain sorting with `admin_order_field = 'field_name'`
4. Use `.boolean = True` for boolean field display
5. Update translations in `backend/locale/ja/LC_MESSAGES/django.po`
6. Run `uv run python manage.py compilemessages` to compile translations