import { Message, MessageStatus } from '../types/Message';

export const messageUtils = {
  createMessage: (
    text: string,
    sender: 'user' | 'bot',
    file?: File,
    status: MessageStatus = 'sent'
  ): Message => {
    return {
      id: Date.now().toString(),
      text: text || (file ? `📎 ${file.name}` : ''),
      sender,
      timestamp: new Date(),
      status,
      file: file ? {
        name: file.name,
        size: file.size,
        type: file.type,
      } : undefined,
      retryCount: 0,
    };
  },

  createWelcomeMessage: (username: string): Message => {
    return {
      id: '1',
      text: `Hello ${username}! 👋 Welcome to DataPro Solutions support. I'm here to help you with any questions or issues you might have. How can I assist you today?`,
      sender: 'bot',
      timestamp: new Date(),
    };
  },

  updateMessageFeedback: (
    messages: Message[],
    messageId: string,
    feedback: 'up' | 'down'
  ): Message[] => {
    return messages.map(msg => {
      if (msg.id === messageId) {
        const previousFeedback = msg.feedback;
        // Toggle off if clicking same button, otherwise set new feedback
        const newFeedback = previousFeedback === feedback ? null : feedback;
        
        return { 
          ...msg, 
          feedback: newFeedback
        };
      }
      return msg;
    });
  },

  validateMessage: (text: string, file?: File): boolean => {
    return !!(text.trim() || file);
  },

  formatFileSize: (bytes: number): string => {
    return (bytes / 1024).toFixed(1);
  },

  formatTime: (timestamp: Date): string => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  },

  updateMessageStatus: (
    messages: Message[],
    messageId: string,
    status: MessageStatus,
    error?: string
  ): Message[] => {
    return messages.map(msg => {
      if (msg.id === messageId) {
        return { 
          ...msg, 
          status,
          error: error || undefined
        };
      }
      return msg;
    });
  },

  incrementRetryCount: (
    messages: Message[],
    messageId: string
  ): Message[] => {
    return messages.map(msg => {
      if (msg.id === messageId) {
        return { 
          ...msg, 
          retryCount: (msg.retryCount || 0) + 1,
          status: 'sending' as MessageStatus
        };
      }
      return msg;
    });
  },

  canRetryMessage: (message: Message): boolean => {
    return message.status === 'failed' && (message.retryCount || 0) < 3;
  },
};