import React, { memo, useEffect, useRef } from 'react';
import {
  AlertTriangle,
  Award,
  Brain,
  Briefcase,
  Code2,
  Cpu,
  FolderGit2,
  GraduationCap,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { PRESETS } from '../constants/assessment';

const FIELDS = {
  cgpa: { id: 'cgpa', label: 'Academic CGPA', min: 5, max: 10, step: 0.1, unit: ' / 10.0' },
  coding_score: {
    id: 'coding-score',
    label: 'Coding Practice (DSA)',
    min: 0,
    max: 100,
    step: 1,
    unit: '%',
  },
  technical_score: {
    id: 'technical-score',
    label: 'Core CS Technical Score',
    min: 0,
    max: 100,
    step: 1,
    unit: '%',
  },
  aptitude_score: {
    id: 'aptitude-score',
    label: 'Aptitude & Logical Reasoning',
    min: 0,
    max: 100,
    step: 1,
    unit: '%',
  },
  communication_score: {
    id: 'communication-score',
    label: 'Communication & HR Fit',
    min: 0,
    max: 100,
    step: 1,
    unit: '%',
  },
};

function SliderField({ field, icon, value, onChange }) {
  const config = FIELDS[field];
  const displayValue = field === 'cgpa' ? Number(value).toFixed(1) : value;
  const progress = Math.min(100, Math.max(0, ((Number(value) - config.min) / (config.max - config.min)) * 100));
  return (
    <div className="input-group">
      <div className="input-label-row">
        <label className="input-label" htmlFor={config.id}>
          {icon} {config.label}
        </label>
        <span className="input-value-badge">
          {displayValue}
          {config.unit}
        </span>
      </div>
      <input
        id={config.id}
        type="range"
        min={config.min}
        max={config.max}
        step={config.step}
        value={value}
        aria-valuetext={`${displayValue}${config.unit}`}
        style={{ '--slider-progress': `${progress}%` }}
        onChange={(event) => onChange(field, event.target.value)}
      />
      <div className="slider-limits" aria-hidden="true"><span>{config.min}{field === 'cgpa' ? '.0' : '%'}</span><span>{config.max}{field === 'cgpa' ? '.0' : '%'}</span></div>
    </div>
  );
}

function NumberField({ field, label, icon, max, value, onChange, danger }) {
  return (
    <div className="input-group">
      <label
        className="input-label"
        htmlFor={field}
        style={danger ? { color: 'var(--color-danger)' } : undefined}
      >
        {icon} {label}
      </label>
      <input
        id={field}
        type="number"
        inputMode="numeric"
        min="0"
        max={max}
        className="number-input-field"
        style={danger ? { borderColor: 'var(--color-danger)' } : undefined}
        value={value}
        onChange={(event) => onChange(field, event.target.value)}
      />
    </div>
  );
}

function StudentFormComponent({
  formData,
  isDirty,
  loading,
  validation,
  onFieldChange,
  onSubmit,
  onReset,
  onPreset,
}) {
  const formRef = useRef(null);

  useEffect(() => {
    if (!validation?.field) return;
    const target = formRef.current?.querySelector(`#${CSS.escape(validation.field)}`);
    if (target) target.focus();
  }, [validation]);

  return (
    <section className="glass-card form-container" aria-labelledby="assessment-form-heading">
      <div className="card-header">
        <div>
          <h2 id="assessment-form-heading">
            <GraduationCap size={20} color="var(--accent-primary)" aria-hidden="true" />
            Student Competency Matrix
          </h2>
          <p>Adjust parameters or use presets</p>
        </div>
        <button
          type="button"
          className="btn-reset"
          onClick={onReset}
          disabled={!isDirty || loading}
          aria-label="Reset assessment form"
        >
          <RotateCcw size={14} aria-hidden="true" />
          Reset
        </button>
      </div>

      <form className="card-body" onSubmit={onSubmit} ref={formRef} noValidate>
        {validation?.message && (
          <div className="form-validation-message" role="alert" id="form-validation-message">
            <AlertTriangle size={16} aria-hidden="true" />
            {validation.message}
          </div>
        )}

        <div className="competency-section">
          <div className="form-section-title">
            <TrendingUp size={14} aria-hidden="true" /> Academics & Coding
          </div>
          <SliderField field="cgpa" icon={null} value={formData.cgpa} onChange={onFieldChange} />
          <SliderField
            field="coding_score"
            icon={<Code2 size={14} aria-hidden="true" />}
            value={formData.coding_score}
            onChange={onFieldChange}
          />
          <SliderField
            field="technical_score"
            icon={<Cpu size={14} aria-hidden="true" />}
            value={formData.technical_score}
            onChange={onFieldChange}
          />
        </div>

        <div className="competency-section">
          <div className="form-section-title">
            <Brain size={14} aria-hidden="true" /> Aptitude & Communication
          </div>
          <SliderField
            field="aptitude_score"
            icon={null}
            value={formData.aptitude_score}
            onChange={onFieldChange}
          />
          <SliderField
            field="communication_score"
            icon={<MessageSquare size={14} aria-hidden="true" />}
            value={formData.communication_score}
            onChange={onFieldChange}
          />
        </div>

        <div className="competency-section">
          <div className="form-section-title">
            <Briefcase size={14} aria-hidden="true" /> Practical Profile & Backlogs
          </div>
          <div className="inputs-subgrid">
            <NumberField
              field="projects"
              label="Projects"
              icon={<FolderGit2 size={14} aria-hidden="true" />}
              max={15}
              value={formData.projects}
              onChange={onFieldChange}
            />
            <NumberField
              field="internships"
              label="Internships"
              icon={<Briefcase size={14} aria-hidden="true" />}
              max={10}
              value={formData.internships}
              onChange={onFieldChange}
            />
            <NumberField
              field="certifications"
              label="Certifications"
              icon={<Award size={14} aria-hidden="true" />}
              max={15}
              value={formData.certifications}
              onChange={onFieldChange}
            />
            <NumberField
              field="backlogs"
              label="Active Backlogs"
              icon={<AlertTriangle size={14} aria-hidden="true" />}
              max={10}
              value={formData.backlogs}
              onChange={onFieldChange}
              danger={Number(formData.backlogs) > 0}
            />
          </div>
        </div>

        <button type="submit" className="btn-submit" disabled={loading} aria-busy={loading}>
          {loading ? (
            <>
              <RefreshCw className="spin-animate" size={18} aria-hidden="true" />
              Calculating Placement Readiness...
            </>
          ) : (
            <>
              <Sparkles size={18} aria-hidden="true" />
              Analyze Placement Readiness
            </>
          )}
        </button>

        <div className="preset-section">
          <span className="presets-title">
            <Sparkles size={14} aria-hidden="true" /> Quick test profiles
          </span>
          <div className="preset-buttons">
            {Object.entries(PRESETS).map(([key, item]) => (
              <button
                key={key}
                type="button"
                className="btn-preset"
                onClick={() => onPreset(key)}
                aria-label={`Load ${item.label} profile`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </form>
    </section>
  );
}

export default memo(StudentFormComponent);
