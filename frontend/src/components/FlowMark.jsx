export function FlowMark({ className = "w-7 h-7" }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#B85C38" />
      <path
        d="M7 21.5c3.4-7.2 6.6-7.2 8.5 0s5.1 7.2 8.5 0"
        fill="none"
        stroke="#F6F1EC"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
    </svg>
  );
}
