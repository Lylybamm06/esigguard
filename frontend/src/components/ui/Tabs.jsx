export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="tabs">
      {tabs.map(t => (
        <button
          key={t.value}
          className={`tab ${value===t.value ? "tabActive" : ""}`}
          onClick={() => onChange(t.value)}
          type="button"
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
