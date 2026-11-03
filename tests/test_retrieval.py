from app import retrieval
from app.environment import InboxEnv
from evaluation.retrieval_eval import SYSTEMS, evaluate, load_corpus, load_queries, score_query
from evaluation.stats import wilson


def test_bm25_ranks_the_exam_email_first():
    env = InboxEnv.load()
    assert retrieval.bm25_search(env.emails, "when is the final exam")[0] == "e2"


def test_stop_words_only_query_returns_nothing_but_naive_returns_almost_everything():
    env = InboxEnv.load()
    assert retrieval.bm25_search(env.emails, "what is my") == []
    assert len(retrieval.naive_search(env.emails, "what is my")) >= 8


def test_search_tool_output_lists_ids_and_handles_no_match():
    env = InboxEnv.load()
    assert env.search_emails("library late fee").startswith("[e5]")
    assert env.search_emails("zzzz qqqq").startswith("No emails match")


def test_retrieval_set_is_well_formed():
    corpus, queries = load_corpus(), load_queries()
    ids = [e["id"] for e in corpus]
    assert len(ids) == len(set(ids)) and len(queries) >= 30
    for q in queries:
        assert q["relevant"] and set(q["relevant"]) <= set(ids), q["id"]


def test_score_query_and_evaluate_structure():
    assert score_query(["e9", "e2"], ["e2"]) == {"hit1": 0.0, "recall3": 1.0, "mrr": 0.5, "n_results": 2}
    assert score_query([], ["e2"])["mrr"] == 0.0
    res = evaluate(SYSTEMS["bm25 (used by the agent)"], load_corpus(), load_queries())
    assert set(res["overall"]) == {"n", "hit1", "recall3", "mrr", "avg_results"}


def test_wilson_interval():
    assert wilson(0, 10)[0] == 0.0
    lo, hi = wilson(5, 10)
    assert 23 < lo < 24 and 76 < hi < 77
    assert wilson(0, 0) == (None, None)
