import { WorkflowEvent } from "@llamaindex/ui";

export function parseInputRequiredEvent(event: WorkflowEvent): string | null {
  const eventType = event.type;
  if (!eventType.endsWith("InputRequiredEvent")) {
    return null;
  }

  const data = event.data as any;
  const prefix = data?.prefix || data?._data?.prefix;
  if (typeof prefix === "string" && prefix.length > 0) {
    return prefix;
  }
  return null;
}
