import React from 'react';

const FIELDS = ['cgpa', 'technical_score', 'aptitude_score', 'communication_score', 'coding_score', 'projects', 'internships', 'certifications', 'backlogs'];

function Breakdown({ title, groups, minimum }) {
  const entries = [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
  // Suppress the whole dimension if one group is small; hiding only one row can
  // expose it by subtracting the other rows from a displayed total.
  if (!entries.length) return <p className="probability-note">No assessed profiles are available for {title.toLowerCase()}.</p>;
  if (entries.some(([, rows]) => rows.length < minimum)) return <p className="probability-note">{title} is hidden because at least one group has fewer than {minimum} assessed profiles.</p>;
  return <div className="table-container"><table className="students-table"><caption>{title}</caption><thead><tr><th scope="col">Group</th><th scope="col">Assessed profiles</th><th scope="col">Average readiness</th><th scope="col">Complete profiles</th></tr></thead><tbody>{entries.map(([name, rows]) => {
    const complete = rows.filter((row) => FIELDS.every((field) => row.profile?.[field] != null)).length;
    const average = rows.reduce((sum, row) => sum + row.readiness_score, 0) / rows.length;
    return <tr key={name}><th scope="row">{name}</th><td>{rows.length}</td><td>{average.toFixed(1)}/100</td><td>{complete}/{rows.length}</td></tr>;
  })}</tbody></table></div>;
}

export default function CohortBreakdown({ students, loading, loaded, minimum }) {
  const assessed = students.filter((student) => typeof student.readiness_score === 'number');
  const cohorts = new Map(); const roles = new Map();
  const add = (map, key, student) => map.set(key, [...(map.get(key) || []), student]);
  assessed.forEach((student) => {
    add(cohorts, student.cohort || 'Cohort not recorded', student);
    const selected = student.target_roles?.length ? [...new Set(student.target_roles)] : student.target_role && student.target_role !== 'Not selected' ? [student.target_role] : ['Role not selected'];
    selected.forEach((role) => add(roles, role, student));
  });
  if (loading && !loaded) return <p role="status">Loading comparisons…</p>;
  if (!loaded) return <p role="alert">Comparisons could not be loaded. Refresh the dashboard to retry.</p>;
  return <><p className="probability-note">Denominator: assessed profiles only. Complete means all nine model fields are present; role counts can overlap when a student selects multiple roles.</p><Breakdown title="By cohort" groups={cohorts} minimum={minimum} /><Breakdown title="By target role" groups={roles} minimum={minimum} /><p className="probability-note">Comparisons are hidden when any group is below {minimum}; these are descriptive indicators, not placement outcomes.</p></>;
}
