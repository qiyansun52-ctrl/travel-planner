from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences
from app.prompts.plan import build_plan_prompt, build_adjustment_prompt


PREFS = UserPreferences(
    destination="上海",
    departureCity="北京",
    departureDate="2026-05-10",
    days=3,
    totalBudget=5000,
    accommodationDescription="精品民宿",
    experienceDescription="本地小馆",
)

CARDS = [
    AttractionCard(
        id="c1",
        name="外滩",
        section="experience",
        description="滨江夜景",
        estimatedCost="免费",
        imageUrl="",
        tags=["地标"],
    ),
    AttractionCard(
        id="c2",
        name="高铁G1",
        section="transport",
        description="北京→上海",
        estimatedCost="¥553",
        imageUrl="",
        tags=["高铁"],
    ),
    AttractionCard(
        id="c3",
        name="南翔小笼",
        section="food",
        description="百年老店",
        estimatedCost="¥30",
        imageUrl="",
        tags=["小吃"],
    ),
]


def test_plan_prompt_includes_destination_and_budget():
    p = build_plan_prompt(PREFS, [])
    assert "上海" in p
    assert "5000" in p


def test_plan_prompt_includes_accommodation_and_experience():
    p = build_plan_prompt(PREFS, [])
    assert "精品民宿" in p
    assert "本地小馆" in p


def test_plan_prompt_includes_all_three_card_names():
    p = build_plan_prompt(PREFS, CARDS)
    assert "外滩" in p
    assert "高铁G1" in p
    assert "南翔小笼" in p


def test_plan_prompt_labels_each_section():
    p = build_plan_prompt(PREFS, CARDS)
    assert "体验" in p
    assert "交通" in p
    assert "美食" in p


def test_adjustment_prompt_includes_user_request():
    p = build_adjustment_prompt('{"days":[]}', "改成轻松一点", CARDS)
    assert "改成轻松一点" in p


def test_adjustment_prompt_includes_original_attractions():
    p = build_adjustment_prompt('{"days":[]}', "改一下", CARDS)
    assert "外滩" in p
    assert "南翔小笼" in p


def test_adjustment_prompt_works_with_no_attractions():
    p = build_adjustment_prompt('{"days":[]}', "调整", [])
    assert "调整" in p
