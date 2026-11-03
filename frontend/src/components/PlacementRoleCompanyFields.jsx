import React from 'react';
import { EXAMPLE_COMPANIES, EXAMPLE_ROLES } from '../constants/pipelineOptions';

function suggestions(recorded, examples) {
  const unique = new Map();
  [...recorded, ...examples].filter(Boolean).forEach((value) => {
    const trimmed = value.trim();
    if (trimmed && !unique.has(trimmed.toLocaleLowerCase())) unique.set(trimmed.toLocaleLowerCase(), trimmed);
  });
  return [...unique.values()];
}

export default function PlacementRoleCompanyFields({ form, setForm, placements }) {
  // CSE is a cohort/branch, not a job role; older records can still retain it.
  const roles = suggestions(placements.map((item) => item.target_role), EXAMPLE_ROLES)
    .filter((role) => role.toLocaleLowerCase() !== 'cse');
  const companies = suggestions(placements.map((item) => item.company), EXAMPLE_COMPANIES);
  return <>
    <label className="input-label">Target role
      <input className="number-input-field" list="placement-role-suggestions" maxLength={120} value={form.target_role}
        placeholder="Select or type a role" onChange={(event) => setForm({ ...form, target_role: event.target.value })} />
      <datalist id="placement-role-suggestions">{roles.map((role) => <option key={role} value={role} />)}</datalist>
    </label>
    <label className="input-label">Company (optional)
      <input className="number-input-field" list="placement-company-suggestions" maxLength={120} value={form.company}
        placeholder="Select or type a company" onChange={(event) => setForm({ ...form, company: event.target.value })} />
      <datalist id="placement-company-suggestions">{companies.map((company) => <option key={company} value={company} />)}</datalist>
    </label>
  </>;
}
