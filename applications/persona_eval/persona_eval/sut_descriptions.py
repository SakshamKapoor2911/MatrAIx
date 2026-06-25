from __future__ import annotations

_DESCRIPTIONS = {
    "game": (
        "You are chatting with a conversational video-game recommender. It can ask about "
        "your tastes and constraints, search a large catalog of games, and suggest specific "
        "titles. Tell it what you want and answer its questions to get game recommendations."
    ),
    "movie": (
        "You are chatting with a conversational movie recommender. It can ask about your "
        "tastes and constraints, search a large film catalog, and suggest specific movies. "
        "Tell it what you want and answer its questions to get movie recommendations."
    ),
    "beauty_product": (
        "You are chatting with a conversational beauty & personal-care product recommender. "
        "It can ask about your needs, skin type, and budget, search a catalog of beauty "
        "products, and suggest specific items. Tell it what you want to get recommendations."
    ),
    "financial_research": (
        "You are chatting with a financial research chatbot. It can ask about "
        "your objective, risk constraints, time horizon, tickers, funds, sectors, "
        "or macro topics, use OpenBB data tools, and provide grounded research "
        "or comparisons without giving personalized buy/sell instructions."
    ),
    "medical_consultation": (
        "You are chatting with a medical assistant chatbot. It can ask about "
        "symptoms, duration, severity, medications, history, and red flags, then "
        "provide general health information and triage-style guidance. It should "
        "recommend professional or urgent care when appropriate and should not "
        "claim to replace a clinician."
    ),
}


def sut_description_for(domain: str) -> str:
    if domain not in _DESCRIPTIONS:
        raise KeyError("no SUT description for domain: {}".format(domain))
    return _DESCRIPTIONS[domain]
