"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import PropertyCard from "@/components/PropertyCard";
import FilterBar from "@/components/FilterBar";
import FilterDrawer from "@/components/FilterDrawer";
import ActiveFilters from "@/components/ActiveFilters";
import Pagination from "@/components/Pagination";
import LoadingSpinner from "@/components/LoadingSpinner";
import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";

import { getProperties, getSources, formatDateTime } from "@/services/api";
import type { Property, PropertyFilters, Source, PaginationMeta } from "@/types";

function ImoveisContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Derive filters from URL
  const filtersFromUrl = useCallback((): PropertyFilters => {
    const typeParam = searchParams.get("type");
    return {
      search: searchParams.get("search") || undefined,
      purpose: (searchParams.get("purpose") as "venda" | "aluguel") || undefined,
      type: typeParam ? typeParam.split(",") : undefined,
      neighborhood: searchParams.get("neighborhood") || undefined,
      min_price: searchParams.get("min_price")
        ? Number(searchParams.get("min_price"))
        : undefined,
      max_price: searchParams.get("max_price")
        ? Number(searchParams.get("max_price"))
        : undefined,
      min_bedrooms: searchParams.get("min_bedrooms")
        ? Number(searchParams.get("min_bedrooms"))
        : undefined,
      min_parking: searchParams.get("min_parking")
        ? Number(searchParams.get("min_parking"))
        : undefined,
      min_area: searchParams.get("min_area")
        ? Number(searchParams.get("min_area"))
        : undefined,
      source_id: searchParams.get("source_id") || undefined,
      is_new: searchParams.get("is_new") === "true" || undefined,
      sort: searchParams.get("sort") || undefined,
      page: searchParams.get("page") ? Number(searchParams.get("page")) : 1,
      per_page: 24,
    };
  }, [searchParams]);

  const [filters, setFilters] = useState<PropertyFilters>(filtersFromUrl);
  const [properties, setProperties] = useState<Property[]>([]);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // Sync filters with URL
  function syncUrl(newFilters: PropertyFilters) {
    const params = new URLSearchParams();
    Object.entries(newFilters).forEach(([key, value]) => {
      if (value === undefined || value === null) return;
      if (key === "type" && Array.isArray(value) && value.length > 0) {
        params.set(key, value.join(","));
      } else if (key !== "per_page") {
        params.set(key, String(value));
      }
    });
    const qs = params.toString();
    router.push(`/imoveis${qs ? `?${qs}` : ""}`, { scroll: false });
  }

  function handleFilterChange(newFilters: PropertyFilters) {
    setFilters(newFilters);
    syncUrl(newFilters);
  }

  function handleRemoveFilter(key: keyof PropertyFilters) {
    const updated = { ...filters };
    delete updated[key];
    // If removing type, we need to clear the entire array
    if (key === "type") {
      delete updated.type;
    }
    setFilters(updated);
    syncUrl(updated);
  }

  function handleClearAll() {
    setFilters({ page: 1, per_page: 24 });
    router.push("/imoveis", { scroll: false });
  }

  function handlePageChange(page: number) {
    const updated = { ...filters, page };
    setFilters(updated);
    syncUrl(updated);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // Fetch sources once
  useEffect(() => {
    getSources()
      .then((res) => setSources(res.data))
      .catch(() => {});
  }, []);

  // Fetch properties when filters change
  useEffect(() => {
    setLoading(true);
    setError(false);

    getProperties(filters)
      .then((res) => {
        setProperties(res.data);
        setMeta(res.meta);
        setLastUpdated(new Date().toISOString());
      })
      .catch(() => {
        setError(true);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [filters, searchParams]);

  const totalText = meta
    ? `${meta.total} imóvel${meta.total !== 1 ? "is" : ""} encontrado${meta.total !== 1 ? "s" : ""}`
    : "";

  const searchTerm = filters.search;

  return (
    <div className="container-page py-6 sm:py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
          {searchTerm
            ? `Resultados para "${searchTerm}"`
            : "Imóveis em Ji-Paraná"}
        </h1>
        {meta && !loading && (
          <p className="text-sm text-gray-500 mt-1">
            {totalText}
            {lastUpdated && (
              <span className="ml-2 text-gray-400">
                &middot; Atualizado em {formatDateTime(lastUpdated)}
              </span>
            )}
          </p>
        )}
      </div>

      {/* Mobile: filter toggle + sort */}
      <div className="flex items-center gap-2 mb-4 lg:hidden">
        <button
          onClick={() => setDrawerOpen(true)}
          className="btn-secondary flex-1 justify-center gap-2"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
          Filtros
        </button>
      </div>

      {/* Active filter chips */}
      <ActiveFilters
        filters={filters}
        onRemove={handleRemoveFilter}
        onClearAll={handleClearAll}
      />

      <div className="flex gap-8">
        {/* Desktop Filter Sidebar */}
        <FilterBar
          filters={filters}
          sources={sources}
          onChange={handleFilterChange}
        />

        {/* Content */}
        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="py-16">
              <LoadingSpinner size="lg" />
            </div>
          ) : error ? (
            <ErrorState
              message="Não foi possível carregar os imóveis. Verifique se a API está rodando."
              onRetry={() => {
                setLoading(true);
                setError(false);
                getProperties(filters)
                  .then((res) => {
                    setProperties(res.data);
                    setMeta(res.meta);
                  })
                  .catch(() => setError(true))
                  .finally(() => setLoading(false));
              }}
            />
          ) : properties.length === 0 ? (
            <EmptyState
              title="Nenhum imóvel encontrado"
              message="Tente ajustar os filtros ou ampliar a busca."
              actionLabel="Limpar filtros"
              actionHref="/imoveis"
            />
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
                {properties.map((property) => (
                  <PropertyCard key={property.id} property={property} />
                ))}
              </div>
              {meta && (
                <Pagination
                  currentPage={meta.current_page}
                  lastPage={meta.last_page}
                  total={meta.total}
                  onPageChange={handlePageChange}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* Mobile Filter Drawer */}
      <FilterDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        filters={filters}
        sources={sources}
        onChange={handleFilterChange}
        onApply={() => {}}
      />
    </div>
  );
}

export default function ImoveisPage() {
  return (
    <Suspense fallback={<LoadingSpinner size="lg" />}>
      <ImoveisContent />
    </Suspense>
  );
}
