export function Input({ label, hint, ...props }) {
  return (
    <label className="field">
      {label && <div className="label">{label}</div>}
      <input className="input" {...props} />
      {hint && <div className="hint">{hint}</div>}
    </label>
  );
}
export function Textarea({ label, hint, ...props }) {
  return (
    <label className="field">
      {label && <div className="label">{label}</div>}
      <textarea className="textarea" {...props} />
      {hint && <div className="hint">{hint}</div>}
    </label>
  );
}
