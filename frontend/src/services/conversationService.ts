/**
 * Conversation Service
 * Handles conversation CRUD operations with the backend API
 */

import authService from './authService';

export interface BackendMessage {
  id: string;
  conversation: string;
  content: string;
  sender_type: 'user' | 'bot';
  timestamp: string;
  feedback: 'positive' | 'negative' | null;
  llm_model_used: string | null;
  response_time: number | null;
  tokens_used: number | null;
}

export interface BackendConversation {
  id: string;
  uuid: string;
  user: number;
  title: string;
  is_active: boolean;
  satisfaction_score: number | null;
  langextract_analysis: any;
  created_at: string;
  updated_at: string;
  total_messages: number;
  messages?: BackendMessage[];
}

export interface ConversationListResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: BackendConversation[];
}

export interface ConversationCreateRequest {
  title: string;
  is_active?: boolean;
}

export interface MessageCreateRequest {
  conversation: string;
  content: string;
  sender_type: 'user' | 'bot';
  feedback?: 'positive' | 'negative' | null;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const CONVERSATION_API_URL = `${API_BASE_URL}/api/chat/api/conversations`;

class ConversationService {
  /**
   * Get conversations for the current user
   */
  async getConversations(page: number = 1, pageSize: number = 20): Promise<ConversationListResponse> {
    try {
      const headers = authService.getAuthHeaders();
      const response = await fetch(
        `${CONVERSATION_API_URL}/?page=${page}&page_size=${pageSize}`,
        {
          method: 'GET',
          headers,
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch conversations: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching conversations:', error);
      throw error;
    }
  }

  /**
   * Get a specific conversation with messages
   */
  async getConversation(conversationId: string): Promise<BackendConversation> {
    try {
      const headers = authService.getAuthHeaders();
      const response = await fetch(`${CONVERSATION_API_URL}/${conversationId}/`, {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch conversation: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching conversation:', error);
      throw error;
    }
  }

  /**
   * Get messages for a specific conversation
   */
  async getConversationMessages(conversationId: string): Promise<BackendMessage[]> {
    try {
      const headers = authService.getAuthHeaders();
      const response = await fetch(`${CONVERSATION_API_URL}/${conversationId}/messages/`, {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch messages: ${response.statusText}`);
      }

      const data = await response.json();
      return data.results || data; // Handle paginated or non-paginated responses
    } catch (error) {
      console.error('Error fetching conversation messages:', error);
      throw error;
    }
  }

  /**
   * Create a new conversation
   */
  async createConversation(data: ConversationCreateRequest): Promise<BackendConversation> {
    try {
      const headers = authService.getAuthHeaders();
      const response = await fetch(CONVERSATION_API_URL + '/', {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`Failed to create conversation: ${JSON.stringify(errorData)}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error creating conversation:', error);
      throw error;
    }
  }

  /**
   * Update an existing conversation
   */
  async updateConversation(conversationId: string, data: Partial<ConversationCreateRequest>): Promise<BackendConversation> {
    try {
      const headers = authService.getAuthHeaders();
      const response = await fetch(`${CONVERSATION_API_URL}/${conversationId}/`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`Failed to update conversation: ${JSON.stringify(errorData)}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating conversation:', error);
      throw error;
    }
  }

  /**
   * Delete a conversation by UUID
   */
  async deleteConversation(conversationUuid: string): Promise<void> {
    try {
      console.log(`ConversationService: Deleting conversation ${conversationUuid}`);
      console.log(`Request URL: ${CONVERSATION_API_URL}/${conversationUuid}/`);
      
      const headers = authService.getAuthHeaders();
      console.log('Request headers:', headers);
      
      const response = await fetch(`${CONVERSATION_API_URL}/${conversationUuid}/`, {
        method: 'DELETE',
        headers,
      });

      console.log('Delete response status:', response.status);
      console.log('Delete response statusText:', response.statusText);

      if (!response.ok) {
        // Handle 404 - conversation already deleted or doesn't exist
        if (response.status === 404) {
          console.warn(`Conversation ${conversationUuid} not found in backend (already deleted)`);
          return; // Treat as success since the goal (deletion) is achieved
        }
        
        const responseText = await response.text();
        console.error('Delete response body:', responseText);
        throw new Error(`Failed to delete conversation: ${response.statusText}`);
      }
      
      console.log('Conversation deleted successfully');
    } catch (error) {
      console.error('Error deleting conversation:', error);
      throw error;
    }
  }

  /**
   * Add a message to a conversation
   */
  async addMessage(conversationId: string, content: string, senderType: 'user' | 'bot'): Promise<BackendMessage> {
    try {
      const headers = authService.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api/chat/api/messages/`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          conversation: conversationId,
          content,
          sender_type: senderType,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`Failed to add message: ${JSON.stringify(errorData)}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error adding message:', error);
      throw error;
    }
  }

  /**
   * Search conversations
   */
  async searchConversations(query: string): Promise<BackendConversation[]> {
    try {
      const headers = authService.getAuthHeaders();
      const response = await fetch(
        `${API_BASE_URL}/api/chat/search/?q=${encodeURIComponent(query)}`,
        {
          method: 'GET',
          headers,
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to search conversations: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error searching conversations:', error);
      throw error;
    }
  }

  /**
   * Generate conversation title from first user message
   */
  generateTitle(messages: BackendMessage[], language: 'en' | 'ja' = 'en'): string {
    const firstUserMessage = messages.find(msg => msg.sender_type === 'user');
    
    if (firstUserMessage && firstUserMessage.content.length > 0) {
      // Use first 30 characters of first user message as title
      return firstUserMessage.content.length > 30 
        ? firstUserMessage.content.substring(0, 30) + '...'
        : firstUserMessage.content;
    }

    // Fallback to date-based title
    const date = new Date().toLocaleDateString(language === 'ja' ? 'ja-JP' : 'en-US');
    return language === 'ja' ? `会話 - ${date}` : `Conversation - ${date}`;
  }

  /**
   * Convert backend conversation to frontend format
   */
  convertToFrontendFormat(backendConv: BackendConversation): any {
    return {
      id: backendConv.uuid,  // Use UUID as primary identifier
      title: backendConv.title,
      messages: backendConv.messages?.map(msg => ({
        id: msg.id,  // Messages still use ID for now, UUID later
        text: msg.content,
        sender: msg.sender_type === 'user' ? 'user' : 'bot',
        timestamp: new Date(msg.timestamp),
        feedback: msg.feedback,
      })) || [],
      createdAt: new Date(backendConv.created_at),
      updatedAt: new Date(backendConv.updated_at),
      username: '', // Will be filled by the context
      language: 'en', // Default language
      messageCount: backendConv.total_messages,
      lastMessage: backendConv.messages && backendConv.messages.length > 0 
        ? backendConv.messages[backendConv.messages.length - 1].content 
        : undefined,
    };
  }

  /**
   * Check service health
   */
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/health/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      return await response.json();
    } catch (error) {
      console.error('Conversation service health check failed:', error);
      throw error;
    }
  }
}

export const conversationService = new ConversationService();
export default conversationService;