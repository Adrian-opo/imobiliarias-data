"use client";

import type { PropertyFilters } from "@/types";
import { PROPERTY_TYPE_LABELS } from "@/services/api";

interface ActiveFiltersProps {
  filters: PropertyFilters;
  onRemove: (key: keyof PropertyFilters) => void;
  onClearAll: () => void;
}

export default function ActiveFilters({
  filters,
  onRemove,
  onClearAll,
}: ActiveFiltersProps) {
  const chips: { key: keyof PropertyFilters; label: string }[] = [];

  if (filters.purpose) {
    chips.push({
      key: "purpose",
      label: filters.purpose === "venda" ? "Venda" : "Aluguel",
    });
  }

  if (filters.neighborhood) {
    chips.push({ key: "neighborhood", label: `Bairro: ${filters.neighborhood}` });
  }

  if (filters.type && filters.type.length > 0) {
    filters.type.forEach((t) => {
      chips.push({
        key: "type",
        label: PROPERTY_TYPE_LABELS[t] || t,
      });
    });
  }

  if (filters.min_price !== undefined) {
    chips.push({
      key: "min_price",
      label: `Min: R$ ${(filters.min_price / 1000).toFixed(0)}k`,
    });
  }

  if (filters.max_price !== undefined) {
    chips.push({
      key: "max_price",
      label: `Max: R$ ${(filters.max_price / 1000).toFixed(0)}k`,
    });
  }

  if (filters.min_bedrooms !== undefined) {
    chips.push({
      key: "min_bedrooms",
      label: `${filters.min_bedrooms}+ quartos`,
    });
  }

  if (filters.min_parking !== undefined) {
    chips.push({
      key: "min_parking",
      label: `${filters.min_parking}+ vagas`,
    });
  }

  if (filters.min_area !== undefined) {
    chips.push({
      key: "min_area",
      label: `Min ${filters.min_area}m²`,
    });
  }

  if (filters.is_new) {
    chips.push({ key: "is_new", label: "Novos" });
  }

  if (filters.source_id) {
    chips.push({ key: "source_id", label: "Imobiliária específica" });
  }

  if (filters.sort) {
    chips.push({ key: "sort", label: `Ordenado` });
  }

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2 py-3">
      <span className="text-sm text-gray-500">Filtros ativos:</span>
      {chips.map((chip) => (
        <span
          key={`${chip.key}-${chip.label}`}
          className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700"
        >
          {chip.label}
          <button
            onClick={() => onRemove(chip.key)}
            className="ml-0.5 inline-flex h-4 w-4 items-center justify-center rounded-full text-gray-400 hover:bg-gray-200 hover:text-gray-600"
            aria-label={`Remover filtro ${chip.label}`}
          >
            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </span>
      ))}
      <button
        onClick={onClearAll}
        className="text-sm text-red-600 hover:text-red-800 hover:underline"
      >
        Limpar todos
      </button>
    </div>
  );
}
