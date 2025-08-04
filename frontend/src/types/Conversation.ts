import { Message } from './Message';

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
  username: string;
  language: 'en' | 'ja';
  messageCount: number;
  lastMessage?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  username: string;
  language: 'en' | 'ja';
  messageCount: number;
  lastMessage?: string;
}

export interface ConversationFilter {
  username?: string;
  language?: 'en' | 'ja';
  dateRange?: {
    start: Date;
    end: Date;
  };
  searchQuery?: string;
}

export interface ConversationHistoryState {
  conversations: Conversation[];
  currentConversationId: string | null;
  isLoading: boolean;
  filter: ConversationFilter;
}