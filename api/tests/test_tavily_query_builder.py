from app.services.tavily import build_search_queries


def test_returns_three_queries():
    qs = build_search_queries("上海")
    assert len(qs) == 3


def test_all_queries_contain_destination():
    qs = build_search_queries("北京")
    for q in qs:
        assert "北京" in q


def test_query_zero_targets_attractions():
    qs = build_search_queries("成都")
    assert any(token in qs[0] for token in ["景点", "体验", "攻略"])


def test_query_one_targets_transport():
    qs = build_search_queries("成都")
    assert any(token in qs[1] for token in ["交通", "出行", "怎么去"])


def test_query_two_targets_food():
    qs = build_search_queries("成都")
    assert any(token in qs[2] for token in ["美食", "餐厅", "必吃"])
