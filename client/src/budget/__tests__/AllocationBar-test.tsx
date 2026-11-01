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
  it('lists the trackers from the largest budget to the smallest', async () => {
    await render(
      <AllocationBar
        trackers={[tracker('Expenses', 350), tracker('Joint', 1400), tracker('Savings', 565)]}
        income={3000}
      />,
    );

    expect(
      screen.getAllByText(/^(Expenses|Joint|Savings) /).map((node) => node.props.children[0]),
    ).toEqual(['Joint', 'Savings', 'Expenses']);
  });

  it('says how much is not yet allocated', async () => {
    await render(<AllocationBar trackers={[tracker('Expenses', 350)]} income={500} />);

    expect(screen.getByText('£150.00 not yet allocated')).toBeOnTheScreen();
  });

  it('calls out budgets that add up to more than came in', async () => {
    await render(<AllocationBar trackers={[tracker('Expenses', 600)]} income={500} />);

    expect(screen.getByText('£100.00 more allocated than came in')).toBeOnTheScreen();
  });
});
