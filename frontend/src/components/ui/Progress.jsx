export function Progress({ value=0 }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className="progress">
      <div className="progressBar" style={{ width: `${v}%` }} />
    </div>
  );
}
