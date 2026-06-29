"""
Job-role catalogue for the demo UI.

The contest scores against ONE job description (the Senior AI Engineer JD, loaded
from jd_intent.json). For the interactive dashboard we generalise: the user picks
a target role from a dropdown, and we hand the scoring engine a role-specific
"intent profile" with the SAME schema as jd_intent.json.

Each role overrides the discriminative fields (query text, must-have keywords,
positive/negative titles, in-domain vs off-domain skills, experience band) while
sharing the generic fields (evidence verbs, product/services lists, locations)
from the base JD so the Council-of-Nine code works unchanged.
"""
from __future__ import annotations

import json

from . import config

with open(config.JD_INTENT_PATH, "r", encoding="utf-8") as _f:
    BASE = json.load(_f)

# fields shared across every role
_SHARED = {
    "evidence_phrases": BASE["evidence_phrases"],
    "product_industries": BASE["product_industries"],
    "services_companies": BASE["services_companies"],
    "preferred_locations": BASE["preferred_locations"],
    "company": "Redrob (configurable employer)",
    # disqualifier vocabularies (inherited so every role gets the same gates)
    "research_industries": BASE["research_industries"],
    "research_titles": BASE["research_titles"],
    "research_company_markers": BASE["research_company_markers"],
    "wrapper_skills": BASE["wrapper_skills"],
    "core_ml_skills": BASE["core_ml_skills"],
    "leadership_titles": BASE["leadership_titles"],
    "eval_skills": BASE["eval_skills"],
    "external_validation_markers": BASE["external_validation_markers"],
}


def _role(title, query, must, nice, pos, neg, indomain, offdomain, exp):
    d = {
        "role_title": title,
        "query_text": query,
        "must_have_capabilities": must,
        "nice_to_have": nice,
        "positive_titles": pos,
        "negative_titles": neg,
        "ir_nlp_skills": indomain,
        "offdomain_skills": offdomain,
        "experience": exp,
    }
    d.update(_SHARED)
    return d


# ---------------------------------------------------------------------------
# Role catalogue
# ---------------------------------------------------------------------------
ROLES = {
    # The exact contest JD — kept verbatim from jd_intent.json.
    "Senior AI / ML Engineer (Contest JD)": BASE,

    "Software / Backend Engineer": _role(
        "Software / Backend Engineer",
        "Backend software engineer building scalable APIs, microservices, "
        "distributed systems and databases. Strong in Python, Java, Go, SQL, "
        "system design, cloud, REST, gRPC, high-throughput production services.",
        must=["python", "java", "go", "golang", "backend", "api", "rest", "grpc",
              "microservices", "distributed systems", "sql", "postgresql", "mysql",
              "redis", "kafka", "system design", "docker", "kubernetes", "aws",
              "spring", "node", "scalability", "database"],
        nice=["graphql", "terraform", "ci/cd", "event-driven", "caching"],
        pos=["software engineer", "backend engineer", "senior software engineer",
             "full stack", "fullstack", "full-stack", "java developer",
             "platform engineer", "staff engineer", "principal engineer",
             "developer", "sde"],
        neg=["hr manager", "human resources", "marketing manager", "content writer",
             "graphic designer", "sales executive", "accountant", "civil engineer",
             "mechanical engineer", "customer support", "nurse", "teacher"],
        indomain=["backend", "api", "microservices", "distributed", "sql",
                  "system design", "scalability", "java", "go", "python"],
        offdomain=["photoshop", "figma", "illustrator", "video editing",
                   "copywriting", "payroll", "recruiting"],
        exp={"required_low": 3, "required_high": 12, "ideal_low": 4, "ideal_high": 9},
    ),

    "Data Scientist / Analyst": _role(
        "Data Scientist / Analyst",
        "Data scientist and analyst skilled in statistics, machine learning, "
        "Python, R, SQL, data visualisation, A/B testing, predictive modelling, "
        "pandas, scikit-learn, business insights and experimentation.",
        must=["data science", "machine learning", "statistics", "python", "r",
              "sql", "pandas", "numpy", "scikit-learn", "tableau", "power bi",
              "visualization", "a/b testing", "regression", "predictive modeling",
              "analytics", "experimentation", "forecasting", "deep learning"],
        nice=["spark", "airflow", "mlops", "nlp", "time series", "causal inference"],
        pos=["data scientist", "data analyst", "machine learning engineer",
             "ml engineer", "applied scientist", "research scientist",
             "business analyst", "analytics", "quantitative"],
        neg=["hr manager", "marketing manager", "content writer", "graphic designer",
             "sales executive", "civil engineer", "mechanical engineer",
             "customer support", "front office"],
        indomain=["statistics", "machine learning", "python", "sql", "analytics",
                  "modeling", "visualization", "experimentation"],
        offdomain=["photoshop", "figma", "video editing", "welding", "plumbing"],
        exp={"required_low": 2, "required_high": 12, "ideal_low": 3, "ideal_high": 8},
    ),

    "Frontend / Full-Stack Developer": _role(
        "Frontend / Full-Stack Developer",
        "Frontend and full-stack developer building modern web apps with "
        "JavaScript, TypeScript, React, Next.js, Vue, HTML, CSS, Tailwind, "
        "responsive UI, REST APIs and great user experience.",
        must=["javascript", "typescript", "react", "next.js", "nextjs", "vue",
              "angular", "html", "css", "tailwind", "frontend", "front-end",
              "ui", "ux", "redux", "node", "web", "responsive", "rest", "api"],
        nice=["graphql", "webpack", "vite", "testing", "accessibility", "figma"],
        pos=["frontend engineer", "front-end engineer", "full stack", "fullstack",
             "full-stack", "web developer", "ui engineer", "software engineer",
             "javascript developer", "react developer", "mobile developer"],
        neg=["hr manager", "marketing manager", "accountant", "sales executive",
             "civil engineer", "mechanical engineer", "customer support",
             "content writer"],
        indomain=["javascript", "react", "frontend", "css", "typescript", "web",
                  "ui", "vue", "angular"],
        offdomain=["payroll", "welding", "accounting", "recruiting", "robotics"],
        exp={"required_low": 2, "required_high": 12, "ideal_low": 3, "ideal_high": 8},
    ),

    "DevOps / Cloud Engineer": _role(
        "DevOps / Cloud Engineer",
        "DevOps and cloud engineer expert in AWS, Azure, GCP, Kubernetes, Docker, "
        "Terraform, CI/CD pipelines, infrastructure as code, observability, "
        "Linux, and site reliability engineering at scale.",
        must=["devops", "aws", "azure", "gcp", "kubernetes", "docker", "terraform",
              "ci/cd", "jenkins", "ansible", "linux", "infrastructure", "cloud",
              "sre", "observability", "prometheus", "monitoring", "helm",
              "automation", "networking"],
        nice=["service mesh", "gitops", "argocd", "security", "cost optimization"],
        pos=["devops engineer", "cloud engineer", "site reliability", "sre",
             "platform engineer", "infrastructure engineer", "systems engineer",
             "software engineer", "cloud architect"],
        neg=["hr manager", "marketing manager", "content writer", "graphic designer",
             "sales executive", "accountant", "civil engineer", "customer support"],
        indomain=["devops", "kubernetes", "cloud", "aws", "terraform", "docker",
                  "infrastructure", "linux", "ci/cd"],
        offdomain=["photoshop", "figma", "copywriting", "payroll", "welding"],
        exp={"required_low": 2, "required_high": 14, "ideal_low": 4, "ideal_high": 10},
    ),

    "Product / Project Manager": _role(
        "Product / Project Manager",
        "Product and project manager driving roadmap, stakeholder management, "
        "agile delivery, user research, product strategy, prioritisation, "
        "cross-functional leadership and data-informed decisions.",
        must=["product management", "project management", "roadmap", "agile",
              "scrum", "stakeholder", "product strategy", "prioritization",
              "user research", "go-to-market", "jira", "kpis", "backlog",
              "leadership", "delivery", "requirements", "analytics"],
        nice=["sql", "a/b testing", "wireframing", "okrs", "p&l"],
        pos=["product manager", "project manager", "program manager",
             "product owner", "operations manager", "delivery manager",
             "business analyst", "scrum master"],
        neg=["graphic designer", "content writer", "civil engineer",
             "mechanical engineer", "nurse", "chef", "qa engineer"],
        indomain=["product", "project", "agile", "roadmap", "stakeholder",
                  "strategy", "delivery", "management"],
        offdomain=["welding", "plumbing", "photoshop", "kubernetes", "soldering"],
        exp={"required_low": 3, "required_high": 16, "ideal_low": 5, "ideal_high": 12},
    ),
}


def role_names():
    return list(ROLES.keys())


def get_role(name: str) -> dict:
    return ROLES.get(name, BASE)
