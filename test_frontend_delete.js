// Test the exact same logic as frontend conversationService.deleteConversation()
const API_BASE_URL = 'http://localhost:8000';
const CONVERSATION_API_URL = `${API_BASE_URL}/api/chat/api/conversations`;

async function testFrontendDelete() {
    const conversationId = '39'; // Test with conversation ID 39
    
    try {
        console.log(`ConversationService: Deleting conversation ${conversationId}`);
        console.log(`Request URL: ${CONVERSATION_API_URL}/${conversationId}/`);
        
        const headers = {
            'Content-Type': 'application/json',
            // No authorization header (simulating unauthenticated user)
        };
        console.log('Request headers:', headers);
        
        const response = await fetch(`${CONVERSATION_API_URL}/${conversationId}/`, {
            method: 'DELETE',
            headers,
        });

        console.log('Delete response status:', response.status);
        console.log('Delete response statusText:', response.statusText);
        console.log('Delete response ok:', response.ok);

        if (!response.ok) {
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

// Run the test
testFrontendDelete()
    .then(() => console.log('✅ Test completed successfully'))
    .catch((error) => console.log('❌ Test failed:', error.message));