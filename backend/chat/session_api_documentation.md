# Customer Session Management API

This API provides session tracking for frontend users (React app at localhost:3000) in the Django backend.

## API Endpoints

All endpoints are available at: `http://127.0.0.1:8000/api/chat/sessions/`

### 1. Start Session
**POST** `/api/chat/sessions/start/`

Creates a new customer session or refreshes existing active session.

```javascript
// Frontend usage example
const startSession = async () => {
  const response = await fetch('http://127.0.0.1:8000/api/chat/sessions/start/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({})
  });
  
  const data = await response.json();
  console.log('Session started:', data);
  // Store session_id for subsequent requests
  localStorage.setItem('chatSessionId', data.session_id);
};
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "message": "New session started",
  "started_at": "2025-08-20T20:00:00Z",
  "user": "demo_user"
}
```

### 2. Update Session Activity
**POST** `/api/chat/sessions/update/`

Updates session activity when user performs actions (sends messages, starts conversations, etc.).

```javascript
// Frontend usage example
const updateSession = async (activityType, additionalData = {}) => {
  const sessionId = localStorage.getItem('chatSessionId');
  
  const response = await fetch('http://127.0.0.1:8000/api/chat/sessions/update/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      activity_type: activityType,
      ...additionalData
    })
  });
  
  const data = await response.json();
  console.log('Session updated:', data);
};

// Usage examples:
updateSession('message_sent');
updateSession('conversation_started');
updateSession('response_received', { response_time: 1.5 });
```

**Request Body:**
```json
{
  "session_id": "uuid-string",
  "activity_type": "message_sent",  // or "conversation_started", "response_received"
  "response_time": 1.5  // optional, for response_received activity
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "message": "Session updated - message_sent",
  "total_messages_sent": 5,
  "total_conversations": 2,
  "average_response_time": 1.2
}
```

### 3. End Session
**POST** `/api/chat/sessions/end/`

Ends the current session when user closes the app or leaves the site.

```javascript
// Frontend usage example
const endSession = async () => {
  const sessionId = localStorage.getItem('chatSessionId');
  
  const response = await fetch('http://127.0.0.1:8000/api/chat/sessions/end/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId
    })
  });
  
  const data = await response.json();
  console.log('Session ended:', data);
  localStorage.removeItem('chatSessionId');
};
```

**Request Body:**
```json
{
  "session_id": "uuid-string"
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "message": "Session ended",
  "started_at": "2025-08-20T20:00:00Z",
  "ended_at": "2025-08-20T20:30:00Z",
  "duration_minutes": 30.0,
  "total_messages_sent": 10,
  "total_conversations": 3
}
```

### 4. Get Session Status
**GET** `/api/chat/sessions/status/`

Checks if user has an active session and gets session details.

```javascript
// Frontend usage example
const getSessionStatus = async () => {
  const response = await fetch('http://127.0.0.1:8000/api/chat/sessions/status/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  const data = await response.json();
  console.log('Session status:', data);
  
  if (data.has_active_session) {
    localStorage.setItem('chatSessionId', data.session_id);
  }
};
```

**Response (Active Session):**
```json
{
  "has_active_session": true,
  "session_id": "uuid-string",
  "started_at": "2025-08-20T20:00:00Z",
  "duration_minutes": 15.5,
  "total_messages_sent": 5,
  "total_conversations": 2,
  "average_response_time": 1.2,
  "user": "demo_user"
}
```

**Response (No Active Session):**
```json
{
  "has_active_session": false,
  "user": "demo_user",
  "message": "No active session found"
}
```

### 5. Get Session History
**GET** `/api/chat/sessions/history/`

Gets user's session history for analytics.

```javascript
// Frontend usage example
const getSessionHistory = async () => {
  const response = await fetch('http://127.0.0.1:8000/api/chat/sessions/history/', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  const data = await response.json();
  console.log('Session history:', data);
};
```

**Response:**
```json
{
  "user": "demo_user",
  "total_sessions": 5,
  "sessions": [
    {
      "session_id": "uuid-string",
      "started_at": "2025-08-20T20:00:00Z",
      "ended_at": "2025-08-20T20:30:00Z",
      "is_active": false,
      "duration_minutes": 30.0,
      "total_messages_sent": 10,
      "total_conversations": 3,
      "average_response_time": 1.2
    }
  ],
  "summary": {
    "total_duration_minutes": 120.0,
    "total_messages_sent": 50,
    "total_conversations": 15,
    "average_session_duration": 24.0
  }
}
```

### 6. Cleanup Expired Sessions
**POST** `/api/chat/sessions/cleanup/`

Cleans up expired sessions (sessions active for more than 1 hour).

```javascript
// Frontend usage example (optional, mainly for maintenance)
const cleanupSessions = async () => {
  const response = await fetch('http://127.0.0.1:8000/api/chat/sessions/cleanup/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({})
  });
  
  const data = await response.json();
  console.log('Cleanup result:', data);
};
```

**Response:**
```json
{
  "message": "Cleaned up 2 expired sessions",
  "cleaned_sessions": 2,
  "user": "demo_user"
}
```

## Integration Pattern for React Frontend

Here's a complete integration pattern for the React frontend:

```javascript
// sessionManager.js
class SessionManager {
  constructor() {
    this.sessionId = localStorage.getItem('chatSessionId');
    this.apiBase = 'http://127.0.0.1:8000/api/chat/sessions';
  }

  async initializeSession() {
    // Check for existing session first
    const status = await this.getStatus();
    
    if (!status.has_active_session) {
      // Start new session
      await this.start();
    } else {
      // Use existing session
      this.sessionId = status.session_id;
      localStorage.setItem('chatSessionId', this.sessionId);
    }
  }

  async start() {
    const response = await fetch(`${this.apiBase}/start/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    
    const data = await response.json();
    this.sessionId = data.session_id;
    localStorage.setItem('chatSessionId', this.sessionId);
    return data;
  }

  async update(activityType, additionalData = {}) {
    if (!this.sessionId) return;
    
    const response = await fetch(`${this.apiBase}/update/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: this.sessionId,
        activity_type: activityType,
        ...additionalData
      })
    });
    
    return response.json();
  }

  async end() {
    if (!this.sessionId) return;
    
    const response = await fetch(`${this.apiBase}/end/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: this.sessionId
      })
    });
    
    localStorage.removeItem('chatSessionId');
    this.sessionId = null;
    return response.json();
  }

  async getStatus() {
    const response = await fetch(`${this.apiBase}/status/`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    
    return response.json();
  }

  async getHistory() {
    const response = await fetch(`${this.apiBase}/history/`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    
    return response.json();
  }

  // Event handlers for React components
  onMessageSent() {
    this.update('message_sent');
  }

  onConversationStarted() {
    this.update('conversation_started');
  }

  onResponseReceived(responseTime) {
    this.update('response_received', { response_time: responseTime });
  }
}

// Usage in React App
const sessionManager = new SessionManager();

// In App.js useEffect
useEffect(() => {
  sessionManager.initializeSession();
  
  // Cleanup on page unload
  const handleUnload = () => {
    sessionManager.end();
  };
  
  window.addEventListener('beforeunload', handleUnload);
  return () => window.removeEventListener('beforeunload', handleUnload);
}, []);

// In chat components
const handleSendMessage = async (message) => {
  sessionManager.onMessageSent();
  // ... send message logic
  
  const startTime = Date.now();
  // ... get response
  const responseTime = (Date.now() - startTime) / 1000;
  sessionManager.onResponseReceived(responseTime);
};
```

## Django Admin Integration

The Customer Sessions are automatically tracked in Django Admin at:
- **Admin URL**: `http://127.0.0.1:8000/admin/chat/usersession/`
- **Display Name**: "Customer Sessions" (to distinguish from Admin Sessions)

Admin users can view:
- Active and ended sessions
- Session duration and activity statistics
- User activity patterns
- Session analytics and insights

## Security Notes

- All endpoints support anonymous users (demo_user is created automatically)
- For production, consider adding authentication requirements
- Session cleanup runs automatically to prevent database bloat
- UUIDs are used for session IDs for security