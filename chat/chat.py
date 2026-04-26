import json
import os
import uuid

from core.config import CHAT_HISTORY
from retrievers.retriever import Retriever
from storage.storage import Storage

# imported lazily to avoid circular imports
def _wiki_builder():
    from wiki.wiki_builder import WikiBuilder
    return WikiBuilder()


class Chat:

    def _load(self):
        if os.path.exists(CHAT_HISTORY):
            with open(CHAT_HISTORY) as f:
                return json.load(f)
        return {}

    def _save(self, chats):
        with open(CHAT_HISTORY, "w") as f:
            json.dump(chats, f)

    def get_history(self, topic_name: str):
        return self._load().get(topic_name, [])

    def send(self, query: str, topic_name: str, llm):
        message_id = str(uuid.uuid4())
        chats = self._load()
        if topic_name not in chats:
            chats[topic_name] = []
        chats[topic_name].append({"message_id": message_id, "role": "user", "content": query})

        history = chats[topic_name][-20:]
        full_query = ""
        if len(history) > 1:
            full_query = "Conversation history:\n"
            for msg in history[:-1]:
                role = "User" if msg["role"] == "user" else "Assistant"
                full_query += f"{role}: {msg['content']}\n"
            full_query += "\n"
        full_query += f"Current question: {query}"

        retriever = Retriever()
        final_response, _ = retriever.retrieve(query=full_query, topic_name=topic_name, llm=llm)
        chats[topic_name].append({"message_id": message_id, "role": "assistant", "content": final_response, "rating": None})
        self._save(chats)
        return {"response": final_response, "message_id": message_id}

    def feedback(self, message_id: str, rating: int, llm, comment: str = None):
        if rating not in (0, 1):
            raise ValueError("rating must be 0 or 1")

        chats = self._load()
        found_topic = None
        user_question = None
        assistant_answer = None

        for topic, messages in chats.items():
            for msg in messages:
                if msg.get("message_id") == message_id:
                    found_topic = topic
                    if msg["role"] == "assistant":
                        assistant_answer = msg["content"]
                        msg["rating"] = rating
                        msg["comment"] = comment
                    elif msg["role"] == "user":
                        user_question = msg["content"]

        if not found_topic or not assistant_answer:
            raise ValueError("Message ID not found.")

        self._save(chats)

        if rating == 1 and user_question and assistant_answer:
            summary_prompt = (
                f"Given this Q&A pair, generate a concise knowledge node.\n"
                f"Question: {user_question}\n"
                f"Answer: {assistant_answer}\n\n"
                f"Respond ONLY with valid JSON in this exact format:\n"
                f'{{ "title": "short title", "summary": "2-3 sentence summary of the key knowledge" }}'
            )
            raw = llm.call(summary_prompt)
            try:
                node_data = json.loads(raw.strip().strip("```json").strip("```").strip())
            except Exception:
                node_data = {"title": user_question[:60], "summary": assistant_answer[:300]}

            synthesized_node = {
                "node_id": str(uuid.uuid4())[:8],
                "title": node_data.get("title", user_question[:60]),
                "summary": node_data.get("summary", assistant_answer[:300]),
                "start_index": None,
                "end_index": None,
                "source": "synthesized",
                "sub_nodes": []
            }

            storage = Storage()
            topic_index = storage.get_topic_index(found_topic)
            if topic_index:
                first_doc_id = list(topic_index.keys())[0]
                doc_path = os.path.join("storage", found_topic, f"{first_doc_id}.json")
                with open(doc_path, "r") as f:
                    tree = json.load(f)
                if "sub_nodes" not in tree:
                    tree["sub_nodes"] = []
                tree["sub_nodes"].append(synthesized_node)
                with open(doc_path, "w") as f:
                    json.dump(tree, f, indent=2)

            # Auto-update wiki now that a new approved Q&A exists
            try:
                wiki_result = _wiki_builder().build(topic_name=found_topic, llm=llm)
            except Exception:
                wiki_result = None

            return {
                "message_id": message_id,
                "rating": rating,
                "node_injected": synthesized_node["title"],
                "wiki_updated": wiki_result["wiki_path"] if wiki_result else None
            }

        return {"message_id": message_id, "rating": rating}
