import React from 'react';
import universitySeal from '../assets/lpu-seal.jpg';

export function BrandLogo() {
  return <span className="brand-logo"><img src={universitySeal} alt="" aria-hidden="true" /></span>;
}

export function SectionIntro({ children, className = '' }) {
  return <p className={`section-intro ${className}`.trim()}>{children}</p>;
}

export function StatusBanner({ icon, children, tone = 'warning' }) {
  return (
    <div className={`status-banner status-banner-${tone}`} role="alert">
      {icon}
      <span>{children}</span>
    </div>
  );
}

export function MetricCard({ label, value, tone = 'success' }) {
  return (
    <article className={`metric-card metric-card-${tone}`}>
      <span className="metric-card-label">{label}</span>
      <strong className="metric-card-value">{value}</strong>
    </article>
  );
}
