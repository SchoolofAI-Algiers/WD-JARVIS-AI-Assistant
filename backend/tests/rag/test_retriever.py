"""Indexing + retrieval test on the REAL SOAI knowledge base (knowledge/processed)."""
import sys
from dataclasses import replace
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from app.rag.config import get_settings  # noqa: E402
from app.rag.embeddings import build_embedder  # noqa: E402
from app.rag.ingest import build_index, load_knowledge  # noqa: E402
from app.rag.retriever import Retriever, format_context, get_sources  # noqa: E402
from app.rag.vector_store import WeaviateStore  # noqa: E402

KB = BACKEND.parent / "knowledge" / "processed"

# (question, original question or None, chunks that answer it)
KNOWN = [
    ("What is the School of AI Algiers?", None,
     ["soai_faq#what-is-the-school-of-ai-algiers", "soai_overview#organization"]),
    ("How is the club structured?", None,
     ["soai_faq#how-is-soai-organized", "soai_overview#organization",
      "soai_overview#internal-structure", "soai_faq#what-departments-exist-in-soai"]),
    ("Can a new member join the Technical Department?", None,
     ["soai_faq#can-all-soai-members-participate-in-technical-department-activities",
      "soai_overview#technical-department"]),
    ("Who takes care of social media, photos and videos?", None,
     ["soai_overview#production-department", "soai_faq#what-does-the-multimedia-division-do",
      "soai_faq#what-is-the-production-department"]),
    ("Who handles sponsors and the club budget?", None,
     ["soai_faq#what-does-marketing-external-relations-do", "soai_overview#marketing-external-relations"]),
    ("What is the SOAI Learning Platform?", None,
     ["soai_faq#what-is-the-soai-learning-platform", "soai_overview#development-department"]),
    ("Which specialization tracks can I choose in AI Camp?", None,
     ["soai_activities#ai-camp-integration-program"]),
    ("Since when has hAIck been organized?", None,
     ["soai_activities#haick-national-datathon"]),
    ("Is there a datathon for beginners inside the club?", None,
     ["soai_activities#ai-real-camp-internal-mini-datathon", "soai_faq#what-is-ai-real-camp"]),
    ("Which robot is used in the language-guided robotics project?", None,
     ["soai_projects#1-language-guided-robotic-manipulation"]),
    ("Which baselines is the Physics-Aware Transformer compared to?", None,
     ["soai_projects#2-physics-aware-transformer"]),
    ("How does the UAV project keep drones safe?", None,
     ["soai_projects#3-safe-multi-agent-reinforcement-learning-for-uavs",
      "soai_faq#what-is-safe-multi-agent-reinforcement-learning-for-uavs"]),
    ("Who designs the posters and certificates?", None,
     ["soai_overview#design-department", "soai_faq#what-does-the-design-department-do"]),
    ("Who organizes everything on the day of an event?", None,
     ["soai_overview#logistics", "soai_faq#what-does-the-logistics-team-do"]),
    ("Can I become a project manager?", None,
     ["soai_overview#human-resources-projects"]),
    ("What is Welcome Day?", "C'est quoi le Welcome Day ?",
     ["soai_activities#welcome-day", "soai_faq#what-is-welcome-day"]),
    ("Does SOAI do research in AI?", "هل يقوم النادي بأبحاث في الذكاء الاصطناعي؟",
     ["soai_faq#does-soai-do-ai-research", "soai_overview#technical-department",
      "soai_faq#what-does-the-technical-department-do"]),
    ("Quels sont les départements du club ?", None,
     ["soai_faq#what-departments-exist-in-soai", "soai_overview#internal-structure",
      "soai_faq#how-is-soai-organized"]),
    ("ما هو هاكاثون البيانات hAIck؟", None,
     ["soai_activities#haick-national-datathon", "soai_faq#what-is-haick"]),
]

# to handle unkown questions case
UNKNOWN = [
    "What is the recipe for couscous?",
    "Who won the 2022 football World Cup?",
    "Quel temps fera-t-il à Alger demain ?",
    "كم عدد سكان الجزائر؟",
]

# in the SOAI context but not answered by the KB.
HARD_UNKNOWN = [
    "How much is the SOAI membership fee?",
    "What is the date of the next hAIck?",
]


def test_retriever():
    settings = replace(get_settings(), collection="SoaiChunkTest")
    embedder = build_embedder(settings)
    store = WeaviateStore(settings)
    try:
        #indexing
        chunks = load_knowledge(KB)
        report = build_index(chunks, embedder, store, reset=True)
        print(f"indexed {report.upserted} chunks from {report.files} files")
        assert report.total_in_store == len(chunks)
        assert build_index(chunks, embedder, store).total_in_store == len(chunks), "duplicates"

        debug = Retriever(embedder, store, replace(settings, min_similarity=-1.0))  # no threshold initially
        normal = Retriever(embedder, store, settings)
        known_sims, unknown_sims, failures = [], [], []

        #known questions
        print(f"\nKNOWN questions (threshold={settings.min_similarity}, top_k={settings.top_k})")
        for question, original, expected in KNOWN:
            top = debug.retrieve(question, original)
            found_ids = [c.id for c in normal.retrieve(question, original)]
            ok = any(e in found_ids for e in expected)
            best = next((c.similarity for c in top if c.id in expected), None)
            if best is not None:
                known_sims.append(best)
            if not ok:
                failures.append(question)
            got = top[0].id if top else "-"
            print(f"  {'OK  ' if ok else 'FAIL'} {question[:55]:55} sim={best if best is None else round(best, 3)}"
                  f"  top={got}")

        #unknown questions
        print("\nUNKNOWN questions (should return nothing)")
        for question in UNKNOWN:
            top = debug.retrieve(question)
            best = top[0].similarity if top else 0.0
            unknown_sims.append(best)
            ok = normal.retrieve(question) == []
            if not ok:
                failures.append(question)
            print(f"  {'OK  ' if ok else 'FAIL'} {question[:55]:55} best sim={best:.3f}")

        print("\nHARD unknown (in-domain, not in the KB) - informative only")
        for question in HARD_UNKNOWN:
            top = debug.retrieve(question)
            print(f"  {question[:55]:55} best sim={top[0].similarity:.3f}  ({top[0].id})")

        result = normal.retrieve("What is hAIck?")
        print("\nCONTEXT FOR THE LLM:\n" + format_context(result))
        print("\nSOURCES:", get_sources(result))
        print("\nNO ANSWER:", format_context([]))

        #threshold choice
        if known_sims and unknown_sims:
            low_known, high_unknown = min(known_sims), max(unknown_sims)
            print(f"\nlowest known sim={low_known:.3f} | highest unknown sim={high_unknown:.3f}")
            if high_unknown < low_known:
                print(f"suggested RAG_MIN_SIMILARITY={(low_known + high_unknown) / 2:.2f}")
            else:
                print("known and unknown overlap: pick a value that fails the fewest questions")

        print(f"\n{len(KNOWN) + len(UNKNOWN) - len(failures)}/{len(KNOWN) + len(UNKNOWN)} passed")
        assert not failures, f"failed: {failures}"
    finally:
        #store.client.collections.delete(settings.collection)
        store.close()


if __name__ == "__main__":
    test_retriever()