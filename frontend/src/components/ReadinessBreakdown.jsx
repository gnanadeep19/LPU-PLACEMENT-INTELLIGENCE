import React from 'react';
import { SectionIntro } from './ui';

const AREAS = [
  { name:'Academics', fields:['cgpa','backlogs'] },
  { name:'Technical skills', fields:['technical_score','coding_score'] },
  { name:'Aptitude', fields:['aptitude_score'] },
  { name:'Communication', fields:['communication_score'] },
  { name:'Projects', fields:['projects'] },
  { name:'Experience', fields:['internships'] },
  { name:'Certifications', fields:['certifications'] },
];
const LABELS = { cgpa:'CGPA',backlogs:'active backlogs',technical_score:'technical',coding_score:'coding',aptitude_score:'aptitude',communication_score:'communication',projects:'projects',internships:'internships',certifications:'certifications' };
const format = (key,value) => value == null ? 'Not entered' : key==='cgpa' ? `${Number(value).toFixed(1)} / 10` : ['projects','internships','certifications','backlogs'].includes(key) ? `${value} ${LABELS[key]}` : `${value}%`;

export default function ReadinessBreakdown({ profile, prediction }) {
  const contributions = new Map((prediction?.local_explanations || []).map((item)=>[item.feature,item.contribution_points]));
  return (
    <section className="glass-card" aria-labelledby="readiness-breakdown-title">
      <div className="card-header"><div><h2 id="readiness-breakdown-title">Readiness breakdown</h2><SectionIntro>Review your current inputs and, where available, the model’s one-input sensitivity comparison.</SectionIntro></div></div>
      <div className="card-body"><div className="table-container"><table className="students-table"><thead><tr><th>Area</th><th>Current profile evidence</th><th>Largest input sensitivity</th></tr></thead><tbody>{AREAS.map((area)=>{const values=area.fields.map((key)=>`${LABELS[key]}: ${format(key,profile?.[key])}`);const impacts=area.fields.map((key)=>({key,value:contributions.get(key)})).filter((item)=>typeof item.value==='number').sort((a,b)=>Math.abs(b.value)-Math.abs(a.value));const impact=impacts[0];return <tr key={area.name}><th scope="row">{area.name}</th><td>{values.join(' · ')}</td><td>{impact ? `${LABELS[impact.key]}: ${impact.value>0?'+':''}${impact.value.toFixed(1)} probability points vs reference` : 'Not available'}</td></tr>;})}</tbody></table></div><p className="probability-note">Each sensitivity compares one input with a model reference value. These comparisons are directional associations, not causal effects, standalone area scores, or values that can be added together. Missing evidence is not treated as proof of low ability.</p></div>
    </section>
  );
}
