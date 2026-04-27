"""
VectorlessRAG Interactive CLI

Run:
    python cli.py

The system will:
  1. Ask which topic to chat with
  2. Take your question
  3. Show the answer
  4. Ask "was this helpful? (y/n)" — automatically triggers feedback + wiki update on 'y'
  5. Repeat until you type 'exit'
"""

import os
from dotenv import load_dotenv

load_dotenv()

from core.config import get_llm
from storage.storage import Storage
from vectorlessrag import VectorLessRag


def pick_topic() -> str:
    topics = Storage().get_topics()
    if not topics:
        print("\n❌ No topics found. Index some documents first.\n")
        exit(1)

    print("\n📚 Available topics:")
    for i, t in enumerate(topics, 1):
        print(f"  {i}. {t}")

    while True:
        choice = input("\nEnter topic number or name: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(topics):
            return topics[int(choice) - 1]
        elif choice in topics:
            return choice
        else:
            print("  Not found, try again.")


def ask_feedback(rag: VectorLessRag, message_id: str, topic_name: str):
    while True:
        rating_input = input("\n👍 Was this helpful? (y/n/skip): ").strip().lower()
        if rating_input == "y":
            comment = input("  Optional comment (press Enter to skip): ").strip() or None
            result = rag.feedback(message_id=message_id, rating=1, comment=comment)
            print(f"\n  ✅ Saved to knowledge base: '{result.get('node_injected', '')}'")
            if result.get("wiki_updated"):
                print(f"  📖 Wiki updated: {result['wiki_updated']}")
            break
        elif rating_input == "n":
            rag.feedback(message_id=message_id, rating=0)
            print("  📝 Noted. Won't be added to the knowledge base.")
            break
        elif rating_input == "skip":
            break
        else:
            print("  Please enter y, n, or skip.")


def main():
    print("\n🧠 VectorlessRAG CLI")
    print("=" * 40)
    print("Type 'exit' to quit, 'switch' to change topic, 'wiki' to view the topic wiki.\n")

    llm = get_llm()
    rag = VectorLessRag(llm=llm)
    topic_name = pick_topic()
    print(f"\n✅ Chatting with topic: '{topic_name}'\n")

    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not query:
            continue

        if query.lower() == "exit":
            print("Goodbye!")
            break

        if query.lower() == "switch":
            topic_name = pick_topic()
            print(f"\n✅ Switched to topic: '{topic_name}'\n")
            continue

        if query.lower() == "wiki":
            wiki_path = os.path.join("wiki", f"{topic_name}.md")
            if os.path.exists(wiki_path):
                with open(wiki_path) as f:
                    print(f"\n{f.read()}\n")
            else:
                print(f"\n  No wiki yet for '{topic_name}'. Rate some answers with 'y' to build one.\n")
            continue

        print("\n⏳ Thinking...\n")
        result = rag.chat(query=query, topic_name=topic_name)

        print(f"Assistant: {result['response']}\n")

        ask_feedback(rag, result["message_id"], topic_name)
        print()


if __name__ == "__main__":
    main()
