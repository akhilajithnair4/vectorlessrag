

from prompts.retriever_prompt import RETRIEVER_PROMPT as retriever_prompt
from storage.storage import Storage
from llms.base import BaseLLM
import json
import re


def _title_keyword_match(flat_nodes: list, query: str) -> list:
    """Return node_ids whose title contains ALL meaningful keywords from the query."""
    stop = {
        "the", "and", "for", "from", "all", "get", "give", "show", "what", "fetch",
        "please", "me", "our", "a", "an", "is", "are", "was", "were", "how", "why",
        "can", "its", "with", "that", "this", "into", "have", "has", "find", "tell",
        "list", "provide", "explain", "describe", "summarize", "retrieve", "pull",
        "need", "want", "would", "could", "should", "about", "does", "do",
    }
    query_words = [w for w in re.findall(r"[a-z]+", query.lower()) if len(w) >= 4 and w not in stop]
    if len(query_words) < 2:
        return []
    matched = []
    for node in flat_nodes:
        title_lower = node["title"].lower()
        hits = sum(1 for w in query_words if w in title_lower)
        if hits == len(query_words):
            matched.append(node["node_id"])
    return matched


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
        entry["summary"] = node["summary"][:250]
    elif "prefix_summary" in node:
        entry["summary"] = node["prefix_summary"][:250]
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

                # add any nodes whose title contains ALL query keywords
                for nid in _title_keyword_match(flat_nodes, query):
                    if nid not in node_ids:
                        print(f"  [title-match] adding node {nid}")
                        node_ids.append(nid)

                all_selected_node_ids.extend(node_ids)

                # collect all page ranges, expand by ±3, then deduplicate
                page_ranges = []
                for node_id in node_ids:
                     node = self._find_node(tree_doc, node_id)
                     if node:
                          start = max(1, node["start_index"] - 3)
                          end = min(len(pages), node["end_index"] + 3)
                          page_ranges.append((start, end))

                # merge overlapping ranges so we don't send duplicate text
                page_ranges.sort()
                merged = []
                for s, e in page_ranges:
                    if merged and s <= merged[-1][1] + 1:
                        merged[-1] = (merged[-1][0], max(merged[-1][1], e))
                    else:
                        merged.append([s, e])

                for s, e in merged:
                    extracted_text = "\n".join(pages[s-1:e])
                    results.append(extracted_text)

        final_response = "\n\n".join(results)
        final_response_prompt = (
            f"Based on the following extracted text from relevant documents, "
            f"answer the query completely and thoroughly. "
            f"If the query asks for a table, statement, or list, reproduce ALL rows and columns exactly — do NOT summarize, skip rows, or say data is unavailable if it appears in the text.\n\n"
            f"Query: {query}\n\nExtracted Text:\n{final_response}"
        )
        llm_response = llm.call(final_response_prompt)
        return llm_response, all_selected_node_ids


        
    







