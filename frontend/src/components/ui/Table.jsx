export function Table({ columns, rows, onRowClick }) {
  return (
    <div className="tableWrap">
      <table className="table">
        <thead>
          <tr>{columns.map(c => <th key={c.key}>{c.header}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr key={r.id ?? idx} onClick={() => onRowClick?.(r)} className={onRowClick ? "rowClick" : ""}>
              {columns.map(c => <td key={c.key}>{c.render ? c.render(r) : r[c.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
