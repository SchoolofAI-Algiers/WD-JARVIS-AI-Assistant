from app.core.llm.client import LLMClient
import random

llm_client = LLMClient()

# generate a response from the LLM client
def test_prompt(prompt: str) -> None:
    """Temporarily generate a response for a supplied prompt."""
    print()
    print("PROMPT:")
    print("--------------------------------------------------------------")
    print(prompt)
    print("--------------------------------------------------------------\n")
    print("LLM OUTPUT:")
    print("--------------------------------------------------------------")
    print(llm_client.generate(prompt))
    print("--------------------------------------------------------------\n")


# pick a random prompt and test the LLM client
prompts = [
    "I'm a university student with zero AI background but a lot of curiosity. What's the most realistic path for me to start learning with the School of AI Algiers and actually stick with it?",
    "What does an active member of the School of AI Algiers student community actually do week to week — study groups, projects, mentorship, or something else entirely?",
    "I keep starting AI courses and quitting halfway. How does the School of AI Algiers community help students stay consistent and accountable?",
    "If I join the School of AI Algiers as a student, what's the fastest way to go from passive learner to contributing to a real project with others?",
    "I want to build a portfolio that actually impresses people. Does the School of AI Algiers community support student projects, and how do I get involved in one?",
    "What skills should I focus on first as a student joining the School of AI Algiers so I don't waste months going in the wrong direction?",
    "How do students in the School of AI Algiers community find mentors or study partners who are at a similar level and share the same goals?",
    "I'm overwhelmed by all the AI resources online. How does the School of AI Algiers community help students cut through the noise and follow a clear path?",
    "What's expected of a new student in the School of AI Algiers community, and what can I realistically expect to get out of it in the first three months?",
    "I want to meet other students who are serious about AI and actually build things together. How do I become part of the School of AI Algiers community and make that happen?",
]

test_prompt(random.choice(prompts))
