export interface Coordinate {
  lat: number
  lng: number
}

export type Provider = "amap" | "mapbox" | "baidu" | "google"
export type CostSignal = "free" | "low" | "medium" | "high" | "unknown"
export type Confidence = "high" | "medium" | "low"
export type BudgetBasis =
  | "per_person"
  | "per_party"
  | "per_room_per_night"
  | "per_day"
  | "per_trip"

export interface NormalizedPlace {
  id: string
  name: string
  coordinate: Coordinate | null
  address: string | null
  category: string | null
  provider: Provider
}

export interface BudgetBand {
  currency: string
  low: number
  high: number
  confidence: Confidence
  basis: BudgetBasis
}

export interface BudgetSummary {
  currency: string
  transport: BudgetBand
  stay: BudgetBand
  food: BudgetBand
  attractions: BudgetBand
  other: BudgetBand
  total: BudgetBand
  user_budget: number
  overrun_flag: boolean
}

export interface DiscoveryCard {
  id: string
  name: string
  reason: string
  category: string
  tags: string[]
  suggested_duration_minutes: number
  cost_signal: CostSignal
  cost_estimate: BudgetBand | null
  image_url: string | null
  reservation_hint: string | null
  place: NormalizedPlace | null
  enrichment_status: "complete" | "partial" | "minimal"
}

export interface AreaSummary {
  id: string
  name: string
  vibe_tags: string[]
  note: string
  center: Coordinate
}

export interface FoodSummary {
  id: string
  name: string
  category: string
  description: string
  image_url: string | null
}

export interface SourceNote {
  provider: string
  url: string | null
  note: string
}

export interface DiscoveryOutput {
  cards: DiscoveryCard[]
  food_summaries: FoodSummary[]
  area_summaries: AreaSummary[]
  budget_estimate: BudgetSummary
  source_notes: SourceNote[]
}

export interface SampleHotel {
  name: string
  style: string
  price_band: BudgetBand
  place: NormalizedPlace
}

export interface StayOption {
  id: string
  area: AreaSummary
  fit_reason: string
  price_band: BudgetBand
  sample_hotels: SampleHotel[]
}

export interface StayRecommendation {
  primary: StayOption
  alternatives: StayOption[]
  user_override_id: string | null
}

export interface ValidatorIssue {
  code: string
  severity: "warning" | "error"
  scope: Record<string, unknown>
  message: string
  suggested_action: string | null
}

export interface ItinerarySegment {
  type:
    | "attraction"
    | "food"
    | "transit"
    | "rest"
    | "hotel_checkin"
    | "hotel_checkout"
    | "hotel_return"
  start_time: string
  end_time: string
  place: NormalizedPlace | null
  card_ref: string | null
  description: string
  cost_estimate: BudgetBand | null
}

export interface ItineraryDay {
  day_index: number
  date: string
  segments: ItinerarySegment[]
  notes: string[]
}

export interface Itinerary {
  id: string
  session_id: string
  days: ItineraryDay[]
  budget: BudgetSummary
  validator_issues: ValidatorIssue[]
  version: number
}

export interface HardConstraints {
  departure_city: string
  destination_city: string
  destination_country_code: string
  departure_date: string
  duration_days: number
  traveler_count: number
  total_budget: number
  currency: string
}

export interface Preference {
  area_vibe: string
  quiet_vs_lively: "quiet" | "balanced" | "lively"
  stay_type: "hotel" | "homestay" | "flexible"
  willing_to_change_hotels: boolean
  intercity_transport_preference: "rail" | "flight" | "flexible"
  early_departure_tolerance: "low" | "medium" | "high"
  transfer_tolerance: "low" | "medium" | "high"
  pay_more_to_save_time: boolean
}

export interface AdjustmentRequest {
  raw_text: string
  type: "A" | "B" | "C" | "unknown"
  confidence: number
  target_scope:
    | "day"
    | "segment"
    | "stay"
    | "transport"
    | "budget"
    | "duration"
    | "destination"
    | "traveler_count"
    | "none"
  proposed_change: string | null
}

export interface ConversationTurn {
  id: string
  raw_text: string
  classification: AdjustmentRequest | null
  created_at: string
}

export interface DiscoveryState {
  payload: DiscoveryOutput | null
  selected_card_ids: string[]
}

export interface PlanningSession {
  session_id: string
  hard_constraints: HardConstraints
  discovery_state: DiscoveryState | null
  preferences: Preference | null
  stay_recommendation: StayRecommendation | null
  transport_recommendation: unknown | null
  itinerary: Itinerary | null
  conversation_history: Array<ConversationTurn | Record<string, unknown>>
  validator_issues: ValidatorIssue[]
  parent_session_id: string | null
  snapshot_label: string | null
  status: "active" | "archived"
  created_at: string
  updated_at: string
}

export interface PlanningProgressEvent {
  stage: string
  status: "start" | "started" | "finish" | "completed" | "skipped" | "failed" | "error"
  message: string
  payload?: Record<string, unknown>
}

// Legacy exports keep the old Next.js routes compiling until Task 4 deletes them.
export interface UserPreferences {
  destination: string
  departureCity: string
  departureDate: string
  days: number
  totalBudget: number
  accommodationDescription: string
  experienceDescription: string
}

export type CardSection = "experience" | "transport" | "food"

export interface AttractionCard {
  id: string
  name: string
  section: CardSection
  description: string
  estimatedCost: string
  imageUrl: string
  tags: string[]
}

export interface DiscoverSections {
  experience: AttractionCard[]
  transport: AttractionCard[]
  food: AttractionCard[]
}

export interface Activity {
  id: string
  time: string
  endTime?: string
  place: string
  description: string
  type: "attraction" | "food" | "transport" | "hotel" | "free"
  estimatedCost?: number
  tips?: string
}

export interface DayPlan {
  day: number
  date: string
  title: string
  activities: Activity[]
  totalCost: number
}

export interface BudgetBreakdown {
  transport: number
  accommodation: number
  food: number
  attractions: number
  other: number
  total: number
}

export interface TravelPlan {
  id: string
  preferences: UserPreferences
  selectedAttractions: AttractionCard[]
  days: DayPlan[]
  budget: BudgetBreakdown
  tips: string[]
  createdAt: string
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  timestamp: string
}
