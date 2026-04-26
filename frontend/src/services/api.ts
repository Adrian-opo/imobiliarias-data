// ============================================================
// Serviço de API - Imóveis Ji-Paraná
// ============================================================

import type {
  Property,
  PropertyListResponse,
  PropertyDetailResponse,
  PropertyFilters,
  Source,
  StatsResponse,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    next: { revalidate: 300 }, // 5 min revalidation
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new ApiError(
      `Erro ao buscar dados: ${res.status} ${res.statusText}`,
      res.status,
      errorBody
    );
  }

  return res.json();
}

type BackendSource = {
  id: string;
  name: string;
  base_url: string;
  platform: string;
  is_active: boolean;
  created_at?: string;
};

type BackendPropertyImage = {
  id: string;
  url: string;
  position: number;
};

type BackendPropertyListItem = {
  id: string;
  source_id: string;
  source_property_id: string;
  source_url: string;
  business_type: string;
  property_type: string;
  title?: string | null;
  price?: number | null;
  condominium_fee?: number | null;
  neighborhood?: string | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  garage_spaces?: number | null;
  total_area?: number | null;
  built_area?: number | null;
  status: string;
  is_new: boolean;
  first_seen_at: string;
  last_seen_at: string;
  thumbnail_url?: string | null;
  source?: BackendSource | null;
};

type BackendPropertyDetail = BackendPropertyListItem & {
  description?: string | null;
  iptu?: number | null;
  city?: string | null;
  state?: string | null;
  address_text?: string | null;
  suites?: number | null;
  land_area?: number | null;
  published_at_source?: string | null;
  last_scraped_at?: string;
  created_at?: string;
  updated_at?: string;
  images?: BackendPropertyImage[];
};

type BackendPropertyListResponse = {
  items: BackendPropertyListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

type BackendStatsResponse = {
  total_properties: number;
  total_sources?: number;
  by_type: Record<string, number>;
  by_neighborhood: Record<string, number>;
  by_business_type: Record<string, number>;
  new_last_24h?: number;
  new_last_3d?: number;
  new_last_7_days: number;
  updated_at?: string;
};

function mapPurpose(value?: string | null): Property["purpose"] {
  return value === "rent" ? "aluguel" : "venda";
}

function mapStatus(value?: string | null): Property["status"] {
  if (value === "removed" || value === "inactive") return "indisponivel";
  return "disponivel";
}

function mapSource(source?: BackendSource | null): Source {
  return {
    id: source?.id || "",
    name: source?.name || "Imobiliária",
    slug: (source?.name || "imobiliaria")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, ""),
    logo_url: null,
    website: source?.base_url || null,
    active: source?.is_active ?? true,
  };
}

function mapProperty(item: BackendPropertyListItem | BackendPropertyDetail): Property {
  const images = "images" in item && item.images
    ? item.images.map((image) => ({
        id: image.id,
        url: image.url,
        thumb_url: image.url,
        order: image.position,
      }))
    : item.thumbnail_url
      ? [{ id: `${item.id}-thumb`, url: item.thumbnail_url, thumb_url: item.thumbnail_url, order: 0 }]
      : [];

  return {
    id: item.id,
    source_id: item.source_id,
    external_id: item.source_property_id,
    title: item.title || "",
    description: "description" in item ? item.description || "" : "",
    price: item.price || 0,
    rent_price: null,
    condo_fee: item.condominium_fee || null,
    iptu: "iptu" in item ? item.iptu || null : null,
    purpose: mapPurpose(item.business_type),
    type: (item.property_type as Property["type"]) || "outro",
    status: mapStatus(item.status),
    bedrooms: item.bedrooms || 0,
    suites: "suites" in item ? item.suites || 0 : 0,
    bathrooms: item.bathrooms || 0,
    parking_spots: item.garage_spaces || 0,
    area_total: item.total_area || null,
    area_built: item.built_area || null,
    address: "address_text" in item ? item.address_text || "" : "",
    neighborhood: item.neighborhood || "",
    city: "city" in item ? item.city || "Ji-Paraná" : "Ji-Paraná",
    state: "state" in item ? item.state || "RO" : "RO",
    zipcode: null,
    latitude: null,
    longitude: null,
    images,
    source: mapSource(item.source),
    source_url: item.source_url,
    is_new: item.is_new,
    collected_at: "last_scraped_at" in item ? item.last_scraped_at || item.last_seen_at : item.last_seen_at,
    updated_at: "updated_at" in item ? item.updated_at || item.last_seen_at : item.last_seen_at,
    created_at: "created_at" in item ? item.created_at || item.first_seen_at : item.first_seen_at,
  };
}

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(message: string, status: number, body: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

// ============================================================
// Properties
// ============================================================

export async function getProperties(
  filters: PropertyFilters = {}
): Promise<PropertyListResponse> {
  const params = new URLSearchParams();

  if (filters.search) params.set("search", filters.search);
  if (filters.purpose)
    params.set("purpose", filters.purpose === "aluguel" ? "rent" : "sale");
  if (filters.type && filters.type.length > 0)
    params.set("type", filters.type[0]);
  if (filters.neighborhood) params.set("neighborhood", filters.neighborhood);
  if (filters.min_price !== undefined)
    params.set("min_price", String(filters.min_price));
  if (filters.max_price !== undefined)
    params.set("max_price", String(filters.max_price));
  if (filters.min_bedrooms !== undefined)
    params.set("min_bedrooms", String(filters.min_bedrooms));
  if (filters.min_parking !== undefined)
    params.set("min_parking", String(filters.min_parking));
  if (filters.min_area !== undefined)
    params.set("min_area", String(filters.min_area));
  if (filters.source_id) params.set("source_id", filters.source_id);
  if (filters.is_new !== undefined)
    params.set("is_new", filters.is_new ? "true" : "false");
  if (filters.sort) {
    const sortMap: Record<string, string> = {
      created_at_desc: "newest",
      price_asc: "price_asc",
      price_desc: "price_desc",
      area_desc: "area_desc",
      area_asc: "area_asc",
    };
    params.set("sort", sortMap[filters.sort] || filters.sort);
  }
  if (filters.page) params.set("page", String(filters.page));
  if (filters.per_page) params.set("per_page", String(filters.per_page));

  const query = params.toString();
  const response = await fetchApi<BackendPropertyListResponse>(
    `/api/v1/properties${query ? `?${query}` : ""}`
  );

  return {
    data: response.items.map(mapProperty),
    meta: {
      current_page: response.page,
      last_page: response.total_pages,
      per_page: response.page_size,
      total: response.total,
      has_more: response.page < response.total_pages,
    },
  };
}

export async function getProperty(
  id: string
): Promise<PropertyDetailResponse> {
  const response = await fetchApi<BackendPropertyDetail>(`/api/v1/properties/${id}`);
  return {
    data: mapProperty(response),
    related: [],
  };
}

// ============================================================
// Sources (Imobiliárias)
// ============================================================

export async function getSources(): Promise<{ data: Source[] }> {
  const response = await fetchApi<BackendSource[]>("/api/v1/sources");
  return {
    data: response.map(mapSource),
  };
}

// ============================================================
// Stats
// ============================================================

export async function getStats(): Promise<StatsResponse> {
  const response = await fetchApi<BackendStatsResponse>("/api/v1/stats");
  return {
    total_properties: response.total_properties,
    total_sources: response.total_sources || 0,
    new_last_24h: response.new_last_24h || 0,
    new_last_3d: response.new_last_3d || 0,
    new_last_7d: response.new_last_7_days,
    by_purpose: {
      venda: response.by_business_type.sale || 0,
      aluguel: response.by_business_type.rent || 0,
    },
    by_type: response.by_type,
    updated_at: response.updated_at || new Date().toISOString(),
  };
}

// ============================================================
// Utilitários
// ============================================================

export function formatPrice(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

export function formatArea(value: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${value} m²`;
}

export function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

export function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffHours < 1) return "menos de 1 hora";
  if (diffHours < 24) return `${diffHours}h atrás`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "ontem";
  if (diffDays < 30) return `${diffDays} dias atrás`;
  return formatDate(dateStr);
}

export const PROPERTY_TYPE_LABELS: Record<string, string> = {
  casa: "Casa",
  apartamento: "Apartamento",
  terreno: "Terreno",
  comercial: "Comercial",
  sobrado: "Sobrado",
  chacara: "Chácara",
  sitio: "Sítio",
  fazenda: "Fazenda",
  galpao: "Galpão",
  predio: "Prédio",
  outro: "Outro",
};

export const SORT_OPTIONS = [
  { value: "created_at_desc", label: "Mais recentes" },
  { value: "price_asc", label: "Menor preço" },
  { value: "price_desc", label: "Maior preço" },
  { value: "area_desc", label: "Maior área" },
  { value: "area_asc", label: "Menor área" },
] as const;

export const NEIGHBORHOODS_OF_JIPARANA = [
  "Centro",
  "Nova Brasília",
  "Jardim dos Migrantes",
  "Urupá",
  "Aeroporto",
  "Bela Vista",
  "Casa Preta",
  "Castanheira",
  "Colina Park",
  "Dom Bosco",
  "Duque de Caxias",
  "Industrial",
  "Jardim Aurélio Bernardi",
  "Jardim Esmeralda",
  "Jardim Presidencial",
  "Jotão",
  "Laranjeiras",
  "Malvinas",
  "Maringá",
  "Monte Castelo",
  "Novo Horizonte",
  "Oeste",
  "Parque São Pedro",
  "Pedrinhas",
  "Pioneiros",
  "Planalto",
  "Primavera",
  "Riachuelo",
  "Santa Clara",
  "Santa Luzia",
  "São Brás",
  "São Cristóvão",
  "São Francisco",
  "São José",
  "Teixeirão",
  "Três Marias",
  "Vale do Sol",
  "Verde",
];

export const PROPERTY_TYPES_FILTER = [
  { value: "casa", label: "Casa" },
  { value: "apartamento", label: "Apartamento" },
  { value: "terreno", label: "Terreno" },
  { value: "comercial", label: "Comercial" },
  { value: "sobrado", label: "Sobrado" },
] as const;
