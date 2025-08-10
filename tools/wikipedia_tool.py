
from langchain_core.tools import tool
import wikipedia

# ===============================
# Wikipedia Tool
# ===============================

@tool
def search_wikipedia(query: str, max_results: int = 3) -> str:
    """
    Search Wikipedia for information on a given topic.
    
    Args:
        query: The search query
        max_results: Maximum number of results to return (default: 3)
        
    Returns:
        Formatted string with Wikipedia search results
    """
    try:
        # Search for pages
        wikipedia.set_lang("en")
        search_results = wikipedia.search(query, results=max_results)
        
        if not search_results:
            return f"No Wikipedia results found for: {query}"
        
        results = []
        for title in search_results:
            try:
                # Get page summary
                summary = wikipedia.summary(title, sentences=2)
                page = wikipedia.page(title)
                
                result = {
                    "title": title,
                    "summary": summary,
                    "url": page.url
                }
                results.append(result)
                
            except (wikipedia.exceptions.DisambiguationError, 
                   wikipedia.exceptions.PageError) as e:
                # Skip problematic pages
                continue
        
        # Format results
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"{i}. **{result['title']}**\n"
                f"   {result['summary']}\n"
                f"   URL: {result['url']}\n"
            )
        
        return f"Wikipedia search results for '{query}':\n\n" + "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error searching Wikipedia: {str(e)}"

@tool
def get_wikipedia_page(title: str) -> str:
    """
    Get full content from a specific Wikipedia page.
    
    Args:
        title: The exact title of the Wikipedia page
        
    Returns:
        Page content summary
    """
    try:
        wikipedia.set_lang("en")
        page = wikipedia.page(title)
        
        # Get a longer summary (5 sentences)
        content = wikipedia.summary(title, sentences=5)
        
        return f"**{page.title}**\n\n{content}\n\nFull article: {page.url}"
        
    except wikipedia.exceptions.DisambiguationError as e:
        # Handle disambiguation
        options = e.options[:5]  # First 5 options
        return f"Multiple pages found for '{title}'. Did you mean: {', '.join(options)}?"
        
    except wikipedia.exceptions.PageError:
        return f"No Wikipedia page found for: {title}"
        
    except Exception as e:
        return f"Error retrieving Wikipedia page: {str(e)}"
