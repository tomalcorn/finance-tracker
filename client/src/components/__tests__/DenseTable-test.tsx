import { fireEvent, render, screen } from '@testing-library/react-native';

import { DenseTable, type DenseColumn } from '@/components/DenseTable';

type Row = { id: string; name: string; amount: number };

const ROWS: Row[] = [
  { id: 'a', name: 'Tesco', amount: 12 },
  { id: 'b', name: 'Netflix', amount: 11 },
];

const COLUMNS: DenseColumn<Row>[] = [
  { key: 'name', label: 'Name', render: (row) => row.name },
  { key: 'amount', label: 'Amount', align: 'right', render: (row) => row.amount },
];

describe('DenseTable', () => {
  it('labels each column in a header', async () => {
    await render(<DenseTable columns={COLUMNS} rows={ROWS} rowKey={(row) => row.id} />);

    expect(screen.getByText('Amount')).toBeOnTheScreen();
  });

  it('renders a cell for each row and column', async () => {
    await render(<DenseTable columns={COLUMNS} rows={ROWS} rowKey={(row) => row.id} />);

    expect(screen.getByText('Netflix')).toBeOnTheScreen();
  });

  it('reports the row that was pressed', async () => {
    const onRowPress = jest.fn();
    await render(
      <DenseTable columns={COLUMNS} rows={ROWS} rowKey={(row) => row.id} onRowPress={onRowPress} />,
    );

    await fireEvent.press(screen.getByText('Netflix'));

    expect(onRowPress).toHaveBeenCalledWith(ROWS[1]);
  });

  it('says so when there are no rows', async () => {
    await render(
      <DenseTable columns={COLUMNS} rows={[]} rowKey={(row) => row.id} empty="No payments." />,
    );

    expect(screen.getByText('No payments.')).toBeOnTheScreen();
  });
});
