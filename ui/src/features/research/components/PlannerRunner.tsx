import { useWorkflow, useHandler, WorkflowEvent } from "@llamaindex/ui";
import { useEffect, useRef, useState } from "react";
import { WORKFLOWS } from "../../../lib/workflows";
import { Send } from "lucide-react";
import { PlanReviewer } from "./PlanReviewer";
import { parsePlannerFeedbackRequestEvent } from "../utils";

interface Message {
  role: "user" | "planner";
  content: string;
}

export function PlannerRunner({
  initialQuery,
  onComplete,
}: {
  initialQuery: string;
  onComplete: (plan: string) => void;
}) {
  const workflow = useWorkflow(WORKFLOWS.planner);
  const [handlerId, setHandlerId] = useState<string | null>(null);
  const handler = useHandler(handlerId);
  const [messages, setMessages] = useState<Message[]>([
    { role: "user", content: initialQuery },
  ]);
  const [statusText, setStatusText] = useState("Starting planner...");
  const [inputValue, setInputValue] = useState("");
  const [awaitingHuman, setAwaitingHuman] = useState(false);
  
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    async function startWorkflow() {
      try {
        const h = await workflow.createHandler({
          initial_query: initialQuery,
        });
        setHandlerId(h.handler_id);
        setStatusText("Planner is thinking...");
      } catch (e) {
        console.error("Failed to start planner workflow:", e);
        const message = e instanceof Error ? e.message : String(e);
        setStatusText(`Error starting planner: ${message}`);
      }
    }

    startWorkflow();
  }, [initialQuery, workflow]);

  useEffect(() => {
    if (!handlerId || !handler) return;

    const sub = handler.subscribeToEvents({
      onData: (event: WorkflowEvent) => {
        console.log("PlannerRunner event:", event);
        const text = parsePlannerFeedbackRequestEvent(event);
        if (text) {
          setMessages((prev) => [...prev, { role: "planner", content: text }]);
          setAwaitingHuman(true);
          setStatusText("Waiting for your response...");
          return;
        }

        const eventType = event.type;
        const isStop = eventType.endsWith("StopEvent");

        if (isStop) {
          const data = event.data as any;
          const result = data?._data?.result;
          if (result?.plan) {
            setAwaitingHuman(false);
            setStatusText("Planning complete.");
            onComplete?.(result.plan);
          }
        }
      },
      onError: (err) => {
        console.error("Workflow stream error:", err);
        setStatusText("Stream error occurred.");
      }
    });

    return () => sub.unsubscribe();
  }, [handlerId, handler, onComplete]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;
    submitResponse(inputValue);
  };

  const handleReviewResponse = (response: string) => {
    setInputValue(response);
    submitResponse(response);
  };

  const submitResponse = async (response: string) => {
    setMessages((prev) => [...prev, { role: "user", content: response }]);
    setAwaitingHuman(false);
    setStatusText("Planner is thinking...");
    setInputValue(""); // Clear input just in case

    try {
      await handler?.sendEvent({
        name: "HumanResponseEvent",
        response: response,
      });
    } catch (e) {
      console.error("Failed to send response:", e);
      setStatusText("Error sending response.");
    }
  };

  const lastMessage = messages[messages.length - 1];
  const showReviewer = awaitingHuman && lastMessage?.role === "planner";

  return (
    <div className="flex flex-col h-[500px] border border-gray-200 rounded-lg bg-white shadow-sm">
      {/* Header */}
      <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
        <h3 className="font-semibold text-gray-700">Planner Workflow (Real)</h3>
        <span className="text-xs text-gray-500">{handlerId}</span>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => {
          if (showReviewer && i === messages.length - 1) {
             return <PlanReviewer key={i} planText={m.content} onResponse={handleReviewResponse} />;
          }

          if (m.role === "planner") {
            return (
              <div key={i} className="flex flex-col gap-1">
                <span className="text-xs font-bold text-purple-600">Planner</span>
                <div className="bg-purple-50 p-3 rounded-lg text-sm whitespace-pre-wrap shadow-sm border border-purple-100">
                  {m.content}
                </div>
              </div>
            );
          }

          return (
            <div key={i} className="flex flex-col gap-1 items-end">
              <span className="text-xs font-bold text-gray-600">You</span>
              <div className="bg-gray-100 p-3 rounded-lg text-sm whitespace-pre-wrap shadow-sm border border-gray-200">
                {m.content}
              </div>
            </div>
          );
        })}

        <div className="flex flex-col gap-1">
          <span className="text-xs font-bold text-gray-400">Status</span>
          <div className="text-sm text-gray-500 italic animate-pulse">
            {statusText}
          </div>
        </div>
        
        <div ref={(el) => el?.scrollIntoView({ behavior: "smooth" })} />
      </div>

      {/* Input Area */}
      {!showReviewer && (
        <div className="p-4 border-t border-gray-100 bg-gray-50">
          <div className="flex gap-2">
            <input
              type="text"
              className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              placeholder={awaitingHuman ? "Type your response..." : "Waiting for planner..."}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              disabled={!awaitingHuman}
            />
            <button
              onClick={handleSend}
              disabled={!awaitingHuman || !inputValue.trim()}
              className="bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
