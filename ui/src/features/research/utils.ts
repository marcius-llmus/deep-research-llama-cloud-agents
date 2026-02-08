import { WorkflowEvent } from "@llamaindex/ui";

export function parsePlannerFeedbackRequestEvent(event: WorkflowEvent): string | null {
  const eventType = event.type;
  if (!eventType.endsWith("InputRequiredEvent")) {
    return null;
  }

  const data = event.data as any;
  const prefix = data?._data?.prefix;
  if (typeof prefix === "string" && prefix.length > 0) {
    return prefix;
  }
  return null;
}

export function splitBackendPayload(text: string): {
  plan: string | null;
  message: string;
} {
  const PLAN_MARKER = "Current Plan:";
  const SEPARATOR_REGEX = /\n-{3,}\n/;

  if (text.includes(PLAN_MARKER) && SEPARATOR_REGEX.test(text)) {
    const parts = text.split(SEPARATOR_REGEX);
    const planPart = parts[0].replace(PLAN_MARKER, "").trim();
    // The rest is the message + instructions
    const messagePart = parts.slice(1).join("\n").trim();
    
    return { plan: planPart, message: messagePart };
  }

  return { plan: null, message: text };
}
