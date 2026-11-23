import { Badge } from './ui/badge';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from './ui/table';
import { Button } from './ui/button';
import { Trash2, Receipt } from 'lucide-react';
import { cn } from '../lib/utils';

export function TransactionsTable({ transactions, onDelete, fc }) {
  if (transactions.length === 0) {
    return (
      <div className="py-8 text-center">
        <Receipt className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
        <p className="text-muted-foreground">No transactions yet</p>
        <p className="text-sm text-muted-foreground mt-1">
          Add transactions manually or connect a bank account
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Source</TableHead>
            <TableHead className="text-right">Amount</TableHead>
            <TableHead className="w-[60px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {transactions.slice(0, 20).map(txn => (
            <TableRow key={txn.transaction_id} data-testid={`txn-row-${txn.transaction_id}`}>
              <TableCell className="text-muted-foreground">{txn.date}</TableCell>
              <TableCell className="font-medium">{txn.description}</TableCell>
              <TableCell><Badge variant="secondary">{txn.category}</Badge></TableCell>
              <TableCell><Badge variant="outline" className="capitalize">{txn.source}</Badge></TableCell>
              <TableCell className={cn(
                "text-right font-medium",
                txn.type === 'income' ? 'text-green-600' : 'text-foreground'
              )}>
                {txn.type === 'income' ? '+' : '-'}{fc(txn.amount)}
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost" size="sm"
                  onClick={() => onDelete(txn.transaction_id)}
                  className="text-muted-foreground hover:text-destructive"
                  data-testid={`delete-txn-${txn.transaction_id}`}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
