# LPU Placement Intelligence Platform
## Dataset repository and audit guide

> **Governance notice:** This folder contains prototype, curated, and external
> benchmark files with different populations and target definitions. The files
> must not be merged or used for institutional decisions without provenance,
> license, label, consent, duplicate, missing-value, and leakage review.
> Run `py -3.13 dataset\data_audit.py` from the repository root before using a
> dataset for training or validation. The generated evidence is stored under
> `reports/data-audit/`.

---

## Datasets in the `dataset/` Folder

The project currently contains **7 distinct datasets** with a combined total of
**4,048 rows**. The total is a repository count, not a count of verified
students: some files contain duplicates, one contains missing salary values,
and provenance and label construction still require owner confirmation.

| # | Dataset File | Rows | Features | Focus / Schema |
|---|---|---|---|---|
| **1** | [`students.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/students.csv) | 253 | 10 | Primary LPU 9-feature Competency Model (CGPA, Coding, Technical, Aptitude, Projects, Backlogs) |
| **2** | [`college_placement_engineering.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/college_placement_engineering.csv) | 2,966 | 8 | Real Engineering Students Placement (Age, Gender, Stream, Internships, CGPA, Backlogs, Placed) |
| **3** | [`campus_recruitment_kaggle.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/campus_recruitment_kaggle.csv) | 215 | 15 | Kaggle Campus Recruitment (10th%, 12th%, Degree%, WorkEx, Aptitude%, MBA%, Salary) |
| **4** | [`job_placement_features.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/job_placement_features.csv) | 215 | 13 | Multi-factor Cleaned Job Placement Data (Standardized percentages, streams, status) |
| **5** | [`engineering_skills_placement.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/engineering_skills_placement.csv) | 99 | 13 | Engineering Semesters + Programming Language + Certifications + Field Placement |
| **6** | [`placement_package_salary.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/placement_package_salary.csv) | 200 | 2 | Student CGPA vs Placement Salary Package in LPA (Linear / Polynomial Regression) |
| **7** | [`placement_iq_academic.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/placement_iq_academic.csv) | 100 | 3 | Cognitive Ability (IQ) + Academic CGPA Placement Classification |

---

## Detailed Dataset Profiles

### Dataset 1 — Primary Curated Dataset: `students.csv`
* **Records**: 253 students
* **Target**: `placement_ready` (1 = Ready, 0 = Not Ready)
* **Key Features**: `cgpa`, `technical_score`, `aptitude_score`, `communication_score`, `coding_score`, `projects`, `internships`, `certifications`, `backlogs`
* **Purpose**: Prototype training candidate matching the 9-feature ML schema.
* **Governance status**: Provenance and `placement_ready` label construction are unverified; do not describe the label as an observed placement outcome until confirmed.

---

### Dataset 2 — Large Engineering College Placement: `college_placement_engineering.csv`
* **Records**: 2,966 engineering students
* **Source**: Kaggle College Placement Dataset (Urvashi Ramdasani / Nirantk)
* **Target**: `PlacedOrNot` (1 = Placed, 0 = Not Placed)
* **Columns**: `Age`, `Gender`, `Stream` (CS, IT, ECE, Mech, Civil, Electrical), `Internships`, `CGPA`, `Hostel`, `HistoryOfBacklogs`, `PlacedOrNot`
* **Purpose**: External engineering-placement benchmark candidate.
* **Governance status**: Contains 1,829 exact duplicate rows in the current repository snapshot; source, license, and duplicate policy require verification before use.

---

### Dataset 3 — Kaggle Campus Recruitment: `campus_recruitment_kaggle.csv`
* **Records**: 215 students
* **Source**: Kaggle Campus Recruitment (Benison Sunil)
* **Target**: `status` (Placed / Not Placed) + `salary`
* **Columns**: `ssc_p`, `ssc_b`, `hsc_p`, `hsc_b`, `hsc_s`, `degree_p`, `degree_t`, `workex`, `etest_p`, `specialisation`, `mba_p`, `status`, `salary`
* **Purpose**: External academic-progression benchmark candidate.
* **Governance status**: Contains 67 missing `salary` values. Salary must not be used as a placement feature without a documented missing-value and leakage policy.

---

### Dataset 4 — Multi-Factor Job Placement: `job_placement_features.csv`
* **Records**: 215 students
* **Source**: Kaushiki Gupta / Job Placement ML Benchmark
* **Target**: `status` (Placed / Not Placed)
* **Columns**: `gender`, `ssc_percentage`, `ssc_board`, `hsc_percentage`, `hsc_board`, `hsc_subject`, `degree_percentage`, `undergrad_degree`, `work_experience`, `emp_test_percentage`, `specialisation`, `mba_percent`, `status`
* **Purpose**: Pre-cleaned, normalized categorical format benchmark for cross-model validation.

---

### Dataset 5 — Engineering Semesters & Skills: `engineering_skills_placement.csv`
* **Records**: 99 engineering students
* **Source**: Kunal Rathod / Engineering Placement Analysis
* **Target**: `placed` (yes / no)
* **Columns**: `name`, `thenthScore`, `twelthScore`, `firstSemScore`, `secondSemScore`, `thirdSemScore`, `fourthSemScore`, `fifthSemScore`, `attendance`, `numberOfCertifications`, `favouriteLanguage` (Java, Python, C++, etc.), `workingField` (Web Dev, ML, Software, etc.), `placed`
* **Purpose**: Real engineering college semester-wise trajectory, coding language preference, and domain specializations.
* **Viva Explanation**: *"Is dataset mein semester 1 se semester 5 tak ke individual semester scores, programming language preference (Python/Java/C++) aur certifications ka placement par impact diya gaya hai."*

---

### Dataset 6 — Salary Package Regression: `placement_package_salary.csv`
* **Records**: 200 students
* **Source**: CampusX ML Repositories
* **Target**: `package` (LPA salary offer)
* **Columns**: `cgpa`, `package`
* **Purpose**: Continuous salary prediction based on academic GPA, demonstrating regression modeling alongside classification.
* **Viva Explanation**: *"Ye dataset continuous salary package (LPA) ko predict karne ke liye regression benchmark provide karta hai."*

---

### Dataset 7 — Academic & Cognitive IQ: `placement_iq_academic.csv`
* **Records**: 100 students
* **Source**: CampusX Classification Benchmark
* **Target**: `placement` (1 = Placed, 0 = Not Placed)
* **Columns**: `cgpa`, `iq`, `placement`
* **Purpose**: Demonstrates decision boundary separation between academic GPA and cognitive intelligence quotient (IQ).

---

## Summary of Total Data Assets

| Metric | Value |
|---|---|
| **Total Datasets** | **7 CSV files** |
| **Total Records** | **4,048 student rows** |
| **Classification Datasets** | 6 datasets |
| **Regression Datasets** | 1 dataset (`placement_package_salary.csv`) |
| **Large-scale Engineering Dataset** | `college_placement_engineering.csv` (2,966 rows) |

---

## Talking Points for Viva / Teacher Presentation

1. **Why do we have 7 datasets in the folder?**
   > *"Sir/Ma'am, humne single dataset par rely nahi kiya. Hamara core model `students.csv` ke 9 granular skill parameters par train hota hai, lekin model ki validity aur generalizability prove karne ke liye humne 6 external datasets add kiye hain: 2,966 engineering student profiles wala Kaggle dataset, semester-wise coding skills dataset, academic progression benchmarks, aur salary package regression dataset."*

2. **Which dataset is used to train the live ML API?**
   > *"Live platform `students.csv` use karta hai kyunki usme technical score, coding score, projects, internships aur active backlogs jaise actionable parameters hain jinhe student improve kar sakta hai."*
