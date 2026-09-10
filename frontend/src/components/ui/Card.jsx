export function Card({ children, className="" }) {
  return <div className={`card ${className}`}>{children}</div>;
}
export function CardHeader({ title, subtitle, right }) {
  return (
    <div className="cardHeader">
      <div>
        <div className="cardTitle">{title}</div>
        {subtitle && <div className="cardSubtitle">{subtitle}</div>}
      </div>
      {right && <div>{right}</div>}
    </div>
  );
}
