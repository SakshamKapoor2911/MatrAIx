import { Link, NavLink } from "react-router";

import { cn } from "~/lib/utils";

const navLinkClassName = ({ isActive }: { isActive: boolean }) =>
  cn(
    "text-sm text-muted-foreground transition-colors hover:text-foreground",
    isActive && "text-foreground"
  );

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background">
      <div className="flex h-12 items-center gap-5 px-4">
        <Link
          to="/"
          className="shrink-0 text-sm font-semibold tracking-tight hover:text-foreground/80"
        >
          PersonaBench
        </Link>
        <nav className="flex min-w-0 items-center gap-4">
          <NavLink to="/" className={navLinkClassName}>
            Jobs
          </NavLink>
          <NavLink to="/persona-synthesis" className={navLinkClassName}>
            Synthesis
          </NavLink>
        </nav>
      </div>
    </header>
  );
}
