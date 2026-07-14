import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { 
  Search, Table, Activity, Sliders, PieChart, 
  Sparkles, Calendar, FileBarChart2, ClipboardList, 
  GitBranch, LogOut, Moon, Palette 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const { toggle } = useTheme();
  
  const inputRef = useRef(null);

  // Command items
  const commands = [
    { name: 'Go to Data Workspace', icon: Table, action: () => navigate('/') },
    { name: 'Go to Data Profiling', icon: Activity, action: () => navigate('/profiling') },
    { name: 'Go to Data Prep Studio', icon: Sliders, action: () => navigate('/preparation') },
    { name: 'Go to Visualization Intelligence', icon: PieChart, action: () => navigate('/graphs') },
    { name: 'Go to Predictive Analytics', icon: Sparkles, action: () => navigate('/predictive') },
    { name: 'Go to Report Builder', icon: FileBarChart2, action: () => navigate('/reports') },
    { name: 'Go to Workflow Builder', icon: GitBranch, action: () => navigate('/workflows') },
    { name: 'Go to Schedule Exports', icon: Calendar, action: () => navigate('/schedule') },
    { name: 'Toggle Theme', icon: Moon, action: () => toggle() },
    { name: 'Logout Profile', icon: LogOut, action: () => logout() }
  ];

  // Filter commands
  const filtered = commands.filter(cmd => 
    cmd.name.toLowerCase().includes(search.toLowerCase())
  );

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setSearch('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % filtered.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filtered.length) % filtered.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
        setIsOpen(false);
      }
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
          {/* Backdrop */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-md"
          />

          {/* Dialog content */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.97, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -8 }}
            className="relative w-full max-w-xl bg-white dark:bg-neutral-850 border border-slate-200 dark:border-neutral-700 rounded-3xl shadow-2xl overflow-hidden font-sans mx-4"
          >
            <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-100 dark:border-neutral-700">
              <Search className="w-5 h-5 text-slate-400 shrink-0" />
              <input
                ref={inputRef}
                type="text"
                placeholder="Type a command or search page..."
                className="w-full bg-transparent border-0 outline-none focus:ring-0 text-slate-800 dark:text-white text-sm"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setSelectedIndex(0);
                }}
                onKeyDown={handleKeyDown}
              />
              <span className="px-2 py-1 bg-slate-100 dark:bg-neutral-800 text-slate-400 rounded-md text-[9px] font-black uppercase shrink-0">ESC</span>
            </div>

            <div className="max-h-80 overflow-y-auto p-2">
              {filtered.length > 0 ? (
                <div className="flex flex-col gap-1">
                  {filtered.map((cmd, idx) => {
                    const IconComponent = cmd.icon;
                    const active = idx === selectedIndex;
                    return (
                      <button
                        key={cmd.name}
                        onClick={() => {
                          cmd.action();
                          setIsOpen(false);
                        }}
                        onMouseEnter={() => setSelectedIndex(idx)}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-left transition ${active ? 'bg-indigo-600 text-white' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-neutral-800'}`}
                      >
                        <IconComponent className={`w-4 h-4 ${active ? 'text-white' : 'text-slate-400'}`} />
                        <span className="text-xs font-bold">{cmd.name}</span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="p-6 text-center text-xs text-slate-400 font-bold">
                  No matching commands found.
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
