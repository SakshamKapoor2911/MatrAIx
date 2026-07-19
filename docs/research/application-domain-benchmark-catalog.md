# Application Domain Benchmark Catalog

> Working brainstorm for the [Application module](../../application/README.md).
> Not a task spec — a breadth-first map of domains MatrAIx's persona-driven
> simulation can be applied to for evaluation.

Organized by **general domain (sector) → vertical**, mapped to the application **types** (1 · Survey · 2 · Chatbot · 3 · Web · 4 · App · 5 · Social-sim), with a reference benchmark/environment, open-source status, trajectory shape, and evaluation per row. Rows marked **—** have no established benchmark yet — open extension areas (intentional). CS/computing sectors are listed first.

_Compiled by [Shirley-Huang](https://github.com/ShirleyHuang11) · 80 verticals across 24 general domains · open-source status verified against each project's public code/dataset._

| General domain | Vertical | App type | Example task (concrete) | Reference benchmark / env | Open-source | Trajectory shape | Evaluation / metric |
|---|---|---|---|---|---|---|---|
| Software Engineering | Issue resolution / bug fixing | 4 · App | Read a GitHub issue, locate the bug, write a patch, pass tests | [SWE-bench](https://github.com/SWE-bench/SWE-bench) | Open | repo edits + test runs | resolved rate (tests pass) |
| Software Engineering | Repo-level code generation | 4 · App | Implement a function/feature to a spec across files | [DevEval](https://github.com/seketeam/DevEval) | Open | code edits | functional correctness |
| Software Engineering | Competitive code generation | 4 · App | Solve a programming problem from a prompt | [LiveCodeBench](https://github.com/LiveCodeBench/LiveCodeBench) | Open | generated code | unit-test pass rate |
| Software Engineering | Instruction-rich code generation | 4 · App | Write code following complex instructions using many libraries | [BigCodeBench](https://github.com/bigcode-project/bigcodebench) | Open | generated code | test pass rate |
| Software Engineering | Freelance software tasks | 4 · App | Complete a real freelance SWE task end-to-end | [SWE-Lancer](https://github.com/openai/SWELancer-Benchmark) | Partial | repo work + tests | task pass / payout |
| Software Engineering | Terminal / DevOps tasks | 4 · App | Complete an end-to-end task in a terminal sandbox | [Terminal-Bench](https://github.com/laude-institute/terminal-bench) | Open | shell commands + outputs | task verifier |
| Data & Analytics | BI / analytics assistant | 2 · Chatbot | Answer a metrics question and build a chart from data | (no established benchmark) | — | dialogue + query/tool calls | answer correctness |
| Data & Analytics | Text-to-SQL querying | 4 · App | Translate a question into SQL over a large database | [BIRD-bench; Spider 2.0](https://github.com/bird-bench/mini_dev) | Open | generated SQL + execution | execution accuracy |
| Data & Analytics | Data-science notebooks | 4 · App | Write code to analyze data and produce a result | [DS-1000](https://github.com/xlang-ai/DS-1000) | Open | code + outputs | functional correctness |
| Cybersecurity | Security operations / alert triage | 2 · Chatbot | Triage a security alert and recommend remediation | (no established benchmark) | — | dialogue + tool calls | correct triage / action |
| Cybersecurity | Vulnerability discovery / PoC | 4 · App | Reproduce a vulnerability by generating a proof-of-concept | [CyberGym](https://github.com/sunblaze-ucb/cybergym) | Open | exploit attempts | reproduces vuln (pass/fail) |
| Computer Use & Web Automation | General web navigation | 3 · Web | Complete a multi-step task on a live website | [WebArena](https://github.com/web-arena-x/webarena) | Open | browser obs + actions | functional correctness |
| Computer Use & Web Automation | Generalist web tasks (real sites) | 3 · Web | Carry out a goal across many real websites | [Mind2Web](https://github.com/OSU-NLP-Group/Mind2Web) | Open | browser obs + actions | step/task accuracy |
| Computer Use & Web Automation | Open-ended assistant tasks | 3 · Web | Answer a question needing web + tools + reasoning | [GAIA](https://huggingface.co/datasets/gaia-benchmark/GAIA) | Partial | tool+web reasoning steps | exact-match answer |
| Computer Use & Web Automation | Computer-use (GUI) | 4 · App | Complete a task via desktop/mobile GUI actions | [Harbor computer-use (iOS/macOS/Linux)](https://github.com/MatrAIx-ai/MatrAIx/pull/14) | Partial | screenshots + GUI actions | task verifier / reward |
| Commerce & Retail | Post-purchase satisfaction survey | 1 · Survey | Rate a recent purchase and explain the rating | (no established benchmark) | — | questionnaire responses | distribution match vs humans |
| Commerce & Retail | Retail customer service | 2 · Chatbot | Resolve an order issue: look up order, apply policy, refund/return | [tau-bench (retail)](https://github.com/sierra-research/tau-bench) | Open | dialogue + tool calls | task reward; pass^k |
| Commerce & Retail | Conversational recommendation | 2 · Chatbot | Elicit taste, recommend items, refine on feedback | [iEvaLM; conv-rec user sim](https://github.com/RUCAIBox/iEvaLM-CRS) | Open | preference dialogue | rec quality; human-likeness |
| Commerce & Retail | E-commerce / online shopping | 3 · Web | Search a product, compare options, add to cart, check out | [WebShop; WebArena (shopping)](https://github.com/princeton-nlp/WebShop) | Open | browser obs + actions | task success (state check) |
| Commerce & Retail | Shopping app | 4 · App | Place an order, track the shipment, start a return | [AppWorld (Amazon)](https://github.com/StonyBrookNLP/appworld) | Open | API/code calls | world-state check |
| Finance & Fintech | Investor risk-profile survey | 1 · Survey | Answer risk-tolerance questions to get a portfolio profile | (no established benchmark) | — | questionnaire responses | choice fidelity vs humans |
| Finance & Fintech | Banking customer service | 2 · Chatbot | Answer an account/policy question grounded in bank docs | [tau-bench (banking_knowledge)](https://github.com/sierra-research/tau-bench) | Open | dialogue + retrieval | answer correctness; pass^k |
| Finance & Fintech | Payments / fintech app | 4 · App | Send a payment, split a bill, check the balance | [AppWorld (Venmo/Splitwise)](https://github.com/StonyBrookNLP/appworld) | Open | API/code calls | world-state check |
| Finance & Fintech | Macroeconomic simulation | 5 · Social sim | Agents work, consume, and trade over many periods | [EconAgent](https://github.com/tsinghua-fib-lab/ACL24-EconAgent) | Open | multi-agent logs | macro indicators |
| Insurance | Policy comparison & quoting | 1 · Survey | Compare plans and state coverage preferences | (no established benchmark) | — | questionnaire responses | choice fidelity vs humans |
| Insurance | Claims processing | 2 · Chatbot | File a claim, check status, dispute a decision | (no established benchmark) | — | dialogue + tool calls | correct claim handling |
| Real Estate & Property | Tenant & rental support | 2 · Chatbot | Ask a lease question, file a maintenance request | (no established benchmark) | — | dialogue + tool calls | task completion |
| Real Estate & Property | Property search | 3 · Web | Filter listings by budget/location, shortlist, book a viewing | (no established benchmark) | — | browser obs + actions | task success |
| Healthcare & Life Sciences | Patient-reported outcomes survey | 1 · Survey | Report symptoms and quality-of-life on a standard scale | (no established benchmark) | — | questionnaire responses | distribution match vs humans |
| Healthcare & Life Sciences | Medical Q&A / triage chatbot | 2 · Chatbot | Triage symptoms, then answer a medical question | [MedQA (+ persona layer)](https://github.com/jind11/MedQA) | Open | dialogue / QA | answer accuracy |
| Healthcare & Life Sciences | Clinical / EHR agent | 4 · App | Retrieve a patient record and order a lab via FHIR APIs | [MedAgentBench](https://github.com/stanfordmlgroup/MedAgentBench) | Open | API calls on EHR | task success vs FHIR state |
| Healthcare & Life Sciences | Biomedical research agent | 4 · App | Answer a research question using literature, figures, and DBs | [LAB-Bench](https://huggingface.co/datasets/futurehouse/lab-bench) | Partial | reasoning steps | accuracy (20% test held out) |
| Healthcare & Life Sciences | Bioinformatics agent | 4 · App | Analyze a dataset in a notebook and report results | [BixBench](https://github.com/Future-House/BixBench) | Open | Jupyter code + outputs | analysis correctness |
| Travel & Hospitality | Airline customer service | 2 · Chatbot | Modify a booking within policy; confirm before charging | [tau-bench (airline)](https://github.com/sierra-research/tau-bench) | Open | dialogue + tool calls | task reward; pass^k |
| Travel & Hospitality | Trip planning & booking | 3 · Web | Find flights + hotel for a trip and book within budget | [Mind2Web (travel)](https://github.com/OSU-NLP-Group/Mind2Web) | Open | browser obs + actions | task accuracy |
| Hospitality & Food Service | Restaurant booking / ordering | 2 · Chatbot | Reserve a table or place an order with dietary constraints | (no established benchmark) | — | dialogue + tool calls | task completion |
| Hospitality & Food Service | Hotel concierge | 2 · Chatbot | Handle a guest request and recommend local options | (no established benchmark) | — | dialogue + tool calls | task completion |
| Telecom | Telecom customer service | 2 · Chatbot | Diagnose a connectivity issue, then adjust the plan | [tau-bench (telecom)](https://github.com/sierra-research/tau-bench) | Open | dialogue + tool calls | task reward; pass^k |
| Telecom | Plan / device upgrade | 4 · App | Compare plans, upgrade a device, update billing | (no established benchmark) | — | API calls | world-state check |
| Energy & Utilities | Utility billing & outage support | 2 · Chatbot | Explain a bill, set a payment plan, report an outage | (no established benchmark) | — | dialogue + tool calls | task completion |
| Energy & Utilities | Home energy optimization | 4 · App | Read usage data and adjust smart-home settings to save energy | (no established benchmark) | — | API calls | world-state check |
| Automotive & Mobility | In-car voice assistant | 2 · Chatbot | Handle navigation and controls by voice while driving | (no established benchmark) | — | dialogue + actions | task completion |
| Automotive & Mobility | Ride-hailing / booking | 4 · App | Book a ride, change destination mid-trip, pay | (no established benchmark) | — | API calls | world-state check |
| Manufacturing & Supply Chain | Procurement & inventory | 4 · App | Reorder low stock and track the shipment | (no established benchmark) | — | API calls | world-state check |
| Manufacturing & Supply Chain | Logistics coordination | 4 · App | Schedule deliveries and resolve a delay | (no established benchmark) | — | API calls + planning | task success |
| Education | Subject tutoring (math) | 2 · Chatbot | Guide a student to the answer without giving it away | [MathDial](https://github.com/eth-nlped/mathdial) | Open | tutor<->student dialogue | pedagogy / correctness |
| Education | Language-learning conversation | 2 · Chatbot | Hold a graded conversation and correct mistakes | (no established benchmark) | — | dialogue | learning gain / correctness |
| Education | Admissions / academic advising | 2 · Chatbot | Answer program questions and plan a course schedule | (no established benchmark) | — | dialogue + tool calls | task completion |
| Human Resources & Recruiting | HR helpdesk | 2 · Chatbot | Answer a benefits question and submit a PTO request | (no established benchmark) | — | dialogue + tool calls | task completion |
| Human Resources & Recruiting | Job search & application | 3 · Web | Find matching roles, tailor a resume, submit applications | (no established benchmark) | — | browser obs + actions | application completion |
| Media & Entertainment | News reading & summarization | 2 · Chatbot | Find articles on a topic and summarize key points | (no established benchmark) | — | dialogue + retrieval | summary quality |
| Media & Entertainment | Video streaming / discovery | 3 · Web | Find a show by criteria and add it to a watchlist | (no established benchmark) | — | browser obs + actions | task success |
| Media & Entertainment | Music streaming app | 4 · App | Build a playlist and play recommended tracks | [AppWorld (Spotify)](https://github.com/StonyBrookNLP/appworld) | Open | API/code calls | world-state check |
| Gaming & Interactive | NPC / character role-play | 2 · Chatbot | Stay in character and respond to the player | [RoleLLM](https://github.com/InteractiveNLP-Team/RoleLLM-public) | Open | in-character dialogue | persona/role adherence |
| Gaming & Interactive | Automated game playtesting | 4 · App | Play a level, complete objectives, log bugs | (no established benchmark) | — | GUI actions | completion / bug discovery |
| Government & Public Sector | Citizen services / benefits | 2 · Chatbot | Help apply for a benefit and answer eligibility questions | (no established benchmark) | — | dialogue + form/tool actions | task completion; policy compliance |
| Government & Public Sector | Gov portal navigation | 3 · Web | Find and complete a permit/license form online | (no established benchmark) | — | browser obs + actions | task success |
| Government & Public Sector | Tax filing assistance | 4 · App | Gather documents, fill a return, and submit | (no established benchmark) | — | form-filling + API calls | correct filing vs rules |
| Legal & Compliance | Contract review / Q&A | 2 · Chatbot | Explain clauses and flag risky terms in a contract | (no established benchmark) | — | document QA dialogue | accuracy vs reference |
| Legal & Compliance | Compliance workflow | 4 · App | Check a filing against rules and submit if compliant | (no established benchmark) | — | rule-check + API calls | compliance pass/fail |
| Agriculture & Environment | Crop & farm advisory | 2 · Chatbot | Diagnose a pest and recommend treatment + timing | (no established benchmark) | — | dialogue / QA | advice accuracy |
| Agriculture & Environment | Sustainability / ESG reporting | 4 · App | Collect metrics and compile an emissions report | (no established benchmark) | — | API calls | report correctness |
| Scientific Research | Literature review assistant | 2 · Chatbot | Find, summarize, and synthesize relevant papers | (no established benchmark) | — | dialogue + retrieval | synthesis quality |
| Scientific Research | Data analysis agent | 4 · App | Load a dataset, run analysis, and report findings | (cf. BixBench) | — | notebook code + outputs | analysis correctness |
| Productivity & Operations | Content management (CMS) | 3 · Web | Update a storefront/admin record in a CMS | [WebArena (CMS/gitlab)](https://github.com/web-arena-x/webarena) | Open | browser obs + actions | task success |
| Productivity & Operations | Personal productivity suite | 4 · App | Create tasks, organize notes, and schedule events | [AppWorld (Todoist/Notes/Files)](https://github.com/StonyBrookNLP/appworld) | Open | API/code calls | world-state check |
| Productivity & Operations | Messaging / email | 4 · App | Send an email, search threads, manage contacts | [AppWorld (Gmail/Phone)](https://github.com/StonyBrookNLP/appworld) | Open | API/code calls | world-state check |
| Productivity & Operations | Tool / API orchestration | 4 · App | Achieve a goal by chaining multiple APIs | [ToolBench / ToolLLM](https://github.com/OpenBMB/ToolBench) | Open | API call chain | tool-use success |
| Marketing & UX Research | Market research survey | 1 · Survey | Answer purchase-intent / concept-test questions | [SSR (Semantic Similarity Rating)](https://github.com/pymc-labs/semantic-similarity-rating) | Open | questionnaire responses | match vs human distributions |
| Marketing & UX Research | Product feedback | 1 · Survey | Give structured feedback on a feature/concept | [UXAgent; MatrAIx survey scenario](https://github.com/neuhai/UXAgent) | Open | questionnaire responses | qual + quant feedback |
| Marketing & UX Research | UX usability testing | 1 · Survey | Attempt tasks on a design and report friction points | [UXAgent](https://github.com/neuhai/UXAgent) | Open | agent actions + interview | issue discovery |
| Marketing & UX Research | A/B testing | 1 · Survey | Interact with one variant; outcomes compared across arms | AgentA/B | Closed | interaction logs per variant | conversion / preference deltas |
| Social, Civic & Safety | Opinion / political polling | 1 · Survey | Answer attitude/value questions by subgroup | [OpinionQA; Out-of-One-Many](https://github.com/tatsu-lab/opinions_qa) | Open | questionnaire responses | subgroup distribution fidelity |
| Social, Civic & Safety | Social-science experiment replication | 1 · Survey | Respond as a subject in a scenario-based study | [Replace-Human-Subjects](https://osf.io/j6wmn/) | Open | questionnaire responses | effect-size replication rate |
| Social, Civic & Safety | Social media diffusion | 5 · Social sim | Agents post, follow, and spread information | [OASIS; AgentSociety](https://github.com/camel-ai/oasis) | Open | multi-agent logs | emergent network dynamics |
| Social, Civic & Safety | Social-platform prototyping | 5 · Social sim | Seed a platform with believable users + activity | Social Simulacra | Closed | multi-agent logs | designer evaluation |
| Social, Civic & Safety | Multi-agent society / civilization | 5 · Social sim | Many agents live, work, and form groups over time | [AgentSociety; Project Sid](https://github.com/tsinghua-fib-lab/AgentSociety) | Partial | long-horizon logs | emergent social metrics |
| Social, Civic & Safety | Adversarial red-teaming | 5 · Social sim | Probe an agent to elicit harmful or failed responses | [Curiosity red-teaming](https://github.com/Improbable-AI/curiosity_redteam) | Open | adversarial dialogues | failure discovery rate |
| Cross-domain / Assistant | Multi-turn assistant eval | 2 · Chatbot | Hold a general multi-turn conversation across abilities | [MT-Bench-101; LLM-as-judge](https://github.com/mtbench101/mt-bench-101) | Open | multi-turn dialogue | LLM-judge scores |
| Cross-domain / Assistant | Tool-agent-user / API assistant | 2 · Chatbot | Use tools mid-conversation to fulfill a request | [ToolBench / ToolLLM](https://github.com/OpenBMB/ToolBench) | Open | dialogue + API calls | tool-use success |
