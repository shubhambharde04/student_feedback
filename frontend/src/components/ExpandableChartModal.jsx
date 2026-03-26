import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

export default function ExpandableChartModal({ title, subtitle, children }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <div className="relative group h-full w-full">
        <div className="h-full w-full">
          {children}
        </div>
        
        <button 
          onClick={() => setIsOpen(true)}
          className="absolute top-2 right-2 p-1.5 bg-surface-800/80 backdrop-blur-md rounded-lg text-surface-300 opacity-0 group-hover:opacity-100 transition-opacity hover:text-white border border-surface-600 shadow-lg z-10"
          title="Expand Chart"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
      </div>

      <AnimatePresence>
        {isOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="absolute inset-0 bg-black/60"
            />
            
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="relative w-full max-w-6xl h-[80vh] flex flex-col bg-surface-900 border border-surface-700 rounded-2xl shadow-2xl overflow-hidden"
            >
              {/* Header */}
              <div className="flex justify-between items-center px-6 py-4 border-b border-surface-700/50 bg-surface-800/50">
                <div>
                  <h3 className="text-xl font-bold text-surface-100 font-display">{title}</h3>
                  {subtitle && <p className="text-sm text-surface-400 mt-0.5">{subtitle}</p>}
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 text-surface-400 hover:text-white bg-surface-800 hover:bg-surface-700 rounded-xl transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Expanded Chart Body */}
              <div className="flex-1 p-6 min-h-0 bg-surface-900">
                <div className="w-full h-full">
                  {children}
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
