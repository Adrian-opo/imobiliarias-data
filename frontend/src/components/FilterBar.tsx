"use client";

import type { PropertyFilters, Source } from "@/types";
import {
  PROPERTY_TYPES_FILTER,
  NEIGHBORHOODS_OF_JIPARANA,
  SORT_OPTIONS,
} from "@/services/api";

interface FilterBarProps {
  filters: PropertyFilters;
  sources: Source[];
  onChange: (filters: PropertyFilters) => void;
}

export default function FilterBar({
  filters,
  sources,
  onChange,
}: FilterBarProps) {
  function update(key: keyof PropertyFilters, value: any) {
    onChange({ ...filters, [key]: value, page: 1 });
  }

  function toggleType(value: string) {
    const current = filters.type || [];
    const updated = current.includes(value)
      ? current.filter((t) => t !== value)
      : [...current, value];
    update("type", updated.length > 0 ? updated : undefined);
  }

  function togglePurpose(value: "venda" | "aluguel") {
    update("purpose", filters.purpose === value ? undefined : value);
  }

  return (
    <aside className="w-72 shrink-0 hidden lg:block">
      <div className="sticky top-20 space-y-6">
        <h2 className="text-lg font-semibold text-gray-900">Filtros</h2>

        {/* Ordenação */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Ordenar por
          </label>
          <select
            value={filters.sort || "created_at_desc"}
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

        {/* Finalidade */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Finalidade
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => togglePurpose("venda")}
              className={`flex-1 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                filters.purpose === "venda"
                  ? "border-brand-600 bg-brand-50 text-brand-700"
                  : "border-gray-300 text-gray-600 hover:bg-gray-50"
              }`}
            >
              Comprar
            </button>
            <button
              onClick={() => togglePurpose("aluguel")}
              className={`flex-1 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                filters.purpose === "aluguel"
                  ? "border-amber-500 bg-amber-50 text-amber-700"
                  : "border-gray-300 text-gray-600 hover:bg-gray-50"
              }`}
            >
              Alugar
            </button>
          </div>
        </div>

        {/* Faixa de preço */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Faixa de preço
          </label>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <input
                type="number"
                placeholder="Mín"
                value={filters.min_price ?? ""}
                onChange={(e) =>
                  update("min_price", e.target.value ? Number(e.target.value) : undefined)
                }
                className="input-field"
              />
            </div>
            <div>
              <input
                type="number"
                placeholder="Máx"
                value={filters.max_price ?? ""}
                onChange={(e) =>
                  update("max_price", e.target.value ? Number(e.target.value) : undefined)
                }
                className="input-field"
              />
            </div>
          </div>
        </div>

        {/* Bairro */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Bairro
          </label>
          <select
            value={filters.neighborhood || ""}
            onChange={(e) => update("neighborhood", e.target.value || undefined)}
            className="input-field"
          >
            <option value="">Todos</option>
            {NEIGHBORHOODS_OF_JIPARANA.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </div>

        {/* Tipo de imóvel */}
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
                  (filters.type || []).includes(t.value)
                    ? "border-brand-600 bg-brand-50 text-brand-700"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Dormitórios */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Dormitórios
          </label>
          <div className="flex gap-2">
            {[1, 2, 3, 4].map((n) => (
              <button
                key={n}
                onClick={() =>
                  update("min_bedrooms", filters.min_bedrooms === n ? undefined : n)
                }
                className={`flex-1 rounded-lg border px-3 py-2 text-sm transition-colors ${
                  filters.min_bedrooms === n
                    ? "border-brand-600 bg-brand-50 text-brand-700"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {n}+
              </button>
            ))}
          </div>
        </div>

        {/* Vagas */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Vagas
          </label>
          <div className="flex gap-2">
            {[1, 2, 3].map((n) => (
              <button
                key={n}
                onClick={() =>
                  update("min_parking", filters.min_parking === n ? undefined : n)
                }
                className={`flex-1 rounded-lg border px-3 py-2 text-sm transition-colors ${
                  filters.min_parking === n
                    ? "border-brand-600 bg-brand-50 text-brand-700"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {n}+
              </button>
            ))}
          </div>
        </div>

        {/* Área mínima */}
        <div>
          <label className="text-sm font-medium text-gray-700 block mb-2">
            Área mínima (m²)
          </label>
          <input
            type="number"
            placeholder="Ex: 50"
            value={filters.min_area ?? ""}
            onChange={(e) =>
              update("min_area", e.target.value ? Number(e.target.value) : undefined)
            }
            className="input-field"
          />
        </div>

        {/* Apenas novos */}
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">
            Apenas novos
          </span>
          <button
            onClick={() => update("is_new", filters.is_new ? undefined : true)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              filters.is_new ? "bg-brand-600" : "bg-gray-300"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                filters.is_new ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        {/* Imobiliária */}
        {sources.length > 0 && (
          <div>
            <label className="text-sm font-medium text-gray-700 block mb-2">
              Imobiliária
            </label>
            <select
              value={filters.source_id || ""}
              onChange={(e) => update("source_id", e.target.value || undefined)}
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
    </aside>
  );
}
