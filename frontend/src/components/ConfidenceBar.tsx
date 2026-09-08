import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface ConfidenceBarProps {
  score: number; // 0.0 to 1.0
  className?: string;
  showLabel?: boolean;
}

export function ConfidenceBar({ score, className, showLabel = true }: ConfidenceBarProps) {
  const percentage = Math.round(score * 100);
  
  return (
    <div className={cn("flex flex-col gap-1 w-full", className)}>
      {showLabel && (
        <div className="flex justify-between text-xs font-medium text-ai">
          <span>AI Confidence</span>
          <span>{percentage}%</span>
        </div>
      )}
      <div className="h-2 w-full bg-slate-200 rounded-full overflow-hidden">
        <motion.div 
          className="h-full bg-ai"
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}
