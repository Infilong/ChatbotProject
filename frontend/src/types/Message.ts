export type MessageStatus = 'sending' | 'sent' | 'failed' | 'delivered';

export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  status?: MessageStatus;
  feedback?: 'up' | 'down' | null;
  file?: {
    name: string;
    size: number;
    type: string;
  };
  error?: string;
  retryCount?: number;
}

export interface TypingIndicator {
  id: string;
  sender: 'bot';
  isTyping: true;
  timestamp: Date;
}