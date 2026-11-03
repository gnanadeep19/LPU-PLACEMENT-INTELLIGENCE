import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import CohortBreakdown from './CohortBreakdown';

const student = (id, cohort, role) => ({ user_id: id, cohort, target_role: role, readiness_score: 70, profile: {} });

describe('cohort comparison privacy', () => {
  it('hides an entire dimension when a group is smaller than the minimum', () => {
    render(<CohortBreakdown students={[student(1, 'CSE-A', 'Developer'), student(2, 'CSE-A', 'Developer'), student(3, 'CSE-B', 'Developer')]} loaded loading={false} minimum={2} />);
    expect(screen.getByText(/by cohort is hidden/i)).toBeInTheDocument();
    expect(screen.queryByText('CSE-A')).not.toBeInTheDocument();
    expect(screen.getByText('Developer')).toBeInTheDocument();
  });
  it('reports assessed and complete denominators for publishable groups', () => {
    render(<CohortBreakdown students={[student(1, 'CSE-A', 'Developer'), student(2, 'CSE-A', 'Developer')]} loaded loading={false} minimum={2} />);
    expect(screen.getAllByText('0/2')).toHaveLength(2);
  });
});
