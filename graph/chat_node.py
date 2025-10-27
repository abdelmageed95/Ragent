"""
Chatbot agent node for LangGraph workflow
Handles conversation with Wikipedia tools, progress tracking, and streaming
"""
import os
from typing import Dict
from tools.wikipedia_tool import search_wikipedia, get_wikipedia_page
from tools.serper_tool import search_web, search_news
from tools.calculator_tool import calculate, convert_units
from tools.datetime_tool import (
    get_current_datetime,
    calculate_date_difference,
    add_days_to_date,
    get_day_of_week,
    convert_timezone,
    get_calendar_month,
    time_until_date
)
from tools.google_calendar_tool import (
    get_calendar_events,
    create_calendar_event,
    calendar_tool
)
from utils.track_progress import progress_callbacks

# LangGraph imports
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage
)
from langchain_openai import ChatOpenAI


# ===============================
# Chatbot Agent Node
# ===============================

# Create comprehensive tool list
all_chatbot_tools = [
    # Wikipedia tools
    search_wikipedia,
    get_wikipedia_page,

    # Web search tools
    search_web,
    search_news,

    # Calculator tools
    calculate,
    convert_units,

    # DateTime/Calendar tools
    get_current_datetime,
    calculate_date_difference,
    add_days_to_date,
    get_day_of_week,
    convert_timezone,
    get_calendar_month,
    time_until_date,

    # Google Calendar tools
    get_calendar_events,
    create_calendar_event
]


# Streaming helper function
async def send_streaming_response(
    session_id,
    partial_response,
    agent_type="chatbot",
    tools_used=[]
):
    """Send a partial response via progress callback for streaming"""
    try:
        await progress_callbacks.notify_progress(
            session_id, "streaming", "partial", {
                "partial_response": partial_response,
                "agent_type": agent_type,
                "tools_used": tools_used
            }
        )
    except Exception as e:
        print(f"Error sending streaming response: {e}")


async def chatbot_agent_node(state: Dict) -> Dict:
    """Chatbot agent with progress tracking and streaming"""
    session_id = state.get("session_id", "")

    await progress_callbacks.notify_progress(
        session_id,
        "agent",
        "active",
        "Processing conversation with AI agent..."
    )

    print("💬 Chatbot Agent Node: Processing conversation...")

    try:
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        llm_with_tools = llm.bind_tools(all_chatbot_tools)

        # Build conversation messages
        messages = []

        system_content = (
            "You are a helpful AI assistant with access to multiple tools "
            "for information retrieval, calculations, and date/time operations."
        )

        memory_context = state.get("memory_context", {})
        context_parts = []

        user_facts = memory_context.get("user_facts", {})
        if user_facts:
            facts_str = "\n".join([
                f"- {k}: {v}"
                for k, v in user_facts.items()
            ])
            context_parts.append(f"User Profile:\n{facts_str}")

        long_term = memory_context.get("long_term", [])
        if long_term:
            long_term_str = "\n".join(long_term[:2])
            context_parts.append(
                f"Relevant past conversations:\n{long_term_str}"
            )

        if context_parts:
            system_content += f"\n\nContext:\n{chr(10).join(context_parts)}"

        system_content += """

Available tools organized by category:

📚 INFORMATION & RESEARCH:
- search_web: Real-time web search via Google for current info, news, facts
- search_news: Search for latest news articles on any topic
- search_wikipedia: Search Wikipedia for encyclopedic information
- get_wikipedia_page: Get detailed content from Wikipedia pages

🧮 CALCULATIONS:
- calculate: Evaluate math expressions (arithmetic, trig, log, percentages)
- convert_units: Convert between units (length, weight, temperature, time, data)

📅 DATE & TIME:
- get_current_datetime: Get current date/time in any timezone
- calculate_date_difference: Calculate days/weeks between dates
- add_days_to_date: Add/subtract days from a date
- get_day_of_week: Find what day a date falls on
- convert_timezone: Convert times between timezones
- get_calendar_month: Display a calendar for any month
- time_until_date: Calculate time remaining until a future date

📆 GOOGLE CALENDAR & MEETINGS:
- get_calendar_events: View calendar events for a specific date or range
- create_calendar_event: Create meeting proposals (requires user approval)

WHEN TO USE TOOLS:
- Web search: Current events, recent news, real-time data, verification
- Wikipedia: Historical facts, biographies, concepts, established knowledge
- Calculator: Math problems, unit conversions, percentages
- DateTime: Scheduling, date calculations, timezone queries
- Calendar: View/create meetings, check schedule (Google Calendar integration)

IMPORTANT:
- Use tools proactively when they would help answer the question
- Integrate tool results naturally into your response
- Cite sources when using web search or Wikipedia
- For calculations, show the formula and result clearly
- Calendar events require HUMAN APPROVAL before creation
- When creating calendar events, explain the approval process to the user"""

        messages.append(SystemMessage(content=system_content))

        # Add recent conversation history
        short_term = memory_context.get("short_term", [])
        for msg in short_term[-6:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        # Current user message
        user_msg = state["user_message"]
        messages.append(HumanMessage(content=user_msg))

        # Check for calendar approval/rejection commands
        user_msg_lower = user_msg.lower()
        calendar_approval_handled = False

        # Handle approval/rejection (with or without explicit proposal ID)
        if "approve" in user_msg_lower or "reject" in user_msg_lower or user_msg_lower in ["yes", "ok", "confirm"]:
            # Extract proposal ID from message
            words = user_msg.split()
            prop_id = None

            # Try to find explicit proposal ID
            for i, word in enumerate(words):
                if "proposal" in word.lower() and i + 1 < len(words):
                    prop_id = words[i + 1].strip('.,!?')
                    break
                elif word.startswith("proposal_"):
                    prop_id = word.strip('.,!?')
                    break

            # If no explicit ID, try to get the most recent pending proposal
            if not prop_id:
                pending = calendar_tool.get_pending_actions()
                if pending:
                    prop_id = pending[-1].get('id')  # Get most recent

            if prop_id:
                if "approve" in user_msg_lower or user_msg_lower in ["yes", "ok", "confirm", "approved"]:
                    result = calendar_tool.approve_action(prop_id)
                    if result["status"] == "success":
                        event = result.get("event", {})
                        agent_response = (
                            f"✅ Event '{event.get('summary')}' has been created successfully!\n\n"
                            f"📅 **Event Details:**\n"
                            f"- Start: {event.get('start')}\n"
                            f"- End: {event.get('end')}\n"
                            f"- Calendar Link: {event.get('link')}\n"
                        )
                        if event.get('meet_link'):
                            agent_response += f"- Google Meet: {event.get('meet_link')}\n"
                        calendar_approval_handled = True
                    else:
                        agent_response = f"❌ Error approving event: {result.get('message', 'Unknown error')}"
                        calendar_approval_handled = True
                else:
                    result = calendar_tool.reject_action(prop_id, reason="User rejected")
                    agent_response = f"❌ Proposal {prop_id} has been rejected."
                    calendar_approval_handled = True

        if not calendar_approval_handled:
            # Get initial response
            response = llm_with_tools.invoke(messages)
        else:
            response = None

        # Handle tool calls
        tools_used = []
        tool_results = []  # Renamed from wikipedia_results for generality

        # If calendar approval was handled, skip tool processing
        if calendar_approval_handled:
            # Already have agent_response from approval/rejection
            pass
        elif response and response.tool_calls:
            # Create tool name to function mapping
            tool_map = {tool.name: tool for tool in all_chatbot_tools}
            print(
                f"🛠️  Chatbot using tools: "
                f"{[tc['name'] for tc in response.tool_calls]}"
            )

            messages.append(response)

            tool_messages = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tools_used.append(tool_name)

                # Invoke the tool dynamically
                if tool_name in tool_map:
                    try:
                        result = tool_map[tool_name].invoke(tool_call["args"])
                    except Exception as e:
                        result = f"Error using {tool_name}: {str(e)}"
                else:
                    result = f"Unknown tool: {tool_name}"

                tool_message = ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"]
                )
                tool_messages.append(tool_message)
                tool_results.append({
                    "tool": tool_name,
                    "query": tool_call["args"],
                    "result": result
                })

            messages.extend(tool_messages)

            # Stream the final response word by word
            agent_response = ""

            # Use streaming with optimized chunking
            chunk_buffer = ""
            word_count = 0

            for chunk in llm.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    agent_response += chunk.content
                    chunk_buffer += chunk.content

                    # Count words to batch updates (send every ~5-10 words)
                    word_count += len(chunk.content.split())

                    # Send update every 8-12 words or if buffer ends
                    # with sentence
                    if (word_count >= 8 or
                            chunk.content.strip().endswith(
                                ('.', '!', '?', '\n')
                            )):
                        await send_streaming_response(
                            session_id,
                            agent_response,
                            "chatbot",
                            tools_used
                        )
                        chunk_buffer = ""
                        word_count = 0

            # Send final update if there's remaining content
            if chunk_buffer.strip():
                await send_streaming_response(
                    session_id,
                    agent_response,
                    "chatbot",
                    tools_used
                )

            # If no streaming happened, fall back to regular response
            if not agent_response:
                final_response = llm.invoke(messages)
                agent_response = final_response.content

        else:
            # No tools needed - stream the response directly
            agent_response = ""

            # Use streaming with optimized chunking
            chunk_buffer = ""
            word_count = 0

            for chunk in llm.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    agent_response += chunk.content
                    chunk_buffer += chunk.content

                    # Count words to batch updates
                    word_count += len(chunk.content.split())

                    # Send update every 8-12 words or if buffer ends
                    # with sentence
                    if (word_count >= 8 or
                            chunk.content.strip().endswith(
                                ('.', '!', '?', '\n')
                            )):
                        await send_streaming_response(
                            session_id,
                            agent_response,
                            "chatbot",
                            tools_used
                        )
                        chunk_buffer = ""
                        word_count = 0

            # Send final update if there's remaining content
            if chunk_buffer.strip():
                await send_streaming_response(
                    session_id,
                    agent_response,
                    "chatbot",
                    tools_used
                )

            # If no streaming happened, fall back
            if not agent_response:
                agent_response = response.content

        metadata = {
            "agent_type": "chatbot",
            "context_used": len(short_term),
            "user_facts_count": len(user_facts),
            "tools_used": tools_used,
            "tool_calls_count": len(tool_results)
        }

        # Prepare detailed progress message
        details = ["Response generated"]
        if tools_used:
            details.append(f"Used tools: {', '.join(tools_used)}")
        if tool_results:
            details.append(f"Tool calls: {len(tool_results)}")

        detail_text = " | ".join(details)

        await progress_callbacks.notify_progress(
            session_id,
            "agent",
            "completed",
            detail_text
        )

        print(f"✅ Chatbot completed (tools: {tools_used})")

        return {
            **state,
            "agent_response": agent_response,
            "metadata": {**state.get("metadata", {}), **metadata},
            "tools_used": tools_used,
            "tool_results": tool_results  # Changed from wikipedia_results
        }

    except Exception as e:
        print(f"❌ Chatbot Agent error: {e}")
        await progress_callbacks.notify_progress(
            session_id,
            "agent",
            "error",
            f"Chatbot agent failed: {str(e)}"
        )
        error_msg = (
            "I apologize, but I encountered an error. "
            "Please try again."
        )
        return {
            **state,
            "agent_response": error_msg,
            "metadata": {**state.get("metadata", {}), "error": str(e)}
        }
