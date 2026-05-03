import React, { useEffect, useRef, useState } from 'react';
import DashboardLayout from '../DashboardLayout';
import apiService from '../api/client';
import { useToast } from '../context/NotificationContext';

export default function RealTimeInsights() {
  const [messages, setMessages] = useState([]);
  const connRef = useRef(null);
  const { error } = useToast();

  useEffect(() => {
    const conn = apiService.realtime.connectInsights({
      onOpen: () => console.log('ws open'),
      onMessage: (ev) => {
        try {
          const data = JSON.parse(ev.data);
          setMessages((m) => [data, ...m].slice(0, 200));
        } catch (err) {
          console.warn('non-json message', ev.data);
        }
      },
      onError: (e) => {
        console.error('ws error', e);
        error('Real-time connection error');
      },
      onClose: () => console.log('ws close'),
    });

    connRef.current = conn;

    return () => {
      try { connRef.current?.close(); } catch (e) {}
    };
  }, [error]);

  return (
    <DashboardLayout>
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-4">Real-time Insights</h1>
        <div className="space-y-2 max-h-[60vh] overflow-auto">
          {messages.length === 0 && <div className="text-sm text-slate-500">Waiting for live insights…</div>}
          {messages.map((m, i) => (
            <div key={i} className="p-2 border-b bg-white dark:bg-slate-800">
              <div className="text-xs text-slate-400">{m.timestamp || ''}</div>
              <div className="font-medium">{m.title || JSON.stringify(m)}</div>
              {m.text && <div className="text-sm mt-1">{m.text}</div>}
            </div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
