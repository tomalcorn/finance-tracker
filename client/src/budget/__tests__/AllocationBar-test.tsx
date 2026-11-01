import { render, screen } from '@testing-library/react-native';

import { AllocationBar } from '@/budget/AllocationBar';
import type { CategoryView } from '@/domain/readModels';

function tracker(name: string, budget: number): CategoryView {
  return {
    id: name,
    user_id: 'auth0|test',
    name,
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    parent_id: null,
    budget,
    accrual: 'monthly',
    cost: 0,
    starting_balance: 0,
    accrued: 0,
    remaining: budget,
    progress: 0,
    split: 0,
  };
}

describe('AllocationBar', () => {
  it('lists the trackers from the largest budget to the smallest, then what is unallocated', async () => {
    await render(
      <AllocationBar
        trackers={[tracker('Expenses', 350), tracker('Joint', 1400), tracker('Savings', 565)]}
        income={3000}
      />,
    );

    expect(
      screen
        .getAllByText(/^(Expenses|Joint|Savings|Unallocated) /)
        .map((node) => node.props.children),
    ).toEqual(['Joint £1,400.00', 'Savings £565.00', 'Expenses £350.00', 'Unallocated £685.00']);
  });

  it('shows what is left unallocated in the legend', async () => {
    await render(<AllocationBar trackers={[tracker('Expenses', 350)]} income={500} />);

    expect(screen.getByText('Unallocated £150.00')).toBeOnTheScreen();
  });

  it('calls out budgets that add up to more than came in', async () => {
    await render(<AllocationBar trackers={[tracker('Expenses', 600)]} income={500} />);

    expect(screen.getByText('£100.00 more allocated than came in')).toBeOnTheScreen();
  });

  it('leaves unallocated out when every pound is allocated', async () => {
    await render(<AllocationBar trackers={[tracker('Expenses', 500)]} income={500} />);

    expect(screen.queryByText(/^Unallocated/)).not.toBeOnTheScreen();
  });
});
