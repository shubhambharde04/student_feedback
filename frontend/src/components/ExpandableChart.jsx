import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Maximize2, X } from 'lucide-react';

export default function ExpandableChart({ title, children, isActive, onActivate }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleExpand = (e) => {
    e.stopPropagation();
    setIsExpanded(true);
  };

  const handleClose = (e) => {
    e.stopPropagation();
    setIsExpanded(false);
  };

  return (
    <>
      {/* Base Card */}
      <motion.div
        layoutId={`chart-container-${title}`}
        className={`glass-card p-6 relative transition-all duration-300 cursor-pointer
          ${isActive === false ? 'opacity-50 grayscale-[50%]' : ''} 
          ${isActive === true ? 'ring-2 ring-primary-500 scale-[1.02]' : ''}`}
        onClick={onActivate}
        whileHover={{ scale: isActive ? 1.02 : 1.01 }}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-surface-100 font-display">{title}</h3>
          <button
            onClick={handleExpand}
            className="text-surface-400 hover:text-primary-400 transition-colors p-1"
            title="Expand Chart"
          >
            <Maximize2 size={18} />
          </button>
        </div>
        <div className="h-[300px] w-full cursor-default" onClick={(e) => e.stopPropagation()}>
          {children}
        </div>
      </motion.div>

      {/* Expanded Modal */}
      <AnimatePresence>
        {isExpanded && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={handleClose}
              className="absolute inset-0 bg-surface-900/80 backdrop-blur-sm"
            />
            
            <motion.div
              layoutId={`chart-container-${title}`}
              className="glass-card relative w-full h-full max-w-6xl max-h-[80vh] flex flex-col pt-16 p-8 z-10 shadow-2xl"
            >
              <button
                onClick={handleClose}
                className="absolute top-4 right-4 text-surface-400 hover:text-accent-rose bg-surface-800 rounded-full p-2 transition-colors z-20"
              >
                <X size={24} />
              </button>
              
              <h2 className="absolute top-6 left-8 text-2xl font-bold text-surface-100 font-display">
                {title}
              </h2>
              
              <div className="flex-1 w-full mt-4">
                {children}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
