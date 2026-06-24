You are extracting persona-attribution fields for ONE category of a structured persona schema, from a Wikipedia-derived profile.

CATEGORY: Skills: Tools  (69 dimensions)

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
- tool_excel — Tool: Excel — Experience with Excel. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_google_sheets — Tool: Google Sheets — Experience with Google Sheets. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_python — Tool: Python — Experience with Python. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_r — Tool: R — Experience with R. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_sql — Tool: SQL — Experience with SQL. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_tableau — Tool: Tableau — Experience with Tableau. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_power_bi — Tool: Power BI — Experience with Power BI. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_looker — Tool: Looker — Experience with Looker. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_figma — Tool: Figma — Experience with Figma. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_sketch — Tool: Sketch — Experience with Sketch. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_photoshop — Tool: Photoshop — Experience with Photoshop. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_illustrator — Tool: Illustrator — Experience with Illustrator. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_indesign — Tool: InDesign — Experience with InDesign. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_after_effects — Tool: After Effects — Experience with After Effects. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_premiere_pro — Tool: Premiere Pro — Experience with Premiere Pro. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_notion — Tool: Notion — Experience with Notion. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_obsidian — Tool: Obsidian — Experience with Obsidian. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_jira — Tool: Jira — Experience with Jira. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_linear — Tool: Linear — Experience with Linear. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_slack — Tool: Slack — Experience with Slack. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_microsoft_teams — Tool: Microsoft Teams — Experience with Microsoft Teams. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_salesforce — Tool: Salesforce — Experience with Salesforce. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_hubspot — Tool: HubSpot — Experience with HubSpot. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_sap — Tool: SAP — Experience with SAP. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_oracle_erp — Tool: Oracle ERP — Experience with Oracle ERP. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_git — Tool: Git — Experience with Git. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_github — Tool: GitHub — Experience with GitHub. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_gitlab — Tool: GitLab — Experience with GitLab. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_docker — Tool: Docker — Experience with Docker. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_kubernetes — Tool: Kubernetes — Experience with Kubernetes. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_terraform — Tool: Terraform — Experience with Terraform. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_aws — Tool: AWS — Experience with AWS. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_azure — Tool: Azure — Experience with Azure. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_google_cloud — Tool: Google Cloud — Experience with Google Cloud. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_vs_code — Tool: VS Code — Experience with VS Code. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_jetbrains_ides — Tool: JetBrains IDEs — Experience with JetBrains IDEs. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_vim — Tool: Vim — Experience with Vim. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_jupyter — Tool: Jupyter — Experience with Jupyter. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_matlab — Tool: MATLAB — Experience with MATLAB. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_stata — Tool: Stata — Experience with Stata. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_spss — Tool: SPSS — Experience with SPSS. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_sas — Tool: SAS — Experience with SAS. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_word — Tool: Word — Experience with Word. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_powerpoint — Tool: PowerPoint — Experience with PowerPoint. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_keynote — Tool: Keynote — Experience with Keynote. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_canva — Tool: Canva — Experience with Canva. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_blender — Tool: Blender — Experience with Blender. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_autocad — Tool: AutoCAD — Experience with AutoCAD. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_solidworks — Tool: SolidWorks — Experience with SolidWorks. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_revit — Tool: Revit — Experience with Revit. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_unity — Tool: Unity — Experience with Unity. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_unreal_engine — Tool: Unreal Engine — Experience with Unreal Engine. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_linux_cli — Tool: Linux CLI — Experience with Linux CLI. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_wordpress — Tool: WordPress — Experience with WordPress. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_webflow — Tool: Webflow — Experience with Webflow. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_shopify — Tool: Shopify — Experience with Shopify. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_stripe — Tool: Stripe — Experience with Stripe. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_quickbooks — Tool: QuickBooks — Experience with QuickBooks. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_xero — Tool: Xero — Experience with Xero. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_zoom — Tool: Zoom — Experience with Zoom. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_trello — Tool: Trello — Experience with Trello. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_asana — Tool: Asana — Experience with Asana. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_airtable — Tool: Airtable — Experience with Airtable. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_chatgpt — Tool: ChatGPT — Experience with ChatGPT. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_claude — Tool: Claude — Experience with Claude. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_github_copilot — Tool: GitHub Copilot — Experience with GitHub Copilot. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_midjourney — Tool: Midjourney — Experience with Midjourney. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_zapier — Tool: Zapier — Experience with Zapier. — [Power user | Regular | Occasional | Tried it | Never used]
- tool_postman — Tool: Postman — Experience with Postman. — [Power user | Regular | Occasional | Tried it | Never used]

INPUT:

{{input_json}}
