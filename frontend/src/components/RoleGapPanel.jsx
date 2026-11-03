import React from 'react';
import { Target } from 'lucide-react';

// Deliberately labelled project-defined starter targets until LPU placement-cell
// requirements or employer-specific criteria are supplied and validated.
const ROLE_PROFILES = {
  'Software Developer': { cgpa:7, technical_score:70, aptitude_score:60, communication_score:60, coding_score:70, projects:2, internships:0, certifications:0, backlogs:0 },
  'Data Analyst': { cgpa:7, technical_score:65, aptitude_score:70, communication_score:65, coding_score:55, projects:2, internships:0, certifications:1, backlogs:0 },
  'Business Analyst': { cgpa:7, technical_score:55, aptitude_score:68, communication_score:72, coding_score:40, projects:1, internships:0, certifications:0, backlogs:0 },
  'UX Designer': { cgpa:6.5, technical_score:45, aptitude_score:55, communication_score:75, coding_score:35, projects:2, internships:0, certifications:0, backlogs:0 },
  'Sales / Marketing Associate': { cgpa:6.5, technical_score:40, aptitude_score:58, communication_score:75, coding_score:25, projects:1, internships:0, certifications:0, backlogs:0 },
};
const LABELS = { cgpa:'Academic CGPA',technical_score:'Core technical',aptitude_score:'Aptitude',communication_score:'Communication',coding_score:'Coding practice',projects:'Projects',internships:'Internships',certifications:'Certifications',backlogs:'Active backlogs' };
const fmt = (key,value) => key === 'cgpa' ? `${Number(value).toFixed(1)}/10` : ['projects','internships','certifications','backlogs'].includes(key) ? `${value}` : `${value}%`;

export const TARGET_ROLES = Object.keys(ROLE_PROFILES);

export default function RoleGapPanel({ formData, targetRoles = [TARGET_ROLES[0]], onRolesChange }) {
  const selectedRoles = targetRoles.length ? targetRoles : [TARGET_ROLES[0]];
  const targetRole = selectedRoles[0];
  const target = ROLE_PROFILES[targetRole] || ROLE_PROFILES[TARGET_ROLES[0]];
  const rows = Object.keys(target).map((key) => {
    const current = Number(formData[key] ?? 0);
    const expected = target[key];
    const meets = key === 'backlogs' ? current <= expected : current >= expected;
    const action = key === 'coding_score' ? 'Complete timed role-level practice, then reassess.'
      : key === 'technical_score' ? 'Choose a focused technical topic and demonstrate it in a project.'
        : key === 'aptitude_score' ? 'Complete two timed aptitude sets and review missed questions.'
          : key === 'communication_score' ? 'Practise a mock interview and ask for structured feedback.'
            : key === 'cgpa' ? 'Review academic support options and keep core subject records current.'
              : key === 'projects' ? 'Build a small portfolio project that demonstrates role-relevant work.'
                : key === 'internships' ? 'Explore internships or supervised practical experience.'
                  : key === 'certifications' ? 'Consider one relevant certification and verify its source.'
                    : 'Discuss an academic completion plan with your advisor.';
    return { key, current, expected, meets, action };
  });
  const gaps = rows.filter((row) => !row.meets);
  const roleSummaries = selectedRoles.map((role) => {
    const requirements = ROLE_PROFILES[role];
    const gapsForRole = Object.keys(requirements).filter((key) => key === 'backlogs'
      ? Number(formData[key] ?? 0) > requirements[key]
      : Number(formData[key] ?? 0) < requirements[key]);
    return { role, gaps: gapsForRole };
  });
  return (
    <section className="glass-card role-gap-panel" aria-labelledby="role-gap-heading">
      <div className="card-header"><div><h2 id="role-gap-heading"><Target size={18} aria-hidden="true" /> Target-role gap analysis</h2><p>Compare your current profile with a selectable role profile.</p></div>
        <fieldset className="role-choice-group"><legend>Target roles</legend><div className="role-choice-list">{TARGET_ROLES.map((role)=><label className="role-choice" key={role}><input type="checkbox" checked={selectedRoles.includes(role)} onChange={(event)=>{const values=event.target.checked?[...selectedRoles,role]:selectedRoles.filter((item)=>item!==role);if(values.length)onRolesChange(values);}} /><span>{role}</span></label>)}</div><small>Select one or more roles. The first selected role drives the detailed gap table.</small></fieldset>
      </div>
      <div className="card-body"><p className="probability-note">These are provisional project-defined starter requirements, not employer guarantees or official LPU placement criteria. They do not alter the model prediction.</p>
        {gaps.length ? <div className="table-container"><table className="students-table"><thead><tr><th>Skill area</th><th>Current evidence</th><th>Starter target</th><th>Suggested next action</th></tr></thead><tbody>{gaps.map(({key,current,expected,action})=><tr key={key}><td>{LABELS[key]}</td><td>{fmt(key,current)}</td><td>{key==='cgpa' ? `${expected}/10` : ['projects','internships','certifications','backlogs'].includes(key) ? `${expected} required` : `${expected}%`}</td><td>{action}</td></tr>)}</tbody></table></div> : <p className="probability-note">Your submitted profile meets these provisional starter targets. Keep evidence current and validate fit with a mentor.</p>}
        {selectedRoles.length > 1 && <div className="table-container"><table className="students-table"><thead><tr><th>Selected role</th><th>Profile gaps to discuss</th></tr></thead><tbody>{roleSummaries.map((item)=><tr key={item.role}><td>{item.role}</td><td>{item.gaps.length ? item.gaps.map((key)=>LABELS[key]).join(', ') : 'No gaps against this starter profile'}</td></tr>)}</tbody></table></div>}
        <details className="rec-card"><summary className="rec-summary"><strong>View all role requirements</strong><span className="rec-toggle">Show table</span></summary><div className="table-container"><table className="students-table"><thead><tr><th>Area</th><th>Current</th><th>Target</th><th>Status</th></tr></thead><tbody>{rows.map(({key,current,expected,meets})=><tr key={key}><td>{LABELS[key]}</td><td>{fmt(key,current)}</td><td>{fmt(key,expected)}</td><td>{meets?'Target met':'Gap to address'}</td></tr>)}</tbody></table></div></details>
      </div>
    </section>
  );
}
