"use client";

import { useState } from "react";

interface SearchBarProps {
  initialValue?: string;
  onSearch: (term: string) => void;
  placeholder?: string;
}

export default function SearchBar({
  initialValue = "",
  onSearch,
  placeholder = "Buscar por bairro, endereço...",
}: SearchBarProps) {
  const [value, setValue] = useState(initialValue);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSearch(value.trim());
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          className="input-field pr-12 py-3 text-base"
        />
        <button
          type="submit"
          className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-lg bg-brand-600 p-2 text-white hover:bg-brand-700 transition-colors"
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
  );
}
