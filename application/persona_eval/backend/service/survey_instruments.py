"""Built-in survey instruments for PersonaEval survey tasks."""

from __future__ import annotations

from .survey_types import SurveyInstrument, SurveyQuestion

__all__ = [
    "DEFAULT_SURVEY_INSTRUMENT_ID",
    "get_survey_instrument",
    "list_survey_instruments",
]

DEFAULT_SURVEY_INSTRUMENT_ID = "product_attitudes_v1"


def _product_attitudes_v1() -> SurveyInstrument:
    return SurveyInstrument(
        id=DEFAULT_SURVEY_INSTRUMENT_ID,
        title="Product Attitudes",
        description=(
            "A short product-concept survey completed directly by the simulated "
            "persona respondent."
        ),
        questions=[
            SurveyQuestion(
                id="concept_fit",
                prompt="This product would fit my current needs.",
                type="likert",
                min_value=1,
                max_value=5,
                construct="product_need_fit",
            ),
            SurveyQuestion(
                id="preference_fit",
                prompt="This product matches my personal preferences.",
                type="likert",
                min_value=1,
                max_value=5,
                construct="personal_preference_fit",
            ),
            SurveyQuestion(
                id="adoption_barrier",
                prompt="What would be your biggest barrier to using this product?",
                type="single_choice",
                options=["price", "privacy", "complexity", "trust", "no clear need"],
                construct="adoption_barrier",
            ),
            SurveyQuestion(
                id="purchase_likelihood",
                prompt="How likely would you be to try or purchase this product?",
                type="single_choice",
                options=["very unlikely", "unlikely", "neutral", "likely", "very likely"],
                construct="purchase_likelihood",
            ),
            SurveyQuestion(
                id="open_feedback",
                prompt="Briefly explain what most influenced your reaction.",
                type="free_text",
                construct="open_feedback",
            ),
        ],
    )


def _software_claude_code_vscode_checkpoints_v1() -> SurveyInstrument:
    return SurveyInstrument(
        id="software_claude_code_vscode_checkpoints_v1",
        title="Claude Code IDE Autonomy Survey",
        description=(
            "Survey reactions to Claude Code's native VS Code extension and "
            "checkpoint feature, where a coding agent can edit code in the IDE, "
            "show inline diffs, and let developers roll back autonomous changes."
        ),
        questions=[
            SurveyQuestion(
                id="reviewable_edits",
                prompt=(
                    "I would use Claude Code inside VS Code to make multi-file code "
                    "edits if I could review inline diffs before accepting changes."
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="coding_agent_reviewability",
            ),
            SurveyQuestion(
                id="checkpoint_control",
                prompt=(
                    "Checkpoint rollback would make me more comfortable letting a "
                    "coding agent work autonomously on a complex task."
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="agentic_coding_control_trust",
            ),
            SurveyQuestion(
                id="adoption_concern",
                prompt=(
                    "What would be your biggest concern before using this feature "
                    "on a real codebase?"
                ),
                type="single_choice",
                options=[
                    "incorrect_code_changes",
                    "hard_to_review_diffs",
                    "security_or_secret_exposure",
                    "too_much_autonomy",
                ],
                construct="coding_agent_adoption_barrier",
            ),
            SurveyQuestion(
                id="safe_first_task",
                prompt="What coding task would you feel safest delegating to Claude Code first?",
                type="free_text",
                construct="safe_initial_coding_agent_use_case",
            ),
        ],
    )


def _finance_robinhood_cortex_digests_v1() -> SurveyInstrument:
    return SurveyInstrument(
        id="finance_robinhood_cortex_digests_v1",
        title="Robinhood Cortex Digests Survey",
        description=(
            "Survey reactions to Robinhood Cortex Digests, an AI feature that "
            "summarizes recent news, events, market information, and signals for "
            "a selected stock or crypto asset."
        ),
        questions=[
            SurveyQuestion(
                id="market_summary_utility",
                prompt=(
                    "I would use Robinhood Cortex Digests to quickly understand why "
                    "a stock or crypto asset may be moving before making my own "
                    "decision."
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="ai_market_summary_utility",
            ),
            SurveyQuestion(
                id="source_transparency",
                prompt=(
                    "I would trust this feature more if it clearly showed the "
                    "sources behind each market summary."
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="financial_source_transparency_trust",
            ),
            SurveyQuestion(
                id="ai_investing_concern",
                prompt=(
                    "What would be your biggest concern about using AI-generated "
                    "investing summaries?"
                ),
                type="single_choice",
                options=[
                    "overreliance_on_ai",
                    "unclear_sources",
                    "missing_risk_context",
                    "too_complex",
                ],
                construct="ai_investing_adoption_barrier",
            ),
            SurveyQuestion(
                id="safety_requirement",
                prompt=(
                    "What would Robinhood need to show you before this feature "
                    "felt safe to use?"
                ),
                type="free_text",
                construct="financial_ai_safety_requirement",
            ),
        ],
    )


def _healthcare_cvs_app_prescription_ai_v1() -> SurveyInstrument:
    return SurveyInstrument(
        id="healthcare_cvs_app_prescription_ai_v1",
        title="CVS Health App Prescription AI Survey",
        description=(
            "Survey reactions to the CVS Health app's conversational AI experience "
            "for checking medication refills, order status, and related pharmacy "
            "tasks."
        ),
        questions=[
            SurveyQuestion(
                id="pharmacy_convenience",
                prompt=(
                    "I would use a CVS app chat assistant to check prescription "
                    "refill status or order status instead of calling the pharmacy."
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="pharmacy_ai_convenience",
            ),
            SurveyQuestion(
                id="pharmacy_boundary_trust",
                prompt=(
                    "I would feel comfortable using this assistant for simple "
                    "pharmacy tasks, as long as it did not replace pharmacist "
                    "support for medical questions."
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="pharmacy_ai_boundary_trust",
            ),
            SurveyQuestion(
                id="pharmacy_hesitation",
                prompt="What would make you most hesitant to use a pharmacy chat assistant?",
                type="single_choice",
                options=[
                    "privacy",
                    "wrong_medication_information",
                    "hard_to_reach_a_human",
                    "app_usability",
                ],
                construct="pharmacy_ai_adoption_barrier",
            ),
            SurveyQuestion(
                id="wanted_pharmacy_task",
                prompt="What pharmacy task would you most want this assistant to handle for you?",
                type="free_text",
                construct="pharmacy_ai_use_case",
            ),
        ],
    )


def _commerce_nike_air_max_dn_dynamic_air_v1() -> SurveyInstrument:
    return SurveyInstrument(
        id="commerce_nike_air_max_dn_dynamic_air_v1",
        title="Nike Air Max Dn Dynamic Air Purchase Survey",
        description=(
            "Survey reactions to the Nike Air Max Dn's Dynamic Air feature, a "
            "dual-chamber, four-tubed Air unit designed for smoother transition, "
            "comfort, and bounce."
        ),
        questions=[
            SurveyQuestion(
                id="dynamic_air_appeal",
                prompt=(
                    "The Dynamic Air cushioning feature would make me more "
                    "interested in trying the Nike Air Max Dn."
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="retail_product_feature_appeal",
            ),
            SurveyQuestion(
                id="comfort_price_tolerance",
                prompt=(
                    "I would pay more for sneakers if the cushioning technology "
                    "felt noticeably more comfortable during everyday walking."
                ),
                type="likert",
                min_value=1,
                max_value=5,
                construct="comfort_feature_price_tolerance",
            ),
            SurveyQuestion(
                id="purchase_driver",
                prompt="What would most affect your decision to buy the Air Max Dn?",
                type="single_choice",
                options=["comfort", "style", "price", "brand_loyalty", "durability"],
                construct="sneaker_purchase_driver",
            ),
            SurveyQuestion(
                id="proof_requirement",
                prompt=(
                    "What would Nike need to show or prove for you to believe the "
                    "Dynamic Air feature is worth it?"
                ),
                type="free_text",
                construct="retail_product_proof_requirement",
            ),
        ],
    )


def _registry() -> dict[str, SurveyInstrument]:
    instruments = [
        _product_attitudes_v1(),
        _software_claude_code_vscode_checkpoints_v1(),
        _finance_robinhood_cortex_digests_v1(),
        _healthcare_cvs_app_prescription_ai_v1(),
        _commerce_nike_air_max_dn_dynamic_air_v1(),
    ]
    return {instrument.id: instrument for instrument in instruments}


def list_survey_instruments() -> list[SurveyInstrument]:
    """Return all built-in survey instruments in stable display order."""
    registry = _registry()
    return list(registry.values())


def get_survey_instrument(instrument_id: str) -> SurveyInstrument:
    """Return one built-in survey instrument, or raise ``KeyError``."""
    registry = _registry()
    try:
        return registry[instrument_id]
    except KeyError as exc:
        raise KeyError("unknown survey instrument: {}".format(instrument_id)) from exc
