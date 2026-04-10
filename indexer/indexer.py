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

    def create_index(self,doc:Document, indexer_prompt:str,batch_size:int,max_page:int) -> TreeIndex:
        
        
        if doc.pages and len(doc.pages)>max_page:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for i in range(0, len(doc.pages), batch_size):
                    batch_pages = doc.pages[i:i+batch_size]
                    batch_text = "\n".join(batch_pages)
                    batch_prompt = indexer_prompt.format(document_text=batch_text)
                    futures.append(executor.submit(self.llm.call, batch_prompt))
                
                # Collect results from all threads
                tree_docs = []
                for future in futures:
                    response = future.result()
                    tree_docs.append(json.loads(_clean_json(response)))

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
            response = self.llm.call(prompt)
            #parse response into TreeIndex object   
            tree_docs = json.loads(_clean_json(response))  
            # have to implement the function from storage.py
            return tree_docs

        




