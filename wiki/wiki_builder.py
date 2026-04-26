import json
import os

from core.config import CHAT_HISTORY
from prompts.wiki_builder_prompt import WIKI_BUILDER_PROMPT
from storage.storage import Storage


class WikiBuilder:

    def _load_chats(self):
        if os.path.exists(CHAT_HISTORY):
            with open(CHAT_HISTORY) as f:
                return json.load(f)
        return {}

    def build(self, topic_name: str, llm):
        chats = self._load_chats()
        topic_messages = chats.get(topic_name, [])

        storage = Storage()
        topic_index = storage.get_topic_index(topic_name)
        if not topic_index:
            raise ValueError("Topic not found or has no indexed documents.")

        grouped = {}
        for message in topic_messages:
            mid = message["message_id"]
            if mid not in grouped:
                grouped[mid] = {"user": None, "assistant": None, "rating": None}
            if message["role"] == "user":
                grouped[mid]["user"] = message["content"]
            elif message["role"] == "assistant":
                grouped[mid]["assistant"] = message["content"]
                grouped[mid]["rating"] = message.get("rating")

        approved_pairs = [
            p for p in grouped.values()
            if p.get("rating") == 1 and p["user"] and p["assistant"]
        ]

        if not approved_pairs:
            raise ValueError("No approved Q&A pairs found. Rate some responses with thumbs up first.")

        wiki_path = os.path.join("wiki", f"{topic_name}.md")
        existing_wiki = ""
        if os.path.exists(wiki_path):
            with open(wiki_path, "r") as f:
                existing_wiki = f.read()

        qa_text = ""
        for i, pair in enumerate(approved_pairs, 1):
            qa_text += f"Q{i}: {pair['user']}\nA{i}: {pair['assistant']}\n\n"

        prompt = WIKI_BUILDER_PROMPT.format(
            topic_name=topic_name,
            existing_wiki=existing_wiki if existing_wiki else "No existing wiki yet.",
            approved_qa_pairs=qa_text.strip()
        )

        wiki_content = llm.call(prompt)

        os.makedirs("wiki", exist_ok=True)
        with open(wiki_path, "w") as f:
            f.write(wiki_content)

        return {
            "topic_name": topic_name,
            "wiki_path": wiki_path,
            "approved_pairs_count": len(approved_pairs),
            "wiki_preview": wiki_content[:500]
        }
