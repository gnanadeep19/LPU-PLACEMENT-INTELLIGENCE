import React, { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react';

const GUIDES = {
  student: {
    title: 'Your readiness workspace',
    description: 'Use your profile as a coaching tool. Your estimate is advisory, not a placement guarantee.',
    steps: ['Review your readiness estimate and the evidence behind it.', 'Choose a target role and compare your skills with its project-defined profile.', 'Turn the most important gap into a short action with a due date.', 'Submit project, assessment, or certificate evidence for review.', 'Check your progress history after updating your profile.'],
  },
  mentor: {
    title: 'Mentor workflow',
    description: 'Start with the support queue, then record a clear next step for each student you meet.',
    steps: ['Review the reason and freshness for each support signal.', 'Open an assigned mentee to inspect evidence, gaps, and goals.', 'Record the check-in and next follow-up date.', 'Assign a manageable student-visible action or add a clearly labeled private note.', 'Use cohort patterns to plan group support.'],
  },
  admin: {
    title: 'Placement operations workflow',
    description: 'Use aggregate views for program decisions. Keep placement outcomes separate from readiness estimates.',
    steps: ['Review profile coverage alongside readiness summaries.', 'Use pipeline stages to inspect actual placement activity.', 'Assign data-quality issues for correction before comparing cohorts.', 'Review mentor follow-ups and student support coverage.', 'Check model version, evaluation scope, and limitations before sharing results.'],
  },
};

export default function WorkspaceGuide({ role }) {
  const guideKey = role === 'mentor' ? 'mentor' : role === 'admin' || role === 'placement_officer' ? 'admin' : 'student';
  const guide = GUIDES[guideKey];
  const [open, setOpen] = useState(false);
  return (
    <section className={`workspace-guide ${open ? 'is-open' : ''}`} aria-labelledby="workspace-guide-title">
      <div className="workspace-guide-heading">
        <div className="workspace-guide-icon"><BookOpen size={18} aria-hidden="true" /></div>
        <div><h2 id="workspace-guide-title">{guide.title}</h2><p>{guide.description}</p></div>
        <button type="button" className="guide-toggle" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
          {open ? 'Hide guide' : 'Show guide'} {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>
      {open ? <ol className="workspace-guide-steps">{guide.steps.map((step) => <li key={step}>{step}</li>)}</ol> : null}
    </section>
  );
}
