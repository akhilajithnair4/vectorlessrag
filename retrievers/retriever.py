

from prompts.retriever_prompt import RETRIEVER_PROMPT as retriever_prompt
from storage.storage import Storage
from llms.base import BaseLLM
import json


def _clean_json(response: str) -> str:
    response = response.strip()
    if response.startswith("```"):
        response = response.split("\n", 1)[-1]
        response = response.rsplit("```", 1)[0]
    return response.strip()


def _flatten_tree(node, flat=None):
    """Flatten nested tree into a simple list of {node_id, title, summary/prefix_summary}."""
    if flat is None:
        flat = []
    if isinstance(node, list):
        for n in node:
            _flatten_tree(n, flat)
        return flat
    entry = {
        "node_id": node["node_id"],
        "title": node["title"],
        "pages": f"{node['start_index']}-{node['end_index']}",
    }
    # Only include summary (not the full text) — keeps the prompt small
    if "summary" in node:
        entry["summary"] = node["summary"][:120]  # truncate to 120 chars
    elif "prefix_summary" in node:
        entry["summary"] = node["prefix_summary"][:120]
    flat.append(entry)
    for child in node.get("sub_nodes", []):
        _flatten_tree(child, flat)
    return flat


class Retriever:
    
    def _find_node(self, node, target_id):
        if isinstance(node, list):
            for item in node:
                result = self._find_node(item, target_id)
                if result:
                    return result
            return None
        # BASE CASE — this is the node we're looking for
        if node["node_id"] == target_id:
            return node

        # RECURSIVE CASE — search inside each child
        for child in node.get("sub_nodes", []):
            result = self._find_node(child, target_id)
            if result:
                return result

        # not found in this branch
        return None

    def retrieve(self, query: str, topic_name: str, llm: BaseLLM):
        storage = Storage()
        tree_docs = storage.get_topic_index(topic_name)
        results = []
        all_selected_node_ids = []
        for doc_id, tree_doc in tree_docs.items():
                pages = storage.load_doc_pages(topic_name, doc_id)

                flat_nodes = _flatten_tree(tree_doc)
                prompt = retriever_prompt.format(question=query, tree=json.dumps(flat_nodes, indent=2))
                response = llm.call(prompt)

                print(f"Response for doc_id {doc_id}: {response}")
                node_ids = json.loads(_clean_json(response))
                all_selected_node_ids.extend(node_ids)

                for node_id in node_ids:
                     node = self._find_node(tree_doc, node_id)
                     if node:
                          start = node["start_index"]
                          end = node["end_index"]
                          extracted_text = "\n".join(pages[start-1:end])
                          results.append(extracted_text)
        final_response = "\n\n".join(results)
        final_response_prompt = f"Based on the following extracted text from relevant documents, provide a concise answer to the query: {query}\n\nExtracted Text:\n{final_response}"
        llm_response = llm.call(final_response_prompt)
        return llm_response, all_selected_node_ids


        
    







