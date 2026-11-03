# LPU Placement Intelligence Platform
## Complete Dataset Repository & Teacher Viva Reference Guide

---

## Datasets in This Project (7 Files · 4,048 Total Student Records)

The project utilizes a comprehensive **multi-dataset repository strategy** — combining a primary competency-based dataset with 6 diverse open benchmark datasets covering 4,048 student records.

| # | Dataset File | Records | Features | Target Variable | Primary Domain |
|---|---|---|---|---|---|
| **1** | [`dataset/students.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/students.csv) | 253 | 10 | `placement_ready` (0 or 1) | LPU Competency Model (Coding, Technical, Backlogs) |
| **2** | [`dataset/college_placement_engineering.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/college_placement_engineering.csv) | 2,966 | 8 | `PlacedOrNot` (0 or 1) | Engineering Branches (CS, IT, Mech, Civil, ECE) |
| **3** | [`dataset/campus_recruitment_kaggle.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/campus_recruitment_kaggle.csv) | 215 | 15 | `status` (Placed/Not) + `salary` | Academic History (10th, 12th, Degree, MBA) |
| **4** | [`dataset/job_placement_features.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/job_placement_features.csv) | 215 | 13 | `status` (Placed/Not) | Standardized Multi-factor Job Placement |
| **5** | [`dataset/engineering_skills_placement.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/engineering_skills_placement.csv) | 99 | 13 | `placed` (yes / no) | Engineering Semesters + Coding Language + Field |
| **6** | [`dataset/placement_package_salary.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/placement_package_salary.csv) | 200 | 2 | `package` (LPA salary) | Academic CGPA vs Placement Salary Regression |
| **7** | [`dataset/placement_iq_academic.csv`](file:///c:/Users/Dell/Desktop/supervised/dataset/placement_iq_academic.csv) | 100 | 3 | `placement` (0 or 1) | Cognitive IQ & Academic CGPA Classification |

**Total Available Records**: **4,048 student profiles** across 7 dataset files  
**Model Trained On**: `students.csv` (all other files serve as external validation benchmarks and analytical extensions)  
**When shown to teacher**: Open any CSV in Excel — each row = one student, last column = outcome label / target

---

## Detailed Breakdown of Each Dataset

### 1. Primary Curated Dataset (`dataset/students.csv`)
* **Rows**: 253 students
* **Target**: `placement_ready` (1 = Ready, 0 = Not Ready)
* **Features**:
  * `cgpa`: Cumulative GPA (5.10 – 9.00)
  * `technical_score`: Core CS fundamentals exam (37 – 95%)
  * `aptitude_score`: Quantitative & logical reasoning (34 – 92%)
  * `communication_score`: Verbal & HR articulation (36 – 94%)
  * `coding_score`: DSA / programming proficiency (39 – 97%)
  * `projects`: Hands-on development projects (0 – 5)
  * `internships`: Industry internship experience (0 – 3)
  * `certifications`: Technical industry certifications (0 – 5)
  * `backlogs`: Active backlogs (0 – 3)
* **Purpose**: Primary training dataset matching our live 9-feature REST API schema.
* **Trained Model Metrics**: Accuracy **94.12%**, ROC-AUC **0.9908**, F1-Score **94.12%**.

---

### 2. Large Engineering College Dataset (`dataset/college_placement_engineering.csv`)
* **Rows**: 2,966 engineering students
* **Source**: Kaggle College Placement Dataset (Urvashi Ramdasani / Nirantk)
* **Target**: `PlacedOrNot` (1 = Placed, 0 = Not Placed)
* **Features**:
  * `Age`: Student age (19 – 30)
  * `Gender`: Male / Female
  * `Stream`: Engineering Discipline (Computer Science, Information Technology, Electronics And Communication, Mechanical, Civil, Electrical)
  * `Internships`: Internships completed (0 – 3)
  * `CGPA`: Engineering CGPA (5 – 9)
  * `Hostel`: Hostel resident (1) or Day scholar (0)
  * `HistoryOfBacklogs`: Prior academic backlogs history (0 or 1)
  * `PlacedOrNot`: Final placement outcome
* **Why it matters**: Demonstrates how branch specialization, internships, and backlog history affect actual placement across thousands of engineering students.

---

### 3. Kaggle Campus Recruitment (`dataset/campus_recruitment_kaggle.csv`)
* **Rows**: 215 students
* **Source**: Kaggle Campus Recruitment Dataset (Benison Sunil)
* **Target**: `status` (Placed or Not Placed) & `salary` (in INR)
* **Features**:
  * `ssc_p` / `ssc_b`: 10th Standard % & Board
  * `hsc_p` / `hsc_b` / `hsc_s`: 12th Standard %, Board & Stream
  * `degree_p` / `degree_t`: Undergraduate Degree % & Stream (Sci&Tech, Comm&Mgmt, Others)
  * `workex`: Prior work experience (Yes / No)
  * `etest_p`: Employability / Aptitude test %
  * `mba_p` / `specialisation`: Post-grad % & MBA Specialization (Mkt&HR, Mkt&Fin)
* **Benchmark Performance**: Accuracy **86.05%**, ROC-AUC **0.9282** (trained via `backend/train_kaggle.py`).

---

### 4. Standardized Multi-Factor Job Placement (`dataset/job_placement_features.csv`)
* **Rows**: 215 students
* **Features**: Standardized, clean categorical dataset tracking 10th, 12th, degree, work experience, and aptitude scores.
* **Target**: `status` (Placed / Not Placed)

---

### 5. Engineering Semesters & Skills Dataset (`dataset/engineering_skills_placement.csv`)
* **Rows**: 99 engineering students
* **Source**: Kunal Rathod / Engineering Placement Analysis
* **Target**: `placed` (yes / no)
* **Features**:
  * `name`: Student identification
  * `thenthScore`: 10th CGPA
  * `twelthScore`: 12th CGPA
  * `firstSemScore` to `fifthSemScore`: Semester-by-semester engineering GPAs
  * `attendance`: Student attendance score (0 – 10)
  * `numberOfCertifications`: Domain certifications count
  * `favouriteLanguage`: Preferred programming language (`python`, `java`, `swift`, `kotlin`, `nodejs`, `angularjs`, `sql`, `php`)
  * `workingField`: Technical field (`Web Development`, `Machine Learning`, `Android`, `IOS`)
* **Why it matters**: Proves progression across 5 college semesters alongside student programming language preferences and domain specializations.

---

### 6. Salary Package Regression Dataset (`dataset/placement_package_salary.csv`)
* **Rows**: 200 students
* **Target**: `package` (Offered salary package in LPA)
* **Features**: `cgpa`, `package`
* **Purpose**: Serves as a regression benchmark to demonstrate continuous salary estimation ($R^2 \approx 0.78$) alongside binary classification.

---

### 7. Cognitive IQ & Academic Placement (`dataset/placement_iq_academic.csv`)
* **Rows**: 100 students
* **Target**: `placement` (1 = Placed, 0 = Not Placed)
* **Features**: `cgpa`, `iq`, `placement`
* **Purpose**: Educational benchmark illustrating linear vs non-linear decision boundary separation between intellectual aptitude (IQ) and academic diligence (CGPA).

---

## How to Inspect All Datasets at Once

You can inspect all 7 datasets and their shapes, columns, and sample rows using the automated inspection script:

```powershell
backend\.venv\Scripts\python.exe dataset\inspect_datasets.py
```

Or view specific files in Python:

```powershell
backend\.venv\Scripts\python.exe -c "import pandas as pd; df = pd.read_csv('dataset/engineering_skills_placement.csv'); print(df.head(5))"
```

---

## Talking Points for Teacher / Viva Defense

1. **"Why do you have 7 datasets in your project?"**
   > *"Sir/Ma'am, we wanted to ensure comprehensive evaluation across multiple educational dimensions. Our primary live model trains on `students.csv` because it tracks 9 actionable engineering competency parameters (DSA, Coding, Projects, Backlogs). To validate our model externally, we incorporated 6 benchmark datasets: a 2,966-student engineering college dataset from Kaggle, a 5-semester trajectory dataset with programming language preferences, academic progression datasets, and a salary package regression dataset. Together, our repository contains 4,048 student records."*

2. **"What is the difference between students.csv and college_placement_engineering.csv?"**
   > *"`college_placement_engineering.csv` captures macro factors like engineering branch stream (CS, IT, Mech), hostel residency, and backlog history across 2,966 students. `students.csv` captures micro technical competencies (coding score, technical score, projects count, certifications) needed to provide personalized improvement roadmaps for students."*

3. **"Does the engineering_skills_placement.csv dataset prove coding skills matter?"**
   > *"Yes, it tracks students across their first 5 semesters of engineering, their programming language preference (Python, Java, Kotlin, Swift, Node.js), certifications count, and technical field (Web, ML, Android, iOS), directly showing how practical technical specialization correlates with placement."*
