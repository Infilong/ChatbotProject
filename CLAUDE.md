# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Backend vs Frontend Architecture Understanding

**VERY IMPORTANT - Admin Chat vs Frontend Chat Separation:**

🔥 **Backend Admin Chat Interface (`/admin/llm/chat/`):**
- This is Django templates + JavaScript running in the backend admin panel
- Has its own separate conversation history stored in Django sessions
- Used by admin staff to test the chatbot and analyze system data
- Completely independent from the React frontend
- Users: Admin staff members (admin, staff users)

🔥 **Frontend React Chat Interface:**  
- This is the React TypeScript frontend at `http://localhost:3000`
- Has its own conversation history stored in Conversation/Message database models
- Used by end customers to chat with the bot
- Users: End customers (demo_user, etc.)

**KEY MISTAKE TO AVOID:**
- The admin chat history has NOTHING to do with the frontend React chat history
- Database conversations from demo_user are from React frontend, not admin interface
- When admin chat was working before, it used Django sessions, not database models
- Never mix or combine these two separate chat systems

**Architecture:**
```
Backend Admin Chat (/admin/llm/chat/) → Django Sessions → Admin staff testing
React Frontend Chat (localhost:3000) → Database Models → Customer conversations
```

**Remember:** When working on admin chat issues, focus on Django sessions and admin users, NOT on React frontend or demo_user database conversations.

## CRITICAL: AI-Driven RAG System Architecture

**ALWAYS USE THE PROPER LLM-DRIVEN WORKFLOW - NEVER PRIMITIVE PATTERN MATCHING:**

### **Required AI-Driven RAG Flow:**

```
User Input → LLM Intent Analysis → Vector/RAG Search → LLM Response Generation → Frontend
```

## CRITICAL: Learning from Implementation Mistakes 

**Why it took so long to implement the proper AI-driven RAG system - Lessons learned:**

### **❌ Major Mistakes That Caused Delays:**

1. **Defaulting to Primitive Solutions First:**
   - **MISTAKE**: Immediately reaching for simple pattern matching instead of proper AI-driven approaches
   - **WHY THIS HAPPENED**: Default to "easy" solutions without considering the user's explicit requirements for advanced AI systems
   - **COST**: Wasted multiple implementation cycles before getting to the right solution
   - **LESSON**: When user asks for "RAG and vector and latest tech", implement proper vector embeddings from the start

2. **Not Reading User Requirements Carefully:**
   - **MISTAKE**: User explicitly said "we use rag and vector and some latest tech to get the meaning" but I kept implementing primitive keyword matching
   - **WHY THIS HAPPENED**: Focused on getting "something working" instead of the specified architecture
   - **COST**: User had to repeatedly explain that they wanted proper AI-driven workflow
   - **LESSON**: Read and understand the full scope of requirements before starting implementation

3. **Underestimating the Complexity of Modern RAG:**
   - **MISTAKE**: Thinking hybrid search meant simple keyword + basic similarity instead of proper vector embeddings + BM25 + semantic reranking
   - **WHY THIS HAPPENED**: Not researching 2024-2025 RAG best practices upfront
   - **COST**: Multiple failed attempts with insufficient search quality
   - **LESSON**: Research current best practices BEFORE implementing, not during debugging

4. **Missing Package Dependencies:**
   - **MISTAKE**: Trying to implement vector search without installing `sentence-transformers`, `rank-bm25`, `faiss-cpu`, `torch`
   - **WHY THIS HAPPENED**: Assumed packages would be available or tried to work around missing dependencies
   - **COST**: System couldn't work properly, requiring multiple debugging sessions
   - **LESSON**: Install ALL required dependencies for the intended architecture upfront

5. **Ignoring User Feedback About Quality:**
   - **MISTAKE**: When user said "the hybrid search doesn't work well, terrible", I tried minor fixes instead of fundamental architecture changes
   - **WHY THIS HAPPENED**: Defensive about existing implementation rather than listening to quality feedback
   - **COST**: Continued with broken approach instead of implementing proper solution
   - **LESSON**: When user reports poor quality, the architecture is likely wrong, not just the implementation details

6. **Overcomplicating Simple Intent Analysis:**
   - **MISTAKE**: Creating complex LLM prompts that triggered Gemini safety filters instead of simple, focused intent extraction
   - **WHY THIS HAPPENED**: Overthinking the prompt design instead of using minimal, reliable approaches
   - **COST**: System failures due to safety filter issues and timeout problems
   - **LESSON**: Use simple, focused LLM prompts for intent analysis - just extract keywords, nothing complex

### **✅ What Should Have Been Done from the Start:**

1. **Proper Requirements Analysis:**
   - User said "universal LLM system" → Should have immediately planned industry-agnostic architecture
   - User mentioned "rag and vector and latest tech" → Should have researched 2024-2025 RAG best practices
   - User wanted "any industry can use it" → Should have made semantic mappings configurable

2. **Correct Technical Implementation Order:**
   ```
   1. Research current RAG best practices (Anthropic contextual retrieval, hybrid search)
   2. Install ALL required packages (sentence-transformers, rank-bm25, faiss-cpu, torch)
   3. Implement vector embeddings with proven models (all-MiniLM-L6-v2)
   4. Build hybrid search (BM25 + Vector + Semantic reranking)
   5. Create simple LLM intent analysis (focused prompts, fallback patterns)
   6. Test end-to-end workflow before claiming completion
   ```

3. **Quality-First Mindset:**
   - Test with actual user queries before marking as "working"
   - Don't accept partial matches when full document content exists
   - Implement proper chunk extraction that preserves complete answers
   - Validate that query variations ("what tech do you use" vs "technologies you use") work equally well

### **🔄 Process Improvements for Future:**

1. **Always Ask: "What's the Modern Best Practice?"**
   - Don't assume 2022-era approaches are still optimal
   - Research latest papers and implementations (Anthropic's contextual retrieval, advanced chunking)
   - Start with proper architecture, not "quick wins"

2. **Install Dependencies FIRST:**
   - When planning vector search, install vector packages immediately
   - Don't try to work around missing dependencies with primitive alternatives
   - Check requirements.txt and install everything needed for the planned architecture

3. **Listen to Quality Feedback Immediately:**
   - If user says "terrible" or "doesn't work well", the ARCHITECTURE is wrong
   - Don't debug implementation details when architecture is fundamentally insufficient
   - Implement proper solution instead of incremental fixes to broken approach

4. **Test Real User Queries:**
   - Test exact queries user mentioned: "What technologies do you primarily use", "what tech do you use"
   - Verify that variations and synonyms work equally well
   - Ensure complete answers are extracted, not partial snippets

### **🎯 Success Pattern for Future RAG Implementations:**

```
1. User Request Analysis → Identify modern AI architecture requirements
2. Research Best Practices → Find 2024-2025 papers and implementations  
3. Install Dependencies → All packages needed for proper implementation
4. Implement Core Architecture → Vector embeddings + Hybrid search + LLM integration
5. Test with Real Queries → User's actual questions, variations, edge cases
6. Verify Quality → Complete answers, not partial matches
7. Document Architecture → Ensure no regression to primitive approaches
```

**Remember: The user explicitly told me they wanted proper AI-driven RAG, not primitive pattern matching. I should have implemented that from the beginning instead of requiring multiple cycles of feedback to get to the right solution.**

**Implementation Details:**

1. **🧠 LLM Intent Analysis** (`chat/llm_services.py::_analyze_user_intent`):
   - User query → LLM semantic understanding → Enhanced search terms
   - Example: "what tech do you use" → "what tech do you use technology technologies tools platforms software stack frameworks systems"
   - **NEVER use primitive pattern matching as primary method**

2. **🔍 Vector/RAG Search** (`documents/advanced_rag_service.py`):
   - Enhanced query → Vector embeddings (`all-MiniLM-L6-v2`) → Semantic similarity search
   - Hybrid search: Vector embeddings + BM25 keyword matching + Contextual chunking
   - **Required packages**: `sentence-transformers`, `rank-bm25`, `faiss-cpu`, `torch`

3. **📄 Knowledge Retrieval** (`documents/knowledge_base.py`):
   - Vector search results → Document chunking → Q&A extraction → Context formatting
   - Semantic reranking for improved precision

4. **💬 LLM Response Generation** (`chat/llm_services.py::generate_chat_response`):
   - Retrieved context + User query → LLM → Natural language response
   - Context-aware, accurate answers based on document knowledge

### **🚫 What NOT to Do:**
- **Pattern-based intent analysis as primary method** (only as fallback)
- **Simple keyword matching without LLM understanding**
- **Direct document search without semantic enhancement**
- **Missing any step in the AI-driven pipeline**

### **✅ Success Metrics:**
- Vector embeddings working: `INFO Built vector index with X embeddings`
- Semantic search active: `INFO Vector search returned X results`
- LLM intent analysis: `INFO Intent analysis (LLM-based): 'query' → 'enhanced_terms'`
- Quality responses with specific details from documents

## CRITICAL: Code Maintainability Standards

**ALWAYS FOLLOW ENTERPRISE-LEVEL CODING PRACTICES:**

🏢 **Follow Google's Coding Standards and Top Company Best Practices**
- Write clean, maintainable, and scalable code that can be easily understood by other developers
- Follow SOLID principles, DRY (Don't Repeat Yourself), and KISS (Keep It Simple, Stupid)
- Prioritize code readability, proper documentation, and consistent naming conventions
- Structure code to be testable, modular, and loosely coupled

### **🔧 Django Backend Architecture Standards**

**File Organization & Structure:**
```
backend/
├── apps/                     # Django apps organized by domain
│   ├── authentication/       # User auth and profiles
│   ├── chat/                # Chat and LLM functionality  
│   ├── documents/           # Document management
│   └── analytics/           # Analytics and reporting
├── core/                    # Shared utilities and base classes
│   ├── models.py           # Abstract base models
│   ├── utils.py            # Shared utility functions
│   ├── exceptions.py       # Custom exception classes
│   └── validators.py       # Custom validators
├── config/                 # Project configuration
│   ├── settings/           # Split settings by environment
│   │   ├── base.py        # Base settings
│   │   ├── development.py # Development settings
│   │   └── production.py  # Production settings
│   ├── urls.py            # Root URL configuration
│   └── wsgi.py            # WSGI configuration
└── tests/                  # Centralized test directory
    ├── factories/          # Model factories for testing
    ├── integration/        # Integration tests
    └── unit/              # Unit tests by app
```

**Code Quality Requirements:**

✅ **Function and Class Design:**
- **Single Responsibility**: Each function/class should have one clear purpose
- **Max 20-25 lines per function** (Google standard)
- **Descriptive names**: `calculate_user_subscription_fee()` not `calc_fee()`
- **Type hints**: Always use Python type hints for function parameters and return types
- **Docstrings**: Google-style docstrings for all public methods

✅ **Django Model Standards:**
```python
class UserProfile(models.Model):
    """User profile information and preferences.
    
    This model extends Django's User model with additional
    user-specific data and preferences.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        help_text=_("Associated Django user account")
    )
    
    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        db_table = 'user_profiles'  # Explicit table naming
        
    def __str__(self) -> str:
        return f"Profile for {self.user.username}"
    
    def get_absolute_url(self) -> str:
        """Return the canonical URL for this profile."""
        return reverse('profile:detail', kwargs={'pk': self.pk})
```

✅ **View Organization:**
- **Class-based views preferred** for complex logic
- **Function-based views** only for simple, single-purpose operations
- **Separate concerns**: Authentication, validation, business logic, presentation
- **Use mixins** for shared functionality across views

✅ **Service Layer Pattern:**
```python
# services/chat_service.py
class ChatService:
    """Service layer for chat operations."""
    
    @staticmethod
    def create_conversation(user: User, title: str) -> Conversation:
        """Create a new conversation for the given user."""
        pass
    
    @staticmethod  
    def send_message(conversation: Conversation, content: str) -> Message:
        """Send a message in the conversation."""
        pass
```

✅ **Error Handling Hierarchy:**
```python
# core/exceptions.py
class ChatbotBaseException(Exception):
    """Base exception for all chatbot-related errors."""
    pass

class LLMServiceException(ChatbotBaseException):
    """Exception raised when LLM service fails."""
    pass

class DocumentProcessingException(ChatbotBaseException):
    """Exception raised during document processing."""
    pass
```

**File Size and Complexity Limits:**
- **Max 300 lines per Python file** (excluding tests)
- **Split large models/views** into multiple files using Django's app structure
- **Extract complex business logic** into separate service classes
- **Use managers and querysets** for complex database operations

**Testing Requirements:**
- **Minimum 80% test coverage** for all new code
- **Unit tests** for all service methods and model methods
- **Integration tests** for API endpoints and user workflows
- **Factory classes** for test data generation instead of fixtures

### **🎨 Frontend Architecture Standards**

**React Component Organization:**
```
frontend/src/
├── components/           # Reusable UI components
│   ├── common/          # Generic components (Button, Modal, etc.)
│   ├── forms/           # Form-specific components
│   └── layout/          # Layout components (Header, Sidebar)
├── pages/               # Page-level components
├── hooks/               # Custom React hooks
├── services/            # API service functions
├── utils/               # Utility functions
├── types/               # TypeScript type definitions
└── constants/           # Application constants
```

**Component Standards:**
- **Max 150 lines per component** (excluding styles)
- **Single responsibility** - one component, one purpose
- **Props interfaces** with clear TypeScript definitions
- **Custom hooks** for shared stateful logic
- **Meaningful component names** that describe their purpose

### **📚 Documentation Requirements**

**Code Documentation:**
- **README.md** for each major component/app explaining its purpose
- **Inline comments** for complex business logic only
- **API documentation** using Django REST framework's built-in tools
- **Architecture Decision Records (ADRs)** for significant design decisions

**Git Commit Standards:**
- **Conventional commits** format: `feat:`, `fix:`, `refactor:`, etc.
- **Clear, descriptive messages** explaining the "why" not just "what"
- **Small, focused commits** that can be easily reviewed and reverted

### **⚡ Performance Standards**

**Database Optimization:**
- **Always use select_related/prefetch_related** to avoid N+1 queries
- **Database indexes** on frequently queried fields
- **Pagination** for all list views
- **Query optimization** - avoid unnecessary database hits

**Caching Strategy:**
- **Redis caching** for expensive operations
- **Template fragment caching** for dynamic content
- **API response caching** for frequently accessed data

### **🔒 Security Standards**

**Django Security:**
- **Never bypass Django's security features** without extensive documentation
- **Input validation and sanitization** at multiple layers
- **HTTPS enforcement** in production
- **Secret management** using environment variables or secure vaults
- **SQL injection prevention** through ORM usage

**Code Review Requirements:**
- **All code must be reviewed** before merging to main branch
- **Security review** for any authentication or authorization changes
- **Performance review** for database-heavy operations

This ensures the codebase remains maintainable, scalable, and follows industry best practices used by top technology companies.

---

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

## CRITICAL: User-Friendly Error Handling

**NEVER SHOW DJANGO ERROR PAGES TO USERS - ALWAYS USE FRIENDLY NOTIFICATIONS:**

❌ **AVOID Django Error Pages:**
- Never let ValidationError exceptions reach users with scary stack traces
- Never show technical Django error pages for user mistakes
- Never display raw exception messages to end users

✅ **ALWAYS Use User-Friendly Notifications:**
- **Form-level validation**: Handle validation in custom form `clean_*()` methods
- **Admin messages**: Use Django's `messages.error()`, `messages.warning()`, `messages.success()`
- **Custom error handling**: Create graceful error responses that keep users on the same page
- **Pop-up notifications**: Use JavaScript modals or toast notifications for immediate feedback
- **Inline field errors**: Show validation errors directly next to form fields

**Implementation Pattern:**
```python
# ❌ Wrong - Model validation that creates scary error pages
def save(self, *args, **kwargs):
    if some_condition:
        raise ValidationError("Scary technical error!")

# ✅ Correct - Form validation with friendly messages  
class MyAdminForm(forms.ModelForm):
    def clean_field_name(self):
        value = self.cleaned_data.get('field_name')
        if some_condition:
            raise ValidationError(
                _('Friendly message explaining what to do instead.')
            )
        return value

# ✅ Correct - View-level error handling with messages
def my_view(request):
    try:
        # Some operation
        pass
    except SomeException:
        messages.error(request, _('Something went wrong. Please try again.'))
        return redirect('back_to_form')
```

**Error Message Guidelines:**
- **Be specific**: Explain exactly what went wrong
- **Be helpful**: Tell users what they can do to fix it
- **Be multilingual**: All error messages must support Japanese translation
- **Be positive**: Focus on solutions, not problems
- **Stay in context**: Keep users on the same form/page when possible

**Examples of Good Error Messages:**
- ❌ "ValidationError: Duplicate file hash detected"
- ✅ "A file with identical content already exists: 'document.pdf'. Please choose a different file or update the existing document instead."

**Frontend Error Handling:**
- Use toast notifications for temporary messages
- Use modal dialogs for important warnings
- Use inline validation for form errors
- Always provide clear actions users can take

## CRITICAL: Backend Code Standards

**NO EMOJIS OR NON-UNICODE CHARACTERS IN BACKEND CODE:**

❌ **STRICTLY FORBIDDEN in Django backend code:**
- Emojis in templates, admin interfaces, or Python code (robot, chart, lock icons, etc.)
- Special Unicode characters that may cause encoding issues
- Non-ASCII characters in user interface elements
- Emojis in admin action descriptions, success messages, or any user-facing text
- Decorative characters in Django admin interfaces

✅ **ALWAYS Use Standard ASCII Text:**
- Plain text labels for admin interfaces
- Standard Unicode-safe characters only
- Professional, clean presentation without decorative characters
- Focus on functionality over visual styling with characters
- Clean, professional admin action names and messages

```

**Django Admin Standards:**
- All admin action descriptions must be plain text
- Success/error messages must be professional without emojis
- Use Django's translation system with _() for all user-facing text
- Admin interfaces should be clean and professional

**Rationale:**
- Ensures consistent encoding across different systems
- Maintains professional appearance in admin interfaces
- Prevents potential Unicode-related issues in databases and templates
- Keeps focus on functionality rather than decoration
- Professional business software appearance

## CRITICAL: Testing and Management Commands Unicode Standards

**NO EMOJIS OR SPECIAL UNICODE CHARACTERS IN TESTS AND MANAGEMENT COMMANDS:**

❌ **STRICTLY FORBIDDEN in tests, management commands, and debug output:**
- Emojis in print statements, test output, or management command messages (🔍, ✅, ❌, 📊, etc.)
- Special Unicode characters that cause encoding errors on Windows
- Non-ASCII characters in console output or command-line tools
- Decorative Unicode symbols in test descriptions or command help text

✅ **ALWAYS Use Standard ASCII Text:**
- Plain text for all console output and command messages
- Standard ASCII characters for test assertions and descriptions
- Professional text-only output for management commands
- Clean, readable console messages without decorative characters

```

**Testing Standards:**
- All test output must use ASCII-only characters
- Management command help text must be emoji-free
- Console logging should avoid Unicode symbols
- Error messages in tests should be plain text

**Rationale:**
- Prevents UnicodeEncodeError on Windows systems with 'gbk' codec
- Ensures compatibility across different terminal environments
- Maintains consistent behavior in CI/CD pipelines
- Avoids console encoding issues in production deployments
- Professional appearance in enterprise environments

## CRITICAL: Security Best Practices

**ALWAYS IMPLEMENT SECURITY-FIRST DESIGN IN BACKEND SYSTEMS:**

### 🔒 **URL Security & Resource Access**

❌ **NEVER Use Sequential/Predictable URLs:**
- `/api/documents/1/`, `/api/documents/2/` - Predictable enumeration
- `/admin/files/download/123/` - Easy to guess other files
- `/user/profile/456/` - Exposes user IDs and allows enumeration attacks

✅ **ALWAYS Use Secure, Non-Enumerable Identifiers:**
- **UUIDs**: `/api/documents/a4c9d8e2-1234-5678-9abc-def123456789/`
- **Hash-based IDs**: `/files/download/7f8e9d2c1b0a/`
- **Slug + UUID**: `/documents/my-document-a4c9d8e2/`
- **Signed URLs**: `/secure/file/abc123?signature=xyz789&expires=1234567890`

### 🛡️ **Data Integrity & Duplication Prevention**

❌ **NEVER Rely Only on Filenames or Surface-Level Checks:**
```python
# Wrong - only checking filename
if Document.objects.filter(name=uploaded_file.name).exists():
    raise ValidationError("File already exists")
```

✅ **ALWAYS Use Content-Based Validation:**
```python
# Correct - checking actual file content with SHA-256 hash
file_hash = calculate_file_hash(uploaded_file)
if Document.objects.filter(file_hash=file_hash).exists():
    raise ValidationError("Identical file content already exists")
```

### 🔐 **Access Control & Authorization**

**Implementation Requirements:**
- **UUID-based URLs**: Use `models.UUIDField(default=uuid.uuid4)` for all public resource identifiers
- **Content hashing**: SHA-256 hash validation for file deduplication and integrity
- **Permission checks**: Always verify user permissions before resource access
- **Rate limiting**: Implement rate limiting on sensitive endpoints
- **Input validation**: Validate and sanitize all user inputs
- **File validation**: Check file types, sizes, and content before processing

### 🚫 **Common Security Anti-Patterns to AVOID:**

1. **Sequential ID Exposure:**
   ```python
   # ❌ Wrong - Exposes database IDs
   class Document(models.Model):
       # Uses default auto-increment ID - security risk
   
   # URLs become: /documents/1/, /documents/2/, etc.
   ```

2. **Filename-Only Duplicate Detection:**
   ```python
   # ❌ Wrong - Can be bypassed by renaming files  
   if os.path.exists(f"uploads/{filename}"):
       return "File exists"
   ```

3. **Predictable Resource URLs:**
   ```python
   # ❌ Wrong - Easy enumeration attack
   path('download/<int:file_id>/', download_view)
   ```

### ✅ **Security-First Implementation Pattern:**

```python
class Document(models.Model):
    # Secure: UUID for public URLs
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Secure: Content-based duplicate detection
    file_hash = models.CharField(max_length=64, db_index=True, editable=False)
    
    def save(self, *args, **kwargs):
        if self.file and not self.file_hash:
            # Generate hash from actual file content
            self.file_hash = calculate_file_hash(self.file)
        super().save(*args, **kwargs)

# Secure URL patterns using UUID
urlpatterns = [
    path('download/<uuid:document_uuid>/', download_view, name='download'),
    path('preview/<uuid:document_uuid>/', preview_view, name='preview'),
]

def download_view(request, document_uuid):
    # Secure: Get by UUID, check permissions
    document = get_object_or_404(Document, uuid=document_uuid)
    
    # Always verify access permissions
    if not request.user.has_perm('documents.view_document', document):
        raise PermissionDenied("Access denied")
    
    return serve_file(document.file)
```

### 🔧 **Admin Interface Security Implementation:**

**CRITICAL**: Django admin URLs must also use UUIDs instead of sequential IDs to prevent enumeration attacks.

```python
# Secure Django Admin with UUID-based URLs
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    # Override get_object to handle UUID lookup
    def get_object(self, request, object_id, from_field=None):
        try:
            # Parse as UUID first
            uuid_obj = uuid.UUID(object_id)
            return self.get_queryset(request).get(uuid=uuid_obj)
        except (ValueError, TypeError):
            # Fallback to PK for backward compatibility
            try:
                return self.get_queryset(request).get(pk=object_id)
            except (ValueError, Document.DoesNotExist):
                return None
        except Document.DoesNotExist:
            return None
    
    def get_urls(self):
        urls = super().get_urls()
        # Override default admin URLs with UUID-based ones
        custom_urls = [
            path('<uuid:object_id>/change/', self.admin_site.admin_view(self.change_view), 
                 name='documents_document_change'),
            path('<uuid:object_id>/delete/', self.admin_site.admin_view(self.delete_view), 
                 name='documents_document_delete'),
            path('<uuid:object_id>/history/', self.admin_site.admin_view(self.history_view), 
                 name='documents_document_history'),
        ]
        return custom_urls + urls
    
    def response_change(self, request, obj):
        """Redirect to UUID-based URLs after form submission"""
        response = super().response_change(request, obj)
        if hasattr(response, 'url') and response.url:
            import re
            pattern = r'/admin/documents/document/\d+/'
            replacement = f'/admin/documents/document/{obj.uuid}/'
            response.url = re.sub(pattern, replacement, response.url)
        return response
    
    def name_display(self, obj):
        """Link to UUID-based admin edit page"""
        name = obj.name or _('Untitled')
        edit_url = reverse('admin:documents_document_change', args=[obj.uuid])
        return format_html('<a href="{}">{}</a>', edit_url, name)
```

**Result**: Admin URLs change from:
- ❌ `http://localhost:8000/admin/documents/document/5/change/` (predictable)
- ✅ `http://localhost:8000/admin/documents/document/a4c9d8e2-1234-5678-9abc-def123456789/change/` (secure)

### 🎯 **Security Checklist for Every Feature:**

- [ ] **UUIDs used** for all public resource identifiers
- [ ] **Content validation** implemented (hashing, file type checking)
- [ ] **Permission checks** in place for all resource access
- [ ] **Input sanitization** applied to all user inputs  
- [ ] **Rate limiting** configured on sensitive endpoints
- [ ] **Error messages** don't expose internal system details
- [ ] **Logging** implemented for security-relevant events
- [ ] **HTTPS enforced** in production (SSL/TLS)

**Remember: Security is not optional - it must be built in from the start, not added later.**



### 📝 **Development Priority**: Medium Priority
These issues don't affect core functionality but impact admin user experience. Both relate to proper handling of asynchronous updates and timezone conversion in Django admin interface.

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
- **Database**: SQLite with Django ORM
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
- SQLite database with Django models for users, conversations, messages
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

**CRITICAL: Avoid Logical Errors and Unnatural Behaviors**

When implementing features, always avoid logical errors and unnatural behaviors which will not be committed by human developers:

❌ **Common Logical Errors to Avoid:**
- Creating empty conversations without any user messages
- Showing generic labels like "New Conversation" instead of meaningful titles
- Displaying empty boxes when no data exists instead of proper "No Data" messages
- Allowing duplicate or unnecessary operations (e.g., creating new conversation when current one is empty)
- Inconsistent state management (e.g., creating conversations that don't get properly tracked)
- Unnatural user flows that real humans wouldn't expect

✅ **Natural Implementation Patterns:**
- Only create conversations when user actually sends a message
- Generate meaningful titles from conversation content
- Show appropriate empty states ("No History", "No Messages", etc.)
- Prevent unnecessary actions (don't create if current conversation is empty)
- Follow expected user interaction patterns from popular apps (ChatGPT, WhatsApp, etc.)
- Maintain consistent state across all operations

**Testing Mindset:** Always think "Would a real user expect this behavior?" and "Does this match how popular apps work?"

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
- SQLite database setup
- Integration with Django models for conversation storage

## Database & Communication Architecture

### SQLite Database
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

## CRITICAL: CSS Layout Best Practices for Consistent UI

**CSS layout issues are extremely annoying and time-consuming. ALWAYS follow these principles to avoid content-dependent sizing problems:**

### 🚫 **NEVER Use These Problematic CSS Patterns:**

❌ **Content-Dependent Sizing:**
```css
/* Wrong - Container size changes based on content */
.container {
    height: auto; /* Dangerous - size depends on content */
    min-height: 60%; /* Percentage-based minimums cause issues */
}

/* Wrong - Absolute positioning without proper constraints */
.chat-messages {
    position: absolute;
    height: calc(100% - 120px); /* Fragile calculations */
}

/* Wrong - Flex without proper growth control */
.flex-container {
    display: flex;
    /* Missing flex-grow/flex-shrink controls */
}
```

❌ **Complex Layout Calculations:**
```css
/* Wrong - Complex height calculations that break */
.main-area {
    height: calc(100vh - 120px - 80px - 2em); /* Too many dependencies */
}
```

### ✅ **ALWAYS Use Viewport + Flexbox Pattern:**

**The ONLY reliable method for consistent UI sizing:**

```css
/* 1. Main container uses viewport units */
.main-container {
    display: flex;
    flex-direction: column;
    width: 100vw;  /* 100% of viewport width */
    height: 100vh; /* 100% of viewport height */
    box-sizing: border-box;
}

/* 2. Header/footer with fixed height */
.header, .footer {
    flex-shrink: 0; /* CRITICAL: Never shrinks */
    /* Fixed height content */
}

/* 3. Main content area grows to fill space */
.content-area {
    flex-grow: 1;      /* CRITICAL: Takes all available space */
    overflow-y: auto;  /* CRITICAL: Scroll when needed, never resize */
    display: flex;
    flex-direction: column;
}

/* 4. Nested flex items with proper controls */
.chat-messages {
    flex-grow: 1;      /* Takes available space */
    overflow-y: auto;  /* Scrolls instead of expanding */
}

.input-form {
    flex-shrink: 0;    /* Never changes size */
}
```

### 🎯 **CSS Layout Checklist - ALWAYS Verify:**

**Before writing any layout CSS, ensure:**
- [ ] **Main container uses `100vh/100vw`** - No `calc()` or percentage dependencies
- [ ] **Flexbox with explicit `flex-grow: 1`** for main content areas
- [ ] **`flex-shrink: 0`** for fixed elements (headers, inputs, toolbars)
- [ ] **`overflow-y: auto`** on scrollable areas instead of height calculations
- [ ] **`box-sizing: border-box`** to include padding in size calculations
- [ ] **No `position: absolute`** unless absolutely necessary
- [ ] **No `min-height` with percentages** - use viewport units only
- [ ] **Test with different content lengths** - layout should never change

### 🔧 **Implementation Pattern for Chat/Dashboard Layouts:**

```css
/* Root container - full viewport */
.app-container {
    display: flex;
    width: 100vw;
    height: 100vh;
    box-sizing: border-box;
}

/* Sidebar - fixed width */
.sidebar {
    width: 280px;
    min-width: 280px;
    flex-shrink: 0;
    /* Content here */
}

/* Main area - flexible */
.main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
}

/* Header - fixed height */
.header {
    flex-shrink: 0;
    /* Fixed header content */
}

/* Content area - grows to fill */
.content {
    flex-grow: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

/* Messages area - scrollable */
.messages {
    flex-grow: 1;
    overflow-y: auto;
    padding: 24px;
}

/* Input area - fixed height */
.input-container {
    flex-shrink: 0;
    display: flex;
    /* Input form content */
}
```

### 🚨 **Common CSS Mistakes That ALWAYS Cause Problems:**

1. **Height Calculations**: `height: calc(100% - Xpx)` - Always breaks
2. **Percentage Min-Heights**: `min-height: 60%` - Causes content-dependent sizing
3. **Missing Flex Controls**: Not specifying `flex-grow` and `flex-shrink`
4. **Absolute Positioning**: Using `position: absolute` for layout instead of flexbox
5. **Content-Based Heights**: Using `height: auto` or `height: max-content`
6. **Mixed Units**: Mixing `vh`, `%`, and `px` in calculations

### 📏 **Word Wrapping for Long Content:**

**ALWAYS prevent horizontal overflow with:**
```css
.message-content {
    /* Comprehensive word wrapping */
    word-wrap: break-word;
    word-break: break-word;
    overflow-wrap: break-word;
    max-width: 100%;
    white-space: pre-wrap; /* Preserve line breaks but wrap */
}
```

### 🎯 **Testing Requirements:**

**Every layout MUST be tested with:**
- Empty content (welcome messages, no data states)
- Short content (single line messages)
- Long content (paragraph-length responses)
- Very long content (multi-paragraph AI responses)
- Dynamic content changes (adding/removing messages)

**If the container size changes in ANY of these scenarios, the CSS is wrong.**

### 💡 **Golden Rule:**

> **Container size should NEVER depend on content. Use viewport units + flexbox with explicit growth controls. Test with different content lengths to verify consistency.**

**Remember: CSS layout problems waste hours of debugging time. Get it right the first time by following these patterns.**