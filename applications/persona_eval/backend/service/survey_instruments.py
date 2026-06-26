"""Built-in survey instruments for PersonaEval survey tasks."""

from __future__ import annotations

from typing import Dict, List

from backend.service.survey_types import SurveyInstrument, SurveyQuestion

__all__ = [
    "DEFAULT_SURVEY_INSTRUMENT_ID",
    "get_survey_instrument",
    "list_survey_instruments",
]

DEFAULT_SURVEY_INSTRUMENT_ID = "chatgpt_images_market_research_v1"


def _chatgpt_images_market_research_v1() -> SurveyInstrument:
    return SurveyInstrument(
        id=DEFAULT_SURVEY_INSTRUMENT_ID,
        title="ChatGPT Images Market Research Survey",
        description=(
            "Market research survey about ChatGPT Images, a ChatGPT feature for "
            "generating and editing images from prompts or uploaded images."
        ),
        questions=[
            SurveyQuestion(
                id="trial_intent",
                prompt=(
                    "How likely would you be to use ChatGPT to create or edit an "
                    "image for a personal, school, or work project?"
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="feature_trial_intent",
            ),
            SurveyQuestion(
                id="most_useful_task",
                prompt="Which image task would be most useful to you?",
                type="single_choice",
                options=[
                    "creating_social_media_images",
                    "editing_or_fixing_photos",
                    "making_presentations_or_posters",
                    "brainstorming_visual_ideas",
                    "none_of_these",
                ],
                construct="primary_use_case_interest",
            ),
            SurveyQuestion(
                id="adoption_barrier",
                prompt="What would most stop you from using ChatGPT Images?",
                type="single_choice",
                options=[
                    "image_does_not_match_my_request",
                    "concerns_about_photo_privacy",
                    "hard_to_get_realistic_results",
                    "prefer_existing_design_tools",
                    "not_sure_when_to_use_it",
                ],
                construct="feature_adoption_barrier",
            ),
            SurveyQuestion(
                id="regular_use_trigger",
                prompt="What would make ChatGPT Images worth using regularly?",
                type="free_text",
                construct="regular_use_trigger",
            ),
        ],
    )


def _instagram_reels_market_research_v1() -> SurveyInstrument:
    return SurveyInstrument(
        id="instagram_reels_market_research_v1",
        title="Instagram Reels Market Research Survey",
        description=(
            "Market research survey about Instagram Reels, Instagram's short-video "
            "feature for watching, creating, and discovering videos in the app."
        ),
        questions=[
            SurveyQuestion(
                id="watch_intent",
                prompt=(
                    "How likely would you be to watch Instagram Reels during a "
                    "normal Instagram visit?"
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="feature_usage_intent",
            ),
            SurveyQuestion(
                id="content_pull",
                prompt="What kind of Reels would make you open Instagram more often?",
                type="single_choice",
                options=[
                    "funny_or_entertaining_videos",
                    "friends_or_creators_i_follow",
                    "how_to_or_learning_content",
                    "news_trends_or_pop_culture",
                    "shopping_or_product_discovery",
                    "none_of_these",
                ],
                construct="content_interest_driver",
            ),
            SurveyQuestion(
                id="usage_barrier",
                prompt="What would most make you use Reels less?",
                type="single_choice",
                options=[
                    "too_many_ads",
                    "irrelevant_recommendations",
                    "too_addictive_or_time_wasting",
                    "low_quality_content",
                    "privacy_or_tracking_concerns",
                ],
                construct="feature_usage_barrier",
            ),
            SurveyQuestion(
                id="improvement_request",
                prompt=(
                    "What change would make Instagram Reels more useful or "
                    "enjoyable for you?"
                ),
                type="free_text",
                construct="desired_feature_improvement",
            ),
        ],
    )


def _nike_air_max_dn_market_research_v1() -> SurveyInstrument:
    return SurveyInstrument(
        id="nike_air_max_dn_market_research_v1",
        title="Nike Air Max Dn Market Research Survey",
        description=(
            "Market research survey about Nike Air Max Dn and its Dynamic Air "
            "cushioning feature."
        ),
        questions=[
            SurveyQuestion(
                id="try_on_intent",
                prompt=(
                    "How likely would you be to try on the Nike Air Max Dn if you "
                    "saw it in a store?"
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="retail_trial_intent",
            ),
            SurveyQuestion(
                id="purchase_driver",
                prompt="What would matter most when deciding whether to buy it?",
                type="single_choice",
                options=[
                    "comfort",
                    "style",
                    "price",
                    "brand_reputation",
                    "durability",
                ],
                construct="purchase_decision_driver",
            ),
            SurveyQuestion(
                id="adoption_barrier",
                prompt="What would most stop you from buying a new Nike Air shoe?",
                type="single_choice",
                options=[
                    "too_expensive",
                    "not_my_style",
                    "unsure_about_comfort",
                    "already_have_similar_shoes",
                    "prefer_other_brands",
                ],
                construct="purchase_adoption_barrier",
            ),
            SurveyQuestion(
                id="proof_needed",
                prompt=(
                    "What would Nike need to show you to make the Dynamic Air "
                    "cushioning feel believable?"
                ),
                type="free_text",
                construct="product_proof_requirement",
            ),
        ],
    )


def _registry() -> Dict[str, SurveyInstrument]:
    instruments = [
        _chatgpt_images_market_research_v1(),
        _instagram_reels_market_research_v1(),
        _nike_air_max_dn_market_research_v1(),
    ]
    return {instrument.id: instrument for instrument in instruments}


def list_survey_instruments() -> List[SurveyInstrument]:
    """Return all built-in survey instruments in stable display order."""
    registry = _registry()
    return list(registry.values())


def get_survey_instrument(instrument_id: str) -> SurveyInstrument:
    """Return one built-in survey instrument, or raise ``KeyError``."""
    registry = _registry()
    try:
        return registry[instrument_id]
    except KeyError:
        raise KeyError("unknown survey instrument: {}".format(instrument_id))
