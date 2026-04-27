
from indexer.indexer import Indexer
from parsers.pdf_parser import PDFParser
from prompts.indexer_prompt import INDEXER_PROMPT
from retrievers.retriever import Retriever
from storage.storage import Storage
from chat.chat import Chat
from wiki.wiki_builder import WikiBuilder


class VectorLessRag:
    def __init__(self, llm):
        self.llm = llm

    def add_document(self, file_path: str, topic_name: str, mode: str):
        #First we parse the document to get raw text and page-level text
        parser = PDFParser(file_path=file_path, mode=mode, llm=self.llm)
        document = parser.parse()

        #Then we call the indexer to get the tree structure
        indexer = Indexer(llm=self.llm)
        tree_docs = indexer.create_index(document, indexer_prompt=INDEXER_PROMPT, batch_size=5, max_page=10)

        #Finally we save the tree structure + page-level text to our storage layer
        storage = Storage()
        doc_id = storage.add_to_storage(tree_docs=tree_docs, topic_name=topic_name, file_path=file_path, doc_pages=document.pages)
        return doc_id

    def query(self, query: str, topic_name: str):
        retriever = Retriever()
        final_response, _ = retriever.retrieve(query=query, topic_name=topic_name, llm=self.llm)
        return final_response

    def chat(self, query: str, topic_name: str):
        return Chat().send(query=query, topic_name=topic_name, llm=self.llm)

    def chat_and_rate(self, query: str, topic_name: str):
        """Ask a question, print the answer, prompt the user to rate it, then call feedback automatically."""
        result = Chat().send(query=query, topic_name=topic_name, llm=self.llm)
        print(f"\n{result['response']}\n")
        while True:
            raw = input("Rate this answer (1 = good, 0 = bad, s = skip): ").strip().lower()
            if raw == "1":
                feedback = self.feedback(result["message_id"], rating=1)
                print(f"✅ Saved: '{feedback.get('node_injected', '')}'")
                if feedback.get("wiki_updated"):
                    print(f"📖 Wiki updated: {feedback['wiki_updated']}")
                break
            elif raw == "0":
                self.feedback(result["message_id"], rating=0)
                print("📝 Noted.")
                break
            elif raw == "s":
                break
            else:
                print("Please enter 1, 0, or s.")
        return result

    def feedback(self, message_id: str, rating: int, comment: str = None):
        return Chat().feedback(message_id=message_id, rating=rating, llm=self.llm, comment=comment)

    def build_wiki(self, topic_name: str):
        return WikiBuilder().build(topic_name=topic_name, llm=self.llm)

