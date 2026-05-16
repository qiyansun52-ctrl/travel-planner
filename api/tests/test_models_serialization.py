"""Models serialize to camelCase JSON to match the TypeScript frontend contract."""

from app.models.preferences import UserPreferences
from app.models.attraction import AttractionCard, DiscoverSections
from app.models.plan import TravelPlan, DayPlan, Activity, BudgetBreakdown


def test_user_preferences_uses_camel_case_keys():
    prefs = UserPreferences(
        destination="上海",
        departureCity="北京",
        departureDate="2026-06-01",
        days=3,
        totalBudget=5000,
        accommodationDescription="精品民宿",
        experienceDescription="本地小馆",
    )
    data = prefs.model_dump(by_alias=True)
    assert data["departureCity"] == "北京"
    assert data["departureDate"] == "2026-06-01"
    assert data["totalBudget"] == 5000
    assert data["accommodationDescription"] == "精品民宿"


def test_attraction_card_section_literal():
    card = AttractionCard(
        id="c1",
        name="外滩",
        section="experience",
        description="滨江夜景",
        estimatedCost="免费",
        imageUrl="",
        tags=["地标"],
    )
    assert card.section == "experience"
    data = card.model_dump(by_alias=True)
    assert data["estimatedCost"] == "免费"
    assert data["imageUrl"] == ""


def test_discover_sections_three_lists():
    sections = DiscoverSections(experience=[], transport=[], food=[])
    data = sections.model_dump(by_alias=True)
    assert "experience" in data
    assert "transport" in data
    assert "food" in data


def test_travel_plan_includes_selected_attractions():
    plan = TravelPlan(
        id="p1",
        preferences=UserPreferences(
            destination="上海",
            departureCity="北京",
            departureDate="2026-06-01",
            days=2,
            totalBudget=3000,
            accommodationDescription="",
            experienceDescription="",
        ),
        selectedAttractions=[],
        days=[
            DayPlan(
                day=1,
                date="2026-06-01",
                title="抵达",
                activities=[
                    Activity(
                        id="a1",
                        time="10:00",
                        place="酒店",
                        description="入住",
                        type="hotel",
                    )
                ],
                totalCost=200,
            )
        ],
        budget=BudgetBreakdown(
            transport=500, accommodation=1000, food=500, attractions=300, other=100, total=2400
        ),
        tips=["带身份证"],
        createdAt="2026-05-06T10:00:00Z",
    )
    data = plan.model_dump(by_alias=True)
    assert "selectedAttractions" in data
    assert data["budget"]["total"] == 2400


def test_activity_optional_fields_omitted_when_none():
    a = Activity(id="x", time="09:00", place="P", description="D", type="free")
    data = a.model_dump(by_alias=True, exclude_none=True)
    assert "endTime" not in data
    assert "estimatedCost" not in data
    assert "tips" not in data
