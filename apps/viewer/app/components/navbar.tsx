import { Link } from "react-router";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background">
      <div className="flex h-12 items-center px-4">
        <Link
          to="/"
          className="text-sm font-semibold tracking-tight hover:text-foreground/80"
        >
          PersonaBench
        </Link>
      </div>
    </header>
  );
}
