"use client";

import { useState, useEffect } from "react";
import type { PropertyFilters, Source } from "@/types";
import { PROPERTY_TYPES_FILTER, NEIGHBORHOODS_OF_JIPARANA, SORT_OPTIONS } from "@/services/api";

interface FilterDrawerProps {
  open: boolean;
  onClose: () => void;
  filters: PropertyFilters;
  sources: Source[];
  onChange: (filters: PropertyFilters) => void;
  onApply: () => void;
}

export default function FilterDrawer({
  open,
  onClose,
  filters,
  sources,
  onChange,
  onApply,
}: FilterDrawerProps) {
  const [localFilters, setLocalFilters] = useState<PropertyFilters>(filters);

  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  function update(key: keyof PropertyFilters, value: any) {
    setLocalFilters((prev) => ({ ...prev, [key]: value }));
  }

  function toggleType(value: string) {
    const current = localFilters.type || [];
    const updated = current.includes(value)
      ? current.filter((t) => t !== value)
      : [...current, value];
    update("type", updated.length > 0 ? updated : undefined);
  }

  function handleApply() {
    onChange(localFilters);
    onApply();
    onClose();
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 md:hidden">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 w-full max-w-sm bg-white shadow-xl overflow-y-auto">
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Filtros</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-500 hover:bg-gray-100"
            aria-label="Fechar filtros"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-6 p-4">
          {/* Purpose */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-2">
              Finalidade
            </label>
            <div className="flex gap-2">
              <button
                onClick={() =>
                  update(
                    "purpose",
                    localFilters.purpose === "venda" ? undefined : "venda"
                  )
                }
                className={`flex-1 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                  localFilters.purpose === "venda"
                    ? "border-brand-600 bg-brand-50 text-brand-700"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                Comprar
              </button>
              <button
                onClick={() =>
                  update(
                    "purpose",
                    localFilters.purpose === "aluguel" ? undefined : "aluguel"
                  )
                }
                className={`flex-1 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                  localFilters.purpose === "aluguel"
                    ? "border-amber-500 bg-amber-50 text-amber-700"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                Alugar
              </button>
            </div>
          </div>

          {/* Sort */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-2">
              Ordenar por
            </label>
            <select
              value={localFilters.sort || "created_at_desc"}
              onChange={(e) =>
                update("sort", e.target.value === "created_at_desc" ? undefined : e.target.value)
              }
              className="input-field"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Neighborhood */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-2">
              Bairro
            </label>
            <select
              value={localFilters.neighborhood || ""}
              onChange={(e) =>
                update("neighborhood", e.target.value || undefined)
              }
              className="input-field"
            >
              <option value="">Todos os bairros</option>
              {NEIGHBORHOODS_OF_JIPARANA.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>

          {/* Price Range */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-2">
              Faixa de preço
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                placeholder="Mínimo"
                value={localFilters.min_price ?? ""}
                onChange={(e) =>
                  update(
                    "min_price",
                    e.target.value ? Number(e.target.value) : undefined
                  )
                }
                className="input-field"
              />
              <input
                type="number"
                placeholder="Máximo"
                value={localFilters.max_price ?? ""}
                onChange={(e) =>
                  update(
                    "max_price",
                    e.target.value ? Number(e.target.value) : undefined
                  )
                }
                className="input-field"
              />
            </div>
          </div>

          {/* Property Type */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-2">
              Tipo de imóvel
            </label>
            <div className="flex flex-wrap gap-2">
              {PROPERTY_TYPES_FILTER.map((t) => (
                <button
                  key={t.value}
                  onClick={() => toggleType(t.value)}
                  className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                    (localFilters.type || []).includes(t.value)
                      ? "border-brand-600 bg-brand-50 text-brand-700"
                      : "border-gray-300 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Bedrooms */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-2">
              Dormitórios
            </label>
            <div className="flex gap-2">
              {[1, 2, 3, 4].map((n) => (
                <button
                  key={n}
                  onClick={() =>
                    update(
                      "min_bedrooms",
                      localFilters.min_bedrooms === n ? undefined : n
                    )
                  }
                  className={`flex-1 rounded-lg border px-3 py-2 text-sm transition-colors ${
                    localFilters.min_bedrooms === n
                      ? "border-brand-600 bg-brand-50 text-brand-700"
                      : "border-gray-300 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {n}+
                </button>
              ))}
            </div>
          </div>

          {/* Parking */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-2">
              Vagas
            </label>
            <div className="flex gap-2">
              {[1, 2, 3].map((n) => (
                <button
                  key={n}
                  onClick={() =>
                    update(
                      "min_parking",
                      localFilters.min_parking === n ? undefined : n
                    )
                  }
                  className={`flex-1 rounded-lg border px-3 py-2 text-sm transition-colors ${
                    localFilters.min_parking === n
                      ? "border-brand-600 bg-brand-50 text-brand-700"
                      : "border-gray-300 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {n}+
                </button>
              ))}
            </div>
          </div>

          {/* Min Area */}
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-2">
              Área mínima (m²)
            </label>
            <input
              type="number"
              placeholder="Ex: 50"
              value={localFilters.min_area ?? ""}
              onChange={(e) =>
                update(
                  "min_area",
                  e.target.value ? Number(e.target.value) : undefined
                )
              }
              className="input-field"
            />
          </div>

          {/* Is New */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-gray-700">
              Apenas imóveis novos
            </label>
            <button
              onClick={() =>
                update("is_new", localFilters.is_new ? undefined : true)
              }
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                localFilters.is_new ? "bg-brand-600" : "bg-gray-300"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  localFilters.is_new ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>

          {/* Source */}
          {sources.length > 0 && (
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">
                Imobiliária
              </label>
              <select
                value={localFilters.source_id || ""}
                onChange={(e) =>
                  update("source_id", e.target.value || undefined)
                }
                className="input-field"
              >
                <option value="">Todas</option>
                {sources.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-4">
          <button onClick={handleApply} className="btn-primary w-full">
            Aplicar filtros
          </button>
        </div>
      </div>
    </div>
  );
}
