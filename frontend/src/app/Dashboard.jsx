import React, { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BarChart3,
  Info,
  ListTodo,
  LogOut,
  Printer,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { DEFAULT_FORM_DATA, DIAGNOSTIC_TABS, PRESETS, isFormDirty } from '../constants/assessment';
import { useApiHealth } from '../hooks/useApiHealth';
import { useAssessment } from '../hooks/useAssessment';
import { useCohortAnalytics } from '../hooks/useCohortAnalytics';
import { ROLE_LABELS, STAFF_ROLES } from '../hooks/useAuth';
import { normalizeForm, validateForm } from '../utils/validation';
import { sortSkillGaps } from '../utils/format';
import { getMyStudentProfile, saveMyTargetRoles } from '../services/assessmentService';
import StudentForm from '../components/StudentForm';
import ReadinessCard, { ReadinessSkeleton } from '../components/ReadinessCard';
import SkillGapPanel from '../components/SkillGapPanel';
import RoadmapPanel from '../components/RoadmapPanel';
import ProgressPanel from '../components/ProgressPanel';
import StudyResources from '../components/StudyResources';
import CvReview from '../components/CvReview';
import RoleGapPanel, { TARGET_ROLES } from '../components/RoleGapPanel';
import ReadinessBreakdown from '../components/ReadinessBreakdown';
import StudentEvidencePanel from '../components/StudentEvidencePanel';
import StudentNextSteps from '../components/StudentNextSteps';
import PreparationPlanner from '../components/PreparationPlanner';
import WorkspaceGuide from '../components/WorkspaceGuide';
import ChunkFallback from '../components/ChunkFallback';
import FeedbackWidget from '../components/FeedbackWidget';
import { BrandLogo, SectionIntro, StatusBanner } from '../components/ui';
import { recordEvent, setTelemetryRoute, startWebVitals } from '../telemetry/telemetry';
import NotificationsMenu from '../components/NotificationsMenu';
import { usesSupabaseAuth } from '../services/supabaseClient';

// Secondary views and the charting dependency stay out of the initial bundle.
const InfluentialFactorsPanel = lazy(() => import('../components/InfluentialFactorsPanel'));
const MentorOverview = lazy(() => import('../components/MentorOverview'));
const AdminDashboard = lazy(() => import('../components/AdminDashboard'));

const PILOT_FEEDBACK_ENABLED = import.meta.env?.VITE_PILOT_FEEDBACK === 'on';

const TAB_CONFIG = [
  { id: 'gaps', label: 'Skill Gap Matrix', icon: ListTodo },
  { id: 'roadmap', label: 'Action Roadmap', icon: Sparkles },
  { id: 'factors', label: 'Influential Factors', icon: BarChart3 },
  { id: 'progress', label: 'Progress History', icon: TrendingUp },
];

export default function Dashboard({ user, onLogout }) {
  const isStaff = STAFF_ROLES.includes(user.role);
  const canUseAdminWorkspace = user.role === 'admin' || user.role === 'placement_officer';
  const [formData, setFormData] = useState(DEFAULT_FORM_DATA);
  const [activeTab, setActiveTab] = useState('gaps');
  const [studentSection, setStudentSection] = useState('overview');
  const [workspace, setWorkspace] = useState(() => user.role === 'mentor' ? 'mentor' : canUseAdminWorkspace ? 'admin' : 'student');
  const [validation, setValidation] = useState(null);
  const [showPriorityGapsOnly, setShowPriorityGapsOnly] = useState(false);
  const [targetRoles, setTargetRoles] = useState(() => {
    try { const saved = JSON.parse(window.localStorage.getItem(`lpu-target-roles-${user.id}`) || 'null'); return Array.isArray(saved) && saved.length && saved.every((role)=>TARGET_ROLES.includes(role)) ? saved : [TARGET_ROLES[0]]; }
    catch { return [TARGET_ROLES[0]]; }
  });
  const [profileLoaded, setProfileLoaded] = useState(false);
  const [profileNotice, setProfileNotice] = useState('');
  const [signOutError, setSignOutError] = useState('');
  const [online, setOnline] = useState(
    typeof navigator === 'undefined' ? true : navigator.onLine !== false,
  );

  const { apiOnline, checking: healthChecking, check: checkHealth } = useApiHealth();
  const { prediction, history, loading, error, historyError, lastUpdated, analyze, retry } =
    useAssessment();
  const cohortScope = `${user.role}:${user.cohort || 'institution'}`;
  const {
    cohort,
    loading: cohortLoading,
    error: cohortError,
    load: loadCohort,
  } = useCohortAnalytics(cohortScope);

  const isDirty = isFormDirty(formData);

  useEffect(() => {
    if (!profileLoaded || user.role !== 'student') return;
    try { window.localStorage.setItem(`lpu-target-roles-${user.id}`, JSON.stringify(targetRoles)); } catch { /* Preference storage is optional. */ }
    saveMyTargetRoles(targetRoles).catch((err) => setProfileNotice(err?.message || 'Target roles could not be saved to your account.'));
  }, [profileLoaded, targetRoles, user.id, user.role]);

  useEffect(() => {
    setTelemetryRoute(window.location.pathname);
    recordEvent('app_boot');
    return startWebVitals();
  }, []);

  useEffect(() => {
    const goOnline = () => {
      setOnline(true);
      checkHealth();
    };
    const goOffline = () => setOnline(false);
    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, [checkHealth]);

  // Restore this student's latest saved profile and target role before analysis.
  useEffect(() => {
    if (user.role !== 'student') { setProfileLoaded(true); return undefined; }
    let active = true;
    getMyStudentProfile().then((saved) => {
      if (!active) return;
      if (Array.isArray(saved?.target_roles) && saved.target_roles.length && saved.target_roles.every((role)=>TARGET_ROLES.includes(role))) setTargetRoles(saved.target_roles);
      else if (TARGET_ROLES.includes(saved?.target_role)) setTargetRoles([saved.target_role]);
      const initialProfile = saved?.profile ? normalizeForm(saved.profile) : DEFAULT_FORM_DATA;
      const checked = validateForm(initialProfile);
      const profile = checked.valid ? initialProfile : DEFAULT_FORM_DATA;
      setFormData(profile);
      analyze(profile);
      setProfileLoaded(true);
    }).catch(() => {
      if (!active) return;
      analyze(DEFAULT_FORM_DATA);
      setProfileLoaded(true);
    });
    return () => { active = false; };
  }, [analyze, user.role]);

  useEffect(() => {
    if ((workspace === 'mentor' || workspace === 'admin') && isStaff) {
      loadCohort();
    }
    if ((workspace === 'mentor' && user.role !== 'mentor') || (workspace === 'admin' && !canUseAdminWorkspace)) {
      setWorkspace('student');
    }
  }, [workspace, isStaff, canUseAdminWorkspace, user.role, loadCohort]);

  const handleFieldChange = useCallback((field, rawValue) => {
    setFormData((previous) => ({ ...previous, [field]: rawValue }));
    setValidation(null);
  }, []);

  const handlePreset = useCallback((presetKey) => {
    const preset = PRESETS[presetKey];
    if (!preset) return;
    // Copy so later edits never mutate the shared preset definition.
    setFormData({ ...preset.data });
    setValidation(null);
  }, []);

  const handleReset = useCallback(() => {
    setFormData(DEFAULT_FORM_DATA);
    setValidation(null);
  }, []);

  const handleSubmit = useCallback(
    (event) => {
      event?.preventDefault();
      const normalized = normalizeForm(formData);
      const result = validateForm(normalized);
      if (!result.valid) {
        setValidation(result);
        return;
      }
      setValidation(null);
      analyze(normalized);
    },
    [analyze, formData],
  );

  const handleRetry = useCallback(() => {
    retry();
  }, [retry]);

  const handleTabKeyDown = useCallback((event, currentTab) => {
    const currentIndex = DIAGNOSTIC_TABS.indexOf(currentTab);
    if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      return;
    }
    event.preventDefault();
    const offset = event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? -1 : 1;
    const nextIndex =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? DIAGNOSTIC_TABS.length - 1
          : (currentIndex + offset + DIAGNOSTIC_TABS.length) % DIAGNOSTIC_TABS.length;
    const nextTab = DIAGNOSTIC_TABS[nextIndex];
    setActiveTab(nextTab);
    recordEvent('tab_viewed', { tab: nextTab });
    document.getElementById(`diagnostic-tab-${nextTab}`)?.focus();
  }, []);

  const selectTab = useCallback((tab) => {
    setActiveTab(tab);
    recordEvent('tab_viewed', { tab });
  }, []);

  const sortedGaps = useMemo(
    () => sortSkillGaps(prediction?.skill_gaps || [], showPriorityGapsOnly),
    [prediction, showPriorityGapsOnly],
  );

  const handleExport = useCallback(() => {
    recordEvent('report_export_requested');
    window.print();
  }, []);

  const openWorkspace = useCallback(
    (nextWorkspace) => {
      setWorkspace(nextWorkspace);
      recordEvent('workspace_viewed', { workspace: nextWorkspace });
      if ((nextWorkspace === 'mentor' || nextWorkspace === 'admin') && isStaff) {
        setActiveTab('gaps');
        loadCohort();
      }
    },
    [isStaff, loadCohort],
  );

  return (
    <div className={`app-wrapper${workspace === 'student' ? ' student-view' : ''}`}>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <header className="app-header">
        <div className="header-container">
          <div className="brand-section">
            <BrandLogo />
            <div>
              <div className="brand-title">
                LPU Placement Intelligence
              </div>
              <div className="brand-sub">
                Placement readiness workspace
              </div>
            </div>
          </div>

          <div className="header-actions">
            <div className="auth-status" title={`Signed in as ${user.username}`}>
              <span className="auth-avatar" aria-hidden="true">{(user.display_name || user.username || 'U').trim().charAt(0).toUpperCase()}</span>
              <span className="auth-name">
                {user.display_name}{user.display_name.trim().toLowerCase() !== (ROLE_LABELS[user.role] || user.role).trim().toLowerCase() && ` · ${ROLE_LABELS[user.role] || user.role}`}
              </span>
              {user.cohort && user.cohort.trim().toLowerCase() !== 'none' ? <span className="auth-cohort">{user.cohort}</span> : null}
            </div>



            {usesSupabaseAuth && <NotificationsMenu />}
            <button
              type="button"
              onClick={handleExport}
              className="btn-preset header-export"
              title="Print student diagnostic report"
            >
              <Printer size={15} aria-hidden="true" />
              <span>Export Report</span>
            </button>

            <button
              type="button"
              className="btn-preset header-signout"
              onClick={async () => { setSignOutError(''); const failure = await onLogout(); if (failure) setSignOutError(failure); }}
              title="Sign out of this session"
            >
              <LogOut size={15} aria-hidden="true" />
              <span>Sign out</span>
            </button>
          </div>
        </div>
        <div className="header-workspace-row">
            {isStaff ? (
              <div className="workspace-switcher" role="group" aria-label="Workspace">
                <button
                  type="button"
                  className={`workspace-btn ${workspace === 'student' ? 'active' : ''}`}
                  onClick={() => openWorkspace('student')}
                  aria-pressed={workspace === 'student'}
                >
                  Student workspace
                </button>
                {user.role === 'mentor' ? <button
                  type="button"
                  className={`workspace-btn ${workspace === 'mentor' ? 'active' : ''}`}
                  onClick={() => openWorkspace('mentor')}
                  aria-pressed={workspace === 'mentor'}
                >
                  Mentor workspace
                </button> : null}
                {canUseAdminWorkspace ? <button
                  type="button"
                  className={`workspace-btn ${workspace === 'admin' ? 'active' : ''}`}
                  onClick={() => openWorkspace('admin')}
                  aria-pressed={workspace === 'admin'}
                >
                  {user.role === 'admin' ? 'Admin workspace' : 'Placement workspace'}
                </button> : null}
              </div>
            ) : null}
        </div>
        {workspace === 'student' && <nav className="student-topic-nav" aria-label="Student workspace sections">{[
          ['overview', 'Assessment & overview'],
          ['preparation', 'Preparation & progress'],
          ['roles', 'Target roles'],
          ['evidence', 'Evidence & corrections'],
        ].map(([id, label]) => <button key={id} type="button" className={`student-topic-button${studentSection === id ? ' active' : ''}`} aria-pressed={studentSection === id} aria-controls={`student-section-${id}`} onClick={() => setStudentSection(id)}>{label}</button>)}</nav>}
      </header>

      <main id="main-content" className={`main-content${workspace === 'student' ? ' student-main' : ''}`}>
        <h1 className="sr-only">{workspace === 'mentor' ? 'Mentor placement readiness dashboard' : workspace === 'admin' ? 'Placement program administration dashboard' : 'Student placement readiness dashboard'}</h1>

        {workspace === 'student' && <div className="student-page-heading"><div><span className="student-page-eyebrow">STUDENT WORKSPACE</span><h2>Your placement readiness</h2><p>Review your progress and choose your next step.</p></div><span className="student-heading-tag">Your preparation, in one place</span></div>}

        <WorkspaceGuide role={workspace === 'student' ? 'student' : workspace} />

        {profileNotice && <StatusBanner tone="warning">{profileNotice}</StatusBanner>}
        {signOutError && <StatusBanner tone="warning">{signOutError}</StatusBanner>}

        {!online && (
          <StatusBanner tone="warning" icon={<Info size={18} aria-hidden="true" />}>
            You are offline. You can keep editing your profile; analysis resumes when the connection
            returns.
          </StatusBanner>
        )}

        {error && (
          <StatusBanner tone="danger" icon={<AlertTriangle size={18} aria-hidden="true" />}>
            <strong>System notice:</strong> {error.message}
            {error.correlationId ? (
              <span className="support-code"> Reference: {error.correlationId.slice(0, 8)}</span>
            ) : null}
            <button type="button" className="inline-retry" onClick={handleRetry} disabled={loading}>
              Retry
            </button>
          </StatusBanner>
        )}

        {!apiOnline && !healthChecking && !error && online && (
          <StatusBanner tone="warning" icon={<Info size={18} aria-hidden="true" />}>
            The API is offline. You can continue editing the assessment, but analysis requires a
            connection to the readiness service.
            <button type="button" className="inline-retry" onClick={checkHealth}>
              Check connection
            </button>
          </StatusBanner>
        )}

        {workspace === 'mentor' ? (
          <Suspense fallback={<ChunkFallback label="Loading mentor workspace" />}>
            <MentorOverview
              cohort={cohort}
              loading={cohortLoading}
              error={cohortError}
              onRetry={loadCohort}
              authorized={isStaff}
              viewer={user}
            />
          </Suspense>
        ) : workspace === 'admin' ? (
          <Suspense fallback={<ChunkFallback label="Loading admin workspace" />}>
            <AdminDashboard
              cohort={cohort}
              loading={cohortLoading}
              error={cohortError}
              onRetry={loadCohort}
              authorized={canUseAdminWorkspace}
              viewer={user}
            />
          </Suspense>
        ) : (
          <div className="student-workspace">
          <div id="student-section-overview" className="student-topic-panel" hidden={studentSection !== 'overview'}>
          {user.role === 'student' && <StudentNextSteps studentId={user.id} recommendations={prediction?.recommendations || []} history={history} onOpenPlan={() => { setStudentSection('preparation'); selectTab('roadmap'); }} onOpenEvidence={() => setStudentSection('evidence')} onOpenProgress={() => { setStudentSection('preparation'); selectTab('progress'); }} />}
          <div className="dashboard-grid">
            <StudentForm
              formData={formData}
              isDirty={isDirty}
              loading={loading}
              validation={validation}
              onFieldChange={handleFieldChange}
              onSubmit={handleSubmit}
              onReset={handleReset}
              onPreset={handlePreset}
            />

            <section className="results-container" aria-label="Readiness results">
              {loading && !prediction ? <ReadinessSkeleton /> : null}

              {prediction ? <ReadinessCard prediction={prediction} /> : null}

              {prediction ? (
                <section className="glass-card profile-quality" aria-labelledby="profile-quality-heading">
                  <div className="card-header"><div><h2 id="profile-quality-heading">Profile coverage and evidence quality</h2><p>Coverage is separate from readiness; this is not a calibrated confidence score.</p></div></div>
                  <div className="card-body">
                    <div className="progress-summary-grid">
                      <article className="metric-card"><span className="metric-card-label">Model inputs entered</span><strong className="metric-card-value">{Object.keys(formData).filter((field) => formData[field] !== '' && formData[field] !== null && formData[field] !== undefined).length}/{Object.keys(formData).length}</strong></article>
                      <article className="metric-card metric-card-warning"><span className="metric-card-label">Evidence status</span><strong className="metric-card-value">Self-reported</strong></article>
                      <article className="metric-card"><span className="metric-card-label">Estimate freshness</span><strong className="metric-card-value">{isDirty ? 'Needs refresh' : lastUpdated ? 'Current' : 'Not assessed'}</strong></article>
                    </div>
                    <p className="probability-note">The current prototype does not verify academic records, project links, internships, or certifications. A complete form can still have limited evidence confidence. {isDirty ? 'Profile changes are not included in the displayed result. Analyze again to update it.' : ''}</p>
                  </div>
                </section>
              ) : null}

              {prediction ? <ReadinessBreakdown profile={formData} prediction={prediction} /> : null}

            </section>
          </div>
          </div>

          <div id="student-section-preparation" className="student-topic-panel" hidden={studentSection !== 'preparation'}>
          {user.role === 'student' && studentSection === 'preparation' && <CvReview studentId={user.id} />}
          <StudyResources studentId={user.id} />
          {user.role === 'student' && <PreparationPlanner studentId={user.id} targetRole={targetRoles[0]} />}
              <div className="glass-card">
                <nav className="tabs-nav" aria-label="Diagnostic sections" role="tablist">
                  {TAB_CONFIG.map((tab) => {
                    const Icon = tab.icon;
                    const selected = activeTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        id={`diagnostic-tab-${tab.id}`}
                        type="button"
                        role="tab"
                        aria-selected={selected}
                        aria-controls="diagnostic-panel"
                        tabIndex={selected ? 0 : -1}
                        className={`tab-btn ${selected ? 'active' : ''}`}
                        onClick={() => selectTab(tab.id)}
                        onKeyDown={(event) => handleTabKeyDown(event, tab.id)}
                      >
                        <Icon size={16} aria-hidden="true" />
                        {tab.label}
                      </button>
                    );
                  })}
                </nav>

                <div
                  id="diagnostic-panel"
                  className="card-body"
                  role="tabpanel"
                  aria-labelledby={`diagnostic-tab-${activeTab}`}
                  tabIndex="0"
                >
                  {!prediction && !loading ? (
                    <div className="empty-state">
                      <p>Analyze your profile to see your diagnostic sections.</p>
                    </div>
                  ) : null}

                  {activeTab === 'gaps' && prediction ? (
                    <SkillGapPanel
                      gaps={sortedGaps}
                      totalGaps={prediction.skill_gaps?.length || 0}
                      priorityOnly={showPriorityGapsOnly}
                      onTogglePriorityOnly={(event) =>
                        setShowPriorityGapsOnly(event.target.checked)
                      }
                    />
                  ) : null}

                  {activeTab === 'roadmap' && prediction ? (
                    <RoadmapPanel recommendations={prediction.recommendations || []} studentId={user.id} assessmentDate={lastUpdated} />
                  ) : null}

                  {activeTab === 'factors' && prediction ? (
                    <Suspense fallback={<ChunkFallback label="Loading explanation charts" />}>
                      <InfluentialFactorsPanel prediction={prediction} />
                    </Suspense>
                  ) : null}

                  {activeTab === 'progress' ? (
                    <ProgressPanel
                      history={history}
                      historyError={historyError}
                      loading={loading}
                    />
                  ) : null}
                </div>
              </div>

              {PILOT_FEEDBACK_ENABLED ? <FeedbackWidget task="assessment" /> : null}
          </div>
          <div id="student-section-roles" className="student-topic-panel" hidden={studentSection !== 'roles'}>
          <RoleGapPanel formData={formData} targetRoles={targetRoles} onRolesChange={setTargetRoles} />
          </div>
          <div id="student-section-evidence" className="student-topic-panel" hidden={studentSection !== 'evidence'}>
          <StudentEvidencePanel studentId={user.id} />
          </div>
          </div>
        )}

        <section className="about-section" aria-labelledby="about-heading">
          <h2 id="about-heading">How to read this dashboard</h2>
          <SectionIntro>
            Readiness scores and gaps are diagnostic indicators from a prototype model. They do not
            determine eligibility, and the published campus drive notice remains authoritative.
          </SectionIntro>
        </section>
      </main>
    </div>
  );
}
