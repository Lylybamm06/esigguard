import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function AppLayout({ title, right, children }) {
  return (
    <div className="shell">
      <Sidebar />
      <main className="main">
        <Topbar title={title} right={right} />
        <div className="container">{children}</div>
      </main>
    </div>
  );
}
