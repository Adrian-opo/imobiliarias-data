"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import PropertyCard from "@/components/PropertyCard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorState from "@/components/ErrorState";
import {
  getProperty,
  formatPrice,
  formatArea,
  formatDateTime,
  timeAgo,
  PROPERTY_TYPE_LABELS,
} from "@/services/api";
import type { Property } from "@/types";

export default function ImovelDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const [property, setProperty] = useState<Property | null>(null);
  const [related, setRelated] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selectedImage, setSelectedImage] = useState(0);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(false);

    getProperty(id)
      .then((res) => {
        setProperty(res.data);
        setRelated(res.related || []);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <LoadingSpinner size="lg" />;

  if (error) {
    return (
      <div className="container-page py-12">
        <ErrorState message="Não foi possível carregar os detalhes do imóvel." />
      </div>
    );
  }

  if (!property) return null;

  const p = property;
  const images = p.images || [];
  const purposeLabel = p.purpose === "venda" ? "Venda" : "Aluguel";
  const purposeBadgeClass =
    p.purpose === "venda" ? "bg-blue-100 text-blue-800" : "bg-amber-100 text-amber-800";

  return (
    <div className="container-page py-6 sm:py-8">
      {/* Breadcrumb */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-gray-500">
        <Link href="/" className="hover:text-gray-900 transition-colors">
          Início
        </Link>
        <span>/</span>
        <Link href="/imoveis" className="hover:text-gray-900 transition-colors">
          Imóveis
        </Link>
        <span>/</span>
        <span className="text-gray-900 line-clamp-1">
          {p.title ||
            `${PROPERTY_TYPE_LABELS[p.type] || p.type} - ${p.neighborhood || "Ji-Paraná"}`}
        </span>
      </nav>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Gallery + Description */}
        <div className="lg:col-span-2 space-y-6">
          {/* Gallery */}
          {images.length > 0 ? (
            <div className="space-y-3">
              {/* Main image */}
              <div className="relative aspect-[16/10] overflow-hidden rounded-xl bg-gray-100">
                <img
                  src={images[selectedImage]?.url}
                  alt={p.title || "Foto do imóvel"}
                  className="h-full w-full object-cover"
                />

                {/* Badges overlay */}
                <div className="absolute left-3 top-3 flex flex-wrap gap-2">
                  <span
                    className={`badge-purpose ${purposeBadgeClass} text-xs uppercase tracking-wider`}
                  >
                    {purposeLabel}
                  </span>
                  {p.is_new && (
                    <span className="badge-new text-xs">Novo</span>
                  )}
                  {p.type && (
                    <span className="badge bg-gray-900/70 text-white text-xs">
                      {PROPERTY_TYPE_LABELS[p.type] || p.type}
                    </span>
                  )}
                </div>

                {/* Image counter */}
                {images.length > 1 && (
                  <div className="absolute right-3 bottom-3 rounded-full bg-black/60 px-3 py-1 text-xs text-white">
                    {selectedImage + 1} / {images.length}
                  </div>
                )}
              </div>

              {/* Thumbnails */}
              {images.length > 1 && (
                <div className="flex gap-2 overflow-x-auto pb-2">
                  {images.map((img, index) => (
                    <button
                      key={img.id}
                      onClick={() => setSelectedImage(index)}
                      className={`relative h-16 w-24 shrink-0 overflow-hidden rounded-lg border-2 transition-colors ${
                        index === selectedImage
                          ? "border-brand-600"
                          : "border-transparent hover:border-gray-300"
                      }`}
                    >
                      <img
                        src={img.thumb_url || img.url}
                        alt={`Foto ${index + 1}`}
                        className="h-full w-full object-cover"
                        loading="lazy"
                      />
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex aspect-[16/10] items-center justify-center rounded-xl bg-gray-100">
              <div className="text-center">
                <svg
                  className="mx-auto h-12 w-12 text-gray-300"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
                <p className="mt-2 text-sm text-gray-400">
                  Sem fotos disponíveis
                </p>
              </div>
            </div>
          )}

          {/* Title & Description */}
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {p.title ||
                `${PROPERTY_TYPE_LABELS[p.type] || p.type} em ${p.neighborhood || "Ji-Paraná"}`}
            </h1>
            {p.description && (
              <p className="mt-3 text-sm sm:text-base text-gray-600 leading-relaxed whitespace-pre-line">
                {p.description}
              </p>
            )}
          </div>

          {/* Location */}
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 sm:p-6">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">
              Localização
            </h2>
            <div className="space-y-1 text-sm text-gray-600">
              {p.neighborhood && (
                <p>
                  <span className="text-gray-400">Bairro:</span>{" "}
                  {p.neighborhood}
                </p>
              )}
              {p.city && (
                <p>
                  <span className="text-gray-400">Cidade:</span> {p.city}
                  {p.state ? ` - ${p.state}` : ""}
                </p>
              )}
              {p.address && (
                <p>
                  <span className="text-gray-400">Endereço:</span>{" "}
                  {p.address}
                </p>
              )}
            </div>
          </div>

          {/* Source & External link */}
          <div className="rounded-xl border border-gray-200 p-4 sm:p-6">
            <h2 className="text-sm font-semibold text-gray-900 mb-3">
              Imobiliária de origem
            </h2>
            <div className="flex items-center gap-3 mb-3">
              {p.source?.logo_url ? (
                <img
                  src={p.source.logo_url}
                  alt={p.source.name}
                  className="h-10 w-10 rounded-lg object-contain"
                />
              ) : (
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-200 text-xs text-gray-500 font-semibold">
                  {p.source?.name?.charAt(0) || "?"}
                </div>
              )}
              <div>
                <p className="font-medium text-gray-900">{p.source?.name}</p>
                <p className="text-xs text-gray-500">
                  Coletado em {formatDateTime(p.collected_at)}
                </p>
              </div>
            </div>

            {p.source_url && (
              <a
                href={p.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary text-sm inline-flex gap-2"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                Ver no site original
              </a>
            )}

            <p className="mt-3 text-xs text-gray-400">
              Última atualização: {timeAgo(p.updated_at)} ({formatDateTime(p.updated_at)})
            </p>
          </div>
        </div>

        {/* Right sidebar: Price + Attributes */}
        <div className="space-y-6">
          {/* Price Card */}
          <div className="rounded-xl border border-gray-200 bg-white p-6 sticky top-20">
            <p className="text-3xl font-bold text-gray-900">
              {formatPrice(p.price)}
            </p>
            {p.purpose === "aluguel" && p.rent_price && (
              <p className="mt-1 text-sm text-gray-500">
                Aluguel: {formatPrice(p.rent_price)}
              </p>
            )}

            <hr className="my-4" />

            {/* Attributes table */}
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <AttributeItem
                  label="Quartos"
                  value={p.bedrooms}
                  icon={
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                    </svg>
                  }
                />
                <AttributeItem
                  label="Suítes"
                  value={p.suites}
                  icon={
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                    </svg>
                  }
                />
                <AttributeItem
                  label="Banheiros"
                  value={p.bathrooms}
                  icon={
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  }
                />
                <AttributeItem
                  label="Vagas"
                  value={p.parking_spots}
                  icon={
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                    </svg>
                  }
                />
              </div>

              <hr className="my-3" />

              <div className="space-y-2 text-sm">
                <RowItem
                  label="Área total"
                  value={formatArea(p.area_total)}
                />
                <RowItem
                  label="Área construída"
                  value={formatArea(p.area_built)}
                />
                {p.condo_fee !== null && (
                  <RowItem
                    label="Condomínio"
                    value={formatPrice(p.condo_fee)}
                  />
                )}
                {p.iptu !== null && (
                  <RowItem label="IPTU" value={formatPrice(p.iptu)} />
                )}
                <RowItem
                  label="Tipo"
                  value={PROPERTY_TYPE_LABELS[p.type] || p.type}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Related Properties */}
      {related.length > 0 && (
        <section className="mt-12 pt-8 border-t border-gray-200">
          <h2 className="text-xl font-bold text-gray-900 mb-6">
            Imóveis Relacionados
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {related.map((item) => (
              <PropertyCard key={item.id} property={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// Helper components
function AttributeItem({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-gray-50 p-3">
      <span className="text-gray-400">{icon}</span>
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="font-semibold text-gray-900">{value}</p>
      </div>
    </div>
  );
}

function RowItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  );
}
