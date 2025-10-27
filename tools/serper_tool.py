"""
Google Serper API tool for web search
Provides real-time web search capabilities via serper.dev
"""
import os
import requests
from typing import Optional
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


@tool
def search_web(query: str, num_results: int = 5) -> str:
    """
    Search the web using Google Serper API for current information.

    Use this tool when you need:
    - Current news, events, or recent information
    - Real-time data (stock prices, weather, sports scores)
    - Information beyond your training data cutoff
    - Verification of facts or current statistics

    Args:
        query: The search query string
        num_results: Number of results to return (default: 5, max: 10)

    Returns:
        Formatted string with search results including titles, snippets, and URLs
    """
    if not SERPER_API_KEY:
        return (
            "Error: SERPER_API_KEY not configured. "
            "Please add it to your .env file. "
            "Get your API key from https://serper.dev"
        )

    try:
        # Serper API endpoint
        url = "https://google.serper.dev/search"

        # Prepare request
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "q": query,
            "num": min(num_results, 10)  # Max 10 results
        }

        # Make API call
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Format results
        results = []

        # Add knowledge graph if available
        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            results.append(
                f"📊 Knowledge Graph:\n"
                f"Title: {kg.get('title', 'N/A')}\n"
                f"Type: {kg.get('type', 'N/A')}\n"
                f"Description: {kg.get('description', 'N/A')}\n"
            )

        # Add organic search results
        if "organic" in data:
            results.append("\n🔍 Search Results:")
            for i, result in enumerate(data["organic"][:num_results], 1):
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No description")
                link = result.get("link", "")

                results.append(
                    f"\n{i}. {title}\n"
                    f"   {snippet}\n"
                    f"   URL: {link}"
                )

        # Add answer box if available
        if "answerBox" in data:
            answer = data["answerBox"]
            if "answer" in answer:
                results.insert(0, f"💡 Quick Answer: {answer['answer']}\n")
            elif "snippet" in answer:
                results.insert(0, f"💡 Answer: {answer['snippet']}\n")

        if not results:
            return f"No results found for query: {query}"

        return "\n".join(results)

    except requests.exceptions.RequestException as e:
        return f"Error searching web: {str(e)}"
    except Exception as e:
        return f"Unexpected error during web search: {str(e)}"


@tool
def search_news(query: str, num_results: int = 5) -> str:
    """
    Search for recent news articles using Google Serper API.

    Use this for:
    - Latest news and current events
    - Recent developments on a topic
    - Breaking news

    Args:
        query: The news search query
        num_results: Number of news articles to return (default: 5)

    Returns:
        Formatted string with news articles including titles, snippets,
        dates, and sources
    """
    if not SERPER_API_KEY:
        return (
            "Error: SERPER_API_KEY not configured. "
            "Get your API key from https://serper.dev"
        )

    try:
        url = "https://google.serper.dev/news"

        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "q": query,
            "num": min(num_results, 10)
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        if "news" not in data or not data["news"]:
            return f"No news articles found for: {query}"

        results = ["📰 Latest News:\n"]

        for i, article in enumerate(data["news"][:num_results], 1):
            title = article.get("title", "No title")
            snippet = article.get("snippet", "No description")
            source = article.get("source", "Unknown source")
            date = article.get("date", "Unknown date")
            link = article.get("link", "")

            results.append(
                f"{i}. {title}\n"
                f"   Source: {source} | Date: {date}\n"
                f"   {snippet}\n"
                f"   URL: {link}\n"
            )

        return "\n".join(results)

    except requests.exceptions.RequestException as e:
        return f"Error searching news: {str(e)}"
    except Exception as e:
        return f"Unexpected error during news search: {str(e)}"
