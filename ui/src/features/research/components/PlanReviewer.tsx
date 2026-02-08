import React, { useState, useEffect } from "react";
import { Check, X, Sparkles, Send } from "lucide-react";
import { cn } from "@/lib/utils.ts";

interface Step {
  id: number;
  description: string;
  status: "enabled" | "disabled";
  originalText: string;
}

interface PlanReviewerProps {
  planText: string;
  onResponse: (response: string) => void;
}

const StepContainer = ({ children }: { children: React.ReactNode }) => (
  <div
    className={cn(
      "relative flex flex-col w-full max-w-2xl mx-auto p-6 rounded-xl shadow-lg backdrop-blur-sm transition-all duration-300",
      "bg-gradient-to-br from-white via-gray-50 to-white text-gray-800 border border-gray-200/80",
      "dark:bg-gradient-to-br dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 dark:text-white dark:border-slate-700/50 dark:shadow-2xl"
    )}
  >
    {children}
  </div>
);

const StepHeader = ({
  enabledCount,
  totalCount,
  showStatus = false,
}: {
  enabledCount: number;
  totalCount: number;
  showStatus?: boolean;
}) => (
  <div className="mb-5">
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
        Review Research Plan
      </h2>
      <div className="flex items-center gap-3">
        <div className="text-sm text-gray-500 dark:text-slate-400">
          {enabledCount}/{totalCount} Selected
        </div>
        {showStatus && (
          <div className="text-xs px-2 py-1 rounded-full font-medium bg-blue-50 text-blue-600 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-500/30">
            Ready
          </div>
        )}
      </div>
    </div>

    <div className="relative h-2 rounded-full overflow-hidden bg-gray-200 dark:bg-slate-700">
      <div
        className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
        style={{ width: `${totalCount > 0 ? (enabledCount / totalCount) * 100 : 0}%` }}
      />
    </div>
  </div>
);

const StepItem = ({
  step,
  onToggle,
}: {
  step: Step;
  onToggle: () => void;
}) => (
  <div
    className={cn(
      "flex items-start p-3 rounded-lg transition-all duration-300 cursor-pointer group",
      step.status === "enabled"
        ? "bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200/60 dark:from-blue-900/20 dark:to-purple-900/10 dark:border-blue-500/30"
        : "bg-gray-50/50 border border-gray-200/40 dark:bg-slate-800/30 dark:border-slate-600/30 hover:bg-gray-100 dark:hover:bg-slate-800/50"
    )}
    onClick={onToggle}
  >
    <div className="relative mt-1">
      <div
        className={cn(
          "w-5 h-5 rounded border-2 flex items-center justify-center transition-all duration-200",
          step.status === "enabled"
            ? "bg-gradient-to-br from-blue-500 to-purple-600 border-blue-500"
            : "border-gray-300 bg-white dark:border-slate-400 dark:bg-slate-700"
        )}
      >
        {step.status === "enabled" && <Check className="w-3 h-3 text-white" />}
      </div>
    </div>
    <span
      className={cn(
        "ml-3 text-sm font-medium transition-all duration-300 leading-relaxed",
        step.status !== "enabled"
          ? "line-through text-gray-400 dark:text-slate-500"
          : "text-gray-800 dark:text-white"
      )}
    >
      {step.description}
    </span>
  </div>
);

const ActionButton = ({
  variant,
  onClick,
  children,
  disabled,
}: {
  variant: "primary" | "secondary" | "danger" | "success";
  onClick: () => void;
  children: React.ReactNode;
  disabled?: boolean;
}) => {
  const baseClasses =
    "px-6 py-2.5 rounded-lg font-semibold transition-all duration-200 flex items-center justify-center gap-2 text-sm";
  const enabledClasses = "hover:scale-105 shadow-md hover:shadow-lg active:scale-95";
  const disabledClasses = "opacity-50 cursor-not-allowed";

  const variants = {
    primary:
      "bg-gradient-to-r from-purple-500 to-purple-700 hover:from-purple-600 hover:to-purple-800 text-white shadow-lg hover:shadow-xl",
    secondary:
      "bg-gray-100 hover:bg-gray-200 text-gray-800 border border-gray-300 hover:border-gray-400 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-white dark:border-slate-600 dark:hover:border-slate-500",
    success:
      "bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white shadow-lg hover:shadow-xl",
    danger:
      "bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white shadow-lg hover:shadow-xl",
  };

  return (
    <button
      className={cn(baseClasses, disabled ? disabledClasses : enabledClasses, variants[variant])}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
};

const DecorativeElements = ({ variant = "default" }: { variant?: "default" | "success" | "danger" }) => (
  <>
    <div
      className={cn(
        "absolute top-3 right-3 w-16 h-16 rounded-full blur-xl pointer-events-none",
        variant === "success"
          ? "bg-gradient-to-br from-green-200/30 to-emerald-200/30 dark:from-green-500/10 dark:to-emerald-500/10"
          : variant === "danger"
            ? "bg-gradient-to-br from-red-200/30 to-pink-200/30 dark:from-red-500/10 dark:to-pink-500/10"
            : "bg-gradient-to-br from-blue-200/30 to-purple-200/30 dark:from-blue-500/10 dark:to-purple-500/10"
      )}
    />
    <div
      className={cn(
        "absolute bottom-3 left-3 w-12 h-12 rounded-full blur-xl pointer-events-none",
        variant === "default"
          ? "bg-gradient-to-br from-purple-200/30 to-pink-200/30 dark:from-purple-500/10 dark:to-pink-500/10"
          : "opacity-50"
      )}
    />
  </>
);

export function PlanReviewer({ planText, onResponse }: PlanReviewerProps) {
  const [steps, setSteps] = useState<Step[]>([]);
  const [preamble, setPreamble] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [feedbackText, setFeedbackText] = useState("");

  useEffect(() => {
    // Parse the plan text
    const lines = planText.split("\n");
    const parsedSteps: Step[] = [];
    let currentPreamble = "";
    let foundSteps = false;

    lines.forEach((line) => {
      const trimmed = line.trim();
      // Match numbered list items (e.g., "1. Step description")
      const match = trimmed.match(/^(\d+)\.\s+(.*)/);
      
      if (match) {
        foundSteps = true;
        parsedSteps.push({
          id: parsedSteps.length,
          description: match[2],
          status: "enabled",
          originalText: line,
        });
      } else if (!foundSteps && trimmed) {
        currentPreamble += line + "\n";
      }
    });

    if (parsedSteps.length > 0) {
      setSteps(parsedSteps);
      setPreamble(currentPreamble.trim());
    } else {
      // Fallback if no structured steps found
      setPreamble(planText);
    }
  }, [planText]);

  const handleToggle = (index: number) => {
    setSteps((prev) =>
      prev.map((step, i) =>
        i === index
          ? { ...step, status: step.status === "enabled" ? "disabled" : "enabled" }
          : step
      )
    );
  };

  const handleConfirm = () => {
    const enabledSteps = steps.filter((s) => s.status === "enabled");
    
    // If all steps are enabled, just accept
    if (enabledSteps.length === steps.length) {
      onResponse("accept");
      return;
    }

    // If some steps are disabled, construct feedback
    const feedback = 
      "Please update the plan to include ONLY these steps:\n" +
      enabledSteps.map((s, i) => `${i + 1}. ${s.description}`).join("\n");
    
    onResponse(feedback);
  };

  const handleRequestChanges = () => {
    setIsEditing(true);
  };

  const handleSubmitFeedback = () => {
    if (feedbackText.trim()) {
      onResponse(feedbackText);
    }
  };

  if (isEditing) {
    return (
      <StepContainer>
        <div className="mb-4">
          <h2 className="text-xl font-bold text-gray-800 dark:text-white mb-2 relative z-10">
            Request Changes
          </h2>
          <p className="text-sm text-gray-500 dark:text-slate-400 relative z-10">
            Describe how you want to modify the plan.
          </p>
        </div>
        <textarea
          className="w-full h-32 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-slate-900 dark:border-slate-700 dark:text-white resize-none mb-4 relative z-10"
          placeholder="E.g., Add a step about market analysis..."
          value={feedbackText}
          onChange={(e) => setFeedbackText(e.target.value)}
          autoFocus
        />
        <div className="flex justify-end gap-3 relative z-10">
          <ActionButton variant="secondary" onClick={() => setIsEditing(false)}>
            Cancel
          </ActionButton>
          <ActionButton 
            variant="primary" 
            onClick={handleSubmitFeedback}
            disabled={!feedbackText.trim()}
          >
            <Send className="w-4 h-4" />
            Submit Feedback
          </ActionButton>
        </div>
        <DecorativeElements />
      </StepContainer>
    );
  }

  if (steps.length === 0) {
    // Fallback view for unstructured plans
    return (
      <StepContainer>
        <div className="prose dark:prose-invert max-w-none mb-6 text-sm">
          <h3 className="font-semibold mb-2 text-gray-700 dark:text-slate-300 relative z-10">Proposed Plan</h3>
          <div className="whitespace-pre-wrap bg-gray-50 dark:bg-slate-900 p-4 rounded-lg border border-gray-100 dark:border-slate-800 relative z-10">
            {preamble || planText}
          </div>
        </div>
        <div className="flex justify-end gap-3 relative z-10">
          <ActionButton variant="secondary" onClick={handleRequestChanges}>
            Reply / Edit
          </ActionButton>
          <ActionButton variant="success" onClick={() => onResponse("accept")}>
            <Check className="w-4 h-4" />
            Accept Plan
          </ActionButton>
        </div>
        <DecorativeElements />
      </StepContainer>
    );
  }

  const enabledCount = steps.filter((s) => s.status === "enabled").length;

  return (
    <StepContainer>
      {preamble && (
        <div className="mb-4 text-sm text-gray-600 dark:text-slate-400 italic border-l-4 border-blue-500 pl-3 py-1 bg-blue-50/50 dark:bg-blue-900/10 rounded-r relative z-10">
          {preamble.replace("Current Plan:", "").trim()}
        </div>
      )}

      <StepHeader enabledCount={enabledCount} totalCount={steps.length} />

      <div className="space-y-3 mb-6 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar relative z-10">
        {steps.map((step, index) => (
          <StepItem
            key={index}
            step={step}
            onToggle={() => handleToggle(index)}
          />
        ))}
      </div>

      <div className="flex flex-col sm:flex-row justify-center gap-4 pt-4 border-t border-gray-100 dark:border-slate-700 relative z-10">
        <ActionButton variant="secondary" onClick={handleRequestChanges}>
          <X className="w-4 h-4" />
          Reject / Edit
        </ActionButton>
        
        <ActionButton 
          variant="success" 
          onClick={handleConfirm}
          disabled={enabledCount === 0}
        >
          <Sparkles className="w-4 h-4" />
          {enabledCount === steps.length ? "Confirm Plan" : `Confirm (${enabledCount} Steps)`}
        </ActionButton>
      </div>
      <DecorativeElements />
    </StepContainer>
  );
}
