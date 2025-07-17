
import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../types';
import { chatService } from '../services/geminiService';

const ChatIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
);

const CloseIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
);

const SendIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
    </svg>
);

const ChatWidget: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (isOpen) {
            setMessages([
                { id: 'init', role: 'model', text: "Hi there! I'm your sustainable living assistant. Ask me anything about eco-friendly habits or products!" }
            ]);
            chatService.resetChat();
        }
    }, [isOpen]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (input.trim() === '' || isLoading) return;

        const userMessage: ChatMessage = { id: Date.now().toString(), role: 'user', text: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        const modelMessageId = (Date.now() + 1).toString();
        setMessages(prev => [...prev, { id: modelMessageId, role: 'model', text: '' }]);

        await chatService.sendMessage(input, (chunk) => {
            setMessages(prev =>
                prev.map(msg =>
                    msg.id === modelMessageId ? { ...msg, text: msg.text + chunk } : msg
                )
            );
        });

        setIsLoading(false);
    };

    return (
        <>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="fixed bottom-6 right-6 bg-brand-green text-white p-4 rounded-full shadow-lg hover:bg-brand-green-dark transition-transform transform hover:scale-110 z-50"
                aria-label="Open chat"
            >
                <ChatIcon />
            </button>

            {isOpen && (
                <div className="fixed bottom-24 right-6 w-80 h-96 bg-white rounded-lg shadow-2xl flex flex-col z-50 transform transition-all duration-300 origin-bottom-right">
                    <header className="bg-brand-green text-white p-4 flex justify-between items-center rounded-t-lg">
                        <h3 className="font-bold">Sustainable Living Assistant</h3>
                        <button onClick={() => setIsOpen(false)} aria-label="Close chat">
                            <CloseIcon />
                        </button>
                    </header>

                    <div className="flex-1 p-4 overflow-y-auto bg-brand-gray-light">
                        {messages.map((msg, index) => (
                            <div key={msg.id} className={`flex mb-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`rounded-lg px-3 py-2 max-w-xs ${msg.role === 'user' ? 'bg-brand-green text-white' : 'bg-gray-200 text-brand-gray-dark'}`}>
                                    {msg.text}
                                    {isLoading && msg.role === 'model' && index === messages.length -1 && <span className="inline-block w-2 h-4 bg-gray-600 animate-ping ml-1"></span>}
                                </div>
                            </div>
                        ))}
                         <div ref={messagesEndRef} />
                    </div>

                    <div className="p-2 border-t border-gray-200">
                        <div className="flex items-center space-x-2">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                                placeholder="Ask a question..."
                                className="flex-1 p-2 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-brand-green"
                                disabled={isLoading}
                            />
                            <button onClick={handleSend} disabled={isLoading} className="bg-brand-green text-white p-2 rounded-full hover:bg-brand-green-dark disabled:bg-gray-400">
                                <SendIcon />
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default ChatWidget;
