/**
 * LlamaStack Streaming Constants
 *
 * These constants define the event types and item types used in LlamaStack's
 * streaming responses API, based on the OpenAI Responses API specification.
 *
 * Reference: llama-stack/src/llama_stack/apis/agents/openai_responses.py
 */

/**
 * Streaming Event Types
 *
 * These are the top-level event types sent in Server-Sent Events (SSE) format.
 * Format: response.<category>.<action>
 */
export const StreamEventType = {
  // Text content streaming
  OUTPUT_TEXT_DELTA: 'response.output_text.delta',

  // Reasoning content streaming (for models with extended thinking)
  REASONING_TEXT_DELTA: 'response.reasoning_text.delta',
  REASONING_TEXT_DONE: 'response.reasoning_text.done',

  // Output item lifecycle
  OUTPUT_ITEM_ADDED: 'response.output_item.added',
  OUTPUT_ITEM_DONE: 'response.output_item.done',

  // Tool call argument streaming
  MCP_CALL_ARGUMENTS_DONE: 'response.mcp_call.arguments.done',
  FUNCTION_CALL_ARGUMENTS_DONE: 'response.function_call.arguments.done',

  // Response lifecycle
  RESPONSE_CREATED: 'response.created',
  RESPONSE_IN_PROGRESS: 'response.in_progress',
  RESPONSE_COMPLETED: 'response.completed',
  RESPONSE_FAILED: 'response.failed',
  RESPONSE_INCOMPLETE: 'response.incomplete',

  // Content parts
  CONTENT_PART_ADDED: 'response.content_part.added',
  CONTENT_PART_DONE: 'response.content_part.done',

  // MCP tool discovery
  MCP_LIST_TOOLS_IN_PROGRESS: 'response.mcp_list_tools.in_progress',
  MCP_LIST_TOOLS_COMPLETED: 'response.mcp_list_tools.completed',

  // Errors
  ERROR: 'error',
} as const;

export type StreamEventTypeValue = (typeof StreamEventType)[keyof typeof StreamEventType];

/**
 * Output Item Types
 *
 * These are the discriminator values for items in output_item.added/done events.
 * Each type represents a different kind of output item in the response.
 */
export const OutputItemType = {
  // Message item - the assistant's text response
  MESSAGE: 'message',

  // MCP (Model Context Protocol) items
  MCP_CALL: 'mcp_call', // Actual MCP tool execution
  MCP_LIST_TOOLS: 'mcp_list_tools', // MCP tool discovery (not an execution)
  MCP_APPROVAL_REQUEST: 'mcp_approval_request', // Request for human approval

  // Function/tool execution items
  FUNCTION_CALL: 'function_call', // Client-side function execution
  WEB_SEARCH_CALL: 'web_search_call', // Web search tool execution
  FILE_SEARCH_CALL: 'file_search_call', // File/knowledge search execution
} as const;

export type OutputItemTypeValue = (typeof OutputItemType)[keyof typeof OutputItemType];

/**
 * Tool Execution Types
 *
 * Subset of OutputItemType that represents actual tool executions.
 * These should be displayed as tool calls in the UI.
 */
export const TOOL_EXECUTION_TYPES = [
  OutputItemType.MCP_CALL,
  OutputItemType.FUNCTION_CALL,
  OutputItemType.WEB_SEARCH_CALL,
  OutputItemType.FILE_SEARCH_CALL,
] as const;

export type ToolExecutionType = (typeof TOOL_EXECUTION_TYPES)[number];

/**
 * Structural Item Types
 *
 * Subset of OutputItemType that represents structural/metadata items.
 * These should NOT be displayed as tool calls in the UI.
 */
export const STRUCTURAL_ITEM_TYPES = [
  OutputItemType.MESSAGE,
  OutputItemType.MCP_LIST_TOOLS,
  OutputItemType.MCP_APPROVAL_REQUEST,
] as const;

export type StructuralItemType = (typeof STRUCTURAL_ITEM_TYPES)[number];

/**
 * Type guard to check if an item type is a tool execution
 */
export function isToolExecutionType(itemType: string | undefined): itemType is ToolExecutionType {
  if (!itemType) return false;
  return TOOL_EXECUTION_TYPES.includes(itemType as ToolExecutionType);
}

/**
 * Type guard to check if an item type is structural
 */
export function isStructuralItemType(itemType: string | undefined): itemType is StructuralItemType {
  if (!itemType) return false;
  return STRUCTURAL_ITEM_TYPES.includes(itemType as StructuralItemType);
}
