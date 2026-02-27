import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { IconChat, IconArrowLeft, IconSend } from '../components/Icons';

const API_URL = 'http://localhost:8000';

const QUICK_QUESTIONS = [
    "Can I terminate this contract early?",
    "What are the payment terms?",
    "Who owns the intellectual property?",
    "What happens if payment is late?",
    "What is the notice period?",
    "Are there any non-compete restrictions?",
];

export default function ChatPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [docName, setDocName] = useState('');
    const messagesEndRef = useRef(null);

    useEffect(() => {
        const cached = sessionStorage.getItem(`result_${id}`);
        if (cached) {
            const result = JSON.parse(cached);
            setDocName(result.document_name || 'Document');
        }
        setMessages([{
            role: 'assistant',
            content: "Hi! I'm your contract Q&A assistant. Ask me anything about this document and I'll find the answer for you.",
        }]);
    }, [id]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async (text) => {
        if (!text.trim() || loading) return;

        const userMsg = { role: 'user', content: text };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const res = await fetch(`${API_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text, analysis_id: id }),
            });

            const data = await res.json();

            if (data.success) {
                setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
            } else {
                setMessages(prev => [...prev, { role: 'assistant', content: data.detail || 'Sorry, something went wrong.' }]);
            }
        } catch (err) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Failed to get a response. Make sure the backend is running and GROQ_API_KEY is configured.',
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        sendMessage(input);
    };

    return (
        <div className="page">
            <div className="container">
                <div className="chat-container animate-in">
                    <div className="chat-header">
                        <h2><IconChat size={18} /> Contract Q&A {docName && `— ${docName}`}</h2>
                        <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/results/${id}`)}><IconArrowLeft size={14} /> Back to Results</button>
                    </div>

                    <div className="chat-messages">
                        {messages.map((msg, i) => (
                            <div key={i} className={`chat-message ${msg.role}`}>
                                {msg.role === 'assistant' ? (
                                    <div className="markdown-body"><ReactMarkdown>{msg.content}</ReactMarkdown></div>
                                ) : msg.content}
                            </div>
                        ))}
                        {loading && (
                            <div className="typing-indicator">
                                <span /><span /><span />
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    <div className="quick-questions">
                        {QUICK_QUESTIONS.map((q, i) => (
                            <button key={i} className="quick-q" onClick={() => sendMessage(q)}>
                                {q}
                            </button>
                        ))}
                    </div>

                    <form className="chat-input-bar" onSubmit={handleSubmit}>
                        <input
                            className="chat-input"
                            type="text"
                            placeholder="Ask anything about your contract..."
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            disabled={loading}
                        />
                        <button type="submit" className="btn btn-primary btn-sm" disabled={loading || !input.trim()}>
                            <IconSend size={14} />
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
