// ============================================================
// Tipos do domínio de imóveis
// ============================================================

export type PropertyPurpose = "venda" | "aluguel";

export type PropertyType =
  | "casa"
  | "apartamento"
  | "terreno"
  | "comercial"
  | "sobrado"
  | "chacara"
  | "sitio"
  | "fazenda"
  | "galpao"
  | "predio"
  | "outro";

export type PropertyStatus = "disponivel" | "vendido" | "alugado" | "indisponivel";

export interface Property {
  id: string;
  source_id: string;
  external_id: string;
  title: string;
  description: string;
  price: number;
  rent_price: number | null;
  condo_fee: number | null;
  iptu: number | null;
  purpose: PropertyPurpose;
  type: PropertyType;
  status: PropertyStatus;
  bedrooms: number;
  suites: number;
  bathrooms: number;
  parking_spots: number;
  area_total: number | null;
  area_built: number | null;
  address: string;
  neighborhood: string;
  city: string;
  state: string;
  zipcode: string | null;
  latitude: number | null;
  longitude: number | null;
  images: PropertyImage[];
  source: Source;
  source_url: string;
  is_new: boolean;
  collected_at: string;
  updated_at: string;
  created_at: string;
}

export interface PropertyImage {
  id: string;
  url: string;
  thumb_url: string | null;
  order: number;
}

export interface Source {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  website: string | null;
  active: boolean;
}

export interface PropertyListResponse {
  data: Property[];
  meta: PaginationMeta;
}

export interface PropertyDetailResponse {
  data: Property;
  related?: Property[];
}

export interface StatsResponse {
  total_properties: number;
  total_sources: number;
  new_last_24h: number;
  new_last_3d: number;
  new_last_7d: number;
  by_purpose: {
    venda: number;
    aluguel: number;
  };
  by_type: Record<string, number>;
  updated_at: string;
}

export interface PaginationMeta {
  current_page: number;
  last_page: number;
  per_page: number;
  total: number;
  has_more: boolean;
}

export interface PropertyFilters {
  search?: string;
  purpose?: PropertyPurpose;
  type?: string[];
  neighborhood?: string;
  min_price?: number;
  max_price?: number;
  min_bedrooms?: number;
  min_parking?: number;
  min_area?: number;
  source_id?: string;
  is_new?: boolean;
  sort?: string;
  page?: number;
  per_page?: number;
}
