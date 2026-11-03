import React, { useEffect, useState } from 'react';
import { Save, UserCheck } from 'lucide-react';
import { get, post } from '../services/apiClient';

export default function AdminMentorAssignments() {
  const [data, setData] = useState(null);
  const [studentId, setStudentId] = useState('');
  const [mentorId, setMentorId] = useState('');
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let active = true;
    setError('');
    Promise.all([get('/admin/students'), get('/admin/mentors'), get('/admin/mentor-assignments')])
      .then(([students, mentors, assignments]) => { if (active) setData({ students: students.data || [], mentors: mentors.data || [], assignments: assignments.data || [], mappedMentors: assignments.mapped_mentor_ids ?? null, mappedStudents: assignments.mapped_student_ids ?? null }); })
      .catch((err) => { if (active) { setData(null); setError(err?.message || 'Assignments could not be loaded.'); } });
    return () => { active = false; };
  }, [reload]);

  const student = data?.students.find((item) => String(item.id) === studentId);
  const assignment = data?.assignments.find((item) => String(item.student_id) === studentId);
  const choices = data?.mentors.filter((item) => item.is_active && (data.mappedMentors === null || data.mappedMentors.includes(item.id))) || [];
  const unavailable = data?.mentors.filter((item) => !item.is_active || (data.mappedMentors !== null && !data.mappedMentors.includes(item.id))) || [];
  const studentLinked = !student || data?.mappedStudents === null || data?.mappedStudents.includes(student.id);
  const mentorLabel = (mentor) => `${mentor.display_name} (${mentor.username}) · ${mentor.cohort || 'No cohort'}`;
  const matchesSearch = (value) => value.toLowerCase().includes(search.trim().toLowerCase());
  const selectStudent = (id) => {
    setStudentId(id);
    const existing = data.assignments.find((item) => String(item.student_id) === id);
    setMentorId(existing?.valid ? String(existing.mentor_id) : '');
    setMessage(''); setError('');
  };
  const save = async (event) => {
    event.preventDefault(); setBusy(true); setError(''); setMessage('');
    try {
      await post(`/admin/students/${studentId}/mentor`, { mentor_id: mentorId ? Number(mentorId) : null });
      setMessage(mentorId ? 'Mentor assignment saved.' : 'Mentor assignment removed.');
      setReload((value) => value + 1);
    } catch (err) { setError(err?.message || 'The assignment could not be saved. Please retry.'); }
    finally { setBusy(false); }
  };
  return <section className="glass-card admin-assignment" aria-labelledby="assignment-title">
    <div className="card-header"><div><h2 id="assignment-title"><UserCheck size={18} aria-hidden="true" /> Assign a mentor</h2><p>Choose the mentor responsible for supporting a student.</p></div></div>
    <div className="card-body">
      <p className="probability-note">An active linked mentor may be assigned from any cohort. The assigned mentor can access this student's records as well as their own cohort.</p>
      {error && <p className="assignment-feedback" role="alert">{error} {!data && <button type="button" className="mentor-link-button" onClick={() => setReload((value) => value + 1)}>Retry</button>}</p>}
      {message && <p className="assignment-feedback" role="status">{message}</p>}
      {!data ? !error && <p role="status">Loading accounts…</p> : <><label className="input-label">Search mentors and students<input className="number-input-field" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, username or cohort" /></label><div className="assignment-directory"><h3 className="panel-subheading">Mentor assignments</h3>{data.mentors.filter((mentor) => matchesSearch(`${mentor.display_name} ${mentor.username} ${mentor.cohort || ''}`) || data.assignments.some((entry) => entry.mentor_id === mentor.id && data.students.some((item) => item.id === entry.student_id && matchesSearch(`${item.display_name} ${item.username} ${item.cohort || ''}`)))).map((mentor) => { const assigned = data.assignments.filter((entry) => entry.mentor_id === mentor.id && entry.valid).map((entry) => data.students.find((item) => item.id === entry.student_id)).filter(Boolean); return <article className="assignment-directory-row" key={mentor.id}><strong>{mentorLabel(mentor)}</strong><span>{assigned.length} assigned</span><p>{assigned.length ? assigned.map((item) => `${item.display_name} (${item.cohort || 'No cohort'})`).join(', ') : 'No students assigned'}</p></article>; })}<h3 className="panel-subheading">Unassigned students</h3><p>{data.students.filter((item) => item.is_active && !data.assignments.some((entry) => entry.student_id === item.id && entry.valid) && matchesSearch(`${item.display_name} ${item.username} ${item.cohort || ''}`)).map((item) => `${item.display_name} (${item.cohort || 'No cohort'})`).join(', ') || 'No matching unassigned students.'}</p></div><form onSubmit={save} className="assignment-form">
        <label className="input-label"><span>Student</span><select className="number-input-field" value={studentId} onChange={(event) => selectStudent(event.target.value)} required><option value="">Choose a student</option>{data.students.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.display_name} ({item.username}) · {item.cohort || 'No cohort'}</option>)}</select></label>
        <label className="input-label"><span>Mentor</span><select className="number-input-field" value={mentorId} onChange={(event) => setMentorId(event.target.value)} disabled={!student || !studentLinked}><option value="">No mentor assigned</option>{choices.length > 0 && <optgroup label="Available mentors">{choices.map((item) => <option key={item.id} value={item.id}>{mentorLabel(item)}</option>)}</optgroup>}{unavailable.length > 0 && <optgroup label="Unavailable mentors">{unavailable.map((item) => <option key={item.id} value={item.id} disabled>{mentorLabel(item)} · {item.is_active ? 'Supabase profile not linked' : 'Inactive'}</option>)}</optgroup>}</select></label>
        <button className="assignment-save" type="submit" disabled={!student || !studentLinked || busy}><Save size={16} aria-hidden="true" />{busy ? 'Saving…' : 'Save assignment'}</button>
        {student && <p className="assignment-hint">{!studentLinked ? 'This student needs an active linked Supabase profile before an assignment can be saved.' : <>{assignment ? `Current assignment: ${assignment.display_name}${assignment.valid ? '' : ' (inactive or unavailable; update it)'}.` : 'This student has no assigned mentor.'} {!choices.length && ' No active linked mentors are available.'}</>}</p>}
      </form></>}
    </div>
  </section>;
}
