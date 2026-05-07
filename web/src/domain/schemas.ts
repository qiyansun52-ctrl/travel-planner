import { z } from "zod"

const isoDateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/)
const isoDateTimeSchema = z.string().datetime()
const timeSchema = z.string().regex(/^\d{2}:\d{2}$/)

export const CoordinateSchema = z
  .object({
    lat: z.number(),
    lng: z.number(),
  })
  .strict()

export type Coordinate = z.infer<typeof CoordinateSchema>

const ProviderSchema = z.enum(["amap", "mapbox", "baidu", "google"])

export const NormalizedPlaceSchema = z
  .object({
    id: z.string().min(1),
    name: z.string().min(1),
    // Always WGS84 once inside the system. Provider-specific raw coordinates
    // must be converted before producing this shape.
    coordinate: CoordinateSchema.nullable(),
    address: z.string().nullable(),
    category: z.string().nullable(),
    provider: ProviderSchema,
  })
  .strict()

export type NormalizedPlace = z.infer<typeof NormalizedPlaceSchema>

export const BudgetBandSchema = z
  .object({
    currency: z.string().length(3),
    low: z.number().nonnegative(),
    high: z.number().nonnegative(),
    confidence: z.enum(["high", "medium", "low"]),
    basis: z.enum(["per_person", "per_party", "per_room_per_night", "per_day", "per_trip"]),
  })
  .strict()
  .refine((band) => band.high >= band.low, {
    message: "BudgetBand.high must be greater than or equal to low",
    path: ["high"],
  })

export type BudgetBand = z.infer<typeof BudgetBandSchema>

export const NormalizedRouteSchema = z
  .object({
    from: NormalizedPlaceSchema,
    to: NormalizedPlaceSchema,
    mode: z.enum(["walk", "transit", "drive", "rail", "flight"]),
    duration_minutes: z.number().nonnegative(),
    distance_meters: z.number().nonnegative(),
    cost_estimate: BudgetBandSchema.nullable(),
    provider: ProviderSchema,
  })
  .strict()

export type NormalizedRoute = z.infer<typeof NormalizedRouteSchema>

export const DiscoveryCardSchema = z
  .object({
    id: z.string().min(1),
    name: z.string().min(1),
    reason: z.string().min(1),
    category: z.string().min(1),
    tags: z.array(z.string()),
    suggested_duration_minutes: z.number().positive(),
    cost_signal: z.enum(["free", "low", "medium", "high", "unknown"]),
    cost_estimate: BudgetBandSchema.nullable(),
    image_url: z.string().url().nullable(),
    reservation_hint: z.string().nullable(),
    place: NormalizedPlaceSchema.nullable(),
    enrichment_status: z.enum(["complete", "partial", "minimal"]),
  })
  .strict()

export type DiscoveryCard = z.infer<typeof DiscoveryCardSchema>

export const AreaSummarySchema = z
  .object({
    id: z.string().min(1),
    name: z.string().min(1),
    vibe_tags: z.array(z.string()),
    note: z.string().min(1),
    center: CoordinateSchema,
  })
  .strict()

export type AreaSummary = z.infer<typeof AreaSummarySchema>

export const FoodSummarySchema = z
  .object({
    id: z.string().min(1),
    name: z.string().min(1),
    category: z.string().min(1),
    description: z.string().min(1),
    image_url: z.string().url().nullable(),
  })
  .strict()

export type FoodSummary = z.infer<typeof FoodSummarySchema>

export const SourceNoteSchema = z
  .object({
    provider: z.string().min(1),
    url: z.string().url().nullable(),
    note: z.string().min(1),
  })
  .strict()

export type SourceNote = z.infer<typeof SourceNoteSchema>

export const BudgetSummarySchema = z
  .object({
    currency: z.string().length(3),
    transport: BudgetBandSchema,
    stay: BudgetBandSchema,
    food: BudgetBandSchema,
    attractions: BudgetBandSchema,
    other: BudgetBandSchema,
    total: BudgetBandSchema,
    user_budget: z.number().nonnegative(),
    overrun_flag: z.boolean(),
  })
  .strict()

export type BudgetSummary = z.infer<typeof BudgetSummarySchema>

export const DiscoveryOutputSchema = z
  .object({
    cards: z.array(DiscoveryCardSchema),
    food_summaries: z.array(FoodSummarySchema),
    area_summaries: z.array(AreaSummarySchema),
    budget_estimate: BudgetSummarySchema,
    source_notes: z.array(SourceNoteSchema),
  })
  .strict()

export type DiscoveryOutput = z.infer<typeof DiscoveryOutputSchema>

export const SampleHotelSchema = z
  .object({
    name: z.string().min(1),
    style: z.string().min(1),
    price_band: BudgetBandSchema,
    place: NormalizedPlaceSchema,
  })
  .strict()

export type SampleHotel = z.infer<typeof SampleHotelSchema>

export const StayOptionSchema = z
  .object({
    id: z.string().min(1),
    area: AreaSummarySchema,
    fit_reason: z.string().min(1),
    price_band: BudgetBandSchema,
    sample_hotels: z.array(SampleHotelSchema),
  })
  .strict()

export type StayOption = z.infer<typeof StayOptionSchema>

export const StayRecommendationSchema = z
  .object({
    primary: StayOptionSchema,
    alternatives: z.array(StayOptionSchema),
    user_override_id: z.string().nullable(),
  })
  .strict()

export type StayRecommendation = z.infer<typeof StayRecommendationSchema>

export const TransportLegSchema = z
  .object({
    mode: z.enum(["rail", "flight", "drive", "bus", "mixed"]),
    duration_minutes: z.number().nonnegative(),
    cost_band: BudgetBandSchema,
    note: z.string().nullable(),
  })
  .strict()

export type TransportLeg = z.infer<typeof TransportLegSchema>

export const IntracityStrategySchema = z
  .object({
    primary_mode: z.enum(["walk", "transit", "taxi", "mixed"]),
    daily_cost_band: BudgetBandSchema,
    note: z.string().nullable(),
  })
  .strict()

export type IntracityStrategy = z.infer<typeof IntracityStrategySchema>

export const TransportRecommendationSchema = z
  .object({
    arrival: TransportLegSchema,
    departure: TransportLegSchema,
    intracity: IntracityStrategySchema,
    tradeoffs: z.array(z.string()),
  })
  .strict()

export type TransportRecommendation = z.infer<typeof TransportRecommendationSchema>

export const ValidatorIssueSchema = z
  .object({
    code: z.string().min(1),
    severity: z.enum(["warning", "error"]),
    scope: z.record(z.string(), z.unknown()),
    message: z.string().min(1),
    suggested_action: z.string().nullable(),
  })
  .strict()

export type ValidatorIssue = z.infer<typeof ValidatorIssueSchema>

export const ItinerarySegmentSchema = z
  .object({
    type: z.enum([
      "attraction",
      "food",
      "transit",
      "rest",
      "hotel_checkin",
      "hotel_checkout",
      "hotel_return",
    ]),
    start_time: timeSchema,
    end_time: timeSchema,
    place: NormalizedPlaceSchema.nullable(),
    card_ref: z.string().nullable(),
    description: z.string().min(1),
    cost_estimate: BudgetBandSchema.nullable(),
  })
  .strict()

export type ItinerarySegment = z.infer<typeof ItinerarySegmentSchema>

export const ItineraryDaySchema = z
  .object({
    day_index: z.number().int().positive(),
    date: isoDateSchema,
    segments: z.array(ItinerarySegmentSchema),
    notes: z.array(z.string()),
  })
  .strict()

export type ItineraryDay = z.infer<typeof ItineraryDaySchema>

export const ItinerarySchema = z
  .object({
    id: z.string().min(1),
    session_id: z.string().min(1),
    days: z.array(ItineraryDaySchema),
    budget: BudgetSummarySchema,
    validator_issues: z.array(ValidatorIssueSchema),
    version: z.number().int().positive(),
  })
  .strict()

export type Itinerary = z.infer<typeof ItinerarySchema>

export const HardConstraintsSchema = z
  .object({
    departure_city: z.string().min(1),
    destination_city: z.string().min(1),
    destination_country_code: z.string().regex(/^[A-Z]{2}$/),
    departure_date: isoDateSchema,
    duration_days: z.number().int().positive(),
    traveler_count: z.number().int().positive(),
    total_budget: z.number().positive(),
    currency: z.string().length(3),
  })
  .strict()

export type HardConstraints = z.infer<typeof HardConstraintsSchema>

export const PreferenceSchema = z
  .object({
    area_vibe: z.string().min(1),
    quiet_vs_lively: z.enum(["quiet", "balanced", "lively"]),
    stay_type: z.enum(["hotel", "homestay", "flexible"]),
    willing_to_change_hotels: z.boolean(),
    intercity_transport_preference: z.enum(["rail", "flight", "flexible"]),
    early_departure_tolerance: z.enum(["low", "medium", "high"]),
    transfer_tolerance: z.enum(["low", "medium", "high"]),
    pay_more_to_save_time: z.boolean(),
  })
  .strict()

export type Preference = z.infer<typeof PreferenceSchema>

export const AdjustmentRequestSchema = z
  .object({
    raw_text: z.string(),
    type: z.enum(["A", "B", "C", "unknown"]),
    confidence: z.number().min(0).max(1),
    target_scope: z.enum([
      "day",
      "segment",
      "stay",
      "transport",
      "budget",
      "duration",
      "destination",
      "traveler_count",
      "none",
    ]),
    proposed_change: z.string().nullable(),
  })
  .strict()

export type AdjustmentRequest = z.infer<typeof AdjustmentRequestSchema>

export const ConversationTurnSchema = z
  .object({
    id: z.string().min(1),
    raw_text: z.string(),
    classification: AdjustmentRequestSchema.nullable(),
    created_at: isoDateTimeSchema,
  })
  .strict()

export type ConversationTurn = z.infer<typeof ConversationTurnSchema>

export const DiscoveryStateSchema = z
  .object({
    payload: DiscoveryOutputSchema.nullable(),
    selected_card_ids: z.array(z.string()),
  })
  .strict()

export type DiscoveryState = z.infer<typeof DiscoveryStateSchema>

export const PlanningSessionSchema = z
  .object({
    session_id: z.string().min(1),
    hard_constraints: HardConstraintsSchema,
    discovery_state: DiscoveryStateSchema.nullable(),
    preferences: PreferenceSchema.nullable(),
    stay_recommendation: StayRecommendationSchema.nullable(),
    transport_recommendation: TransportRecommendationSchema.nullable(),
    itinerary: ItinerarySchema.nullable(),
    conversation_history: z.array(ConversationTurnSchema).or(z.array(z.record(z.string(), z.unknown()))),
    validator_issues: z.array(ValidatorIssueSchema),
    parent_session_id: z.string().nullable(),
    snapshot_label: z.string().nullable(),
    status: z.enum(["active", "archived"]),
    created_at: isoDateTimeSchema,
    updated_at: isoDateTimeSchema,
  })
  .strict()

export type PlanningSession = z.infer<typeof PlanningSessionSchema>
