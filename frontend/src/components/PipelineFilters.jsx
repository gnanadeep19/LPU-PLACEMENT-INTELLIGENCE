import React from 'react';
import { EXAMPLE_COHORTS, EXAMPLE_ROLES, EXAMPLE_COMPANIES } from '../constants/pipelineOptions';

function FilterField({ label, allLabel, value, onChange, recorded, examples }) {
  const unique = [...new Set(recorded.filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const recordedKeys = new Set(unique.map((item) => item.toLocaleLowerCase()));
  const suggestions = examples.filter(([item]) => !recordedKeys.has(item.toLocaleLowerCase()));
  return <label className="pipeline-filter-field"><span>{label}</span>
    <select className="number-input-field" value={value} onChange={(event) => onChange(event.target.value)}>
      <option value={allLabel}>{allLabel}</option>
      {unique.length > 0 && <optgroup label="In placement records">{unique.map((item) => <option key={item} value={item}>{item}</option>)}</optgroup>}
      {suggestions.length > 0 && <optgroup label="Examples (may have no records)">{suggestions.map(([item, display]) => <option key={item} value={item}>{display}</option>)}</optgroup>}
    </select>
  </label>;
}

export default function PipelineFilters({ placements, cohort, setCohort, role, setRole, company, setCompany }) {
  return <>
    <div className="pipeline-filters" role="group" aria-label="Filter placement outcomes">
      <FilterField label="Cohort" allLabel="All cohorts" value={cohort} onChange={setCohort} recorded={placements.map((item) => item.cohort)} examples={EXAMPLE_COHORTS} />
      <FilterField label="Target role" allLabel="All roles" value={role} onChange={setRole} recorded={placements.map((item) => item.target_role)} examples={EXAMPLE_ROLES.map((item) => [item, item])} />
      <FilterField label="Company" allLabel="All companies" value={company} onChange={setCompany} recorded={placements.map((item) => item.company)} examples={EXAMPLE_COMPANIES.map((item) => [item, item])} />
    </div>
    <p className="probability-note">Example options help you explore filters; they do not imply placement records or employer partnerships.</p>
  </>;
}
