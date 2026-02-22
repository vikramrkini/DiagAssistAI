"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { getToken, logout, subscribeToAuthChanges } from "@/lib/api";

const authedNav = [
  { href: "/", label: "Dashboard" },
  { href: "/clinician/profile", label: "Clinician" },
  { href: "/patients", label: "Patients" },
  { href: "/encounters/new", label: "New Encounter" },
  { href: "/settings", label: "Settings" }
];

const guestNav = [
  { href: "/", label: "Home" },
  { href: "/about", label: "About" },
  { href: "/auth/signup", label: "Register" }
];

export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  useEffect(() => {
    const syncAuthState = () => setIsAuthenticated(Boolean(getToken()));
    syncAuthState();
    return subscribeToAuthChanges(syncAuthState);
  }, []);

  const navItems = useMemo(() => (isAuthenticated ? authedNav : guestNav), [isAuthenticated]);
  const isMarketingTheme = useMemo(
    () =>
      !isAuthenticated &&
      (pathname === "/" ||
        pathname.startsWith("/about") ||
        pathname.startsWith("/auth/signin") ||
        pathname.startsWith("/auth/signup")),
    [isAuthenticated, pathname]
  );
  const isAppTheme = useMemo(
    () =>
      isAuthenticated &&
      (pathname === "/" ||
        pathname.startsWith("/clinician") ||
        pathname.startsWith("/patients") ||
        pathname.startsWith("/encounters") ||
        pathname.startsWith("/settings")),
    [isAuthenticated, pathname]
  );

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.body.classList.toggle("marketing-theme-active", isMarketingTheme);
    document.body.classList.toggle("app-theme-active", isAppTheme);
    return () => {
      document.body.classList.remove("marketing-theme-active");
      document.body.classList.remove("app-theme-active");
    };
  }, [isMarketingTheme, isAppTheme]);

  async function onLogout() {
    setIsLoggingOut(true);
    await logout();
    setIsLoggingOut(false);
    router.push("/auth/signin");
    router.refresh();
  }

  function isActive(href: string) {
    if (href === "/") {
      return pathname === "/";
    }
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <header className={isMarketingTheme ? "app-header app-header--marketing" : isAppTheme ? "app-header app-header--app" : "app-header"}>
      <div
        className={
          isMarketingTheme
            ? "app-header__frame app-header__frame--marketing"
            : isAppTheme
              ? "app-header__frame app-header__frame--app"
              : "app-header__frame"
        }
      >
        <Link href="/" className="brand">
          <img src="/diagassist-logo.svg" alt="DiagAssistAI logo" className="brand__logo" />
          <span className="brand__text">DiagAssistAI</span>
          <span className="brand__tag">Clinical Intelligence</span>
        </Link>

        <nav className="top-nav" aria-label="Primary">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href} className={isActive(item.href) ? "top-nav__link is-active" : "top-nav__link"}>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="header-actions">
          {!isAuthenticated ? (
            <Link href="/auth/signin" className="button button--ghost">
              Sign in
            </Link>
          ) : (
            <button
              type="button"
              onClick={onLogout}
              disabled={isLoggingOut}
              className="button button--ghost"
              aria-label="Log out"
            >
              {isLoggingOut ? "Logging out..." : "Logout"}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
