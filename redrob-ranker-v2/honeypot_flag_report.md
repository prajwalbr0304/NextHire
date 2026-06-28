# Honeypot Flag Report (post-fix)

Generated: 2026-06-28 - source: redrob-ranker-v2/src/integrity.py over candidates.jsonl (99,999 candidates)

## TL;DR

The integrity layer now flags **80** candidates pool-wide (was 690), matching the documented ~80 honeypots in submission_spec Section 7. Every flag is a genuine impossibility; zero legitimate engineers are caught.

Per-rule breakdown:

| Rule | Count | What it detects (spec pattern) |
|---|---|---|
| expert_zero (>=3) | 21 | >=3 skills marked 'expert' with 0 months used (pattern b) |
| tenure_over_span | 19 | role claims more months than its start->end dates allow (pattern a: '8y at a 3y-old company') |
| tech_age | 40 | a skill used for more years than the technology has existed |
| timeline | 0 | role starts after it ends / in the future |
| **TOTAL** | **80** | |

## Impact on the submission (top 100)

Re-ranking with these rules changed 23 positions in the top 100:

- **23 genuine honeypots were removed** from the old top 100 - all recent-technology-age impossibilities. Most striking: `CAND_0002025` sat at **rank #2** in the old submission while claiming **81 months (~7 years) of QLoRA**, a technique that only appeared in 2023. The old broken 'skill > career' rule missed these entirely.
- **3 legitimate engineers were restored** that the old rule wrongly excluded: `CAND_0075439` (#51), `CAND_0079284` (#52), `CAND_0042506` (#53) - each flagged before only on mature tech (Elasticsearch / Information Retrieval / Deep Learning), where long total usage is plausible.
- The new top 100 contains **0 honeypots** (verified).

## Why the old count was 690

663 of the old 690 came from a single rule comparing a skill's `duration_months` (defined by candidate_schema.json as *total* usage - academic, personal, professional) against `years_of_experience` (*professional* tenure only). Those are different fields, so 17.9% of the whole pool legitimately has skill usage exceeding professional tenure. That rule has been removed.

## Tenure exceeds actual date-span (pattern a) - 19 candidates

| # | candidate_id | current_title | prof_yrs | why flagged |
|---|---|---|---|---|
| 1 | CAND_0007353 | Frontend Engineer | 9.9 | role 'Frontend Engineer' claims 166mo but its dates span only 33mo — impossible tenure |
| 2 | CAND_0008960 | Graphic Designer | 10.3 | role 'Graphic Designer' claims 171mo but its dates span only 21mo — impossible tenure |
| 3 | CAND_0010294 | .NET Developer | 8.0 | role '.NET Developer' claims 144mo but its dates span only 19mo — impossible tenure |
| 4 | CAND_0018515 | Marketing Manager | 8.5 | role 'Marketing Manager' claims 150mo but its dates span only 39mo — impossible tenure |
| 5 | CAND_0035104 | Software Engineer | 5.5 | role 'Software Engineer' claims 114mo but its dates span only 18mo — impossible tenure |
| 6 | CAND_0037539 | Project Manager | 4.9 | role 'Project Manager' claims 106mo but its dates span only 49mo — impossible tenure |
| 7 | CAND_0040075 | Marketing Manager | 15.0 | role 'Marketing Manager' claims 228mo but its dates span only 39mo — impossible tenure |
| 8 | CAND_0040853 | Operations Manager | 1.1 | role 'Operations Manager' claims 61mo but its dates span only 13mo — impossible tenure |
| 9 | CAND_0042453 | Marketing Manager | 4.2 | role 'Marketing Manager' claims 98mo but its dates span only 50mo — impossible tenure |
| 10 | CAND_0043721 | Sales Executive | 4.5 | role 'Sales Executive' claims 102mo but its dates span only 48mo — impossible tenure |
| 11 | CAND_0053734 | Sales Executive | 8.6 | role 'Sales Executive' claims 151mo but its dates span only 32mo — impossible tenure |
| 12 | CAND_0055685 | Customer Support | 1.4 | role 'Customer Support' claims 64mo but its dates span only 16mo — impossible tenure |
| 13 | CAND_0057711 | Java Developer | 7.7 | role 'Java Developer' claims 140mo but its dates span only 51mo — impossible tenure |
| 14 | CAND_0064077 | Project Manager | 10.1 | role 'Project Manager' claims 169mo but its dates span only 51mo — impossible tenure |
| 15 | CAND_0065710 | Marketing Manager | 4.4 | role 'Marketing Manager' claims 100mo but its dates span only 38mo — impossible tenure |
| 16 | CAND_0070189 | Operations Manager | 6.9 | role 'Operations Manager' claims 130mo but its dates span only 39mo — impossible tenure |
| 17 | CAND_0077239 | Content Writer | 7.6 | role 'Content Writer' claims 139mo but its dates span only 49mo — impossible tenure |
| 18 | CAND_0084182 | Civil Engineer | 12.7 | role 'Civil Engineer' claims 200mo but its dates span only 51mo — impossible tenure |
| 19 | CAND_0093364 | Business Analyst | 7.9 | role 'Business Analyst' claims 142mo but its dates span only 26mo — impossible tenure |

## Expert proficiency with 0 months used (pattern b) - 21 candidates

| # | candidate_id | current_title | prof_yrs | why flagged |
|---|---|---|---|---|
| 1 | CAND_0003582 | Mobile Developer | 8.2 | 3 'expert' skills with 0 months of use (MLflow, Photoshop, Content Writing) — impossible |
| 2 | CAND_0016000 | Full Stack Developer | 2.0 | 5 'expert' skills with 0 months of use (TypeScript, Go, Docker, Hadoop, Photoshop) — impossible |
| 3 | CAND_0033817 | HR Manager | 13.3 | 4 'expert' skills with 0 months of use (JavaScript, BigQuery, Six Sigma, gRPC) — impossible |
| 4 | CAND_0033972 | QA Engineer | 6.0 | 3 'expert' skills with 0 months of use (Airflow, OpenCV, Figma) — impossible |
| 5 | CAND_0036839 | Operations Manager | 8.1 | 3 'expert' skills with 0 months of use (SAP, GCP, Rust) — impossible |
| 6 | CAND_0042245 | Business Analyst | 7.9 | 3 'expert' skills with 0 months of use (Databricks, BentoML, Vue.js) — impossible |
| 7 | CAND_0046649 | Business Analyst | 3.8 | 5 'expert' skills with 0 months of use (SAP, Node.js, gRPC, Flask, Hadoop) — impossible |
| 8 | CAND_0046689 | Business Analyst | 2.3 | 4 'expert' skills with 0 months of use (Node.js, SQL, gRPC, Spark) — impossible |
| 9 | CAND_0048740 | HR Manager | 9.9 | 3 'expert' skills with 0 months of use (gRPC, Angular, Content Writing) — impossible |
| 10 | CAND_0055792 | .NET Developer | 9.8 | 3 'expert' skills with 0 months of use (Scrum, TTS, LoRA) — impossible |
| 11 | CAND_0056983 | Accountant | 12.3 | 5 'expert' skills with 0 months of use (Rust, Next.js, Redis, Salesforce CRM, MongoDB) — impossible |
| 12 | CAND_0060642 | Frontend Engineer | 3.0 | 5 'expert' skills with 0 months of use (Milvus, Agile, Azure, Diffusion Models, MongoDB) — impossible |
| 13 | CAND_0061722 | Software Engineer | 6.8 | 5 'expert' skills with 0 months of use (Terraform, GANs, Milvus, MongoDB, Speech Recognition) — impossible |
| 14 | CAND_0063888 | .NET Developer | 2.4 | 5 'expert' skills with 0 months of use (Project Management, Accounting, MLOps, React, Webpack) — impossible |
| 15 | CAND_0065096 | Civil Engineer | 6.7 | 4 'expert' skills with 0 months of use (ETL, Tally, Flask, Rust) — impossible |
| 16 | CAND_0070429 | Software Engineer | 8.1 | 5 'expert' skills with 0 months of use (MLOps, Figma, Accounting, YOLO, Java) — impossible |
| 17 | CAND_0072379 | Content Writer | 3.8 | 4 'expert' skills with 0 months of use (Azure, Redux, Illustrator, Spark) — impossible |
| 18 | CAND_0073853 | Operations Manager | 8.0 | 5 'expert' skills with 0 months of use (CI/CD, Marketing, GCP, Excel, AWS) — impossible |
| 19 | CAND_0095140 | Backend Engineer | 5.0 | 3 'expert' skills with 0 months of use (Kafka, QLoRA, CNN) — impossible |
| 20 | CAND_0095317 | HR Manager | 7.0 | 3 'expert' skills with 0 months of use (Webpack, Figma, dbt) — impossible |
| 21 | CAND_0095480 | .NET Developer | 2.3 | 4 'expert' skills with 0 months of use (Agile, React, Snowflake, Content Writing) — impossible |

## Skill older than the technology itself - 40 candidates

| # | candidate_id | current_title | prof_yrs | why flagged |
|---|---|---|---|---|
| 1 | CAND_0002025 | Senior AI Engineer | 5.9 | skill 'QLoRA' used 81mo (since ~2019) but the technology only existed since ~2023 — impossible |
| 2 | CAND_0009691 | Applied ML Engineer | 6.2 | skill 'LangChain' used 85mo (since ~2019) but the technology only existed since ~2022 — impossible |
| 3 | CAND_0009837 | Senior Data Scientist | 4.3 | skill 'QLoRA' used 76mo (since ~2020) but the technology only existed since ~2023 — impossible |
| 4 | CAND_0011432 | Senior Data Scientist | 7.6 | skill 'QLoRA' used 75mo (since ~2020) but the technology only existed since ~2023 — impossible |
| 5 | CAND_0013536 | Applied ML Engineer | 14.1 | skill 'QLoRA' used 74mo (since ~2020) but the technology only existed since ~2023 — impossible |
| 6 | CAND_0020877 | Applied ML Engineer | 5.1 | skill 'QLoRA' used 83mo (since ~2019) but the technology only existed since ~2023 — impossible |
| 7 | CAND_0029367 | Senior Data Scientist | 5.7 | skill 'LangChain' used 86mo (since ~2019) but the technology only existed since ~2022 — impossible |
| 8 | CAND_0030348 | Machine Learning Engineer | 4.5 | skill 'LlamaIndex' used 96mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 9 | CAND_0030827 | Senior Data Scientist | 5.4 | skill 'LangChain' used 96mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 10 | CAND_0032807 | Machine Learning Engineer | 4.2 | skill 'LangChain' used 92mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 11 | CAND_0037000 | Search Engineer | 2.7 | skill 'LangChain' used 87mo (since ~2019) but the technology only existed since ~2022 — impossible |
| 12 | CAND_0037566 | Machine Learning Engineer | 6.9 | skill 'LangChain' used 91mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 13 | CAND_0040117 | Recommendation Systems Engineer | 6.5 | skill 'LlamaIndex' used 85mo (since ~2019) but the technology only existed since ~2022 — impossible |
| 14 | CAND_0041611 | Staff Machine Learning Engineer | 6.4 | skill 'LangChain' used 90mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 15 | CAND_0042100 | Machine Learning Engineer | 7.3 | skill 'QLoRA' used 84mo (since ~2019) but the technology only existed since ~2023 — impossible |
| 16 | CAND_0044222 | AI Engineer | 7.7 | skill 'LangChain' used 90mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 17 | CAND_0044883 | AI Engineer | 6.3 | skill 'QLoRA' used 80mo (since ~2019) but the technology only existed since ~2023 — impossible |
| 18 | CAND_0045250 | Applied ML Engineer | 6.6 | skill 'LangChain' used 85mo (since ~2019) but the technology only existed since ~2022 — impossible |
| 19 | CAND_0046064 | Senior NLP Engineer | 8.9 | skill 'PEFT' used 92mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 20 | CAND_0050454 | AI Engineer | 6.8 | skill 'QLoRA' used 87mo (since ~2019) but the technology only existed since ~2023 — impossible |
| 21 | CAND_0052682 | NLP Engineer | 6.6 | skill 'QLoRA' used 76mo (since ~2020) but the technology only existed since ~2023 — impossible |
| 22 | CAND_0058688 | AI Engineer | 6.7 | skill 'LlamaIndex' used 91mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 23 | CAND_0061339 | Search Engineer | 4.2 | skill 'LlamaIndex' used 95mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 24 | CAND_0064326 | Search Engineer | 7.6 | skill 'QLoRA' used 76mo (since ~2020) but the technology only existed since ~2023 — impossible |
| 25 | CAND_0065195 | Search Engineer | 5.1 | skill 'QLoRA' used 93mo (since ~2018) but the technology only existed since ~2023 — impossible |
| 26 | CAND_0065878 | Senior Data Scientist | 7.8 | skill 'QLoRA' used 75mo (since ~2020) but the technology only existed since ~2023 — impossible |
| 27 | CAND_0066376 | Applied ML Engineer | 5.7 | skill 'LlamaIndex' used 93mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 28 | CAND_0068351 | Lead AI Engineer | 6.4 | skill 'PEFT' used 94mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 29 | CAND_0076163 | NLP Engineer | 6.9 | skill 'LlamaIndex' used 86mo (since ~2019) but the technology only existed since ~2022 — impossible |
| 30 | CAND_0078002 | Machine Learning Engineer | 6.3 | skill 'QLoRA' used 90mo (since ~2018) but the technology only existed since ~2023 — impossible |
| 31 | CAND_0079064 | Senior Data Scientist | 5.2 | skill 'QLoRA' used 74mo (since ~2020) but the technology only existed since ~2023 — impossible |
| 32 | CAND_0079387 | AI Engineer | 6.9 | skill 'QLoRA' used 83mo (since ~2019) but the technology only existed since ~2023 — impossible |
| 33 | CAND_0081686 | Search Engineer | 6.0 | skill 'QLoRA' used 75mo (since ~2020) but the technology only existed since ~2023 — impossible |
| 34 | CAND_0083307 | Search Engineer | 7.8 | skill 'PEFT' used 92mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 35 | CAND_0087364 | Recommendation Systems Engineer | 4.9 | skill 'LlamaIndex' used 91mo (since ~2018) but the technology only existed since ~2022 — impossible |
| 36 | CAND_0087630 | AI Engineer | 7.2 | skill 'QLoRA' used 92mo (since ~2018) but the technology only existed since ~2023 — impossible |
| 37 | CAND_0088025 | Staff Machine Learning Engineer | 8.6 | skill 'QLoRA' used 83mo (since ~2019) but the technology only existed since ~2023 — impossible |
| 38 | CAND_0091909 | Machine Learning Engineer | 6.9 | skill 'QLoRA' used 89mo (since ~2019) but the technology only existed since ~2023 — impossible |
| 39 | CAND_0092278 | Senior NLP Engineer | 6.8 | skill 'QLoRA' used 79mo (since ~2019) but the technology only existed since ~2023 — impossible |
| 40 | CAND_0093547 | Senior Machine Learning Engineer | 2.9 | skill 'PEFT' used 93mo (since ~2018) but the technology only existed since ~2022 — impossible |
