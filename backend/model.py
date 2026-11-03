"""
LPU Placement Intelligence & Student Readiness Prediction Platform
Core Machine Learning Logic, Synthetic Data Generation, and Explainability Engine
"""

import os
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

# Feature definitions
FEATURE_NAMES = [
    "cgpa",
    "technical_score",
    "aptitude_score",
    "communication_score",
    "coding_score",
    "projects",
    "internships",
    "certifications",
    "backlogs",
]

FEATURE_METADATA = {
    "cgpa": {"label": "Academic CGPA", "unit": "Scale 0-10", "type": "float"},
    "technical_score": {"label": "Technical Skills", "unit": "%", "type": "int"},
    "aptitude_score": {"label": "Aptitude & Reasoning", "unit": "%", "type": "int"},
    "communication_score": {"label": "Communication Skills", "unit": "%", "type": "int"},
    "coding_score": {"label": "Coding Proficiency", "unit": "%", "type": "int"},
    "projects": {"label": "Hands-on Projects", "unit": "count", "type": "int"},
    "internships": {"label": "Industry Internships", "unit": "count", "type": "int"},
    "certifications": {"label": "Relevant Certifications", "unit": "count", "type": "int"},
    "backlogs": {"label": "Active Backlogs", "unit": "count", "type": "int"},
}

# Institutional Target Thresholds for Campus Placement Readiness
TARGET_THRESHOLDS = {
    "cgpa": 7.5,
    "technical_score": 75,
    "aptitude_score": 70,
    "communication_score": 70,
    "coding_score": 75,
    "projects": 2,
    "internships": 1,
    "certifications": 2,
    "backlogs": 0,
}

FEATURE_BOUNDS = {
    "cgpa": (0.0, 10.0),
    "technical_score": (0, 100),
    "aptitude_score": (0, 100),
    "communication_score": (0, 100),
    "coding_score": (0, 100),
    "projects": (0, 30),
    "internships": (0, 15),
    "certifications": (0, 30),
    "backlogs": (0, 20),
}


def generate_synthetic_student_data(n_samples: int = 2500, random_state: int = 42) -> pd.DataFrame:
    """
    Generates a reproducible synthetic student dataset modeling campus placement dynamics.
    NOTE: This is synthetic demonstration data and does not represent actual LPU placement statistics.
    """
    np.random.seed(random_state)

    # 1. CGPA: Normally distributed around 7.2 with standard deviation 1.1, bounded [5.0, 9.9]
    cgpa = np.clip(np.random.normal(loc=7.2, scale=1.1, size=n_samples), 5.0, 9.9)
    cgpa = np.round(cgpa, 2)

    # 2. Coding score: partially correlated with CGPA + individual effort
    coding_noise = np.random.normal(0, 12, size=n_samples)
    coding_score = (cgpa - 5.0) * 11.0 + 35 + coding_noise
    coding_score = np.clip(np.round(coding_score), 25, 99).astype(int)

    # 3. Technical score: correlated with coding and academic performance
    tech_noise = np.random.normal(0, 10, size=n_samples)
    technical_score = 0.5 * coding_score + (cgpa - 5.0) * 6.0 + 20 + tech_noise
    technical_score = np.clip(np.round(technical_score), 30, 99).astype(int)

    # 4. Aptitude & Reasoning: independent test distribution
    aptitude_score = np.random.normal(loc=65, scale=14, size=n_samples)
    aptitude_score = np.clip(np.round(aptitude_score), 25, 98).astype(int)

    # 5. Communication skills: independent distribution with moderate variance
    communication_score = np.random.normal(loc=67, scale=13, size=n_samples)
    communication_score = np.clip(np.round(communication_score), 30, 98).astype(int)

    # 6. Hands-on projects (0 to 5)
    projects_prob = [0.10, 0.25, 0.35, 0.20, 0.08, 0.02]
    projects = np.random.choice([0, 1, 2, 3, 4, 5], size=n_samples, p=projects_prob)

    # 7. Industry Internships (0 to 3)
    internships_prob = [0.50, 0.35, 0.12, 0.03]
    internships = np.random.choice([0, 1, 2, 3], size=n_samples, p=internships_prob)

    # 8. Certifications (0 to 4)
    cert_prob = [0.20, 0.35, 0.25, 0.15, 0.05]
    certifications = np.random.choice([0, 1, 2, 3, 4], size=n_samples, p=cert_prob)

    # 9. Active Backlogs: 0 for majority, small percentage have 1-3
    backlog_prob = [0.78, 0.14, 0.06, 0.02]
    backlogs = np.random.choice([0, 1, 2, 3], size=n_samples, p=backlog_prob)

    # Calculate realistic Placement Readiness Index using a non-linear logit function
    # Weights reflecting standard campus hiring stages (eligibility, coding test, tech interview, HR)
    z = (
        0.55 * (cgpa - 7.0)
        + 0.035 * (coding_score - 65)
        + 0.030 * (technical_score - 65)
        + 0.025 * (aptitude_score - 65)
        + 0.020 * (communication_score - 65)
        + 0.40 * (projects - 1)
        + 0.65 * (internships - 0.5)
        + 0.15 * (certifications - 1)
        - 1.40 * backlogs  # Backlogs severely impact campus drive eligibility
        + np.random.normal(0, 0.5, size=n_samples)  # Unobserved interview variance
    )

    # Sigmoid to get probability of readiness
    prob = 1.0 / (1.0 + np.exp(-z))
    placement_ready = (prob >= 0.50).astype(int)

    df = pd.DataFrame(
        {
            "cgpa": cgpa,
            "technical_score": technical_score,
            "aptitude_score": aptitude_score,
            "communication_score": communication_score,
            "coding_score": coding_score,
            "projects": projects,
            "internships": internships,
            "certifications": certifications,
            "backlogs": backlogs,
            "placement_ready": placement_ready,
        }
    )

    return df


def train_placement_model(
    data_df: pd.DataFrame = None, save_path: str = "placement_model.joblib"
) -> dict:
    """
    Trains the approved Gradient Boosting classifier on the canonical readiness
    dataset and saves the model artifact. Evaluation results are reported by
    compare_models.py using repeated cross-validation.
    """
    if data_df is None:
        csv_path = os.path.join(os.path.dirname(__file__), "..", "dataset", "students.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(
                f"Canonical training dataset '{csv_path}' was not found. "
                "Synthetic fallback is disabled for production training."
            )
        data_df = pd.read_csv(csv_path)

    X = data_df[FEATURE_NAMES]
    y = data_df["placement_ready"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    clf = GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=5,
        random_state=42,
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_pred_proba = clf.predict_proba(X_test)[:, 1]

    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_pred_proba)), 4),
        "confusion_matrix": cm,
        "test_rows": len(y_test),
        "train_rows": len(y_train),
        "model_name": "Gradient Boosting",
        "data_note": "Educational prototype trained against the project dataset label; source provenance and alignment with actual LPU placement outcomes are unverified.",
    }

    # Calculate global feature importance
    importance_map = {}
    total_imp = sum(clf.feature_importances_)
    for f, imp in zip(FEATURE_NAMES, clf.feature_importances_, strict=False):
        importance_map[f] = round(float(imp / total_imp) * 100, 2)

    # Sort descending
    sorted_importance = dict(sorted(importance_map.items(), key=lambda item: item[1], reverse=True))

    payload = {
        "model": clf,
        "algorithm": "Gradient Boosting Classifier",
        "feature_names": FEATURE_NAMES,
        "feature_metadata": FEATURE_METADATA,
        "target_thresholds": TARGET_THRESHOLDS,
        "metrics": metrics,
        "feature_importance": sorted_importance,
        "trained_at": datetime.now().isoformat(),
        "model_version": "1.0.0-gb-winner",
    }

    joblib.dump(payload, save_path)
    return payload


def load_model(model_path: str = "placement_model.joblib") -> dict:
    """
    Loads saved model artifact dictionary.
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model file '{model_path}' not found. Please run train_model.py first."
        )
    return joblib.load(model_path)


def validate_student_input(data: dict) -> tuple[bool, str | dict]:
    """
    Validates student profile input bounds and types.
    """
    if not isinstance(data, dict):
        return False, "Input payload must be a JSON object."

    sanitized = {}

    bounds = {
        "cgpa": (0.0, 10.0, float, "CGPA must be a number between 0.0 and 10.0"),
        "technical_score": (0, 100, int, "Technical score must be an integer between 0 and 100"),
        "aptitude_score": (0, 100, int, "Aptitude score must be an integer between 0 and 100"),
        "communication_score": (
            0,
            100,
            int,
            "Communication score must be an integer between 0 and 100",
        ),
        "coding_score": (0, 100, int, "Coding score must be an integer between 0 and 100"),
        "projects": (0, 30, int, "Projects must be an integer between 0 and 30"),
        "internships": (0, 15, int, "Internships must be an integer between 0 and 15"),
        "certifications": (0, 30, int, "Certifications must be an integer between 0 and 30"),
        "backlogs": (0, 20, int, "Active backlogs must be an integer between 0 and 20"),
    }

    for field, (min_val, max_val, cast_type, err_msg) in bounds.items():
        if field not in data:
            return False, f"Missing required field: '{field}'."
        try:
            val = cast_type(data[field])
            if val < min_val or val > max_val:
                return False, err_msg
            sanitized[field] = val
        except (ValueError, TypeError):
            return False, f"Invalid value for '{field}'. {err_msg}"

    return True, sanitized


def calculate_skill_gaps(student: dict, thresholds: dict | None = None) -> list[dict]:
    """
    Evaluates individual student skills against institutional placement benchmarks.
    """
    thresholds = thresholds or TARGET_THRESHOLDS
    gaps = []

    # 1. CGPA
    cgpa_target = thresholds["cgpa"]
    cgpa_val = student["cgpa"]
    if cgpa_val >= cgpa_target:
        cgpa_status = "Target Met"
        cgpa_action = "Maintain academic consistency to clear initial company eligibility cutoffs."
        severity = "met"
    elif cgpa_val >= 6.5:
        cgpa_status = "Minor Gap"
        cgpa_action = "Focus on upcoming end-term examinations to push cumulative CGPA above 7.5."
        severity = "warning"
    else:
        cgpa_status = "Critical Gap"
        cgpa_action = (
            "Urgent academic focus needed. Minimum 6.5-7.0 CGPA required for 75%+ campus drives."
        )
        severity = "critical"

    gaps.append(
        {
            "skill": "Academic Performance (CGPA)",
            "current": cgpa_val,
            "target": cgpa_target,
            "unit": "Scale 0-10",
            "status": cgpa_status,
            "severity": severity,
            "action": cgpa_action,
        }
    )

    # 2. Coding Proficiency
    coding_target = thresholds["coding_score"]
    coding_val = student["coding_score"]
    if coding_val >= coding_target:
        coding_status = "Target Met"
        coding_action = "Practice advanced dynamic programming, graphs, and system design basics."
        severity = "met"
    elif coding_val >= 55:
        coding_status = "Moderate Gap"
        coding_action = (
            "Complete 2 medium DSA problems daily on LeetCode/HackerRank (focus on Trees & DP)."
        )
        severity = "warning"
    else:
        coding_status = "Critical Gap"
        coding_action = (
            "Initiate a 60-day structured DSA roadmap: Arrays, Strings, Hashmaps, Recursion."
        )
        severity = "critical"

    gaps.append(
        {
            "skill": "Coding Proficiency",
            "current": coding_val,
            "target": coding_target,
            "unit": "%",
            "status": coding_status,
            "severity": severity,
            "action": coding_action,
        }
    )

    # 3. Technical Skills
    tech_target = thresholds["technical_score"]
    tech_val = student["technical_score"]
    if tech_val >= tech_target:
        tech_status = "Target Met"
        tech_action = (
            "Deepen specialized domain knowledge (Cloud, Microservices, or ML/AI architectures)."
        )
        severity = "met"
    elif tech_val >= 55:
        tech_status = "Moderate Gap"
        tech_action = "Revise Core CS fundamentals: DBMS (SQL & Normalization), OS (Threading), and Computer Networks."
        severity = "warning"
    else:
        tech_status = "Critical Gap"
        tech_action = (
            "Revisit Object-Oriented Programming (Java/C++/Python) and Database query writing."
        )
        severity = "critical"

    gaps.append(
        {
            "skill": "Technical Knowledge",
            "current": tech_val,
            "target": tech_target,
            "unit": "%",
            "status": tech_status,
            "severity": severity,
            "action": tech_action,
        }
    )

    # 4. Aptitude & Reasoning
    apt_target = thresholds["aptitude_score"]
    apt_val = student["aptitude_score"]
    if apt_val >= apt_target:
        apt_status = "Target Met"
        apt_action = "Take speed-based timed sectional mock tests every weekend."
        severity = "met"
    elif apt_val >= 55:
        apt_status = "Moderate Gap"
        apt_action = "Focus on Quantitative Aptitude (Time & Work, Permutations, Probability) and Logical Seating."
        severity = "warning"
    else:
        apt_status = "Critical Gap"
        apt_action = "Start daily 45-minute timed aptitude drills using IndiaBIX or Prepleet tests."
        severity = "critical"

    gaps.append(
        {
            "skill": "Aptitude & Reasoning",
            "current": apt_val,
            "target": apt_target,
            "unit": "%",
            "status": apt_status,
            "severity": severity,
            "action": apt_action,
        }
    )

    # 5. Communication Skills
    comm_target = thresholds["communication_score"]
    comm_val = student["communication_score"]
    if comm_val >= comm_target:
        comm_status = "Target Met"
        comm_action = "Practice structuring leadership responses using the STAR method for behavioral interviews."
        severity = "met"
    elif comm_val >= 55:
        comm_status = "Moderate Gap"
        comm_action = "Participate in departmental Group Discussions and record 2-minute spontaneous tech talk videos."
        severity = "warning"
    else:
        comm_status = "Critical Gap"
        comm_action = (
            "Practice mock HR interviews; focus on structured self-introduction and articulation."
        )
        severity = "critical"

    gaps.append(
        {
            "skill": "Communication & HR Fit",
            "current": comm_val,
            "target": comm_target,
            "unit": "%",
            "status": comm_status,
            "severity": severity,
            "action": comm_action,
        }
    )

    # 6. Projects
    proj_target = thresholds["projects"]
    proj_val = student["projects"]
    if proj_val >= proj_target:
        proj_status = "Target Met"
        proj_action = "Add live deployment links, architecture diagrams, and comprehensive README documentation on GitHub."
        severity = "met"
    elif proj_val == 1:
        proj_status = "Moderate Gap"
        proj_action = "Build a second full-stack or domain-specific project featuring authentication and REST APIs."
        severity = "warning"
    else:
        proj_status = "Critical Gap"
        proj_action = "Immediately build at least 2 end-to-end deployed projects to substantiate resume claims."
        severity = "critical"

    gaps.append(
        {
            "skill": "Practical Projects",
            "current": proj_val,
            "target": proj_target,
            "unit": "projects",
            "status": proj_status,
            "severity": severity,
            "action": proj_action,
        }
    )

    # 7. Internships
    intern_target = thresholds["internships"]
    intern_val = student["internships"]
    if intern_val >= intern_target:
        intern_status = "Target Met"
        intern_action = "Prepare quantifiable impact metrics (e.g., % latency reduced, tickets resolved) for interviews."
        severity = "met"
    else:
        intern_status = "Experience Gap"
        intern_action = "Apply for summer internships via LPU Career Portal or contribute to open-source GitHub projects."
        severity = "warning"

    gaps.append(
        {
            "skill": "Industry Internship",
            "current": intern_val,
            "target": intern_target,
            "unit": "internships",
            "status": intern_status,
            "severity": severity,
            "action": intern_action,
        }
    )

    # 8. Active Backlogs
    backlog_target = thresholds["backlogs"]
    backlog_val = student["backlogs"]
    if backlog_val == 0:
        backlog_status = "Clean Record"
        backlog_action = (
            "Eligible for tier-1 product and consulting companies with zero backlog criteria."
        )
        severity = "met"
    else:
        backlog_status = "Urgent Alert"
        backlog_action = f"{backlog_val} active backlog(s) disqualify from 80%+ campus drives. Clear during remedial exams."
        severity = "critical"

    gaps.append(
        {
            "skill": "Backlog Status",
            "current": backlog_val,
            "target": backlog_target,
            "unit": "backlogs",
            "status": backlog_status,
            "severity": severity,
            "action": backlog_action,
        }
    )

    certification_target = thresholds["certifications"]
    certification_val = student["certifications"]
    certification_gap = max(certification_target - certification_val, 0)
    gaps.append(
        {
            "skill": "Relevant Certifications",
            "current": certification_val,
            "target": certification_target,
            "unit": "certifications",
            "status": "Target Met" if certification_gap == 0 else "Certification Gap",
            "severity": "met" if certification_gap == 0 else "warning",
            "action": (
                "Maintain current credentials and keep them aligned with target roles."
                if certification_gap == 0
                else f"Complete {certification_gap} relevant certification(s) in the target domain and add a practical project demonstrating the skill."
            ),
        }
    )

    for gap in gaps:
        is_backlog = gap["skill"] == "Backlog Status"
        gap["target_met"] = (
            gap["current"] == gap["target"] if is_backlog else gap["current"] >= gap["target"]
        )
        gap["gap_delta"] = round(
            (
                float(gap["current"] - gap["target"])
                if is_backlog
                else float(gap["target"] - gap["current"])
            ),
            2,
        )
        gap["priority"] = (
            "high"
            if gap["severity"] == "critical"
            else "medium" if gap["severity"] == "warning" else "low"
        )

    return gaps


def generate_personalized_recommendations(
    student: dict, skill_gaps: list[dict], readiness_score: int
) -> list[dict]:
    """
    Produces transparent, prioritized recommendations mapped directly to low-scoring attributes.
    """
    recommendations = []

    # Priority 1: Backlogs
    if student["backlogs"] > 0:
        recommendations.append(
            {
                "category": "Immediate Priority",
                "priority": "High",
                "badge": "Academic Clearance",
                "title": "Review your active backlog plan",
                "details": f"Your profile records {student['backlogs']} active backlog(s). Check the current eligibility notice for each drive; requirements vary by employer.",
                "action_items": [
                    "Confirm the next available assessment or remediation date with your department.",
                    "Agree a weekly study plan with your academic mentor.",
                    "Recheck the published eligibility notice for your target drive.",
                ],
            }
        )

    # Priority 2: Coding Proficiency
    if student["coding_score"] < 70:
        recommendations.append(
            {
                "category": "Technical Assessment",
                "priority": "High" if student["coding_score"] < 50 else "Medium",
                "badge": "DSA & Problem Solving",
                "title": "Structured 45-Day Data Structures & Algorithms Sprint",
                "details": f"Your latest profile records a coding score of {student['coding_score']}%. The role profile uses a provisional coding reference; employer assessments vary.",
                "action_items": [
                    "Solve Blind 75 LeetCode problems (focus: Sliding Window, Two Pointers, Trees, HashMaps).",
                    "Practice on HackerRank / CodeChef under timed 45-minute constraints.",
                    "Master language-specific libraries (C++ STL, Java Collections, or Python standard data structures).",
                ],
            }
        )

    # Priority 3: Aptitude & Reasoning
    if student["aptitude_score"] < 70:
        recommendations.append(
            {
                "category": "Online Assessment Round",
                "priority": "High" if student["aptitude_score"] < 50 else "Medium",
                "badge": "Aptitude Drill",
                "title": "Daily Speed-Math and Analytical Reasoning Routine",
                "details": f"Your latest profile records an aptitude score of {student['aptitude_score']}%. The comparison target is a project-defined practice reference, not an employer cutoff.",
                "action_items": [
                    "Practice 20 quantitative questions daily (Time & Distance, Permutations, Percentages).",
                    "Solve 2 logical reasoning sets (Syllogisms, Blood Relations, Seating Arrangements).",
                    "Take weekly mock company-pattern tests on platforms like Prepleet or IndiaBIX.",
                ],
            }
        )

    # Priority 4: Communication & HR Fit
    if student["communication_score"] < 70:
        recommendations.append(
            {
                "category": "Interview Performance",
                "priority": "Medium",
                "badge": "Communication & HR",
                "title": "Mock Interview & Technical Articulation Practice",
                "details": f"Communication score is {student['communication_score']}%. Clear articulation of technical ideas and structured HR responses are essential for final selections.",
                "action_items": [
                    "Prepare STAR method (Situation, Task, Action, Result) answers for resume projects.",
                    "Attend departmental peer mock interviews twice weekly.",
                    "Practice 2-minute elevator pitches for 'Tell me about yourself' and 'Why this company?'.",
                ],
            }
        )

    # Priority 5: Projects
    if student["projects"] < 2:
        recommendations.append(
            {
                "category": "Resume Enhancement",
                "priority": "Medium",
                "badge": "Portfolio Project",
                "title": "Build and Deploy an Industry-Grade Capstone Project",
                "details": "A documented project gives you evidence to discuss your design choices and contribution.",
                "action_items": [
                    "Build a full-stack project (e.g., MERN, Flask/React, or AI service) with live deployment.",
                    "Implement secure authentication, clean API documentation, and relational/NoSQL storage.",
                    "Publish a comprehensive GitHub repository with a detailed README and system architecture diagram.",
                ],
            }
        )

    # Priority 6: Internships
    if student["internships"] == 0:
        recommendations.append(
            {
                "category": "Industry Exposure",
                "priority": "Low",
                "badge": "Internship Hunting",
                "title": "Target Live Industrial Training or Open-Source Programs",
                "details": "Internship or practical-work evidence can help you describe how you applied your skills.",
                "action_items": [
                    "Optimize LinkedIn profile with relevant keywords and project showcases.",
                    "Apply to early-stage startup internships via AngelList / Wellfound / Internshala.",
                    "Contribute bug fixes to active open-source GitHub repositories.",
                ],
            }
        )

    # Priority 6: Certifications
    if student["certifications"] < TARGET_THRESHOLDS["certifications"]:
        recommendations.append(
            {
                "category": "Credential Development",
                "priority": "Medium",
                "badge": "Certification Plan",
                "title": "Earn Role-Relevant Certifications",
                "details": (
                    f"Complete at least {TARGET_THRESHOLDS['certifications']} relevant "
                    "certifications and connect each credential to a practical project."
                ),
                "action_items": [
                    "Choose one target role and select certifications that map to its required tools.",
                    "Complete one credential within the next 8 weeks.",
                    "Publish a project or portfolio artifact demonstrating the certified skill.",
                ],
            }
        )

    # If already high readiness, add advanced acceleration tips
    if readiness_score >= 75 and len(recommendations) < 3:
        recommendations.append(
            {
                "category": "High Performance",
                "priority": "Low",
                "badge": "Dream Package Acceleration",
                "title": "Prepare for your next interview milestone",
                "details": "Your profile demonstrates strong foundation across all key dimensions.",
                "action_items": [
                    "Study Low-Level Design (LLD) design patterns and High-Level Design (HLD) concepts.",
                    "Practice competitive programming (Codeforces Div 2 / LeetCode Hard).",
                    "Ask a mentor to review your target-role preparation plan.",
                ],
            }
        )

    recommendation_features = {
        "Academic Clearance": "backlogs",
        "DSA & Problem Solving": "coding_score",
        "Aptitude Drill": "aptitude_score",
        "Communication & HR": "communication_score",
        "Portfolio Project": "projects",
        "Internship Hunting": "internships",
        "Certification Plan": "certifications",
    }
    for recommendation in recommendations:
        recommendation["target_feature"] = recommendation_features.get(recommendation["badge"])
        feature = recommendation["target_feature"]
        if feature:
            current = student.get(feature)
            target = TARGET_THRESHOLDS.get(feature)
            labels = {
                "backlogs": "active backlogs", "coding_score": "coding assessment",
                "aptitude_score": "aptitude assessment", "communication_score": "communication assessment",
                "projects": "completed projects", "internships": "internships",
                "certifications": "certifications",
            }
            recommendation["evidence"] = (
                f"Current profile records {current} {labels.get(feature, feature)}; "
                f"the project-defined reference is {target}. These criteria are provisional."
            )
            recommendation["progress_measure"] = (
                f"Update the {labels.get(feature, feature)} evidence and complete a comparable reassessment."
            )
            recommendation["effort_hours"] = 3 if feature in {"coding_score", "aptitude_score", "communication_score"} else 4
            recommendation["suggested_days"] = 7
        else:
            recommendation["evidence"] = "Based on the current readiness estimate and available profile fields."
            recommendation["progress_measure"] = "Review progress with your mentor and reassess after completing the action."
            recommendation["effort_hours"] = 3
            recommendation["suggested_days"] = 7
        recommendation["measurable"] = True
    # Keep the immediate plan short; the other gaps remain visible in the gap matrix.
    return recommendations[:3]


def _predict_probability(model, feature_names: list[str], student: dict) -> float:
    input_df = pd.DataFrame([student])[feature_names]
    return float(model.predict_proba(input_df)[0][1])


def _local_explanations(
    model,
    feature_names: list[str],
    feature_metadata: dict,
    target_thresholds: dict,
    student: dict,
    probability: float,
) -> list[dict]:
    """Estimate local feature direction by replacing one value with its target reference.

    This is a one-feature-at-a-time sensitivity explanation, not a causal effect
    and not a guarantee that contributions sum to the predicted probability.
    """
    explanations = []
    for feature in feature_names:
        reference_student = dict(student)
        reference_student[feature] = target_thresholds[feature]
        reference_probability = _predict_probability(model, feature_names, reference_student)
        contribution = probability - reference_probability
        explanations.append(
            {
                "feature": feature,
                "label": feature_metadata[feature]["label"],
                "current_value": student[feature],
                "reference_value": target_thresholds[feature],
                "contribution": round(contribution, 4),
                "contribution_points": round(contribution * 100, 1),
                "direction": (
                    "supports readiness"
                    if contribution > 0.01
                    else (
                        "reduces readiness"
                        if contribution < -0.01
                        else "neutral at current profile"
                    )
                ),
                "explanation_method": "one_feature_reference_sensitivity",
            }
        )
    return sorted(explanations, key=lambda item: abs(item["contribution"]), reverse=True)


def _counterfactual_scenarios(
    model,
    feature_names: list[str],
    feature_metadata: dict,
    target_thresholds: dict,
    student: dict,
    probability: float,
) -> list[dict]:
    scenarios = []
    for feature in feature_names:
        current = student[feature]
        target = target_thresholds[feature]
        if feature == "backlogs":
            improved_value = min(current, target)
        else:
            improved_value = max(current, target)
        if improved_value == current:
            continue

        scenario_student = dict(student)
        scenario_student[feature] = improved_value
        scenario_probability = _predict_probability(model, feature_names, scenario_student)
        scenarios.append(
            {
                "feature": feature,
                "label": feature_metadata[feature]["label"],
                "current_value": current,
                "target_value": improved_value,
                "change": round(float(improved_value - current), 2),
                "projected_probability": round(scenario_probability, 4),
                "probability_gain": round(scenario_probability - probability, 4),
                "unit": feature_metadata[feature]["unit"],
                "note": "Directional scenario only; it is not a placement guarantee.",
            }
        )
    return sorted(scenarios, key=lambda item: item["probability_gain"], reverse=True)[:5]


def predict_student_readiness(model_payload: dict, student: dict) -> dict:
    """
    Performs inference, calculates readiness explanations, evaluates skill gaps,
    and creates personalized recommendations.
    """
    model = model_payload.get("probability_model", model_payload["model"])
    feature_names = model_payload["feature_names"]

    # Create 1-row DataFrame with exact training columns
    input_df = pd.DataFrame([student])[feature_names]

    # Predict probability of placement readiness
    proba = model.predict_proba(input_df)[0][1]
    is_calibrated = "calibration" in model_payload or "calibration_metrics" in model_payload
    readiness_score = int(round(proba * 100))

    # Determine readiness classification
    if readiness_score >= 75:
        category = "Placement Ready"
        category_description = "Strong profile meeting top campus criteria. Focus on interview polish and dream offers."
        badge_variant = "success"
    elif readiness_score >= 50:
        category = "Nearly Ready"
        category_description = "Solid foundation with identifiable gaps. Targeted 4-week preparation will cross placement thresholds."
        badge_variant = "warning"
    else:
        category = "Needs Focus"
        category_description = "Significant skill and eligibility gaps detected. Immediate academic and coding intervention required."
        badge_variant = "critical"

    # Skill gaps
    target_thresholds = model_payload.get("target_thresholds", TARGET_THRESHOLDS)
    skill_gaps = calculate_skill_gaps(student, target_thresholds)

    # Recommendations
    recommendations = generate_personalized_recommendations(student, skill_gaps, readiness_score)

    local_explanations = _local_explanations(
        model,
        feature_names,
        model_payload.get("feature_metadata", FEATURE_METADATA),
        model_payload.get("target_thresholds", TARGET_THRESHOLDS),
        student,
        float(proba),
    )
    counterfactuals = _counterfactual_scenarios(
        model,
        feature_names,
        model_payload.get("feature_metadata", FEATURE_METADATA),
        model_payload.get("target_thresholds", TARGET_THRESHOLDS),
        student,
        float(proba),
    )

    # Feature importance for display
    importance_list = [
        {
            "feature": f,
            "label": FEATURE_METADATA[f]["label"],
            "importance": model_payload["feature_importance"].get(f, 0.0),
        }
        for f in feature_names
    ]
    importance_list.sort(key=lambda x: x["importance"], reverse=True)

    return {
        "model_version": model_payload.get("model_version", "unversioned"),
        "outcome_label": "placement_ready",
        "outcome_definition": "Project dataset label placement_ready; its source meaning and alignment with LPU placement outcomes are unverified.",
        "evaluation_summary": {
            "train_rows": model_payload.get("metrics", {}).get("train_rows"),
            "test_rows": model_payload.get("metrics", {}).get("test_rows"),
            "evaluated_at": model_payload.get("trained_at"),
            "metrics": model_payload.get("metrics"),
        },
        "readiness_score": readiness_score,
        "readiness_category": category,
        "readiness_description": category_description,
        "badge_variant": badge_variant,
        "model_probability": round(float(proba), 4),
        "calibrated_probability": round(float(proba), 4) if is_calibrated else None,
        "probability_is_calibrated": is_calibrated,
        "probability_note": (
            "Calibrated readiness probability estimated with sigmoid calibration."
            if is_calibrated
            else "Raw model score from predict_proba; it is not calibrated and should only be used as a readiness ranking indicator."
        ),
        "top_factors": importance_list,
        "local_explanations": local_explanations,
        "counterfactual_scenarios": counterfactuals,
        "skill_gaps": skill_gaps,
        "recommendations": recommendations,
        "student_profile": student,
        "disclaimer": "This readiness assessment is generated by an educational prototype trained against a project dataset label whose provenance and meaning are unverified. It is not validated against actual LPU student outcomes and does not guarantee campus placement.",
    }
