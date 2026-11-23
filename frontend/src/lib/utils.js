import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount, currency = 'EUR') {
  return new Intl.NumberFormat('en-EU', {
    style: 'currency',
    currency: currency,
  }).format(amount);
}

export function formatPercent(value, decimals = 0) {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function getRiskColor(riskLevel) {
  switch (riskLevel?.toLowerCase()) {
    case 'low':
    case 'conservative':
      return 'text-green-600 bg-green-50';
    case 'medium':
    case 'moderate':
      return 'text-amber-600 bg-amber-50';
    case 'high':
    case 'aggressive':
      return 'text-red-500 bg-red-50';
    default:
      return 'text-gray-600 bg-gray-50';
  }
}

export function getStatusColor(status) {
  switch (status?.toLowerCase()) {
    case 'excellent':
      return 'status-excellent';
    case 'good':
      return 'status-good';
    case 'moderate':
      return 'status-moderate';
    case 'not_recommended':
      return 'status-not-recommended';
    default:
      return 'bg-muted text-muted-foreground';
  }
}
