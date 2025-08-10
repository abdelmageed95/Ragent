
import os
import asyncio
from typing import Dict
from tools.wikipedia_tool import search_wikipedia, get_wikipedia_page
from utils.track_progress import progress_callbacks
# LangGraph imports
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
# ===============================
# Chatbot Agent Node (with Wikipedia Tools)
# ===============================
# Create tool list
wikipedia_tools = [search_wikipedia, get_wikipedia_page]

# Streaming helper function
async def send_streaming_response(session_id, partial_response, agent_type="chatbot", tools_used=[]):
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


def chatbot_agent_node(state: Dict) -> Dict:
    """
    Chatbot agent node with Wikipedia tool support
    """
    print("💬 Chatbot Agent Node: Processing conversation...")
    
    try:
        # Initialize LLM with tools
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Bind Wikipedia tools to the LLM
        llm_with_tools = llm.bind_tools(wikipedia_tools)
        
        # Build conversation messages
        messages = []
        
        # System message with context
        system_content = "You are a helpful AI assistant with access to Wikipedia search tools."
        
        memory_context = state.get("memory_context", {})
        context_parts = []
        
        user_facts = memory_context.get("user_facts", {})
        if user_facts:
            facts_str = "\n".join([f"- {k}: {v}" for k, v in user_facts.items()])
            context_parts.append(f"User Profile:\n{facts_str}")
        
        long_term = memory_context.get("long_term", [])
        if long_term:
            long_term_str = "\n".join(long_term[:2])  # Top 2 most relevant
            context_parts.append(f"Relevant past conversations:\n{long_term_str}")
        
        if context_parts:
            system_content += f"\n\nContext:\n{chr(10).join(context_parts)}"
        
        system_content += """
        
        Available tools:
        - search_wikipedia: Search Wikipedia for information on any topic
        - get_wikipedia_page: Get detailed content from a specific Wikipedia page

        Use these tools when users ask about:
        1. Factual information, historical events, people, places, concepts
        2. Current/accurate information that might be beyond your training data  
        3. Specific Wikipedia information requests

        When you use Wikipedia tools:
        - Always integrate the Wikipedia information naturally into your response
        - Provide context and explain the relevance
        - Cite Wikipedia as the source
        - Don't just say "I'll search Wikipedia" - actually use the information in your answer"""

        messages.append(SystemMessage(content=system_content))
        
        # Add recent conversation history
        short_term = memory_context.get("short_term", [])
        for msg in short_term[-6:]:  # Last 6 messages
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Current user message
        messages.append(HumanMessage(content=state["user_message"]))
        
        # Get initial response (may include tool calls)
        response = llm_with_tools.invoke(messages)
        
        # Handle tool calls if present
        tools_used = []
        wikipedia_results = []
        
        if response.tool_calls:
            print(f"🛠️ Using tools: {[tc['name'] for tc in response.tool_calls]}")
            
            # Add the AI response with tool calls
            messages.append(response)
            
            # Execute tools and collect results
            tool_messages = []
            for tool_call in response.tool_calls:
                tools_used.append(tool_call["name"])
                
                # Execute the tool
                if tool_call["name"] == "search_wikipedia":
                    result = search_wikipedia.invoke(tool_call["args"])
                elif tool_call["name"] == "get_wikipedia_page":
                    result = get_wikipedia_page.invoke(tool_call["args"])
                else:
                    result = f"Unknown tool: {tool_call['name']}"
                
                tool_message = ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"]
                )
                tool_messages.append(tool_message)
                wikipedia_results.append({
                    "tool": tool_call["name"],
                    "query": tool_call["args"],
                    "result": result
                })
            
            # Add tool responses to messages
            messages.extend(tool_messages)
            
            # Get final response that incorporates tool results
            final_response = llm.invoke(messages)
            agent_response = final_response.content
            
        else:
            # No tools needed
            agent_response = response.content
        
        metadata = {
            "agent_type": "chatbot",
            "context_used": len(short_term),
            "user_facts_count": len(user_facts),
            "tools_used": tools_used,
            "wikipedia_searches": len(wikipedia_results)
        }
        
        print(f"✅ Chatbot completed (tools: {tools_used})")
        
        return {
            **state,
            "agent_response": agent_response,
            "metadata": {**state.get("metadata", {}), **metadata},
            "tools_used": tools_used,
            "wikipedia_results": wikipedia_results
        }
        
    except Exception as e:
        print(f"❌ Chatbot Agent error: {e}")
        error_msg = "I apologize, but I encountered an error. Please try again."
        return {
            **state,
            "agent_response": error_msg,
            "metadata": {**state.get("metadata", {}), "error": str(e)}
        }

async def enhanced_chatbot_agent_node(state: Dict) -> Dict:
    """Enhanced chatbot agent with progress tracking"""
    session_id = state.get("session_id", "")
    
    await progress_callbacks.notify_progress(
        session_id, "agent", "active", "Processing conversation with AI agent..."
    )
    
    print("💬 Enhanced Chatbot Agent Node: Processing conversation...")
    
    try:
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        llm_with_tools = llm.bind_tools(wikipedia_tools)
        
        # Build conversation messages
        messages = []
        
        system_content = "You are a helpful AI assistant with access to Wikipedia search tools."
        
        memory_context = state.get("memory_context", {})
        context_parts = []
        
        user_facts = memory_context.get("user_facts", {})
        if user_facts:
            facts_str = "\n".join([f"- {k}: {v}" for k, v in user_facts.items()])
            context_parts.append(f"User Profile:\n{facts_str}")
        
        long_term = memory_context.get("long_term", [])
        if long_term:
            long_term_str = "\n".join(long_term[:2])
            context_parts.append(f"Relevant past conversations:\n{long_term_str}")
        
        if context_parts:
            system_content += f"\n\nContext:\n{chr(10).join(context_parts)}"
        
        system_content += """

Available tools:
- search_wikipedia: Search Wikipedia for information on any topic
- get_wikipedia_page: Get detailed content from a specific Wikipedia page

Use these tools when users ask about:
1. Factual information, historical events, people, places, concepts
2. Current/accurate information that might be beyond your training data  
3. Specific Wikipedia information requests

When you use Wikipedia tools:
- Always integrate the Wikipedia information naturally into your response
- Provide context and explain the relevance
- Cite Wikipedia as the source
- Don't just say "I'll search Wikipedia" - actually use the information in your answer"""

        messages.append(SystemMessage(content=system_content))
        
        # Add recent conversation history
        short_term = memory_context.get("short_term", [])
        for msg in short_term[-6:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Current user message
        messages.append(HumanMessage(content=state["user_message"]))
        
        # Get initial response
        response = llm_with_tools.invoke(messages)
        
        # Handle tool calls
        tools_used = []
        wikipedia_results = []
        
        if response.tool_calls:
            print(f"🛠️ Enhanced Chatbot using tools: {[tc['name'] for tc in response.tool_calls]}")
            
            messages.append(response)
            
            tool_messages = []
            for tool_call in response.tool_calls:
                tools_used.append(tool_call["name"])
                
                if tool_call["name"] == "search_wikipedia":
                    result = search_wikipedia.invoke(tool_call["args"])
                elif tool_call["name"] == "get_wikipedia_page":
                    result = get_wikipedia_page.invoke(tool_call["args"])
                else:
                    result = f"Unknown tool: {tool_call['name']}"
                
                tool_message = ToolMessage(
                    content=result,
                    tool_call_id=tool_call["id"]
                )
                tool_messages.append(tool_message)
                wikipedia_results.append({
                    "tool": tool_call["name"],
                    "query": tool_call["args"],
                    "result": result
                })
            
            messages.extend(tool_messages)
            
            # Stream the final response word by word
            agent_response = ""
            
            # Use streaming for final response
            for chunk in llm.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    agent_response += chunk.content
                    # Send streaming update
                    await send_streaming_response(
                        session_id, agent_response, "chatbot", tools_used
                    )
            
            # If no streaming happened, fall back to regular response
            if not agent_response:
                final_response = llm.invoke(messages)
                agent_response = final_response.content
            
        else:
            # No tools needed - stream the response directly
            agent_response = ""
            
            # Use streaming for response
            for chunk in llm.stream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    agent_response += chunk.content
                    # Send streaming update
                    await send_streaming_response(
                        session_id, agent_response, "chatbot", tools_used
                    )
            
            # If no streaming happened, fall back to regular response
            if not agent_response:
                agent_response = response.content
        
        metadata = {
            "agent_type": "chatbot",
            "context_used": len(short_term),
            "user_facts_count": len(user_facts),
            "tools_used": tools_used,
            "wikipedia_searches": len(wikipedia_results)
        }
        
        # Prepare detailed progress message
        details = ["Response generated"]
        if tools_used:
            details.append(f"Used tools: {', '.join(tools_used)}")
        if wikipedia_results:
            details.append(f"Wikipedia searches: {len(wikipedia_results)}")
        
        detail_text = " | ".join(details)
        
        await progress_callbacks.notify_progress(
            session_id, "agent", "completed", detail_text
        )
        
        print(f"✅ Enhanced Chatbot completed (tools: {tools_used})")
        
        return {
            **state,
            "agent_response": agent_response,
            "metadata": {**state.get("metadata", {}), **metadata},
            "tools_used": tools_used,
            "wikipedia_results": wikipedia_results
        }
        
    except Exception as e:
        print(f"❌ Enhanced Chatbot Agent error: {e}")
        await progress_callbacks.notify_progress(
            session_id, "agent", "error", f"Chatbot agent failed: {str(e)}"
        )
        error_msg = "I apologize, but I encountered an error. Please try again."
        return {
            **state,
            "agent_response": error_msg,
            "metadata": {**state.get("metadata", {}), "error": str(e)}
        }