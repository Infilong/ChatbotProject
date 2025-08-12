import { Message, MessageStatus } from '../types/Message';
import { messageUtils } from '../utils/messageUtils';

type LanguageType = 'en' | 'ja';

export interface ChatResponse {
  message: Message;
  delay?: number;
  provider?: string;
  model?: string;
  responseTime?: number;
  tokensUsed?: number;
  conversationId?: string;
}

export interface ChatError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface ChatConfig {
  provider?: 'openai' | 'gemini' | 'claude';
  language?: LanguageType;
  maxTokens?: number;
  temperature?: number;
}

export interface ApiResponse {
  response: string;
  conversation_id: string;
  message_id: string;
  timestamp: string;
  provider: string;
  model: string;
  response_time: number;
  tokens_used?: number;
  metadata: Record<string, any>;
}

class ChatService {
  private readonly API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  private readonly MAX_RETRY_ATTEMPTS = 3;
  private readonly RETRY_DELAY_BASE = 1000; // 1 second
  
  // Current conversation ID for session management
  private currentConversationId: string | null = null;

  private async makeApiCall(endpoint: string, data: Record<string, any>): Promise<ApiResponse> {
    // Simplified API call for demo environment
    // Backend has AllowAny permissions and csrf_exempt
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    const response = await fetch(`${this.API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      if (response.status === 401) {
        const error: ChatError = {
          code: 'AUTH_ERROR',
          message: 'Authentication required. Please log in.',
          retryable: false,
        };
        throw error;
      } else if (response.status === 503) {
        const error: ChatError = {
          code: 'SERVICE_UNAVAILABLE',
          message: 'LLM service is currently unavailable. Please try again later.',
          retryable: true,
        };
        throw error;
      } else {
        const error: ChatError = {
          code: 'API_ERROR',
          message: `API request failed with status ${response.status}`,
          retryable: true,
        };
        throw error;
      }
    }

    return await response.json();
  }

  // Generate real LLM response using backend API
  async generateResponse(
    userMessage: Message, 
    language: LanguageType = 'en', 
    config: ChatConfig = {},
    retryCount: number = 0
  ): Promise<ChatResponse> {
    try {
      const requestData = {
        message: userMessage.text,
        conversation_id: this.currentConversationId,
        provider: config.provider,
        language,
        max_tokens: config.maxTokens || 1000,
        temperature: config.temperature || 0.7,
      };

      console.log('Making API call with data:', requestData);
      const apiResponse = await this.makeApiCall('/api/chat/chat/', requestData);
      
      // Store conversation ID for future messages
      this.currentConversationId = apiResponse.conversation_id;
      
      // Create bot message from API response
      const botMessage = messageUtils.createMessage(
        apiResponse.response,
        'bot'
      );

      return {
        message: botMessage,
        delay: Math.round(apiResponse.response_time * 1000), // Convert to milliseconds
        provider: apiResponse.provider,
        model: apiResponse.model,
        responseTime: apiResponse.response_time,
        tokensUsed: apiResponse.tokens_used,
        conversationId: apiResponse.conversation_id,
      };

    } catch (error) {
      console.error('LLM API call failed:', error);
      
      if (error && typeof error === 'object' && 'code' in error) {
        throw error;
      }
      
      const chatError: ChatError = {
        code: 'NETWORK_ERROR',
        message: 'Failed to connect to chat service. Please check your internet connection.',
        retryable: true,
      };
      throw chatError;
    }
  }

  // Retry failed message with exponential backoff
  async retryMessage(
    userMessage: Message, 
    language: LanguageType = 'en', 
    config: ChatConfig = {},
    retryCount: number = 0
  ): Promise<ChatResponse> {
    if (retryCount >= this.MAX_RETRY_ATTEMPTS) {
      const error: ChatError = {
        code: 'MAX_RETRIES_EXCEEDED',
        message: 'Maximum retry attempts exceeded. Please try again later.',
        retryable: false,
      };
      throw error;
    }

    const retryDelay = this.RETRY_DELAY_BASE * Math.pow(2, retryCount);
    
    // Wait for exponential backoff delay
    await new Promise(resolve => setTimeout(resolve, retryDelay));
    
    return this.generateResponse(userMessage, language, config, retryCount + 1);
  }

  // Create human service escalation message
  createHumanServiceMessage(language: LanguageType = 'en'): Message {
    const translations = {
      en: "I've connected you with our human support team. A customer service representative will be with you shortly. Thank you for your patience!",
      ja: "人間のサポートチームにおつなぎいたします。カスタマーサービス担当者がまもなく対応いたします。お待ちいただき、ありがとうございます！"
    };
    
    return messageUtils.createMessage(
      translations[language],
      'bot'
    );
  }

  // Provider-specific API calls
  async sendToOpenAI(message: string): Promise<string> {
    const userMsg = messageUtils.createMessage(message, 'user');
    const response = await this.generateResponse(userMsg, 'en', { provider: 'openai' });
    return response.message.text;
  }

  async sendToGemini(message: string): Promise<string> {
    const userMsg = messageUtils.createMessage(message, 'user');
    const response = await this.generateResponse(userMsg, 'en', { provider: 'gemini' });
    return response.message.text;
  }

  async sendToClaude(message: string): Promise<string> {
    const userMsg = messageUtils.createMessage(message, 'user');
    const response = await this.generateResponse(userMsg, 'en', { provider: 'claude' });
    return response.message.text;
  }

  // Conversation analysis using LangExtract backend
  async analyzeConversation(messages: Message[]): Promise<{
    sentiment: 'positive' | 'neutral' | 'negative';
    urgency: 'low' | 'medium' | 'high';
    categories: string[];
    insights: string[];
  }> {
    if (!this.currentConversationId) {
      throw new Error('No active conversation to analyze');
    }

    try {
      const response = await fetch(`${this.API_BASE_URL}/api/chat/api/conversations/${this.currentConversationId}/analyze/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Analysis failed with status ${response.status}`);
      }

      const analysisData = await response.json();
      
      return {
        sentiment: analysisData.analysis.sentiment || 'neutral',
        urgency: analysisData.analysis.urgency || 'low',
        categories: analysisData.analysis.categories || [],
        insights: analysisData.analysis.insights || [],
      };
    } catch (error) {
      console.error('Conversation analysis failed:', error);
      throw new Error('Failed to analyze conversation');
    }
  }

  // Conversation management methods
  async startNewConversation(): Promise<string> {
    this.currentConversationId = null;
    return 'new-conversation';
  }

  getCurrentConversationId(): string | null {
    return this.currentConversationId;
  }

  // Submit feedback for a bot message
  async submitFeedback(messageId: string, feedback: 'positive' | 'negative'): Promise<void> {
    try {
      await fetch(`${this.API_BASE_URL}/api/chat/api/messages/${messageId}/feedback/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ feedback }),
      });
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  }
}

export const chatService = new ChatService();