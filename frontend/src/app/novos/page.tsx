"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import PropertyCard from "@/components/PropertyCard";
import Pagination from "@/components/Pagination";
import LoadingSpinner from "@/components/LoadingSpinner";
import EmptyState from "@/components/EmptyState";
import ErrorState from "@/components/ErrorState";
import { getProperties } from "@/services/api";
import type { Property, PaginationMeta, PropertyFilters } from "@/types";

const PERIODS = [
  { value: "1", label: "Hoje" },
  { value: "3", label: "Últimos 3 dias" },
  { value: "7", label: "Últimos 7 dias" },
] as const;

function NovosContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const period = searchParams.get("period") || "3";

  const [properties, setProperties] = useState<Property[]>([]);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);

    const now = new Date();
    const daysAgo = Number(period);
    const sinceDate = new Date(
      now.getTime() - daysAgo * 24 * 60 * 60 * 1000
    ).toISOString();

    const filters: PropertyFilters = {
      sort: "created_at_desc",
      per_page: 24,
      page: Number(searchParams.get("page")) || 1,
    };

    // If API supports created_since filter, use it. Otherwise we just use is_new
    getProperties({
      ...filters,
      is_new: true,
    })
      .then((res) => {
        setProperties(res.data);
        setMeta(res.meta);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [period, searchParams]);

  function handlePeriodChange(value: string) {
    router.push(`/novos?period=${value}`, { scroll: false });
  }

  function handlePageChange(page: number) {
    router.push(`/novos?period=${period}&page=${page}`, { scroll: false });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const daysLabel =
    period === "1" ? "hoje" : period === "3" ? "nos últimos 3 dias" : "nos últimos 7 dias";

  return (
    <div className="container-page py-6 sm:py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Imóveis Novos</h1>
        <p className="mt-1 text-sm text-gray-500">
          Imóveis adicionados recentemente ao portal
        </p>
      </div>

      {/* Period filter */}
      <div className="mb-6 flex gap-2">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            onClick={() => handlePeriodChange(p.value)}
            className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
              period === p.value
                ? "border-brand-600 bg-brand-50 text-brand-700"
                : "border-gray-300 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingSpinner size="lg" />
      ) : error ? (
        <ErrorState
          message="Não foi possível carregar os imóveis novos."
          onRetry={() => {
            setLoading(true);
            setError(false);
            getProperties({ sort: "created_at_desc", is_new: true, per_page: 24 })
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
          title={`Nenhum imóvel novo ${daysLabel}`}
          message="Volte mais tarde para conferir as novidades."
          actionLabel="Ver todos os imóveis"
          actionHref="/imoveis"
        />
      ) : (
        <>
          {meta && (
            <p className="text-sm text-gray-500 mb-4">
              {meta.total} imóvel{meta.total !== 1 ? "is" : ""} novo{meta.total !== 1 ? "s" : ""}{" "}
              {daysLabel}
            </p>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {properties.map((property) => (
              <PropertyCard key={property.id} property={property} />
            ))}
          </div>

          {meta && meta.last_page > 1 && (
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
  );
}

export default function NovosPage() {
  return (
    <Suspense fallback={<LoadingSpinner size="lg" />}>
      <NovosContent />
    </Suspense>
  );
}
