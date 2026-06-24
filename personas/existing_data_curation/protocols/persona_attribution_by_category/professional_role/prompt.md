You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Professional: Role  (1 dimensions)

Return ONLY JSON with this shape (no markdown, no commentary):

{
  "fields": [
    {
      "field_id": "<one id from the DIMENSIONS list below>",
      "value": "<exactly one allowed value for that id, copied verbatim, or null>",
      "confidence": 0.0,
      "evidence": "<short quote copied from profile_text>",
      "assignment_type": "direct"
    }
  ],
  "reported_model": null,
  "model_source": "user_declared",
  "model_confidence": "user_declared"
}

Allowed assignment_type values:
- direct: explicitly stated in the text.
- structured_claim: derived from structured facts in the input.
- summary_inference: reasonable inference from the profile summary.
- unsupported: not supported by the input.

Rules:
- Emit exactly one object per dimension listed below, in the same order.
- value MUST be exactly one of that dimension's allowed values (copy it verbatim), OR null.
- If the profile does not support a dimension, set value to null and assignment_type to "unsupported".
- Every non-null value MUST include a short evidence quote copied from profile_text.
- Do not infer private, sensitive, or psychological traits unless directly stated; when unsure, prefer null/unsupported.
- Return valid JSON only, with no markdown.

DIMENSIONS (field_id — label — description — allowed values):
- nemotron_occupation — Occupation — Primary occupation or job role. — [accountant_or_auditor | architect | assembler_or_fabricator | cashier | civil_engineer | computer_or_information_research_scientist | computer_systems_analyst | construction_laborer | correctional_officer_or_jailer | database_administrator_or_architect | dental_assistant | dining_room_or_cafeteria_attendant_or_bartender_helper | driver_sales_worker_or_truck_driver | electrical_power_line_installer_or_repairer | electrician | elementary_or_middle_school_teacher | emergency_medical_technician | engineer | fast_food_or_counter_worker | financial_manager | first_line_supervisor_of_food_preparation_or_serving_worker | food_service_manager | home_appliance_repairer | host_or_hostess_restaurant_lounge_or_coffee_shop | industrial_truck_or_tractor_operator | insurance_sales_agent | marketing_manager | massage_therapist | mathematical_science_occupation | network_or_computer_systems_administrator | no_occupation | not_in_workforce | nursing_assistant | office_clerk_general | painting_worker | personal_care_aide | physical_scientist | postsecondary_teacher | preschool_or_kindergarten_teacher | public_safety_telecommunicator | retail_salesperson | sales_manager | sales_representative_of_services | secretary_or_administrative_assistant | security_guard_or_gambling_surveillance_officer | software_developer | telephone_operator | waiter_or_waitress]

INPUT:

{{input_json}}
