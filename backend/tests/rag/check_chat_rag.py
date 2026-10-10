
import json
import sys
import urllib.request
import uuid

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
CHAT_URL = f"{BASE_URL}/api/v1/chat"

IN_KB = [
    ("I'm new here, what is SOAI exactly?", "AI club, education, projects, community"),
    ("What happens at the Welcome Day?", "welcomes new members, vision and values"),
    ("I'm a beginner, is there an event where I can practice?", "AI Real Camp (beginner mini-datathon)"),
    ("What is AI Camp and what will I learn there?", "integration program"),
    ("Which departments are there in the club?", "Technical, Production, Development, Marketing, Design, Logistics..."),
    ("Can I join the Technical Department?", "not open to new members, but its workshops are open to all"),
    ("Does the club organize workshops?", "educational activities"),
    ("What does the Design department do?", "design department role"),
    ("Is there a learning platform for members?", "SOAI Learning Platform (planned)"),
    ("What kind of projects does the club work on?", "robotics, physics-aware transformer, UAVs"),
    ("Je suis nouvelle, comment le club est organisé ?", "answer in French, departments"),
    ("واش هو AI Summit؟", "answer in Arabic/Darija"),
]

NOT_IN_KB = [
    ("How do I join SOAI?", "should NOT invent a process"),
    ("Is there a membership fee?", "should say it doesn't know"),
    ("Who is the president of the club?", "should say it doesn't know"),
    ("When is the next Welcome Day?", "should NOT invent a date"),
    ("Do I need to know programming to join?", "should not invent a rule"),
]

FOLLOW_UP = ["What is hAIck?", "Can beginners participate in it?"]


def ask(message: str, conversation_id: str) -> dict:
    body = json.dumps({"conversation_id": conversation_id, "message": message}).encode()
    request = urllib.request.Request(CHAT_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def show(question: str, expected: str, data: dict) -> None:
    meta = data.get("metadata", {})
    sources = [s["id"] for s in meta.get("sources", [])]
    print(f"\nQ: {question}")
    print(f"   expected: {expected}")
    print(f"   type={meta.get('type')}  sources={sources}")
    print(f"   answer: {data.get('message', '')[:300]}")


def main() -> None:
    print("=== In the knowledge base (should be type=rag, with sources) ===")
    for question, expected in IN_KB:
        show(question, expected, ask(question, str(uuid.uuid4())))

    print("\n=== Not in the knowledge base (must not invent) ===")
    for question, expected in NOT_IN_KB:
        show(question, expected, ask(question, str(uuid.uuid4())))

    print("\n=== Follow-up in the same conversation ===")
    conv = str(uuid.uuid4())
    for question in FOLLOW_UP:
        show(question, "the 2nd answer should still be about hAIck", ask(question, conv))


if __name__ == "__main__":
    main()