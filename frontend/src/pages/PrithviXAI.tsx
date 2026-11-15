
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Bot, Send, User, Sparkles } from 'lucide-react';
import type { Farm } from '../types';
import { askPrithviX } from '../services/api';

import './PrithviXAI.css';

type Message = {
    role: 'assistant' | 'user';
    content: string;
};

const SUGGESTIONS = [
    'What should I plant next?',
    'How much water do I need this week?',
    'Why is crop health declining?',
    'How can I improve soil health?'
];

export default function PrithviXAI({ farm }: { farm: Farm }) {

    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'assistant',
            content:
                'Hello! I am PrithviX. Once you set up your farm profile, I can help you understand your crops, water needs, and soil health using your farm information and connected NASA Earth observation datasets.'
        }
    ]);

    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({
            behavior: 'smooth'
        });
    }, [messages, loading]);

    async function sendMessage(text: string) {

        const question = text.trim();

        if (!question || loading) return;

        setMessages(previous => [
            ...previous,
            {
                role: 'user',
                content: question
            }
        ]);

        setInput('');
        setError('');
        setLoading(true);

        try {

            const profile = JSON.parse(
                localStorage.getItem('prithvix.profile.v1') || '{}'
            );

            const response = await askPrithviX({
                message: question,
                farm_id: farm.id,

                farm: {
                    name: farm.name,
                    location: farm.location,
                    latitude: farm.lat,
                    longitude: farm.lng,
                    timezone: farm.tz,
                    zone: farm.z,

                    currentCrop: profile.currentCrop || '',
                    soilType: profile.soilType || 'Unknown',
                    waterSource: profile.waterSource || 'Unknown',
                    irrigation: profile.irrigation || 'Unknown',
                    farmArea: profile.farmArea || '',
                    areaUnit: profile.areaUnit || 'Acres',
                    primaryGoal: profile.primaryGoal || ''
                }
            });

            setMessages(previous => [
                ...previous,
                {
                    role: 'assistant',
                    content: response.reply
                }
            ]);

        } catch (err) {

            setError(
                err instanceof Error
                    ? err.message
                    : 'Unable to connect to PrithviXAI. Please try again.'
            );

        } finally {
            setLoading(false);
        }
    }

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        void sendMessage(input);
    }

    function handleKeyDown(
        event: KeyboardEvent<HTMLTextAreaElement>
    ) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            void sendMessage(input);
        }
    }

    return (

        <div className="pxai-page">

            {/* HEADER */}

            <div className="pxai-header">

                <div className="pxai-header-icon">
                    <Bot size={25} />
                </div>

                <div className="pxai-header-text">
                    <h2>
                        Ask PrithviX — Your Trusted Agronomy Advisor
                    </h2>

                    <p>
                        Grounded in your farm profile and NASA Earth observation datasets.
                    </p>
                </div>

                <span className="pxai-status">
                    {loading ? 'Thinking...' : 'Online'}
                </span>

            </div>


            {/* CHAT WINDOW */}

            <div className="pxai-chat-window">

                {messages.map((message, index) => (

                    <div
                        className={`pxai-message ${message.role}`}
                        key={index}
                    >

                        <div className="pxai-avatar">

                            {message.role === 'assistant'
                                ? <Bot size={19} />
                                : <User size={19} />
                            }

                        </div>

                        <div className="pxai-bubble">

                            <p>{message.content}</p>

                            {/* SUGGESTED QUESTIONS */}

                            {message.role === 'assistant' &&
                                index === 0 && (

                                <div className="pxai-suggestions">

                                    {SUGGESTIONS.map((question) => (

                                        <button
                                            type="button"
                                            key={question}
                                            disabled={loading}
                                            onClick={() => sendMessage(question)}
                                        >
                                            "{question}"
                                        </button>

                                    ))}

                                </div>

                            )}

                        </div>

                    </div>

                ))}


                {/* LOADING ANIMATION */}

                {loading && (

                    <div className="pxai-message assistant">

                        <div className="pxai-avatar">
                            <Bot size={19} />
                        </div>

                        <div className="pxai-bubble pxai-typing">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>

                    </div>

                )}

                <div ref={chatEndRef} />

            </div>


            {/* ERROR MESSAGE */}

            {error && (

                <div className="pxai-error">
                    {error}
                </div>

            )}


            {/* MESSAGE INPUT */}

            <form
                className="pxai-composer"
                onSubmit={handleSubmit}
            >

                <textarea
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask anything about your farm, irrigation, or weather..."
                    rows={1}
                    disabled={loading}
                />

                <button
                    type="submit"
                    disabled={!input.trim() || loading}
                >

                    Send
                    <Send size={17} />

                </button>

            </form>


            {/* FOOTER */}

            <div className="pxai-footer">

                <Sparkles size={14} />

                AI-generated agricultural advice should be
                verified against local agricultural guidance.

            </div>

        </div>
    );
}
