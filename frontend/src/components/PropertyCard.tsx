import Link from "next/link";
import type { Property } from "@/types";
import { formatPrice, formatArea, PROPERTY_TYPE_LABELS, timeAgo } from "@/services/api";

interface PropertyCardProps {
  property: Property;
}

export default function PropertyCard({ property }: PropertyCardProps) {
  const {
    id,
    title,
    price,
    rent_price,
    purpose,
    type,
    bedrooms,
    bathrooms,
    parking_spots,
    area_total,
    neighborhood,
    source,
    images,
    is_new,
    updated_at,
  } = property;

  const mainImage =
    images && images.length > 0
      ? images[0].thumb_url || images[0].url
      : null;

  return (
    <Link href={`/imoveis/${id}`} className="card group block">
      {/* Image */}
      <div className="relative aspect-[4/3] overflow-hidden bg-gray-100">
        {mainImage ? (
          <img
            src={mainImage}
            alt={title}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <svg
              className="h-12 w-12 text-gray-300"
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
          </div>
        )}

        {/* Badges */}
        <div className="absolute left-2 top-2 flex flex-wrap gap-1">
          <span
            className={`badge-purpose ${purpose} text-[11px] uppercase tracking-wider`}
          >
            {purpose === "venda" ? "Venda" : "Aluguel"}
          </span>
          {type && (
            <span className="badge bg-gray-900/70 text-white text-[11px]">
              {PROPERTY_TYPE_LABELS[type] || type}
            </span>
          )}
          {is_new && <span className="badge-new text-[11px]">Novo</span>}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Price */}
        <div className="mb-1">
          <p className="text-xl font-bold text-gray-900">
            {formatPrice(price)}
          </p>
          {purpose === "aluguel" && rent_price && (
            <p className="text-sm text-gray-500">
              + {formatPrice(rent_price)} de aluguel
            </p>
          )}
        </div>

        {/* Title */}
        <p className="text-sm font-medium text-gray-800 line-clamp-1 mb-2">
          {title || `${PROPERTY_TYPE_LABELS[type] || type} em ${neighborhood || "Ji-Paraná"}`}
        </p>

        {/* Attributes */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 mb-2">
          {neighborhood && (
            <span className="flex items-center gap-1">
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {neighborhood}
            </span>
          )}
          {bedrooms > 0 && (
            <span>
              {bedrooms} quarto{bedrooms > 1 ? "s" : ""}
            </span>
          )}
          {parking_spots > 0 && (
            <span>
              {parking_spots} vaga{parking_spots > 1 ? "s" : ""}
            </span>
          )}
          {area_total && (
            <span>{formatArea(area_total)}</span>
          )}
        </div>

        {/* Source */}
        <div className="flex items-center justify-between pt-2 border-t border-gray-100">
          <div className="flex items-center gap-1.5">
            {source?.logo_url ? (
              <img
                src={source.logo_url}
                alt={source.name}
                className="h-4 w-4 rounded object-contain"
              />
            ) : (
              <div className="h-4 w-4 rounded bg-gray-200" />
            )}
            <span className="text-xs text-gray-400">{source?.name || "Imobiliária"}</span>
          </div>
          <span className="text-[11px] text-gray-400">
            {timeAgo(updated_at)}
          </span>
        </div>
      </div>
    </Link>
  );
}
