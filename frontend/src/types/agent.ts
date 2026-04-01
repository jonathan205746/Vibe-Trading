/** Chat message types */
export type AgentMessageType =
  | "user" | "thinking" | "tool_call" | "tool_result"
  | "answer" | "error" | "run_complete" | "compact";

export interface AgentMessage {
  id: string;
  type: AgentMessageType;
  content: string;
  tool?: string;
  args?: Record<string, string>;
  status?: "running" | "ok" | "error";
  elapsed_ms?: number;
  timestamp: number;
  runId?: string;
  metrics?: Record<string, number>;
  equityCurve?: Array<{ time: string; equity: number | string }>;
  /** Phase label for thinking entries */
  stage?: string;
}

/** Tool call tracking entry */
export interface ToolCallEntry {
  id: string;
  tool: string;
  arguments: Record<string, string>;
  status: "running" | "ok" | "error";
  preview?: string;
  elapsed_ms?: number;
  timestamp: number;
}
