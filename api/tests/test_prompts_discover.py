from app.prompts.discover import build_discover_prompt, SearchItem


def _item(title: str, snippet: str = "snippet") -> SearchItem:
    return SearchItem(title=title, snippet=snippet, link="https://x.com", image_url="")


def test_includes_destination():
    prompt = build_discover_prompt("上海", [], [], [])
    assert "上海" in prompt


def test_includes_experience_search_results():
    prompt = build_discover_prompt("上海", [_item("外滩夜景")], [], [])
    assert "外滩夜景" in prompt


def test_includes_transport_search_results():
    prompt = build_discover_prompt("上海", [], [_item("地铁攻略")], [])
    assert "地铁攻略" in prompt


def test_includes_food_search_results():
    prompt = build_discover_prompt("上海", [], [], [_item("小笼包推荐")])
    assert "小笼包推荐" in prompt


def test_requests_three_section_json():
    prompt = build_discover_prompt("上海", [], [], [])
    assert "experience" in prompt
    assert "transport" in prompt
    assert "food" in prompt
    assert "JSON" in prompt
