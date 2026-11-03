import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import PipelineFilters from './PipelineFilters';

it('keeps recorded values and lets the user choose example filters', () => {
  const setCohort = vi.fn();
  const setRole = vi.fn();
  const setCompany = vi.fn();
  render(<PipelineFilters placements={[{ cohort: 'CSE-2027', target_role: 'Software Developer', company: 'TCS' }]}
    cohort="All cohorts" setCohort={setCohort} role="All roles" setRole={setRole} company="All companies" setCompany={setCompany} />);

  const cohort = screen.getByLabelText('Cohort');
  const role = screen.getByLabelText('Target role');
  const company = screen.getByLabelText('Company');
  expect(within(cohort).getAllByRole('option', { name: 'CSE-2027' })).toHaveLength(1);
  expect(within(company).getAllByRole('option', { name: 'TCS' })).toHaveLength(1);
  fireEvent.change(cohort, { target: { value: 'ECE-2027' } });
  fireEvent.change(role, { target: { value: 'Data Analyst' } });
  fireEvent.change(company, { target: { value: 'Infosys' } });
  expect(setCohort).toHaveBeenCalledWith('ECE-2027');
  expect(setRole).toHaveBeenCalledWith('Data Analyst');
  expect(setCompany).toHaveBeenCalledWith('Infosys');
  expect(screen.getByText(/do not imply placement records/i)).toBeInTheDocument();
});
