// motivo de azulejo português (quadrifólio num losango) — a assinatura
// visual recorrente: micro-glifo no canto dos cards e marca-d'água nos cadernos

export function AzulejoGlifo({
  className = "",
  size = 16,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <g stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
        <path d="M16 2 L30 16 L16 30 L2 16 Z" />
        <path d="M16 9c2.6 0 4.2 1.6 4.2 4.2 1.6 0 2.6 1.6 2.6 2.6 0 2.6-1.6 4.2-4.2 4.2 0 1.6-1.6 2.6-2.6 2.6-2.6 0-4.2-1.6-4.2-4.2-1.6 0-2.6-1.6-2.6-2.6 0-2.6 1.6-4.2 4.2-4.2C13.4 10.6 15 9 16 9Z" />
      </g>
      <circle cx="16" cy="16" r="1.6" fill="currentColor" />
    </svg>
  );
}

// faixa de azulejos a baixa opacidade, pra marca-d'água no topo dos cadernos
const TILE = encodeURIComponent(
  `<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 32 32' fill='none'>
    <g stroke='%COLOR%' stroke-width='1.2' stroke-linejoin='round'>
      <path d='M16 2 L30 16 L16 30 L2 16 Z'/>
      <path d='M16 9c2.6 0 4.2 1.6 4.2 4.2 1.6 0 2.6 1.6 2.6 2.6 0 2.6-1.6 4.2-4.2 4.2 0 1.6-1.6 2.6-2.6 2.6-2.6 0-4.2-1.6-4.2-4.2-1.6 0-2.6-1.6-2.6-2.6 0-2.6 1.6-4.2 4.2-4.2C13.4 10.6 15 9 16 9Z'/>
    </g>
  </svg>`.replace(/%COLOR%/g, "%231f5c5a"),
);

export function azulejoFundo(opacidade = 0.05): React.CSSProperties {
  return {
    backgroundImage: `url("data:image/svg+xml,${TILE}")`,
    backgroundSize: "48px 48px",
    opacity: opacidade,
  };
}
