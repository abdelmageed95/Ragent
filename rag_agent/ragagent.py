import os
from typing import List, Dict, Any, Optional
import numpy as np
from PIL import Image
import cohere
from google import genai
from openai import OpenAI
from rag_agent.embedding_helpers import l2_normalize
from rag_agent.loading_helpers import load_indices

# load from env
from dotenv import load_dotenv
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------
# RAG Agent: Retrieval & LLM
# -------------------------------

class RagAgent:
    """
    RAG Agent that handles multimodal retrieval (text + image) from separate FAISS indices,
    and can query Gemini for direct answers via the google-genai client.
    """
    def __init__(
        self,
        text_index_path: str = os.path.join("data", "faiss_text.index"),
        image_index_path: str = os.path.join("data", "faiss_image.index"),
        text_meta_path: str = os.path.join("data", "text_docs_info.pkl"),
        image_meta_path: str = os.path.join("data", "image_docs_info.pkl"),
    ) -> None:
        # Load FAISS indices and metadata
        self.idx_text, self.text_meta, self.idx_img, self.image_meta = load_indices(
            text_index_path, image_index_path, text_meta_path, image_meta_path
        )

        # Cohere client for embeddings
        self.co_client = cohere.ClientV2(api_key="SJcDVJBzLECN6S8mAT0SGbzx6PMUtFoyvHVQ5Kt0")

        # google-genai client for LLM generation
        self.genai_client = genai.Client(api_key="AIzaSyDoElOZE1wayqlHYGaTNh_uAc2QRgjs85Q")

    def embed_query(self, query: str) -> Optional[np.ndarray]:
        """
        Embed the user query into the shared vector space.
        """
        try:
            resp = self.co_client.embed(
                model="embed-v4.0",
                input_type="search_query",
                embedding_types=["float"],
                texts=[query],
            )
            vec = np.array(resp.embeddings.float[0], dtype=np.float32)
            return l2_normalize(vec)
        except Exception as e:
            print(f"Query embedding error: {e}")
            return None

    def retrieve(
        self,
        query: str,
        top_k_text: int = 5,
        top_k_image: int = 5,
        top_n: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Perform multimodal retrieval: query both text and image FAISS indices,
        fuse and re-rank results, and return top_n entries.

        Each hit dict contains: doc_id, source, modality, chunk/page, score, content/preview.
        """
        q_vec = self.embed_query(query)
        if q_vec is None:
            return []

        all_hits: List[Dict[str, Any]] = []
        # --- Text retrieval ---
        if self.idx_text:
            D_t, I_t = self.idx_text.search(np.array([q_vec]), top_k_text)
            for score, idx in zip(D_t[0], I_t[0]):
                if idx < len(self.text_meta):
                    meta = self.text_meta[idx]
                    all_hits.append({
                        "doc_id": meta["doc_id"],
                        "source": meta["source"],
                        "modality": "text",
                        "chunk": meta.get("chunk"),
                        "score": float(score),
                        "content": meta.get("content"),
                    })
        # --- Image retrieval ---
        if self.idx_img:
            D_i, I_i = self.idx_img.search(np.array([q_vec]), top_k_image)
            for score, idx in zip(D_i[0], I_i[0]):
                if idx < len(self.image_meta):
                    meta = self.image_meta[idx]
                    all_hits.append({
                        "doc_id": meta["doc_id"],
                        "source": meta["source"],
                        "modality": "image",
                        "page": meta.get("page"),
                        "score": float(score),
                        "preview": meta.get("preview_image"),
                    })
        # --- Fuse & re-rank ---
        sorted_hits = sorted(all_hits, key=lambda x: x["score"], reverse=True)
        return sorted_hits[:top_n]

    def generate_answer(
        self,
        question: str,
        context: Dict[str, Any],
        use_image: bool = False,
    ) -> str:
        """
        Use google-genai to generate an answer given either text content or an image preview.
        """
        try:
            if use_image and context.get("preview"):
                img = Image.open(context["preview"])
                prompt = [
                    f"Answer the question based on the following image.\nDon't use markdown.\nPlease provide enough context.\n\nQuestion: {question}",
                    img,
                ]
                response = self.genai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
            else:
                text = context.get("content", "")
                prompt = [
                    f"Answer the question based on the following information.\nDon't use markdown.\nPlease provide enough context.\n\nInformation: {text}\nQuestion: {question}"
                ]
                response = self.genai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt[0]]  # Pass a list of one string
                )
            if response.text is not None:
                return response.text.strip()
            else:
                return ""
        except Exception as e:
            print(f"Gemini generation error: {e}")
            return ""




def rag_answer(query, top_k_text=5, top_k_image=5, top_n=3):
    """
    Generate a coherent answer to the given query by retrieving relevant text and image data,
    generating candidate answers, and then selecting the best one using a language model.
    """
    agent = RagAgent()
    hits = agent.retrieve(query, top_k_text=top_k_text, top_k_image=top_k_image, top_n=top_n)
    for h in hits:
        modality = h['modality'].upper()
        print(f"[{modality}] {h['score']:.3f} — {h['source']} (ID: {h['doc_id']})")
    
    metadata = {
                "agent_type": "rag_agent",
                "hits_count": len(hits),
                "sources": [hit.get("source", "unknown") for hit in hits],
                "modalities": [hit.get("modality", "unknown") for hit in hits]
            }
    concat_ans= []
    for h in hits:
        ans = agent.generate_answer(query,
                                    h,
                                    use_image=(h['modality']=='image')
                                    )
        concat_ans.append(ans)
        
    msg = [
        {
            "role":"user",
            "content":f"""you are a helpful assistant who can decide and select the right answer among 
            multiple answers for the given question.
            here is the question: {query} \n\n
            candidate answers: {concat_ans} \n

            - If you find that more than one answer is correct and complement to each other,combine them
            into one coherent and well organized answer.

            """
        }
    ]
    res = openai_client.chat.completions.create(
        model = "gpt-4o-mini",
        messages= msg,
        temperature=0.0
    )
    fans= res.choices[0].message.content
    return fans, metadata
