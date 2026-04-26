"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import SearchBar from "@/components/SearchBar";
import PropertyCard from "@/components/PropertyCard";
import LoadingSpinner from "@/components/LoadingSpinner";
import { getProperties, getStats } from "@/services/api";
import type { Property, StatsResponse } from "@/types";

export default function HomePage() {
  const router = useRouter();
  const [recentProperties, setRecentProperties] = useState<Property[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [propsRes, statsData] = await Promise.all([
          getProperties({ sort: "created_at_desc", per_page: 8 }),
          getStats(),
        ]);
        setRecentProperties(propsRes.data);
        setStats(statsData);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  function handleSearch(term: string) {
    const params = term ? `?search=${encodeURIComponent(term)}` : "";
    router.push(`/imoveis${params}`);
  }

  return (
    <div>
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-gray-900 via-gray-800 to-brand-900">
        <div className="container-page py-16 sm:py-24">
          <div className="mx-auto max-w-2xl text-center">
            <h1 className="text-3xl font-extrabold text-white sm:text-4xl lg:text-5xl">
              Encontre o imóvel ideal em{" "}
              <span className="text-brand-400">Ji-Paraná</span>
            </h1>
            <p className="mt-4 text-base sm:text-lg text-gray-300">
              Imóveis de várias imobiliárias reunidos em um só lugar. Sua busca
              pelo lar perfeito começa aqui.
            </p>

            {/* Search */}
            <div className="mt-8">
              <SearchBar onSearch={handleSearch} />
            </div>

            {/* Quick actions */}
            <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                href="/imoveis?purpose=venda"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-white/10 px-8 py-3 text-sm font-semibold text-white backdrop-blur-sm transition-all hover:bg-white/20 border border-white/20"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                Comprar
              </Link>
              <Link
                href="/imoveis?purpose=aluguel"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-white/10 px-8 py-3 text-sm font-semibold text-white backdrop-blur-sm transition-all hover:bg-white/20 border border-white/20"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Alugar
              </Link>
              <Link
                href="/novos"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-8 py-3 text-sm font-semibold text-white transition-all hover:bg-brand-700"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Novos imóveis
              </Link>
            </div>
          </div>

          {/* Stats */}
          {stats && !loading && (
            <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-4 max-w-2xl mx-auto">
              <div className="rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 px-4 py-3 text-center">
                <p className="text-2xl font-bold text-white">
                  {stats.total_properties}
                </p>
                <p className="text-xs text-gray-300">Imóveis</p>
              </div>
              <div className="rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 px-4 py-3 text-center">
                <p className="text-2xl font-bold text-white">
                  {stats.total_sources}
                </p>
                <p className="text-xs text-gray-300">Imobiliárias</p>
              </div>
              <div className="rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 px-4 py-3 text-center">
                <p className="text-2xl font-bold text-white">
                  {stats.by_purpose.venda}
                </p>
                <p className="text-xs text-gray-300">Venda</p>
              </div>
              <div className="rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 px-4 py-3 text-center">
                <p className="text-2xl font-bold text-white">
                  {stats.by_purpose.aluguel}
                </p>
                <p className="text-xs text-gray-300">Aluguel</p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Recent Properties */}
      <section className="py-12 sm:py-16">
        <div className="container-page">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                Imóveis Novos
              </h2>
              <p className="mt-1 text-sm text-gray-500">
                Últimos imóveis adicionados ao portal
              </p>
            </div>
            <Link
              href="/novos"
              className="btn-ghost hidden sm:inline-flex gap-1"
            >
              Ver todos
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          </div>

          {loading ? (
            <LoadingSpinner size="lg" />
          ) : error ? (
            <div className="rounded-xl bg-red-50 border border-red-200 p-6 text-center">
              <p className="text-sm text-red-600">
                Não foi possível carregar os imóveis. Verifique se a API está
                rodando em localhost:8000.
              </p>
            </div>
          ) : recentProperties.length === 0 ? (
            <div className="rounded-xl bg-gray-50 border border-gray-200 p-12 text-center">
              <p className="text-gray-500">
                Nenhum imóvel encontrado. Em breve novidades!
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {recentProperties.map((property) => (
                <PropertyCard key={property.id} property={property} />
              ))}
            </div>
          )}

          <div className="mt-8 text-center sm:hidden">
            <Link href="/novos" className="btn-secondary">
              Ver todos os imóveis novos
            </Link>
          </div>
        </div>
      </section>

      {/* Info Section */}
      <section className="border-t border-gray-100 bg-gray-50 py-12 sm:py-16">
        <div className="container-page">
          <div className="mx-auto max-w-3xl text-center">
            <h2 className="text-2xl font-bold text-gray-900">
              Como funciona?
            </h2>
            <p className="mt-4 text-sm sm:text-base text-gray-500 leading-relaxed">
              O <strong>Imóveis Ji-Paraná</strong> é um agregador de imóveis.
              Coletamos automaticamente os imóveis disponíveis nas principais
              imobiliárias de Ji-Paraná e reunimos tudo em um só lugar para
              facilitar sua busca.
            </p>

            <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-3">
              <div className="rounded-xl bg-white border border-gray-200 p-6 text-left">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-100 text-brand-600">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">
                  Encontre
                </h3>
                <p className="text-sm text-gray-500">
                  Busque por bairro, tipo ou faixa de preço. Milhares de
                  imóveis em um só lugar.
                </p>
              </div>
              <div className="rounded-xl bg-white border border-gray-200 p-6 text-left">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-100 text-brand-600">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5-5m0 0l5 5m-5-5v12" />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">
                  Compare
                </h3>
                <p className="text-sm text-gray-500">
                  Veja fotos, preços e detalhes lado a lado de diferentes
                  imobiliárias.
                </p>
              </div>
              <div className="rounded-xl bg-white border border-gray-200 p-6 text-left">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-100 text-brand-600">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-1">
                  Atualizado
                </h3>
                <p className="text-sm text-gray-500">
                  Dados atualizados 2 vezes ao dia. Imóveis novos e removidos
                  automaticamente.
                </p>
              </div>
            </div>

            <div className="mt-8">
              <Link href="/como-funciona" className="btn-primary">
                Saiba mais
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
