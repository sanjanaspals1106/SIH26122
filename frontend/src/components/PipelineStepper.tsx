import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';

export type PipelineStepId = 'INGEST' | 'EXTRACT' | 'MATCH' | 'VALIDATE' | 'REVIEW' | 'SYNC';

const PIPELINE_STEPS: { id: PipelineStepId; label: string }[] = [
  { id: 'INGEST', label: 'Ingest' },
  { id: 'EXTRACT', label: 'Extract' },
  { id: 'MATCH', label: 'Match' },
  { id: 'VALIDATE', label: 'Validate' },
  { id: 'REVIEW', label: 'Review' },
  { id: 'SYNC', label: 'Sync' },
];

interface PipelineStepperProps {
  currentStep: PipelineStepId;
  failedStep?: PipelineStepId;
  className?: string;
}

export function PipelineStepper({ currentStep, failedStep, className }: PipelineStepperProps) {
  const currentIndex = PIPELINE_STEPS.findIndex((s) => s.id === currentStep);
  const failedIndex = failedStep ? PIPELINE_STEPS.findIndex((s) => s.id === failedStep) : -1;

  return (
    <div className={cn("flex items-center justify-between w-full max-w-3xl", className)}>
      {PIPELINE_STEPS.map((step, index) => {
        const isCompleted = index < currentIndex && index !== failedIndex;
        const isActive = index === currentIndex && !failedStep;
        const isFailed = index === failedIndex;
        
        let circleClass = "bg-slate-200 border-slate-300 text-slate-400";
        if (isCompleted) circleClass = "bg-status-validated border-status-validated text-white";
        else if (isActive) circleClass = "bg-white border-primary text-primary border-2";
        else if (isFailed) circleClass = "bg-status-rejected border-status-rejected text-white";

        return (
          <React.Fragment key={step.id}>
            <div className="relative flex flex-col items-center">
              <motion.div
                layout
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center font-medium text-sm transition-colors duration-300",
                  circleClass,
                  !isActive && !isCompleted && !isFailed && "border-2"
                )}
                initial={false}
                animate={{
                  scale: isActive ? 1.1 : 1,
                }}
              >
                {isCompleted ? <Check className="w-4 h-4" /> : index + 1}
              </motion.div>
              <div className="absolute top-10 w-20 text-center">
                <span className={cn(
                  "text-xs font-medium",
                  isActive || isFailed ? "text-slate-900" : "text-slate-500"
                )}>
                  {step.label}
                </span>
              </div>
            </div>

            {/* Connecting Line */}
            {index < PIPELINE_STEPS.length - 1 && (
              <div className="flex-1 h-1 mx-2 bg-slate-200 rounded overflow-hidden relative">
                {index < currentIndex && index !== failedIndex && (
                  <motion.div
                    className="absolute top-0 left-0 h-full bg-status-validated"
                    initial={{ width: 0 }}
                    animate={{ width: "100%" }}
                    transition={{ duration: 0.4 }}
                  />
                )}
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
