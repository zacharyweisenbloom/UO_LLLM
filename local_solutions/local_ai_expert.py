from __future__ import annotations as _annotations

from dataclasses import dataclass
from dotenv import load_dotenv
import logfire
import asyncio
import httpx
import os
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import AsyncOpenAI
from supabase import Client
from typing import List
import httpx
from typing import List
load_dotenv()

llm = os.getenv('LLM_MODEL', 'gpt-4o-mini')
base_url = "http://192.168.0.19:11434/v1"
model = OpenAIModel(
    model_name="tinyllama", provider=OpenAIProvider(base_url=base_url)
)

logfire.configure(send_to_logfire='if-token-present')

@dataclass
class PydanticAIDeps:
    supabase: Client
   

system_prompt = """
You are an expert assistant for the University of Oregon's Computer Science program. 
You have access to the department's official documentation, including course listings, program requirements, research opportunities, admissions information, and other academic resources.

Your sole purpose is to assist with questions related to the University of Oregon Computer Science program. 
You do not answer unrelated questions, and you always stay focused on academic and departmental content.

Do not ask the user for permission to act—take direct action. Always consult the documentation using the available tools before answering, unless you already have the relevant information.

When first accessing documentation, always begin with a RAG (retrieval-augmented generation) search. 
Also check the list of available documentation pages and retrieve the content of any page that may help answer the question.

Always be transparent: if you cannot find the answer in the documentation or the appropriate page URL, let the user know clearly and honestly.
"""

pydantic_ai_expert = Agent(
    model,
    system_prompt=system_prompt,
    deps_type=PydanticAIDeps,
    retries=2
)

async def get_embedding(text: str) -> List[float]:
    """Use local Ollama server to generate embeddings."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/embeddings",
                json={
                    "model": "mxbai-embed-large",
                    "prompt": text
                },
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()["embedding"]
    except Exception as e:
        print(f"Error getting embedding from Ollama: {e}")
        return [0.0] * 1024  # mxbai-embed-large returns 1024-dim vectors@pydantic_ai_expert.tool

async def retrieve_relevant_documentation(ctx: RunContext[PydanticAIDeps], user_query: str) -> str:
    """
    Retrieve relevant documentation chunks based on the query with RAG.
    
    Args:
        ctx: The context including the Supabase client and OpenAI client
        user_query: The user's question or query
        
    Returns:
        A formatted string containing the top 5 most relevant documentation chunks
    """
    try:
        # Get the embedding for the query
        query_embedding = await get_embedding(user_query)
        
        # Query Supabase for relevant documents
        result = ctx.deps.supabase.rpc(
            'match_site_pages',
            {
                'query_embedding': query_embedding,
                'match_count': 5,
                'filter': {'source': 'pydantic_ai_docs'}
            }
        ).execute()
        
        if not result.data:
            return "No relevant documentation found."
            
        # Format the results
        formatted_chunks = []
        for doc in result.data:
            chunk_text = f"""
# {doc['title']}

{doc['content']}
"""
            formatted_chunks.append(chunk_text)
            
        # Join all chunks with a separator
        return "\n\n---\n\n".join(formatted_chunks)
     
    except Exception as e:
        print(f"Error retrieving documentation: {e}")
        return f"Error retrieving documentation: {str(e)}"

@pydantic_ai_expert.tool
async def list_documentation_pages(ctx: RunContext[PydanticAIDeps]) -> List[str]:
    """
    Retrieve a list of all available Pydantic AI documentation pages.
    
    Returns:
        List[str]: List of unique URLs for all documentation pages
    """
    try:
        # Query Supabase for unique URLs where source is pydantic_ai_docs
        result = ctx.deps.supabase.from_('site_pages') \
            .select('url') \
            .eq('metadata->>source', 'pydantic_ai_docs') \
            .execute()
        
        if not result.data:
            return []
            
        # Extract unique URLs
        urls = sorted(set(doc['url'] for doc in result.data))
        return urls
        
    except Exception as e:
        print(f"Error retrieving documentation pages: {e}")
        return []

@pydantic_ai_expert.tool
async def get_page_content(ctx: RunContext[PydanticAIDeps], url: str) -> str:
    """
    Retrieve the full content of a specific documentation page by combining all its chunks.
    
    Args:
        ctx: The context including the Supabase client
        url: The URL of the page to retrieve
        
    Returns:
        str: The complete page content with all chunks combined in order
    """
    try:
        # Query Supabase for all chunks of this URL, ordered by chunk_number
        result = ctx.deps.supabase.from_('site_pages') \
            .select('title, content, chunk_number') \
            .eq('url', url) \
            .eq('metadata->>source', 'pydantic_ai_docs') \
            .order('chunk_number') \
            .execute()
        
        if not result.data:
            return f"No content found for URL: {url}"
            
        # Format the page with its title and all chunks
        page_title = result.data[0]['title'].split(' - ')[0]  # Get the main title
        formatted_content = [f"# {page_title}\n"]
        
        # Add each chunk's content
        for chunk in result.data:
            formatted_content.append(chunk['content'])
            
        # Join everything together
        return "\n\n".join(formatted_content)
        
    except Exception as e:
        print(f"Error retrieving page content: {e}")
        return f"Error retrieving page content: {str(e)}"

"""
async def main():

    embeddings = await get_embedding("this is some text")
    print(embeddings)


if __name__ == "__main__":
    asyncio.run(main())

"""
