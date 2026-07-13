import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles } from 'lucide-react';
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, ResponsiveContainer, Legend 
} from 'recharts';
import axios from 'axios';
import useDataStore from '../store'; // आपका Zustand Store

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const storeApi = axios.create({
  baseURL: API_BASE_URL.replace(/\/api\/?$/, ''),
});

storeApi.interceptors.request.use((config) => {
  let token = null;
  try {
    const raw = sessionStorage.getItem('my_data_platform_auth') || localStorage.getItem('my_data_platform_auth');
    if (raw) {
      token = JSON.parse(raw)?.token;
    }
  } catch (e) {
    console.error("Error reading auth token in storeApi", e);
  }
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const AnalyticsChat = () => {
  const { rawData, cleanedData } = useDataStore();
  const currentDataset = cleanedData.length > 0 ? cleanedData : rawData;
  const [messages, setMessages] = useState([
    { 
      type: 'bot', 
      text: "Hello! I've analyzed your data. Ask me anything like 'Compare Sales by Region' or 'What is the trend of Profit?'",
      chartData: null
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  // जब भी नया मैसेज आए, स्क्रॉल को नीचे ले जाएं
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || currentDataset.length === 0) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { type: 'user', text: userMessage }]);
    setIsTyping(true);

    try {
      // आपके FastAPI बैकएंड पर रिक्वेस्ट (analytics_engine.py को हिट करेगा)
      const response = await storeApi.post('/api/analytics/query', {
        question: userMessage,
        rows: currentDataset // चूँकि डेटा क्लीन हो चुका है, हम इसे सीधे भेज रहे हैं
      });

      const data = response.data;

      // बॉट का रिस्पॉन्स जोड़ें
      setMessages(prev => [...prev, { 
        type: 'bot', 
        text: data.answer || "Here is what I found:", 
        chartData: data.chart_data || null,
        intent: data.intent // e.g., 'predictive', 'compare'
      }]);
    } catch (error) {
      console.error("AI Analytics Error:", error);
      setMessages(prev => [...prev, { 
        type: 'bot', 
        text: "Sorry, I couldn't process that query. Make sure the backend is running.",
        isError: true
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  // डायनामिक चार्ट रेंडर करने का फंक्शन
  const renderChart = (chartData, intent) => {
    if (!chartData || chartData.length === 0) return null;

    // First key is usually the x-axis label (like Category/Date), second is the metric value
    const keys = Object.keys(chartData[0]);
    const xKey = keys[0];
    const yKey = keys[1] || "value";

    // अगर टाइम-सीरीज़ या ट्रेंड पूछा है, तो LineChart दिखाएं
    if (intent === 'predictive' || chartData[0].hasOwnProperty('date') || chartData[0].hasOwnProperty('month') || chartData[0].hasOwnProperty('timestamp')) {
      return (
        <div className="h-72 w-full mt-4 bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey={xKey} tick={{fontSize: 12}} tickLine={false} />
              <YAxis tick={{fontSize: 12}} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
              <Legend />
              <Line type="monotone" dataKey={yKey} stroke="#3b82f6" strokeWidth={3} dot={{r: 4}} activeDot={{ r: 8 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      );
    }

    // बाकी सभी चीज़ों (जैसे Compare) के लिए BarChart दिखाएं
    return (
      <div className="h-72 w-full mt-4 bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis dataKey={xKey} tick={{fontSize: 12}} tickLine={false} />
            <YAxis tick={{fontSize: 12}} tickLine={false} axisLine={false} />
            <Tooltip cursor={{fill: '#f8fafc'}} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
            <Bar dataKey={yKey} fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  return (
    <div className="w-full max-w-7xl mx-auto mt-8 bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden flex flex-col h-[600px] font-sans">
      
      {/* 🚀 Header */}
      <div className="p-5 border-b border-slate-100 bg-slate-900 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500 rounded-lg">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <h2 className="text-xl font-bold text-white">AI Data Analyst</h2>
        </div>
        <p className="text-slate-400 text-sm">Powered by NLP & Polars Engine</p>
      </div>

      {/* 💬 Chat Area */}
      <div className="flex-1 overflow-y-auto p-6 bg-slate-50 space-y-6">
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex gap-4 max-w-[85%] ${msg.type === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              
              {/* Avatar */}
              <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 shadow-sm
                ${msg.type === 'user' ? 'bg-blue-100 text-blue-600' : 'bg-white border border-slate-200 text-slate-700'}`}>
                {msg.type === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-6 h-6" />}
              </div>

              {/* Message Bubble */}
              <div className={`flex flex-col ${msg.type === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`px-5 py-3 rounded-2xl shadow-sm text-[15px] leading-relaxed
                  ${msg.type === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 
                    msg.isError ? 'bg-red-50 text-red-700 border border-red-100 rounded-tl-none' : 
                    'bg-white border border-slate-200 text-slate-800 rounded-tl-none'}`}>
                  {msg.text}
                </div>
                
                {/* 📊 Render Dynamic Chart if AI returned chart_data */}
                {msg.chartData && renderChart(msg.chartData, msg.intent)}
              </div>

            </div>
          </div>
        ))}
        
        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center shrink-0">
                <Bot className="w-6 h-6 text-slate-400" />
              </div>
              <div className="bg-white border border-slate-200 px-5 py-4 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* ⌨️ Input Area */}
      <div className="p-4 bg-white border-t border-slate-100">
        <form onSubmit={handleSendMessage} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your data (e.g., 'Show total sales by category')..."
            className="w-full pl-5 pr-14 py-4 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition text-slate-700"
            disabled={isTyping || currentDataset.length === 0}
          />
          <button 
            type="submit"
            disabled={!input.trim() || isTyping}
            className="absolute right-2 p-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default AnalyticsChat;
