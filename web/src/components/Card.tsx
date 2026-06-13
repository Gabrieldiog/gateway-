import { AzulejoGlifo } from "./Azulejo";

// card base: hairline em vez de sombra, canto superior-esquerdo marcado pelo
// glifo de azulejo como assinatura recorrente.
export function Card({
  children,
  className = "",
  glifo = true,
}: {
  children: React.ReactNode;
  className?: string;
  glifo?: boolean;
}) {
  return (
    <div
      className={`relative rounded-lg border border-line bg-surface ${className}`}
    >
      {glifo && (
        <AzulejoGlifo
          size={14}
          className="absolute left-2 top-2 text-accent-2/35"
        />
      )}
      {children}
    </div>
  );
}
