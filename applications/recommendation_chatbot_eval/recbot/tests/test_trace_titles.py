from recbot.types import RecBotTrace


def test_trace_recommended_items_roundtrip_and_default():
    t = RecBotTrace(recommended_item_ids=["6574"],
                    recommended_items=[{"id": "6574", "title": "X"}])
    d = t.to_dict()
    assert d["recommended_items"] == [{"id": "6574", "title": "X"}]
    assert RecBotTrace.from_dict(d).recommended_items == [{"id": "6574", "title": "X"}]
    assert RecBotTrace().recommended_items == []
