"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getStats, getSources, formatDateTime } from "@/services/api";
import type { StatsResponse, Source } from "@/types";

export default function ComoFuncionaPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [statsData, sourcesData] = await Promise.all([
          getStats(),
          getSources(),
        ]);
        setStats(statsData);
        setSources(sourcesData.data);
      } catch {
        // Silently fail - data is optional on this page
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="container-page py-8 sm:py-12">
      {/* Hero */}
      <div className="mx-auto max-w-2xl text-center mb-12">
        <h1 className="text-3xl font-bold text-gray-900">Como funciona</h1>
        <p className="mt-3 text-base text-gray-500 leading-relaxed">
          Entenda como o Imóveis Ji-Paraná reúne imóveis de várias imobiliárias
          em um só lugar.
        </p>
      </div>

      <div className="mx-auto max-w-3xl space-y-10">
        {/* Section: O que é */}
        <section className="rounded-xl border border-gray-200 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            O que é o Imóveis Ji-Paraná?
          </h2>
          <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
            Somos um <strong>agregador de imóveis</strong> — coletamos
            automaticamente os anúncios das principais imobiliárias de
            Ji-Paraná e os reunimos em um único portal. Você pode buscar,
            comparar e encontrar o imóvel ideal sem precisar visitar o site de
            cada imobiliária separadamente.
          </p>
        </section>

        {/* Section: Atualização */}
        <section className="rounded-xl border border-gray-200 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            Frequência de atualização
          </h2>
          <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
            Os dados são coletados automaticamente <strong>2 vezes ao dia</strong>, às{" "}
            <strong>12h</strong> e às <strong>18h</strong>. Isso garante que os
            imóveis mais recentes apareçam rapidamente no portal e que imóveis
            já vendidos ou alugados sejam removidos.
          </p>
          <div className="mt-4 flex items-center gap-2 text-xs text-gray-400">
            {stats?.updated_at && (
              <>
                <span>Última atualização geral:</span>
                <span className="font-medium text-gray-500">
                  {formatDateTime(stats.updated_at)}
                </span>
              </>
            )}
          </div>
        </section>

        {/* Section: Imobiliárias */}
        <section className="rounded-xl border border-gray-200 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            Imobiliárias monitoradas
          </h2>
          <p className="text-sm sm:text-base text-gray-600 leading-relaxed mb-4">
            Atualmente monitoramos as seguintes imobiliárias de Ji-Paraná:
          </p>

          {loading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-10 rounded-lg bg-gray-100" />
              ))}
            </div>
          ) : sources.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {sources.map((source) => (
                <div
                  key={source.id}
                  className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3"
                >
                  {source.logo_url ? (
                    <img
                      src={source.logo_url}
                      alt={source.name}
                      className="h-8 w-8 rounded object-contain"
                    />
                  ) : (
                    <div className="flex h-8 w-8 items-center justify-center rounded bg-gray-200 text-xs font-semibold text-gray-500">
                      {source.name.charAt(0)}
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {source.name}
                    </p>
                    {source.website && (
                      <a
                        href={source.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-brand-600 hover:text-brand-800 hover:underline"
                      >
                        Visitar site
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              Dados das imobiliárias não disponíveis no momento.
            </p>
          )}

          {stats && (
            <p className="mt-4 text-sm text-gray-500">
              Total de <strong>{stats.total_properties}</strong> imóveis
              cadastrados de <strong>{stats.total_sources}</strong> imobiliárias
              diferentes.
            </p>
          )}
        </section>

        {/* Section: Selo Novo */}
        <section className="rounded-xl border border-gray-200 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            Sobre o selo &ldquo;Novo&rdquo;
          </h2>
          <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
            Imóveis marcados com o selo <span className="badge-new">Novo</span>{" "}
            foram adicionados ao portal nas últimas 24 horas. É uma forma de
            destacar os imóveis que acabaram de ser coletados das imobiliárias,
            ajudando você a encontrar as novidades mais rapidamente.
          </p>
        </section>

        {/* Section: Disclaimer */}
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-amber-900 mb-3">
            Aviso importante
          </h2>
          <div className="text-sm sm:text-base text-amber-800 leading-relaxed space-y-2">
            <p>
              O Imóveis Ji-Paraná é um agregador de anúncios. Não somos uma
              imobiliária e não realizamos visitas, negociações ou contratos.
            </p>
            <p>
              <strong>Preços e disponibilidade</strong> estão sujeitos a
              alterações sem aviso prévio. Sempre confirme as informações
              diretamente com a imobiliária de origem antes de tomar qualquer
              decisão.
            </p>
            <p>
              Os dados são coletados automaticamente e podem conter
              divergências em relação ao anúncio original.
            </p>
          </div>
        </section>

        {/* CTA */}
        <div className="text-center py-6">
          <p className="text-sm text-gray-500 mb-4">
            Pronto para encontrar seu imóvel?
          </p>
          <Link href="/imoveis" className="btn-primary">
            Ver imóveis disponíveis
          </Link>
        </div>
      </div>
    </div>
  );
}
