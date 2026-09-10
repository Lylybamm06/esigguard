import { NavLink } from "react-router-dom";

const nav = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/analyze", label: "Analyse" },
  { to: "/history", label: "Historique" },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="logoDot" />
        <div>
          <div className="brandName">ESIG’GUARD</div>
          <div className="brandSub">Email Threat Analysis</div>
        </div>
      </div>

      <div className="nav">
        {nav.map(i => (
          <NavLink key={i.to} to={i.to} className={({isActive}) => `navItem ${isActive ? "navActive" : ""}`}>
            {i.label}
          </NavLink>
        ))}
      </div>

      <div className="sidebarFoot">
        <div className="muted">Status</div>
        <div className="row">
          <span className="dotGood" />
          <span style={{fontSize:13}}>Operational</span>
        </div>
      </div>
    </aside>
  );
}
