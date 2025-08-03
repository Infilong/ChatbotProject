import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider } from '@mui/material/styles';
import MessageList from './MessageList';
import { theme } from '../theme';
import { Message } from '../types/Message';

const mockMessages: Message[] = [
  {
    id: '1',
    text: 'Hello, how are you?',
    sender: 'user',
    timestamp: new Date('2023-01-01T10:00:00Z'),
    status: 'sent',
  },
  {
    id: '2',
    text: 'I am doing well, thank you!',
    sender: 'bot',
    timestamp: new Date('2023-01-01T10:01:00Z'),
    status: 'delivered',
  },
  {
    id: '3',
    text: 'This message failed to send',
    sender: 'user',
    timestamp: new Date('2023-01-01T10:02:00Z'),
    status: 'failed',
    error: 'Network error',
    retryCount: 1,
  },
];

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('MessageList', () => {
  const mockOnFeedback = jest.fn();
  const mockOnRetryMessage = jest.fn();

  beforeEach(() => {
    mockOnFeedback.mockClear();
    mockOnRetryMessage.mockClear();
  });

  it('renders messages correctly', () => {
    renderWithTheme(
      <MessageList 
        messages={mockMessages} 
        onFeedback={mockOnFeedback}
        onRetryMessage={mockOnRetryMessage}
      />
    );

    expect(screen.getByText('Hello, how are you?')).toBeInTheDocument();
    expect(screen.getByText('I am doing well, thank you!')).toBeInTheDocument();
    expect(screen.getByText('This message failed to send')).toBeInTheDocument();
  });

  it('shows typing indicator when isTyping is true', () => {
    renderWithTheme(
      <MessageList 
        messages={[]} 
        onFeedback={mockOnFeedback}
        isTyping={true}
      />
    );

    // Check for typing indicator container
    const typingIndicator = screen.getByRole('generic');
    expect(typingIndicator).toBeInTheDocument();
  });

  it('shows retry button for failed messages', () => {
    renderWithTheme(
      <MessageList 
        messages={mockMessages} 
        onFeedback={mockOnFeedback}
        onRetryMessage={mockOnRetryMessage}
      />
    );

    const retryButton = screen.getByLabelText('Retry sending message');
    expect(retryButton).toBeInTheDocument();
  });

  it('calls onRetryMessage when retry button is clicked', () => {
    renderWithTheme(
      <MessageList 
        messages={mockMessages} 
        onFeedback={mockOnFeedback}
        onRetryMessage={mockOnRetryMessage}
      />
    );

    const retryButton = screen.getByLabelText('Retry sending message');
    fireEvent.click(retryButton);
    
    expect(mockOnRetryMessage).toHaveBeenCalledWith('3');
  });

  it('displays error message for failed messages', () => {
    renderWithTheme(
      <MessageList 
        messages={mockMessages} 
        onFeedback={mockOnFeedback}
      />
    );

    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('displays timestamp for all messages', () => {
    renderWithTheme(
      <MessageList 
        messages={mockMessages} 
        onFeedback={mockOnFeedback}
      />
    );

    // Check that timestamps are displayed (format: HH:MM)
    expect(screen.getByText('10:00')).toBeInTheDocument();
    expect(screen.getByText('10:01')).toBeInTheDocument();
    expect(screen.getByText('10:02')).toBeInTheDocument();
  });
});