"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const router = useRouter();

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (searchTerm.trim()) {
      router.push(`/imoveis?search=${encodeURIComponent(searchTerm.trim())}`);
    } else {
      router.push("/imoveis");
    }
    setSearchTerm("");
  }

  return (
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
      <div className="container-page">
        <div className="flex h-16 items-center justify-between gap-4">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white text-sm font-bold">
              JP
            </div>
            <div className="hidden sm:block">
              <span className="text-lg font-bold text-gray-900">
                Imóveis Ji-Paraná
              </span>
            </div>
          </Link>

          {/* Search - Desktop */}
          <form
            onSubmit={handleSearch}
            className="hidden md:flex flex-1 max-w-md"
          >
            <div className="relative w-full">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar por bairro, endereço..."
                className="input-field pr-10"
              />
              <button
                type="submit"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                aria-label="Buscar"
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </button>
            </div>
          </form>

          {/* Nav links */}
          <nav className="hidden md:flex items-center gap-1">
            <Link href="/" className="btn-ghost text-sm">
              Início
            </Link>
            <Link href="/imoveis" className="btn-ghost text-sm">
              Imóveis
            </Link>
            <Link href="/novos" className="btn-ghost text-sm">
              Novos
            </Link>
            <Link href="/como-funciona" className="btn-ghost text-sm">
              Como funciona
            </Link>
          </nav>

          {/* Mobile menu button */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden rounded-lg p-2 text-gray-600 hover:bg-gray-100"
            aria-label="Abrir menu"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {mobileOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="border-t border-gray-200 md:hidden">
          <div className="container-page py-4 space-y-3">
            <form onSubmit={handleSearch}>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar por bairro, endereço..."
                className="input-field"
              />
            </form>
            <nav className="flex flex-col gap-1">
              <Link
                href="/"
                className="btn-ghost justify-start"
                onClick={() => setMobileOpen(false)}
              >
                Início
              </Link>
              <Link
                href="/imoveis"
                className="btn-ghost justify-start"
                onClick={() => setMobileOpen(false)}
              >
                Imóveis
              </Link>
              <Link
                href="/novos"
                className="btn-ghost justify-start"
                onClick={() => setMobileOpen(false)}
              >
                Novos
              </Link>
              <Link
                href="/como-funciona"
                className="btn-ghost justify-start"
                onClick={() => setMobileOpen(false)}
              >
                Como funciona
              </Link>
            </nav>
          </div>
        </div>
      )}
    </header>
  );
}
