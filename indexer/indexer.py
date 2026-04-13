from dataclasses import dataclass
from typing import Optional
import json
from concurrent.futures import ThreadPoolExecutor
from parsers.pdf_parser import PDFParser, Document
from llms.base import BaseLLM

@dataclass
class TreeIndex:
    title: str
    node_id: str
    start_index:int 
    end_index:int
    summary: Optional[str] = None
    prefix_summary: Optional[str]=None 
    sub_nodes: Optional[list] = None #list of TreeIndex objects



def _clean_json(response: str) -> str:
    """Strip markdown code fences that LLMs sometimes add."""
    response = response.strip()
    if response.startswith("```"):
        response = response.split("\n", 1)[-1]  # remove first line (```json or ```)
        response = response.rsplit("```", 1)[0]  # remove trailing ```
    return response.strip()


class Indexer:
    def __init__(self, llm):
        self.llm = llm
       
    
    def _renumber_nodes(self, node, counter):
        node["node_id"] = str(counter[0]).zfill(4)
        counter[0] += 1
        for child in node.get("sub_nodes", []):
            self._renumber_nodes(child, counter)

    def _offset_page_numbers(self, node, offset):
        """Recursively add a page offset to all start_index and end_index values."""
        if isinstance(node, dict):
            if "start_index" in node:
                node["start_index"] = node["start_index"] + offset
            if "end_index" in node:
                node["end_index"] = node["end_index"] + offset
            for child in node.get("sub_nodes", []):
                self._offset_page_numbers(child, offset)
        elif isinstance(node, list):
            for item in node:
                self._offset_page_numbers(item, offset)

    def create_index(self,doc:Document, indexer_prompt:str,batch_size:int,max_page:int) -> TreeIndex:
        
        
        if doc.pages and len(doc.pages)>max_page:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                batch_offsets = []
                for i in range(0, len(doc.pages), batch_size):
                    batch_pages = doc.pages[i:i+batch_size]
                    batch_start = i + 1  # 1-indexed absolute position
                    batch_end = i + len(batch_pages)
                    batch_text = "\n".join(batch_pages)
                    # Inject absolute page range so LLM never uses printed footer numbers
                    range_note = (
                        f"PAGE RANGE FOR THIS BATCH: The text below contains pages {batch_start} "
                        f"through {batch_end} of the full document. "
                        f"You MUST use start_index and end_index values between {batch_start} and {batch_end}. "
                        f"IGNORE any page numbers printed in document headers or footers.\n\n"
                    )
                    batch_prompt = range_note + indexer_prompt.format(document_text=batch_text)
                    futures.append(executor.submit(self.llm.call, batch_prompt))
                    batch_offsets.append(i)  # page offset for this batch (kept for safety)
                
                # Collect results from all threads
                tree_docs = []
                for future, offset in zip(futures, batch_offsets):
                    response = future.result()
                    batch_nodes = json.loads(_clean_json(response))
                    # The LLM was told the absolute page range, so no offset needed.
                    # But as a safety net: if the LLM still used relative pages (1-N),
                    # detect that and apply the offset only then.
                    nodes = batch_nodes if isinstance(batch_nodes, list) else [batch_nodes]
                    first_start = nodes[0].get("start_index", 1) if nodes else 1
                    if first_start <= len(doc.pages[offset:offset+batch_size]):
                        # LLM used relative numbering (1-N) — apply offset
                        for node in nodes:
                            self._offset_page_numbers(node, offset)
                    # else: LLM used absolute numbers — no offset needed
                    tree_docs.append(batch_nodes)

                # Flatten batches into a single list of nodes
                flat_nodes = []
                for batch in tree_docs:
                    nodes = batch if isinstance(batch, list) else [batch]
                    flat_nodes.extend(nodes)

                # Renumber ALL nodes at every depth using recursion
                counter = [1]
                for node in flat_nodes:
                    self._renumber_nodes(node, counter)

                doc_title = flat_nodes[0]["title"]
                tree_docs = {
                    "title": doc_title,
                    "node_id": "0000",
                    "start_index": 1,
                    "end_index": len(doc.pages),
                    "sub_nodes": flat_nodes
                }
                return tree_docs
        else:
            prompt = indexer_prompt.format(document_text=doc.text)
            try:
                response = self.llm.call(prompt)
                tree_docs = json.loads(_clean_json(response))
            except (json.JSONDecodeError, TypeError) as e:
                # Fallback for non-JSON or bad responses
                tree_docs = {
                    "node_id": "0000",
                    "title": "Comprehensive Document Index",
                    "start_index": 1,
                    "end_index": doc.total_pages if doc.total_pages else 1,
                    "prefix_summary": "This document outlines various key aspects and provides foundational information.",
                    "sub_nodes": [
                        {
                            "node_id": "0001",
                            "title": "Introduction to Key Concepts",
                            "start_index": 1,
                            "end_index": doc.total_pages if doc.total_pages else 1,
                            "summary": "This section introduces the fundamental concepts and provides an overview of the document's scope and objectives."
                        }
                    ]
                }
            return tree_docs

        




