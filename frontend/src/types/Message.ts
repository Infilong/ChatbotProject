export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  feedback?: 'up' | 'down' | null;
  file?: {
    name: string;
    size: number;
    type: string;
  };
}