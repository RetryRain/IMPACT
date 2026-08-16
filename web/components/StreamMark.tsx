type StreamMarkProps = {
  className?: string;
  /** Unique prefix for gradient ids when multiple marks on one page */
  idPrefix?: string;
};

export function StreamMark({ className = "h-6 w-6", idPrefix = "sm" }: StreamMarkProps) {
  const streamId = `${idPrefix}-stream`;
  const innerId = `${idPrefix}-stream-inner`;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 500 500"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={streamId} x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#059669" />
          <stop offset="50%" stopColor="#10B981" />
          <stop offset="100%" stopColor="#34D399" />
        </linearGradient>
        <linearGradient id={innerId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#065F46" />
          <stop offset="100%" stopColor="#047857" />
        </linearGradient>
      </defs>
      <path
        d="M 250, 70
           C 290, 130 360, 210 360, 290
           C 360, 370 310, 420 250, 420
           C 190, 420 140, 370 140, 290
           C 140, 230 180, 160 220, 120
           C 210, 160 210, 190 225, 220
           C 240, 250 265, 270 270, 300
           C 275, 330 260, 355 240, 365
           C 290, 360 320, 320 315, 270
           C 310, 220 270, 160 250, 70 Z"
        fill={`url(#${streamId})`}
      />
      <path
        d="M 245, 160
           C 270, 210 300, 250 295, 300
           C 290, 340 265, 365 235, 370
           C 260, 350 270, 320 260, 290
           C 250, 260 225, 240 220, 210
           C 215, 185 230, 170 245, 160 Z"
        fill={`url(#${innerId})`}
      />
    </svg>
  );
}
