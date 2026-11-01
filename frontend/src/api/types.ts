export type Role = 'owner' | 'admin' | 'broker' | 'customer';
export type PropertyKind = 'house' | 'commercial_building' | 'plot' | 'apartment' | 'portion' | 'pg';
export type Purpose = 'sale' | 'rent';
export type Status = 'draft' | 'published' | 'archived';
export type RoomType = 'single' | 'twin' | 'dormitory';
export type PortionKind = 'upper' | 'lower' | 'floor';
export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'won' | 'lost';

export interface PGDetails {
  room_type: RoomType; total_beds: number; available_beds: number;
  food_included: boolean; rules: Record<string, string | number | boolean | string[]>;
}
export interface PortionDetails {
  portion_kind: PortionKind; floor_number: number | null;
  separate_electricity_meter: boolean; separate_gas_meter: boolean;
  separate_water_meter: boolean; parent_property_id: string | null;
}
export interface PropertyPhoto {
  id: string; property_id: string; alt_text: string; category: 'gallery' | 'floorplan';
  width: number; height: number; byte_size: number;
  position: number; is_cover: boolean; url: string; thumbnail_url: string;
}
export interface ListingReadiness {
  ready: boolean; blockers: string[]; suggestions: string[]; score: number;
}
export interface Property {
  id: string; tenant_id: string; title: string; description: string;
  kind: PropertyKind; purpose: Purpose; status: Status; city: string;
  area_name: string; address: string; society: string; block: string;
  price_negotiable: boolean; ready_to_move: boolean; video_url: string | null;
  price: string; currency: string;
  area_sqft: string; bedrooms: number; bathrooms: number; furnished: boolean;
  photo_url: string | null; photos: PropertyPhoto[];
  amenities: string[]; highlights: string[]; contact_phone: string | null;
  latitude: number | null; longitude: number | null;
  pg: PGDetails | null; portion: PortionDetails | null;
  version: number; created_at: string; updated_at: string;
}
export type PropertyInput = Omit<Property, 'id' | 'tenant_id' | 'version' | 'photos' | 'created_at' | 'updated_at'>;
export interface Page<T> { items: T[]; total: number; page: number; size: number }
export interface Tokens { access_token: string; refresh_token: string; token_type: string }
export interface User {
  id: string; tenant_id: string; full_name: string; email: string; role: Role;
  preferences: Record<string, string | number>;
}
export interface Lead {
  id: string; tenant_id: string; property_id: string; customer_user_id: string | null;
  contact_name: string; contact_email: string; contact_phone: string | null;
  message: string; status: LeadStatus; notes: string; budget: string | null; created_at: string;
}
export type CustomerInquiry = Pick<Lead, 'id' | 'property_id' | 'message' | 'status' | 'created_at'>;
export interface Prediction {
  status: 'available' | 'insufficient_data'; reason: string | null;
  estimate: number | null; currency: string; method: string | null;
  sample_count: number; holdout_mae: number | null; pricing_basis: string;
}
export interface Recommendation {
  property: Property; score: number; reasons: string[];
}
export interface BrokerMatch {
  lead: Lead; property: Property; score: number; reasons: string[];
}
export interface Trend {
  month: string; city: string; area_name: string; kind: PropertyKind;
  median_sale_price: string | null; median_monthly_rent: string | null;
  sample_size: number; source: string;
}
export interface Forecast {
  status: string; reason: string | null;
  projected: { month: string; estimated_monthly_rent: number }[];
  method: string | null;
}

export interface Agency {
  id: string; name: string; slug: string; public_description: string;
  public_city: string; public_phone: string | null;
  public_email: string | null; published_listings: number;
}
export interface SavedSearch {
  id: string; name: string; filters: Record<string, string | number | boolean>;
  alerts_enabled: boolean; last_checked_at: string | null; created_at: string;
}
export interface SavedSearchMatches {
  search: SavedSearch; new_count: number; items: Property[];
}
export interface Viewing {
  id: string; property_id: string; preferred_at: string;
  contact_name: string; contact_phone: string; note: string;
  status: 'requested' | 'confirmed' | 'declined' | 'completed' | 'cancelled'; created_at: string;
}
