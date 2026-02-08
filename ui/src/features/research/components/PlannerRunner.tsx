import { useWorkflow, useHandler, WorkflowEvent } from "@llamaindex/ui";
import { useEffect, useRef, useState } from "react";
import { WORKFLOWS } from "@/lib/workflows.ts";
import { Send } from "lucide-react";
import { parseInputRequiredEvent } from "../utils";

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

  const onCompleteRef = useRef(onComplete);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

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
        const message = e instanceof Error ? e.message : String(e);
        setStatusText(`Error starting planner: ${message}`);
      }
    }

    void startWorkflow();
  }, [initialQuery, workflow]);

  useEffect(() => {
    if (!handler) return;

    const sub = handler.subscribeToEvents({
      onData: (event: WorkflowEvent) => {
        const rawText = parseInputRequiredEvent(event);

        if (rawText) {
          setMessages((prev) => [...prev, { role: "planner", content: rawText }]);

          setAwaitingHuman(true);
          setStatusText("Waiting for your response...");
          return;
        }

        if (!event.type.endsWith("StopEvent")) return;

        const data = event.data as { result?: unknown };
        const result = data.result as { plan?: string } | undefined;

        if (!result?.plan) return;

        setAwaitingHuman(false);
        setStatusText("Planning complete.");
        if (onCompleteRef.current) {
          onCompleteRef.current(result.plan);
        }
      },
      onError: (err) => {
        console.error("Workflow stream error:", err);
        setStatusText("Stream error occurred.");
      }
    });

    return () => {
      sub.unsubscribe();
    };
  }, [handlerId]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;
    await submitResponse(inputValue);
  };

  const submitResponse = async (response: string) => {
    setMessages((prev) => [...prev, { role: "user", content: response }]);
    setAwaitingHuman(false);
    setStatusText("Planner is thinking...");
    setInputValue(""); // Clear input just in case

    try {
      await handler.sendEvent({
        type: "HumanResponseEvent",
        data: { response },
        timestamp: new Date().toISOString(),
      } as any);
    } catch (e) {
      console.error("Failed to send response:", e);
      setStatusText("Error sending response.");
    }
  };

  return (
    <div className="flex flex-col h-[700px] border border-gray-200 rounded-lg bg-white shadow-sm">
      {/* Header */}
      <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
        <h3 className="font-semibold text-gray-700">Planner Workflow (Real)</h3>
        <span className="text-xs text-gray-500">{handlerId}</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => {
          if (m.role === "planner") {
            return (
              <div key={i} className="flex flex-col gap-1">
                <span className="text-xs font-bold text-purple-600">Planner</span>
                
                {m.content && (
                  <div className="bg-purple-50 p-3 rounded-lg text-sm whitespace-pre-wrap shadow-sm border border-purple-100">
                    {m.content}
                  </div>
                )}
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

      {/* Bottom Area: Chat Input */}
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
    </div>
  );
}
