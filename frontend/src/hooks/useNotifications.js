import { useState, useEffect, useCallback } from 'react';

const NOTIFICATION_ICON = 'https://customer-assets.emergentagent.com/job_money-brain-ai/artifacts/fodh5r8x_image.png';
const NOTIFICATION_DURATION_MS = 8000;

export function useNotifications() {
  const [permission, setPermission] = useState('default');
  const [supported, setSupported] = useState(false);

  useEffect(() => {
    const isSupported = 'Notification' in window;
    setSupported(isSupported);
    if (isSupported) {
      setPermission(Notification.permission);
    }
  }, []);

  const requestPermission = useCallback(async () => {
    if (!supported) return 'unsupported';
    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      return result;
    } catch (err) {
      return 'denied';
    }
  }, [supported]);

  const sendNotification = useCallback((title, options = {}) => {
    if (!supported || permission !== 'granted') return;
    try {
      const notification = new Notification(title, {
        icon: NOTIFICATION_ICON,
        badge: NOTIFICATION_ICON,
        ...options
      });
      setTimeout(() => notification.close(), NOTIFICATION_DURATION_MS);
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Notification API failed:', err);
    }
  }, [supported, permission]);

  const checkBudgetAlerts = useCallback((alerts) => {
    if (!supported || permission !== 'granted' || !alerts?.length) return;

    const warningAlerts = alerts.filter(a => a.status === 'warning' || a.status === 'exceeded');
    warningAlerts.forEach(alert => {
      const body = alert.status === 'exceeded'
        ? `You've exceeded your ${alert.category} budget! Spent EUR ${alert.spent.toFixed(2)} of EUR ${alert.limit.toFixed(2)}.`
        : `Warning: ${alert.percentage}% of your ${alert.category} budget used. EUR ${alert.remaining.toFixed(2)} remaining.`;

      sendNotification(`Budget Alert: ${alert.category}`, { body, tag: `budget-${alert.category}` });
    });
  }, [supported, permission, sendNotification]);

  return {
    supported,
    permission,
    isEnabled: permission === 'granted',
    requestPermission,
    sendNotification,
    checkBudgetAlerts
  };
}
